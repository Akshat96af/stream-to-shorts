#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Pick WHERE in a track to start so its drop lands on the clip's highlight. Pure numpy+ffmpeg, no LLM.

    python music.py              # analyse music/ -> music/index.json, print drops
    python music.py --selftest
Use: pick(clip_len=30, highlight=15) -> (track_path, start_seconds)  # ffmpeg: -ss start -i track
"""
import json, random, subprocess, sys, tempfile
from pathlib import Path

import numpy as np

from common import MUSIC_DIR as MUSIC
STEP, K = 0.5, 8  # 0.5 s energy frames; 8 frames = 4 s windows
EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".opus"}


def energy(path):
    """Loudness in dB per 0.5 s frame (mono, 8 kHz)."""
    sr = 8000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = int(sr * STEP)
    x = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-6), len(x) * STEP


def drop(e):
    """Second where loudness jumps up most and STAYS loud (the drop).
    Flat track (no jump >= 3 dB, e.g. beat from second 0) -> start of its loudest stretch."""
    if len(e) < 3 * K:
        return 0.0
    loud, best, at = np.percentile(e, 70), -1e9, None
    for i in range(K, len(e) - K):
        after = e[i:i + K].mean()
        if after >= loud and after - e[i - K:i].mean() > best:
            best, at = after - e[i - K:i].mean(), i
    if at is None or best < 3:
        at = int(np.argmax(np.convolve(e, np.ones(K) / K, "valid")))
    return at * STEP


def index(folder=MUSIC):
    f = folder / "index.json"
    idx = json.loads(f.read_text()) if f.exists() else {}
    for p in sorted(folder.glob("*")):
        if p.suffix.lower() in EXT and idx.get(p.name, {}).get("size") != p.stat().st_size:
            e, length = energy(p)  # analysed once, then cached
            idx[p.name] = {"size": p.stat().st_size, "len": round(length, 1), "drop": drop(e)}
    f.write_text(json.dumps(idx, indent=1))
    return idx


def pick(clip_len=30.0, highlight=15.0, folder=MUSIC, rng=random):
    """Random track; start it so its drop hits `highlight` seconds into the clip."""
    idx = index(folder)
    if not idx:
        return None
    ok = [n for n in idx if idx[n]["drop"] >= highlight] or list(idx)  # drop must be able to land on the moment
    name = rng.choice(sorted(ok))
    t = idx[name]
    start = min(max(0.0, t["drop"] - highlight), max(0.0, t["len"] - clip_len))
    return folder / name, round(start, 2)


def selftest():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)  # 20 s quiet pad, then 20 s loud = drop at 20 s
        subprocess.run(["ffmpeg", "-v", "error", "-y",
                        "-f", "lavfi", "-i", "anoisesrc=d=20:c=pink:a=0.03",
                        "-f", "lavfi", "-i", "anoisesrc=d=20:c=pink:a=0.6",
                        "-filter_complex", "[0][1]concat=n=2:v=0:a=1", str(d / "t.wav")], check=True)
        got = index(d)["t.wav"]
        assert 19 <= got["drop"] <= 21, got
        path, start = pick(30, 15, d)
        assert abs(start - 5) <= 1.5, start  # drop(20) - highlight(15)
        assert (d / "index.json").exists()
    print("music selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        MUSIC.mkdir(exist_ok=True)
        for k, v in index().items():
            print(f"{k}: drop at {v['drop']}s of {v['len']}s")
