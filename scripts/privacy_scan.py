#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Scan a folder for personal data before you share or publish it (a skill copy, a project, a support bundle).

    python privacy_scan.py [folder] [--terms "my name,my channel,@handle"] [--terms-file private_terms.txt]
Finds e-mail addresses, YouTube channel ids, user names inside file paths, API keys and tokens, phone numbers, IP
addresses, and any words you list (your name, channel name, handles). Prints file:line for each hit and exits 1 when
something is found. Keep your terms file OUTSIDE the folder you publish.
"""
import argparse, re, sys
from pathlib import Path

PATTERNS = {
    "e-mail": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "YouTube channel id": r"\bUC[A-Za-z0-9_-]{22}\b",
    "user path": r"(?:[A-Za-z]:[\\/]+Users[\\/]+|/home/|/Users/)(?!<|\{|USER|user\b|you\b|name\b|Public\b|Shared\b)[A-Za-z0-9._-]+",
    "API key / token": r"\b(?:AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,}|ya29\.[0-9A-Za-z_-]{20,})\b",
    "phone number": r"(?<![\w.])\+?\d[\d -]{8,}\d(?![\w.])",
    "IP address": r"\b(?!127\.0\.0\.1\b)(?:\d{1,3}\.){3}\d{1,3}\b",
}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
TEXT = {".py", ".md", ".txt", ".json", ".js", ".html", ".css", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".sh", ".svg", ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", default=".")
    ap.add_argument("--terms", default="", help="comma-separated private words: your name, channel, handles")
    ap.add_argument("--terms-file", help="one private word per line (keep this file outside the folder)")
    a = ap.parse_args()
    terms = [t.strip() for t in a.terms.split(",") if t.strip()]
    if a.terms_file:
        terms += [l.strip() for l in Path(a.terms_file).read_text(encoding="utf-8").splitlines() if l.strip()]
    rx = {k: re.compile(v) for k, v in PATTERNS.items()}
    rx.update({f"private term '{t}'": re.compile(re.escape(t), re.I) for t in terms})
    hits = 0
    root = Path(a.folder).resolve()
    for f in sorted(root.rglob("*")):
        if not f.is_file() or SKIP_DIRS & set(f.parts) or f.suffix.lower() not in TEXT or f.stat().st_size > 5_000_000:
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for kind, r in rx.items():
                for m in r.finditer(line):
                    if kind == "phone number" and (len(re.sub(r"\D", "", m.group())) < 10
                                                   or re.match(r"\d{4}-\d{2}-\d{2}", m.group())):
                        continue
                    hits += 1
                    print(f"{f.relative_to(root)}:{n}: {kind}: {m.group()[:60]}")
    print(f"privacy scan: {hits} finding(s) in {root}")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
