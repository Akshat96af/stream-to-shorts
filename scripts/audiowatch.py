#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Audio-spike watcher for a GROWING recording (for live streams whose chat you cannot read: screams show in audio).

    python audiowatch.py <rec .ts> <name> [--db 7] [--floor -38] [--cooldown 30]
Every 5 s it measures the last 10 s of the file; spike = level >= median(last 3 min) + --db and above --floor.
Cuts through clipwatcher.worker (same clips/ + .json sidecars) and prints `  clip ...` lines for the Monitor.
The clip offset comes from the FILE position (not wall clock), so HLS start-up backlog can't shift it.
"""
import argparse, queue, statistics, subprocess, threading, time, types
from collections import deque
from pathlib import Path

import numpy as np

import clipwatcher as cw
from common import CFG


def file_pos(rec):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(rec)],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def level(rec, secs=10):
    """Loudness (dB): mean of the 3 loudest 0.5 s frames in the last `secs` seconds of the file."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-sseof", f"-{secs + 2}", "-i", str(rec), "-vn", "-ac", "1",
                          "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    x = x[: len(x) // 4000 * 4000].reshape(-1, 4000)
    if len(x) < 6:
        return None
    return float(np.sort(20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-6))[-3:].mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rec")
    ap.add_argument("name", help="short name used in clip file names, e.g. the streamer")
    ap.add_argument("--db", type=float, default=7, help="dB above the 3-min median")
    ap.add_argument("--floor", type=float, default=-38, help="ignore spikes quieter than this (dB)")
    ap.add_argument("--cooldown", type=int, default=30)
    a = ap.parse_args()
    rec = Path(a.rec).resolve()
    q = queue.Queue()
    wa = types.SimpleNamespace(shift=0, size="720:1280", enc=CFG["encoder"], model="base", final=False, layout="crop",
                               music="none", hook=None)
    th = threading.Thread(target=cw.worker, args=(q, wa))
    th.start()
    hist, last = deque(maxlen=36), -1e9  # 36 x 5 s = 3 min baseline
    print(f"audiowatch {a.name}: {rec.name} (+{a.db} dB over median, floor {a.floor} dB)", flush=True)
    try:
        while True:
            t = time.time()
            lv = level(rec)
            if lv is not None:
                if len(hist) >= 12:  # 1 min warm-up
                    med = statistics.median(hist)
                    if lv >= med + a.db and lv > a.floor and t - last >= a.cooldown:
                        last, pos = t, file_pos(rec)
                        print(f"[{time.strftime('%H:%M:%S')}] {a.name}: LOUD {lv:.0f} dB (median {med:.0f})", flush=True)
                        q.put((a.name, rec, t - pos, t, 0, 0, f"+{lv - med:.0f} dB loud ({lv:.0f} dB)"))
                hist.append(lv)
            time.sleep(max(0.0, 5 - (time.time() - t)))
    except KeyboardInterrupt:
        pass
    finally:
        q.put(None)
        th.join()


if __name__ == "__main__":
    main()
