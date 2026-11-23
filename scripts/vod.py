#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Find the best moments in a FINISHED YouTube video/stream and cut them at 1080p60, ready for finalize.py.

    python vod.py <youtube url> [--n 6] [--win 0:30:00-3:00:00] [--name tg] [--no-chat]

Signals per 10 s bin:
  REPLAYED  YouTube's "most replayed" graph (yt-dlp heatmap): what real viewers rewatched (strongest signal)
  CHAT      live-chat replay rate vs its rolling median, + hype words (yt-dlp live_chat)
  LOUD      streamer audio loudness vs its 3-min rolling median
heat = noisy-or of the three signals. Top N windows, >= 120 s apart, intro skipped.
Per pick: rec/<name>_<t>.mp4 (1080p60 section), clips/<name>_<t>.mp4 + .json sidecar (start=5 s), Whisper words
(clips/<name>_<t>.words.json) and a frame sheet logs/vod_<name>_<t>.jpg. The agent then LOOKS at the sheet, writes a
truthful hook and runs: python finalize.py clips/<name>_<t>.mp4 --layout facecam --cam <box> --hook "..." (or --layout blur).
Uses the yt-dlp executable (no extra Python packages). Live streams are refused: run it after the stream ends.
"""
import argparse, json, subprocess, sys
from pathlib import Path

import numpy as np

from common import WORK as ROOT
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BIN, PRE, POST, PAD = 10, 20, 30, 5           # clip = 20 s before the peak + 30 s after, 5 s seek pad
FMT = "299+140/bv*[height<=1080][fps>30][ext=mp4]+ba[ext=m4a]/bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b"
HYPE = set("kekw lul lol lmao lmfao omegalul icant omg wtf pog poggers w ww www l nooo noooo holy bruh sheesh insane "
           "cinema cooked 💀 😭 😂 🤣".split())


def hms(s):
    s = int(s); return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}"


def secs(t):
    return sum(float(v) * 60 ** i for i, v in enumerate(reversed(str(t).split(":"))))


def ytdlp(*a, timeout=1800):
    r = subprocess.run(["yt-dlp", "--no-warnings", *a], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    if r.returncode:
        raise SystemExit("yt-dlp failed: " + r.stderr.strip()[-400:])
    return r.stdout


def clip_rule(meta):
    """Optional clip_rules.json in your folder: {"youtube:@handle": {"rule": "allowed|ask|no", "note": "..."}}."""
    f = ROOT / "clip_rules.json"
    if not f.exists():
        return None
    rules = json.loads(f.read_text(encoding="utf-8"))
    keys = {f"youtube:{str(meta.get(k) or '').lower()}" for k in ("uploader_id", "channel_handle")}
    keys.add(f"youtube:@{str(meta.get('uploader') or '').lower().replace(' ', '')}")
    return next((dict(key=k, **rules[k]) for k in keys if k in rules), None)


def rolling_median(x, w):
    return np.array([np.median(x[max(0, i - w):i + 1]) for i in range(len(x))])


def loud(audio, t0, n):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    x = x[: len(x) // (8000 * BIN) * 8000 * BIN].reshape(-1, 8000 * BIN)
    db = 20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-6)
    seg = np.clip(db - rolling_median(db, 18), 0, None)   # dB above the 3-min rolling median
    out, k = np.zeros(n), int(t0 // BIN)
    m = max(0, min(len(seg), n - k))
    out[k:k + m] = seg[:m]
    return out


def replay(heat_map, n):
    out = np.zeros(n)
    if not heat_map:
        return out
    v = sorted(h["value"] for h in heat_map); med = max(v[len(v) // 2], 0.05)
    for h in heat_map:
        for b in range(int(h["start_time"] // BIN), min(n, int(h["end_time"] // BIN) + 1)):
            out[b] = max(out[b], h["value"] / med)
    return out                                           # times the median replay level


def chat(url, t0, t1, n, name):
    stem = ROOT / "logs" / f"vod_{name}"
    f = Path(str(stem) + ".live_chat.json")
    if not f.exists():
        try:
            ytdlp("--skip-download", "--write-subs", "--sub-langs", "live_chat", "-o", str(stem), url, timeout=900)
        except (SystemExit, subprocess.TimeoutExpired) as e:
            print("  chat: none (", str(e)[:120], ")"); return np.zeros(n), np.zeros(n)
    if not f.exists():
        print("  chat: no live-chat replay for this video"); return np.zeros(n), np.zeros(n)
    cnt, hype = np.zeros(n), np.zeros(n)
    for line in f.open(encoding="utf-8"):
        try:
            act = json.loads(line)["replayChatItemAction"]; s = int(act["videoOffsetTimeMsec"]) / 1000
        except (KeyError, ValueError):
            continue
        b = int(s // BIN)
        if not (t0 <= s < t1) or b >= n:
            continue
        for x in act.get("actions", []):
            m = x.get("addChatItemAction", {}).get("item", {}).get("liveChatTextMessageRenderer")
            if m:
                cnt[b] += 1
                words = "".join(r.get("text", "") for r in m["message"].get("runs", [])).lower().split()
                hype[b] += any(w.strip("!?.") in HYPE for w in words)
    return cnt / np.maximum(rolling_median(cnt, 18), 1), hype / np.maximum(cnt, 1)


def heat(db, rep, ch, hy):
    """Noisy-or: LOUD 15 dB -> .6, CHAT x6 -> .8 (+.1 hype), REPLAYED x8 -> .8."""
    q = np.ones_like(db)
    for x in (np.clip(db / 15, 0, 1) * .6, np.clip(ch / 6, 0, 1) * .8 + .1 * (hy > .3), np.clip(rep / 8, 0, 1) * .8):
        q *= 1 - np.clip(x, 0, .95)
    return 100 * (1 - q)


def selftest():
    n = 100
    rep = replay([dict(start_time=i * 10, end_time=i * 10 + 10, value=1.0 if i == 50 else 0.1) for i in range(n)], n)
    assert rep[50] == 10 and rep[10] == 1, rep[48:52]
    h = heat(np.zeros(n), rep, np.zeros(n), np.zeros(n))
    assert int(np.argmax(h)) == 50 and h[50] == 80, h[50]
    assert hms(3725) == "1:02:05" and secs("1:02:05") == 3725 and secs("90") == 90
    print("vod selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("--n", type=int, default=6); ap.add_argument("--win")
    ap.add_argument("--name", default="vod"); ap.add_argument("--no-chat", action="store_true")
    a = ap.parse_args()
    if a.url == "selftest":
        return selftest()
    for d in ("logs", "rec", "clips"):
        (ROOT / d).mkdir(exist_ok=True)
    meta = json.loads(ytdlp("-J", a.url, timeout=300))
    if meta.get("is_live") or meta.get("live_status") == "is_live":
        raise SystemExit("still live: run vod.py after the stream ends (no replay graph or Ask button for live streams)")
    dur = float(meta.get("duration") or 0)
    t0, t1 = (secs(x) for x in a.win.split("-")) if a.win else (0.0, dur)
    n = int(dur // BIN) + 1
    print(f"{meta.get('title')} | {meta.get('uploader')} | {hms(dur)} | window {hms(t0)}-{hms(t1)}")
    r = clip_rule(meta)
    print(f"  clip rule: {r['rule']} - {r.get('note', '')[:120]}" if r else "  clip rule: unknown (check the channel's rules)")
    if r and r["rule"] == "no":
        raise SystemExit("this streamer said NO to clipping: stop unless the user has permission")
    hm = meta.get("heatmap") or []
    print(f"  replay graph: {'yes' if hm else 'none'} ({len(hm)} points)")
    audio = ROOT / "rec" / f"{a.name}_audio.m4a"
    if not audio.exists():
        print("  downloading audio for the window ...", flush=True)
        ytdlp("-f", "ba[ext=m4a]/ba", "--download-sections", f"*{hms(t0)}-{hms(t1)}", "-o", str(audio), a.url, timeout=3600)
    db = loud(audio, t0, n)
    rep = replay(hm, n)
    ch, hy = (np.zeros(n), np.zeros(n)) if a.no_chat else chat(a.url, t0, t1, n, a.name)
    h = heat(db, rep, ch, hy)
    lo, hi = int(max(t0, 0.03 * dur) // BIN) + 3, int(t1 // BIN) - 3     # skip the intro (always replayed) and the edges
    picks = []
    for b in np.argsort(-h):
        if lo <= b < hi and h[b] >= 20 and all(abs(b - p) * BIN >= 120 for p in picks):
            picks.append(int(b))
        if len(picks) == a.n:
            break
    if not picks:
        raise SystemExit("no moment scored >= 20 heat: try another window or video")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import finalize
    for rank, b in enumerate(picks, 1):
        t = b * BIN + BIN / 2; nm = f"{a.name}_{int(t)}"
        src = ROOT / "rec" / f"{nm}.mp4"
        if not src.exists():
            ytdlp("-f", FMT, "--download-sections", f"*{hms(t - PRE - PAD)}-{hms(t + POST)}", "--force-keyframes-at-cuts",
                  "--merge-output-format", "mp4", "-o", str(src), a.url, timeout=1800)
        prev = ROOT / "clips" / f"{nm}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(PAD), "-i", str(src), "-t", "30", "-vf",
                        "scale=540:960:force_original_aspect_ratio=increase,crop=540:960", "-c:v", "libx264", "-preset",
                        "veryfast", "-crf", "28", "-c:a", "aac", str(prev)], check=True)
        prev.with_suffix(".json").write_text(json.dumps(dict(chan=a.name, rec=str(src), start=float(PAD), end=0, n=0, med=0,
                                                            source=a.url, source_t=t, credit=meta.get("uploader"))))
        sheet = ROOT / "logs" / f"vod_{nm}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "fps=8/50,scale=400:-1,tile=4x2",
                        "-frames:v", "1", str(sheet)], check=True)
        txt = " ".join(w["w"] for w in finalize.get_words(prev.resolve(), "small"))
        src_q = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height,r_frame_rate:"
                                "format=bit_rate", "-of", "csv=p=0", str(src)], capture_output=True, text=True).stdout.split()
        flag = finalize.adult_flags(txt)
        print(f"#{rank} {nm}  at {hms(t)}  heat {h[b]:.0f}  (replay x{rep[b]:.1f}, chat x{ch[b]:.1f}, loud +{db[b]:.0f} dB)"
              f"  src {' '.join(src_q)}" + (f"  [ADULT-FLAG: {', '.join(flag)}]" if flag else ""))
        print(f"   sheet {sheet.relative_to(ROOT)} | {txt[:260] or '(no speech)'}", flush=True)


if __name__ == "__main__":
    main()
