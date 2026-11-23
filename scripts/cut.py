#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Cut one candidate moment from any local video or recording, ready for finalize.py.

    python cut.py <source video> <moment H:MM:SS or seconds> <streamer-name> [--before 20]
Writes clips/<streamer>_<sec>.mp4 (30 s low-res preview) + clips/<streamer>_<sec>.json (the sidecar finalize.py
renders from: it reads the SOURCE file again at full quality) + logs/cut_<streamer>_<sec>.jpg (8 full frames to LOOK at:
moment, faces, 18+ check, webcam position). The Short starts --before seconds ahead of the moment.
"""
import argparse, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, CFG


def secs(t):
    return sum(float(v) * 60 ** i for i, v in enumerate(reversed(str(t).split(":"))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source"); ap.add_argument("moment"); ap.add_argument("name")
    ap.add_argument("--before", type=float, default=20)
    a = ap.parse_args()
    src = Path(a.source).resolve()
    if not src.exists():
        raise SystemExit(f"no such file: {src}")
    t = secs(a.moment)
    start = max(0.0, t - a.before)
    name = f"{a.name.lower().replace(' ', '')}_{int(t)}"
    for d in ("clips", "logs"):
        (WORK / d).mkdir(exist_ok=True)
    prev = WORK / "clips" / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.2f}", "-i", str(src), "-t", "30", "-vf",
                    "scale=540:960:force_original_aspect_ratio=increase,crop=540:960", "-c:v", "libx264", "-preset",
                    "veryfast", "-crf", "28", "-c:a", "aac", str(prev)], check=True)
    prev.with_suffix(".json").write_text(json.dumps(dict(chan=a.name, rec=str(src), start=start, end=0, n=0, med=0)))
    sheet = WORK / "logs" / f"cut_{name}.jpg"
    span = int(CFG["clip_seconds"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.2f}", "-t", str(span), "-i", str(src), "-vf",
                    f"fps=8/{span},scale=400:-1,tile=4x2", "-frames:v", "1", str(sheet)], check=True)
    print(f"clip  {prev}\nsheet {sheet}  <- look at it before writing a hook")


if __name__ == "__main__":
    main()
