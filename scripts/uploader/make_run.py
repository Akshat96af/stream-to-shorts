#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Build uploader/run.js from queue.json (the Playwright MCP sandbox has no fs) and record results.

    python uploader/make_run.py build [--cap 15] [--not-before "2026-01-01 18:00"]
    python uploader/make_run.py done <final mp4> [...]
Queued = approved && !done. Hard cap on uploads in the last 24 h. PUBLIC items need --not-before
(the release time, local) and wait until it has passed. Nothing here uploads; it only prepares run.js.
"""
import argparse, datetime, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import WORK, CFG

P = WORK / "uploader"          # queue.json + run.js live in your folder, the template in the skill
Q = P / "queue.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["build", "done"])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--cap", type=int, default=int(CFG["daily_cap"]), help="max uploads per rolling 24 h")
    ap.add_argument("--not-before", help='release time, e.g. "2026-01-01 18:00" (local time)')
    a = ap.parse_args()
    q = json.loads(Q.read_text(encoding="utf-8"))
    now = datetime.datetime.now()
    if a.mode == "done":
        names = {Path(f).name for f in a.files}
        n = 0
        for i in q:
            if Path(i["file"]).name in names and not i["done"]:
                i["done"], i["uploaded_at"] = True, now.isoformat(timespec="minutes")
                n += 1
        Q.write_text(json.dumps(q, indent=1), encoding="utf-8")
        print(f"marked {n} done")
        return
    day = now - datetime.timedelta(hours=24)  # entries without uploaded_at (old tests) are not counted
    used = sum(1 for i in q if i["done"] and i.get("uploaded_at") and
               datetime.datetime.fromisoformat(i["uploaded_at"]) > day)
    nb = datetime.datetime.fromisoformat(a.not_before) if a.not_before else None
    pend = [i for i in q if i.get("approved") and not i["done"]]
    ready, waiting = [], 0
    for i in pend:
        if i.get("visibility", "private") == "public" and (nb is None or now < nb):
            waiting += 1  # public needs an explicit release time that has already passed
            continue
        ready.append(i)
    ready = ready[:max(0, a.cap - used)]
    if ready and not CFG["studio_url"].startswith("https://studio.youtube.com/channel/"):
        raise SystemExit("set studio_url in sts.config.json to https://studio.youtube.com/channel/<your channel id>")
    tpl = (HERE / "upload.js").read_text(encoding="utf-8")
    (P / "run.js").write_text(tpl.replace("__CHANNEL__", CFG["studio_url"]).replace("__QUEUE__", json.dumps(ready)), encoding="utf-8")
    print(f"uploaded in last 24h {used}/{a.cap} | queued {len(ready)} | waiting for release {waiting} | "
          f"over cap {len(pend) - len(ready) - waiting}")


if __name__ == "__main__":
    main()
