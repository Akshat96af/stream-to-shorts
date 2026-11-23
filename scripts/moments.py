#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Find moments where the streamer's VOICE and FACE both react in a (growing) recording; cut them; print transcripts
and write one stacked facecam contact sheet. No LLM, cheap. Cutscene audio never moves the facecam, so it is ignored.

    python moments.py <rec.ts> <name> --cam x,y,w,h [--last 45] [--k 4]
      --cam = the streamer's webcam box as fractions of the frame, e.g. 0,0.42,0.205,0.235 (lower-left)
Output: `#n clip_name  mm:ss  +dB  motion | transcript`, and logs/moments_<name>.jpg (4x2 face frames per clip).
Cuts land in clips/ like any other clip (use finalize.py --layout facecam --cam ... --hook "..." to render).
"""
import argparse, json, queue, subprocess, threading, types
from pathlib import Path

import numpy as np

import clipwatcher as cw
import finalize


def analyse(rec, cam, last_min, frm=None):
    dur = finalize.dur(rec)
    s0 = max(0.0, dur - last_min * 60) if frm is None else frm * 60
    span = [] if frm is None else ["-t", f"{last_min * 60:.0f}"]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{s0:.1f}", *span, "-i", str(rec), "-vn", "-ac", "1", "-ar",
                          "8000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    x = x[: len(x) // 4000 * 4000].reshape(-1, 4000)                 # 0.5 s frames
    db = 20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-6)
    base = np.array([np.median(db[max(0, i - 360):i + 1]) for i in range(len(db))])  # 3 min rolling median
    ex = np.convolve(db - base, np.ones(4) / 4, "same")
    ex2 = np.array([ex[i * 4:(i + 1) * 4].mean() for i in range(len(ex) // 4)])      # per 2 s
    cx, cy, cw_, ch = cam
    v = subprocess.run(["ffmpeg", "-v", "error", "-skip_frame", "nokey", "-ss", f"{s0:.1f}", *span, "-i", str(rec), "-vf",
                        f"fps=0.5,crop=iw*{cw_}:ih*{ch}:iw*{cx}:ih*{cy},scale=48:32,format=gray", "-f", "rawvideo",
                        "-"], capture_output=True).stdout
    fr = np.frombuffer(v[: len(v) // 1536 * 1536], np.uint8).reshape(-1, 32, 48).astype(np.float32)
    mot = np.r_[0, np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))]
    n = min(len(ex2), len(mot))
    return s0, ex2[:n], mot[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rec")
    ap.add_argument("name")
    ap.add_argument("--cam", required=True)
    ap.add_argument("--last", type=float, default=45, help="analyse the last N minutes of the recording")
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--frm", type=float, default=None, help="start minute; then --last is the window length")
    a = ap.parse_args()
    rec, cam = Path(a.rec).resolve(), [float(v) for v in a.cam.split(",")]
    s0, ex, mot = analyse(rec, cam, a.last, a.frm)
    n = len(ex)
    z = lambda v: (v - v.mean()) / (v.std() + 1e-6)
    score = z(ex) + z(mot)
    used = []  # windows already cut from this recording (any earlier run)
    for p in Path("clips").glob(f"{a.name}_*.json"):
        if p.name.endswith(".words.json"):
            continue
        o = json.loads(p.read_text())
        if Path(o["rec"]).name == rec.name:
            used.append((o["start"], o["start"] + 30))
    picks = []
    for i in np.argsort(-score):
        t = s0 + i * 2.0
        if i < 90 or ex[i] < 6 or mot[i] < np.percentile(mot, 70):  # baseline warm-up, quiet, or a still face
            continue
        if any(u0 - 20 <= t <= u1 + 20 for u0, u1 in used) or any(abs(t - p) <= 60 for p in picks):
            continue
        picks.append(float(t))
        if len(picks) == a.k:
            break
    picks.sort()
    if not picks:
        print("no voice+face moments in the analysed window")
        return
    q = queue.Queue()
    wa = types.SimpleNamespace(shift=0, size="720:1280", enc="qsv", model="none", final=False, layout="crop",
                               music="none", hook=None)
    th = threading.Thread(target=cw.worker, args=(q, wa))
    th.start()
    t0 = cw.birth(rec)
    for t in picks:
        q.put((a.name, rec, t0, t0 + t, 0, 0, f"voice+face {int(t // 60)}:{int(t % 60):02d}"))
    q.put(None)
    th.join()
    names = sorted(c.stem for c in Path("clips").glob(f"{a.name}_*.mp4") if not c.name.endswith(".sheet.jpg")
                   and json.loads(c.with_suffix(".json").read_text()).get("rec") == str(rec)
                   and any(abs(json.loads(c.with_suffix(".json").read_text())["start"] + 20 - t) < 3 for t in picks))
    sheets = []
    for i, nm in enumerate(names, 1):
        meta = json.loads(Path(f"clips/{nm}.json").read_text())
        words = finalize.get_words(Path(f"clips/{nm}.mp4").resolve(), "base")
        Path(f"clips/{nm}.words.json").unlink(missing_ok=True)       # the final render re-transcribes with `small`
        txt = " ".join(w["w"] for w in words)
        flag = finalize.adult_flags(txt)
        mm = meta["start"] + 20
        print(f"#{i} {nm}  {int(mm // 60)}:{int(mm % 60):02d}  | {txt[:230] or '(no speech)'}"
              + (f"  [ADULT-FLAG: {', '.join(flag)}]" if flag else ""))
        png = Path("logs") / f"_m{i}.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{meta['start']:.1f}", "-t", "30", "-i", str(rec),
                        "-vf", f"fps=8/30,crop=iw*{cam[2]}:ih*{cam[3]}:iw*{cam[0]}:ih*{cam[1]},scale=240:160,tile=4x2",
                        "-frames:v", "1", str(png)], capture_output=True)
        sheets.append(str(png))
    if sheets:
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for s in sheets:
            cmd += ["-i", s]
        cmd += ["-filter_complex", f"vstack={len(sheets)}" if len(sheets) > 1 else "null",
                f"logs/moments_{a.name}.jpg"]
        subprocess.run(cmd, capture_output=True)
        print(f"sheet: logs/moments_{a.name}.jpg  (rows = #1..#{len(sheets)}, 4x2 facecam frames over 30 s)")


if __name__ == "__main__":
    main()
