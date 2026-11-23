#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""python check_setup.py  ->  checks every tool the skill needs and prints the exact fix for anything missing."""
import importlib, shutil, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, CFG, MUSIC_DIR, SFX_DIR

ok = True


def check(label, good, fix=""):
    global ok
    print(("  OK   " if good else "  MISS ") + label + ("" if good else f"\n       fix: {fix}"))
    if not good and fix.startswith("required"):
        ok = False


print(f"stream-to-shorts by Akshat96af - setup check (work folder: {WORK})")
check("Python 3.9+", sys.version_info >= (3, 9), "required: install Python 3.10-3.12")
for tool, fix in (("ffmpeg", "required: install ffmpeg (Windows: winget install Gyan.FFmpeg; macOS: brew install ffmpeg)"),
                  ("ffprobe", "required: comes with ffmpeg"),
                  ("yt-dlp", "required for VODs: pip install yt-dlp (or winget install yt-dlp)")):
    check(tool, shutil.which(tool), fix)
for mod, fix in (("numpy", "required: pip install numpy"),
                 ("faster_whisper", "required: pip install faster-whisper==1.2.1 \"av>=14,<17\""),
                 ("streamlink", "optional (live recording): pip install streamlink")):
    try:
        importlib.import_module(mod)
        check(mod, True)
    except Exception:
        check(mod, False, fix)
enc = CFG["encoder"]
if shutil.which("ffmpeg"):
    encs = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    name = {"qsv": "h264_qsv", "nvenc": "h264_nvenc", "x264": "libx264"}.get(enc, enc)
    check(f"encoder {enc} ({name})", name in encs, 'optional: set "encoder": "x264" in sts.config.json')
check(f"music folder {MUSIC_DIR}", MUSIC_DIR.is_dir() and any(MUSIC_DIR.iterdir()),
      "optional: add your OWN licensed tracks, or render with --music none")
check(f"sfx folder {SFX_DIR} (whoosh/ riser/ hit/ pop/ shutter/)", SFX_DIR.is_dir(),
      "optional: add free-licence SFX files in those sub-folders; missing ones are skipped")
check("sts.config.json", (WORK / "sts.config.json").exists(), "optional: copy config.example.json from the skill folder")
print("READY" if ok else "NOT READY: fix the required items above")
sys.exit(0 if ok else 1)
