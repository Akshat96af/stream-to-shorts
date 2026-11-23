#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Fast moment ranking for a long recording or video: analyse only, cut nothing (about 90 s per 2 h of video).

    python scan.py <video> <name> [--cam x,y,w,h | --full] [--frm MIN] [--win MIN] [--k 8] [--sheets]
Scores every 2 s by the streamer's voice loudness above its rolling median plus motion inside the webcam box
(--cam), or inside the whole frame (--full, for videos without a webcam). Prints the top K moments at least 90 s
apart and, with --sheets, writes logs/scan_<name>_<sec>.jpg: 8 full frames around each moment to LOOK at
(moment, faces, 18+ check, webcam position). Then cut the keepers with cut.py and render with finalize.py.
"""
import argparse, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import moments
from common import WORK, CFG


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("name")
    ap.add_argument("--cam", help="webcam box x,y,w,h as fractions of the frame")
    ap.add_argument("--full", action="store_true", help="no webcam: measure motion over the whole frame")
    ap.add_argument("--frm", type=float, default=0, help="start minute")
    ap.add_argument("--win", type=float, default=120, help="window length in minutes")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--sheets", action="store_true", help="write an 8-frame sheet per moment")
    a = ap.parse_args()
    if not a.cam and not a.full:
        raise SystemExit("give --cam x,y,w,h (webcam box) or --full (no webcam)")
    cam = [0.0, 0.0, 1.0, 1.0] if a.full else [float(v) for v in a.cam.split(",")]
    src = Path(a.video).resolve()
    s0, ex, mot = moments.analyse(src, cam, a.win, a.frm)
    z = lambda v: (v - v.mean()) / (v.std() + 1e-6)
    sc = z(ex) + z(mot)
    picks = []
    for i in np.argsort(-sc):
        t = s0 + i * 2.0
        if i < 90 or ex[i] < 6 or mot[i] < np.percentile(mot, 70) or any(abs(t - p) <= 90 for p in picks):
            continue
        picks.append(t)
        line = f"#{len(picks)} t={t:.0f}  {int(t // 3600)}:{int(t // 60 % 60):02d}:{int(t % 60):02d}  voice +{ex[i]:.1f} dB  motion {mot[i]:.1f}"
        if a.sheets:
            (WORK / "logs").mkdir(exist_ok=True)
            sheet = WORK / "logs" / f"scan_{a.name}_{int(t)}.jpg"
            span = int(CFG["clip_seconds"])
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, t - 20):.1f}", "-t", str(span), "-i", str(src),
                            "-vf", f"fps=8/{span},scale=320:-1,tile=8x1", "-frames:v", "1", str(sheet)], check=False)
            line += f"  sheet {sheet.relative_to(WORK)}"
        print(line, flush=True)
        if len(picks) == a.k:
            break
    if not picks:
        print("no strong moment in this window: try another --frm/--win or --full")


if __name__ == "__main__":
    main()
