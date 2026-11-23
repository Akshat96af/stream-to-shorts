#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Clip Factory dashboard server: python dash.py  ->  http://127.0.0.1:8765 (this PC only).
Serves status.html + its data and lets the page move a bad Short to render/trash/<stem>/ (video, cover, QC, meta) and
back (Restore). Nothing is deleted for good: empty render/trash/ yourself. YouTube is never touched (delete there in Studio).
The ledger keeps the item (uploads still count toward YouTube's daily limit) and gets "trashed": true."""
import json, shutil, subprocess, sys, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import WORK as ROOT
PORT = 8765
TRASH = ROOT / "render" / "trash"
ALLOWED = ("status.html", "status.js", "final/", "render/covers/", "render/qc/")


def parts(stem):
    return [(ROOT / "final" / f"{stem}.mp4", "video.mp4"), (ROOT / "render" / "covers" / f"{stem}.jpg", "cover.jpg"),
            (ROOT / "render" / "qc" / f"{stem}.qc.json", "qc.json"), (ROOT / "render" / "qc" / f"{stem}.qc.jpg", "qc.jpg"),
            (ROOT / "render" / "meta" / f"{stem}.meta.json", "meta.json")]


def safe_stem(s):
    s = str(s or "")
    if not s or any(c in s for c in "/\\:") or ".." in s or len(s) > 200:
        raise ValueError("bad name")
    return s


def ledger(stem, trashed):
    q = ROOT / "uploader" / "queue.json"
    items = json.loads(q.read_text(encoding="utf-8"))
    for i in items:
        if Path(i.get("file", "")).stem == stem:
            i["trashed"] = trashed
    q.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")


def trash(stem):
    stem = safe_stem(stem)
    if not (ROOT / "final" / f"{stem}.mp4").exists():
        raise ValueError("no such Short")
    d = TRASH / stem
    d.mkdir(parents=True, exist_ok=True)
    for src, name in parts(stem):
        if src.exists():
            shutil.move(str(src), str(d / name))
    ledger(stem, True)


def restore(stem):
    stem = safe_stem(stem)
    d = TRASH / stem
    if not d.is_dir():
        raise ValueError("not in trash")
    for dst, name in parts(stem):
        if (d / name).exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(d / name), str(dst))
    d.rmdir()
    ledger(stem, False)


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def log_message(self, *a):
        pass

    def bad_origin(self):  # only this page may call us (no other website, no DNS rebinding)
        ok = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
        o = self.headers.get("Origin")
        return self.headers.get("Host") not in ok or (o is not None and o not in {f"http://{h}" for h in ok})

    def do_GET(self):
        p = unquote(self.path.split("?")[0].lstrip("/")) or "status.html"
        if self.bad_origin() or ".." in p or not p.startswith(ALLOWED):
            return self.send_error(404)
        if p == "status.js":
            subprocess.run([sys.executable, str(HERE / "status.py")], cwd=ROOT)   # always fresh data
        self.path = "/" + p
        return super().do_GET()

    def do_POST(self):
        if self.bad_origin():
            return self.send_error(403)
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            {"/api/trash": trash, "/api/restore": restore}[self.path](d.get("stem"))
            subprocess.run([sys.executable, str(HERE / "status.py")], cwd=ROOT)
            code, out = 200, {"ok": True}
        except (KeyError, ValueError, OSError) as e:
            code, out = 400, {"error": str(e)[:200]}
        b = json.dumps(out).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


if __name__ == "__main__":
    shutil.copy2(HERE / "status.html", ROOT / "status.html")   # the page lives next to your data
    subprocess.run([sys.executable, str(HERE / "status.py")], cwd=ROOT)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"Clip Factory dashboard: http://127.0.0.1:{PORT}  (Ctrl+C to stop)")
    if "--no-open" not in sys.argv:
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    srv.serve_forever()
