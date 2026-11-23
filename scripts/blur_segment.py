#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Blur part of a finished Short for a time range (rescue a good clip that shows something it must not).

    python blur_segment.py <final.mp4> <from_s> <to_s> [--area game|all|top|bottom] [--out new.mp4]
game = the lower 64 % (the gameplay part of the facecam layout), all = whole frame, top/bottom = halves.
Writes <name> blurred.mp4 next to the input (the original is kept). LOOK at the result's frames before using it.
"""
import argparse, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CFG

AREAS = {"game": (0.36, 0.64), "all": (0.0, 1.0), "top": (0.0, 0.5), "bottom": (0.5, 0.5)}
ENC = {"x264": ["-c:v", "libx264", "-preset", "slow", "-crf", "16"],
       "qsv": ["-c:v", "h264_qsv", "-global_quality", "13", "-preset", "slow"],
       "nvenc": ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("start", type=float); ap.add_argument("end", type=float)
    ap.add_argument("--area", choices=list(AREAS), default="game"); ap.add_argument("--out")
    a = ap.parse_args()
    src = Path(a.video).resolve()
    out = Path(a.out) if a.out else src.with_name(src.stem + " blurred.mp4")
    y, h = AREAS[a.area]
    vf = (f"[0:v]split[a][b];[b]crop=iw:ih*{h}:0:ih*{y},boxblur=50:6[bl];"
          f"[a][bl]overlay=0:H*{y}:enable='between(t,{a.start},{a.end})'[v]")
    for enc in dict.fromkeys([CFG["encoder"], "x264"]):
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", vf, "-map", "[v]", "-map", "0:a?",
                            *ENC.get(enc, ENC["x264"]), "-c:a", "copy", "-movflags", "+faststart", str(out)])
        if r.returncode == 0:
            print(out); return
    raise SystemExit("blur failed")


if __name__ == "__main__":
    main()
