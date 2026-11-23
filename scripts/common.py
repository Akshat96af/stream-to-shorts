# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Shared paths and settings for every stream-to-shorts script.

WORK = the user's project folder (all recordings, clips, finals, logs live here): the STS_WORK environment variable,
else the current directory. Settings come from WORK/sts.config.json (copy config.example.json from the skill folder);
anything missing falls back to DEFAULTS. The skill folder itself is never written to.
"""
import json, os, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
WORK = Path(os.environ.get("STS_WORK") or Path.cwd()).resolve()

DEFAULTS = {
    "studio_url": "",            # optional uploader only: https://studio.youtube.com/channel/<your channel id>
    "visibility": "private",     # uploads stay private until you choose public (safest default)
    "daily_cap": 10,             # max uploads per rolling 24 h; YouTube's own limit may be lower
    "encoder": "x264",           # x264 (works everywhere) | qsv (Intel iGPU) | nvenc (NVIDIA)
    "music_dir": "music",        # your own licensed tracks (none are shipped)
    "sfx_dir": "sfx",            # your own SFX, in sub-folders: whoosh/ riser/ hit/ pop/ shutter/
    "clip_seconds": 45,          # default Short length (a story with a payoff may need more)
    "whisper_model": "small",
    "quality": "balanced",        # high | balanced | fast
    "fps": 60,
    "caption_style": "pop",       # pop | clean | none
    "caption_color": "yellow",
    "caption_case": "upper",
    "caption_position": "low",
}


def load_config():
    cfg = dict(DEFAULTS)
    f = WORK / "sts.config.json"
    if f.exists():
        cfg.update(json.loads(f.read_text(encoding="utf-8")))
    return cfg


CFG = load_config()
MUSIC_DIR = (WORK / CFG["music_dir"]).resolve()
SFX_DIR = (WORK / CFG["sfx_dir"]).resolve()


# ---- authorship (stream-to-shorts by Akshat96af) ------------------------------------------------------------------
# The LICENSE allows free use and private changes, never removing the author's name or republishing the skill.
# These checks are disclosed in LICENSE section 7. They stop the tools when the notices have been stripped.
AUTHOR = "Akshat96af"
_MARK = "\u2060\u200b\u200c\u200b\u200b\u200b\u200b\u200b\u200c\u200b\u200c\u200c\u200b\u200c\u200b\u200c\u200c\u200b\u200c\u200c\u200c\u200b\u200b\u200c\u200c\u200b\u200c\u200c\u200b\u200c\u200b\u200b\u200b\u200b\u200c\u200c\u200b\u200b\u200b\u200b\u200c\u200b\u200c\u200c\u200c\u200b\u200c\u200b\u200b\u200b\u200b\u200c\u200c\u200c\u200b\u200b\u200c\u200b\u200b\u200c\u200c\u200b\u200c\u200c\u200b\u200b\u200c\u200c\u200b\u200b\u200b\u200b\u200c\u200b\u200c\u200c\u200b\u200b\u200c\u200c\u200b\u2060"  # invisible watermark (zero-width characters), also embedded in every document of the skill
_NOTICE_FILES = ("LICENSE", "SKILL.md", "README.md", "scripts/.lib/res/k7/manifest.md")


def watermark(text):
    """Decode the invisible authorship watermark hidden in a text (returns the author name, or '')."""
    zw = {"\u200b": "0", "\u200c": "1"}
    for chunk in text.split("\u2060")[1::2]:
        bits = "".join(zw.get(ch, "") for ch in chunk)
        if bits and len(bits) % 8 == 0:
            return "".join(chr(int(bits[i:i + 8], 2)) for i in range(0, len(bits), 8))
    return ""


def verify_notice():
    """Refuse to run when the authorship notices, the watermark or the notice files were removed (LICENSE 2c, 7)."""
    missing = []
    for n in _NOTICE_FILES:
        p = SKILL / n
        t = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
        if AUTHOR not in t or (n != "SKILL.md" and watermark(t) != AUTHOR):
            missing.append(n)
    if missing or watermark(_MARK) != AUTHOR:
        sys.exit("stream-to-shorts: the authorship notice of " + AUTHOR + " is missing or altered in: "
                 + ", ".join(missing or ["scripts/common.py"]) + ".\nRestore the original files from the official "
                 "repository. This skill is copyright " + AUTHOR + "; see LICENSE.")


verify_notice()
