#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Dashboard data for status.html (open <your folder>/status.html, or run dash.py; no network).
    python status.py <stage> [note]   stages: scan|render|upload|check|idle  (also refreshes all data)
    python status.py posted           a clip was just published: resets the "since last post" timer
    python status.py                  refresh the data only
    python status.py loop             refresh every 10 s (run in the background while working)
Writes status.js = window.S (stage) + window.D (Shorts, ledger, QC, logs, recordings)."""
import glob, json, os, sys, time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK as ROOT, CFG
P = ROOT / "status.js"
RANGE = {"scan": "2-15 min", "render": "2-6 min", "upload": "1-3 min", "check": "3-10 min (YouTube's check)", "idle": ""}
CAP = int(CFG["daily_cap"])


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def load_stage():
    try:
        return json.loads(P.read_text(encoding="utf-8").split("\n")[0].split("=", 1)[1].rstrip("; \n"))
    except Exception:
        return {"last_post": time.time(), "stage": "idle", "since": time.time()}


def tail(p, n=12):
    try:
        with open(p, "rb") as f:
            f.seek(0, 2); f.seek(max(0, f.tell() - 6000))
            return [l.decode("utf-8", "replace").rstrip() for l in f.read().splitlines()[-n:]]
    except Exception:
        return []


def data():
    q = jload(ROOT / "uploader" / "queue.json", []) or []
    by_file = {Path(i.get("file", "")).stem: i for i in q}
    shorts = []
    for f in sorted(glob.glob(str(ROOT / "final" / "*.mp4")), key=os.path.getmtime, reverse=True)[:30]:
        stem = Path(f).stem
        meta = jload(ROOT / "render" / "meta" / f"{stem}.meta.json", {}) or {}
        qc = jload(ROOT / "render" / "qc" / f"{stem}.qc.json", {}) or meta.get("qc") or {}
        it = by_file.get(stem, {})
        cover = ROOT / "render" / "covers" / f"{stem}.jpg"
        state = "posted" if it.get("done") else "queued" if it.get("approved") else "rendered"
        shorts.append(dict(stem=stem, file=f"final/{Path(f).name}", cover=f"render/covers/{cover.name}" if cover.exists() else "",
                           sheet=f"render/qc/{stem}.qc.jpg", title=it.get("title") or meta.get("hook") or stem,
                           hook=meta.get("hook") or it.get("hook", ""), state=state, at=it.get("uploaded_at", ""),
                           made=datetime.fromtimestamp(os.path.getmtime(f)).strftime("%d %b %H:%M"),
                           layout=meta.get("layout", ""), music=(meta.get("music") or "")[:48], sfx=meta.get("sfx") or [],
                           qc_ok=qc.get("ok"), lufs=qc.get("lufs"), peak=qc.get("peak"), dur=qc.get("dur"),
                           issues=qc.get("issues") or [], url=it.get("url")))
    now = datetime.now()
    recent = [i for i in q if i.get("done") and i.get("uploaded_at")
              and now - datetime.fromisoformat(i["uploaded_at"]) < timedelta(hours=24)]
    rec = [dict(name=Path(f).name, gb=round(os.path.getsize(f) / 1e9, 2),
                live=time.time() - os.path.getmtime(f) < 30,
                at=datetime.fromtimestamp(os.path.getmtime(f)).strftime("%d %b %H:%M"))
           for f in sorted(glob.glob(str(ROOT / "rec" / "*")), key=os.path.getmtime, reverse=True)[:8]]
    logs = sorted((f for f in glob.glob(str(ROOT / "logs" / "*.out")) + glob.glob(str(ROOT / "logs" / "*.txt"))
                   if os.path.getsize(f) > 300), key=os.path.getmtime, reverse=True)   # skip tiny marker files
    return dict(updated=time.time(), shorts=shorts, cap=CAP, used24=len(recent), posted=sum(1 for i in q if i.get("done")),
                queued=sum(1 for i in q if i.get("approved") and not i.get("done")),
                rendering=(ROOT / "logs" / "render.lock").exists(), rec=rec,
                trash=sorted((d.name for d in (ROOT / "render" / "trash").glob("*") if d.is_dir()), reverse=True),
                log_name=Path(logs[0]).name if logs else "", log=tail(logs[0]) if logs else [])


def write(s):
    P.write_text("window.S = " + json.dumps(s) + ";\nwindow.D = " + json.dumps(data(), ensure_ascii=False) + ";\n",
                 encoding="utf-8")


if __name__ == "__main__":
    s, a = load_stage(), sys.argv[1:]
    if a[:1] == ["loop"]:
        while True:
            write(load_stage()); time.sleep(10)
    if a[:1] == ["posted"]:
        s["last_post"] = time.time(); a = ["idle", "just posted"]
    if a:
        s.update(stage=a[0], note=" ".join(a[1:]), since=time.time(), typical=RANGE.get(a[0], ""))
    write(s)
