#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""Final render: 9:16 layout + effects + word captions + phonk (drop on the moment) + SFX -> final/.

    python finalize.py clips/<name>.mp4 [--hook "TEXT"] [--layout crop|blur] [--music DIR|none]
Needs clips/<name>.json (written by clipwatcher / audiowatch). LOCAL ONLY: never uploads anything.
final/ holds finished mp4 only ("clip 07 - streamer - short title"); covers, QC sheets, metadata -> render/<kind>/.
No LLM calls. Effects are cheap ffmpeg expressions (weak-CPU friendly).
"""
import argparse, contextlib, json, os, random, re, subprocess, sys, tempfile, time
from pathlib import Path

import numpy as np

import music

from common import WORK as ROOT, CFG, MUSIC_DIR, SFX_DIR
FINAL, SFX, RENDER = ROOT / "final", SFX_DIR, ROOT / "render"
W, H, LEN, FPS = 1080, 1920, int(CFG["clip_seconds"]), int(CFG.get("fps", 60))  # 1080x1920 @ 60 fps (the sources are 60 fps; 30 fps looked choppy/soft)
K = W / 720                          # pixel scale for effect sizes
VOICE_UP, MUSIC_BELOW = 3, 14        # stream audio +3 dB; phonk sits 14 LU under it, then ducks further
ADULT = ("strip club", "stripper", "strippers", "strip", "lap dance", "naked", "nude", "nudity", "topless", "porn",
         "sex", "sexy", "sexual", "boobs", "tits", "horny", "onlyfans", "erotic", "hooker", "prostitute", "brothel")
ENC = {"qsv": ["-c:v", "h264_qsv", "-global_quality", "13", "-preset", "slow"],  # lower = better; ~8-16 Mbps
       "nvenc": ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19"],
       "x264": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16"]}
# quality chosen by the user: high = slower and sharper, fast = quick drafts (applies to x264, the portable encoder)
ENC["x264"] = {"high": ["-c:v", "libx264", "-preset", "slow", "-crf", "16"],
               "fast": ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22"]}.get(CFG.get("quality", "balanced"), ENC["x264"])


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(path)], capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def lufs(args):
    """Integrated loudness (LUFS) of an ffmpeg input segment, e.g. ["-ss", "3", "-t", "30", "-i", file]."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args, "-vn", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    return float(m[-1]) if m and float(m[-1]) > -70 else None


def adult_flags(text):
    """18+ words in the English transcript: such clips are skipped automatically (the editor checks frames too)."""
    return sorted({m.lower() for m in re.findall(r"\b(" + "|".join(ADULT) + r")\b", text, re.I)})


PROFANE = re.compile(r"\b\w*(fuck|shit|bitch|cunt|nigg|fagg|whore|slut|pussy|asshole|dick)\w*\b", re.I)


def censor(t):
    """Caption-safe words (f***, s***): limits age-restriction / ad trouble; the audio is untouched."""
    return PROFANE.sub(lambda m: m.group(0)[0] + "*" * (len(m.group(0)) - 1), t)


def auto_hook(words, hl):
    """Fallback when no --hook is given: the <= 6 words spoken closest to the moment (never one canned line)."""
    near = sorted((w for w in words if abs((w["s"] + w["e"]) / 2 - hl) <= 4), key=lambda w: abs(w["s"] - hl))[:6]
    text = " ".join(re.sub(r"[^A-Za-z0-9' ]", "", w["w"]).upper() for w in sorted(near, key=lambda w: w["s"])).strip()
    return text or "WATCH THIS"


def stem_for(clip, chan, hook):
    """'clip 07 - streamer - he did not expect that': the serial is kept per raw clip in render/serial.json."""
    RENDER.mkdir(exist_ok=True)
    f = RENDER / "serial.json"
    d = json.loads(f.read_text()) if f.exists() else {"next": 1, "serial": {}}
    n = d["serial"].setdefault(clip.stem, d["next"])
    d["next"] = max(d["next"], n + 1)
    f.write_text(json.dumps(d, indent=1))
    slug = " ".join(re.sub(r"[^a-z0-9 ]", "", hook.lower()).split()[:5]) or "clip"
    return f"clip {n:02d} - {chan} - {slug}"


def tidy(stem):
    """A re-render with a new hook changes the stem: drop the older files of the same serial."""
    pre = stem.split(" - ")[0] + " - "
    for d in (FINAL, RENDER / "covers", RENDER / "qc", RENDER / "meta"):
        for p in d.glob(pre + "*"):
            if not p.name.startswith(stem):
                p.unlink()


def peak(rec, start):
    """Second (in the clip) of the loudest 0.5 s between 6 s and 24 s = the moment effects/drop hit."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.2f}", "-i", str(rec), "-t", str(LEN),
                          "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    x = x[: len(x) // 4000 * 4000].reshape(-1, 4000)  # 0.5 s frames
    e = np.sqrt((x ** 2).mean(1))
    return (int(np.argmax(e[12:48])) + 12) * 0.5 + 0.25


LANG = None  # "hi" -> Hindi transcript (Devanagari), romanised by hand into Hinglish


def transcribe(clip, model_name):
    from faster_whisper import WhisperModel  # English subtitles whatever the language
    m = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=2,
                     download_root=str(ROOT / "models"))
    segs, info = m.transcribe(str(clip), word_timestamps=True, vad_filter=True, language=LANG)  # plain transcription, auto language
    if LANG is None and info.language != "en":  # captions must be English: translate only when the speech is not English
        segs, _ = m.transcribe(str(clip), task="translate", word_timestamps=True, vad_filter=True)
    # drop low-confidence words: garbled captions ("she lawyer me some elbow room") look worse than a gap
    words = [{"w": w.word.strip(), "s": w.start, "e": w.end} for s in segs for w in (s.words or [])
             if w.word.strip() and (getattr(w, "probability", None) is None or w.probability >= 0.4)]
    return dedupe(words)


def dedupe(words, keep=2):
    """Whisper loops on music/chants ("like him like him like him ..."): keep at most `keep` back-to-back repeats of
    the same 1-3 word phrase (a real "first race, first race" survives)."""
    key = lambda w: w["w"].lower().strip(".,!?-'\"")
    out = []
    for w in words:
        out.append(w)
        for n in (1, 2, 3):
            if len(out) >= n * (keep + 1) and all(
                    [key(x) for x in out[-n:]] == [key(x) for x in out[-n * (k + 1):len(out) - n * k]] for k in range(1, keep + 1)):
                del out[-n:]
                break
    return out


def ass_time(t):
    cs = int(round(max(0.0, t) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def groups(words, n=3, gap=0.6):
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= n or w["s"] - cur[-1]["e"] > gap or cur[-1]["w"][-1:] in ".!?,"):
            out.append(cur); cur = []
        cur.append(w)
    return out + ([cur] if cur else [])


def build_ass(path, words, hook):
    """Hook box on top from FRAME 0 (no fade-in) for 3.5 s; word-by-word captions, current word highlighted."""
    L = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 720", "PlayResY: 1280", "WrapStyle: 0",
         "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
         "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
         "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
         "Alignment, MarginL, MarginR, MarginV, Encoding",
         "Style: Cap,Arial Black,62,&H00FFFFFF,&H00FFFFFF,&H00101010,&H90000000,-1,0,0,0,100,100,1,0,1,6,4,2,40,40,360,1",
         "Style: Hook,Arial Black,52,&H00000000,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,12,0,8,50,50,150,1",
         "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
         f"Dialogue: 1,{ass_time(0)},{ass_time(3.5)},Hook,,0,0,0,,{{\\fad(0,200)}}{hook}"]
    # caption look, chosen by the user (sts.config.json): style pop|clean|none, colour, case, position
    style = CFG.get("caption_style", "pop")
    hl_col = {"yellow": "&H0000F0FF&", "green": "&H0040FF40&", "cyan": "&H00FFFF00&", "red": "&H004040FF&",
              "orange": "&H000090FF&", "white": "&H00FFFFFF&"}.get(CFG.get("caption_color", "yellow"), "&H0000F0FF&")
    upper = CFG.get("caption_case", "upper") == "upper"
    Y = 1280 - (640 if CFG.get("caption_position", "low") == "middle" else 360)  # caption baseline
    for g in ([] if style == "none" else groups(words)):
        for i, w in enumerate(g):
            end = g[i + 1]["s"] if i + 1 < len(g) else g[-1]["e"] + 0.15
            parts = []
            for j, x in enumerate(g):
                t = censor(x["w"]).replace("{", "(").replace("}", ")")
                t = t.upper() if upper else t
                if j != i:
                    parts.append(t)
                elif style == "clean":  # the spoken word changes colour only
                    parts.append("{\\c" + hl_col + "}" + t + "{\\c&H00FFFFFF&}")
                else:  # pop: the spoken word pops (overshoot 124% -> 108%) in the highlight colour
                    parts.append("{\\c" + hl_col + "\\fscx100\\fscy100\\t(0,70,\\fscx124\\fscy124)\\t(70,170,\\fscx108\\fscy108)}" + t
                                 + "{\\c&H00FFFFFF&\\fscx100\\fscy100}")
            if style == "clean":
                enter, leave = f"\\pos(360,{Y})", ""
            else:  # group slides up and fades in, fades out after its last word
                enter = f"\\move(360,{Y + 22},360,{Y},0,110)\\fad(70,0)" if i == 0 else f"\\pos(360,{Y})"
                leave = "\\fad(0,90)" if i == len(g) - 1 else ""
            L.append(f"Dialogue: 0,{ass_time(w['s'])},{ass_time(min(end, LEN))},Cap,,0,0,0,,{{\\blur0.8{enter}{leave}}}{' '.join(parts)}")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


@contextlib.contextmanager
def render_lock():
    """One render at a time on this weak CPU: parallel editor agents + the live worker queue up here."""
    lock = ROOT / "logs" / "render.lock"
    lock.parent.mkdir(exist_ok=True)
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > 900:  # stale lock from a crashed render
                    lock.unlink()
            except OSError:
                pass
            time.sleep(2)
    try:
        yield
    finally:
        os.close(fd)
        try:
            lock.unlink()
        except OSError:
            pass


def get_words(clip, model_name):
    """English word timings, cached next to the clip so the editor can read them BEFORE rendering."""
    f = clip.with_suffix(".words.json")
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    src, sc = clip, clip.with_suffix(".json")
    tmp = None
    if sc.exists():  # transcribe the SOURCE segment so captions cover the full LEN, not just the 30 s preview cut
        o = json.loads(sc.read_text())
        tmp = Path(tempfile.mkdtemp()) / "seg.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{o['start']:.2f}", "-i", o["rec"], "-t", str(LEN), "-vn", "-ac", "1",
                        "-ar", "16000", str(tmp)], check=True)
        src = tmp
    w = transcribe(src, model_name)
    f.write_text(json.dumps(w, ensure_ascii=False), encoding="utf-8")
    return w


def make_cover(out, hl, hook, cover):
    """Cover = frame just after the moment + big hook text (ASS, no extra deps) -> render/covers/<stem>.jpg"""
    tmp = Path(tempfile.mkdtemp())
    text = hook.upper().replace("{", "(").replace("}", ")")
    (tmp / "c.ass").write_text("\n".join([
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 720", "PlayResY: 1280", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
        "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: C,Arial Black,92,&H0000F0FF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,3,8,40,40,170,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 0,0:00:00.00,0:01:00.00,C,,0,0,0,,{text}", ""]), encoding="utf-8")
    cover.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(hl + 0.3, LEN - 1):.2f}", "-i", str(out.resolve()),
                    "-vf", "ass=c.ass", "-frames:v", "1", "-q:v", "2", str(cover.resolve())],
                   cwd=tmp, capture_output=True)
    return cover


def qc(out, dest):
    """Automatic render checks + a contact sheet (dest/<stem>.qc.jpg) that the editor agent LOOKS at."""
    dest.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out), "-vf", "blackdetect=d=0.3",
                        "-af", "silencedetect=n=-50dB:d=1.5,ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr

    def last(pat):
        m = re.findall(pat, r)
        return float(m[-1]) if m else None
    lufs_, pk = last(r"I:\s+(-?[\d.]+) LUFS"), last(r"Peak:\s+(-?[\d.]+) dBFS")
    black, silent = r.count("black_start"), r.count("silence_start")
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height", "-show_entries", "format=duration", "-of", "json",
                                      str(out)], capture_output=True, text=True).stdout)
    w, h, d = info["streams"][0]["width"], info["streams"][0]["height"], float(info["format"]["duration"])
    issues = []
    if (w, h) != (W, H):
        issues.append(f"size {w}x{h}")
    if not LEN - 2 <= d <= LEN + 1:
        issues.append(f"duration {d:.1f}s")
    if pk is None or pk > -1.0:
        issues.append(f"peak {pk} dBFS (clipping risk)")
    if lufs_ is None or not -19 <= lufs_ <= -11:
        issues.append(f"loudness {lufs_} LUFS")
    if black:
        issues.append(f"{black} black segment(s)")
    if silent:
        issues.append(f"{silent} silent gap(s) > 1.5 s")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vf", f"fps=8/{LEN},scale=180:320,tile=4x2",
                    "-frames:v", "1", str(dest / f"{out.stem}.qc.jpg")], capture_output=True)
    res = {"ok": not issues, "issues": issues, "lufs": lufs_, "peak": pk, "dur": round(d, 1)}
    (dest / f"{out.stem}.qc.json").write_text(json.dumps(res))
    return res


def triage(clip, model_name):
    """Cheap pre-filter run BEFORE an Opus editor is spawned: 18+ words, or flat audio (nothing loud happens)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le",
                          "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    x = x[: len(x) // 4000 * 4000].reshape(-1, 4000)
    db = 20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-6)
    dyn = float(db.max() - np.median(db))  # loudest 0.5 s vs typical: good clips ~10+ dB, dead footage ~3 dB
    words = get_words(clip, model_name)  # cached: the editor reuses it
    flags = adult_flags(" ".join(w["w"] for w in words))
    if flags:
        return f"SKIP: 18+ words ({', '.join(flags)})"
    if dyn < 5:
        return f"SKIP: flat audio (dyn {dyn:.1f} dB)"
    return f"PASS dyn={dyn:.1f} dB words={len(words)}"


def render(clip, a):
    with render_lock():
        return _render(clip, a)


def queue_add(out, meta, cover=None, hook="", key=""):
    """Ledger for the uploader: approved=false until the user says go. Template title, no LLM."""
    q = ROOT / "uploader" / "queue.json"
    items = json.loads(q.read_text(encoding="utf-8")) if q.exists() else []
    f = out.resolve().as_posix()
    ent = next((i for i in items if key and i.get("clip") == key and not i["done"]), None)
    if ent is None:  # a re-render of the same clip updates its entry instead of adding a second one
        ch = meta["chan"]
        ent = {"title": f"{ch}: GTA 6 live moment #shorts #gta6",
               "desc": f"Clipped from {ch} (live stream). #shorts #gta6 #gtavi",
               "visibility": CFG["visibility"], "approved": False, "done": False}  # approval is always a separate, explicit step
        items.append(ent)
    ent.update({"clip": key, "file": f, "hook": hook, "cover": cover.resolve().as_posix() if cover else None})
    q.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")


def _render(clip, a):
    meta = json.loads(clip.with_suffix(".json").read_text())
    rec, start = Path(meta["rec"]), meta["start"]
    pad = min(5, start)  # seek early, trim exactly (mpegts seeks land mid-GOP)
    fps = getattr(a, "fps", FPS)
    hl = peak(rec, start)
    track = music.pick(LEN, hl, Path(a.music)) if a.music != "none" else None
    def pick_sfx(cat):  # your own files in sfx/<cat>/ (none are shipped); a missing category is simply skipped
        fs = sorted(p for p in (SFX / cat).glob("*") if p.suffix.lower() in (".mp3", ".wav", ".ogg", ".m4a", ".flac"))
        return random.choice(fs) if fs else None
    whoosh, hit, riser, pop, shutter = (pick_sfx(c) for c in ("whoosh", "hit", "riser", "pop", "shutter"))
    words = get_words(clip, a.model)
    flags = adult_flags(" ".join(w["w"] for w in words))
    if flags and not getattr(a, "allow_adult", False):  # 18+ screen on the transcript; the editor checks frames too
        (RENDER / "skips").mkdir(parents=True, exist_ok=True)
        (RENDER / "skips" / f"{clip.stem}.skip").write_text("18+ words: " + ", ".join(flags))
        print(f"  SKIPPED (18+ words: {', '.join(flags)})", flush=True)
        return None
    tmp = Path(tempfile.mkdtemp())
    hook_text = (a.hook or auto_hook(words, hl)).replace("{", "(").replace("}", ")")
    build_ass(tmp / "cap.ass", words, hook_text)

    voice_l = lufs(["-ss", f"{start:.2f}", "-t", str(LEN), "-i", str(rec)])  # stream audio (voice + game)
    vup = VOICE_UP if (voice_l is None or voice_l < -18) else 0  # loud streamers (~-9 LUFS) need no boost
    mgain = 0.05
    if track and voice_l is not None:  # phonk is mastered ~-8 LUFS, the stream ~-25: match, then sit MUSIC_BELOW under
        music_l = lufs(["-ss", str(track[1]), "-t", str(LEN), "-i", str(track[0])])
        if music_l is not None:
            mgain = min(1.0, 10 ** ((voice_l + vup - MUSIC_BELOW - music_l) / 20))
    print(f"  moment {hl:.1f}s | hook \"{hook_text}\" | voice {voice_l} LUFS (+{vup} dB) | music "
          f"{track[0].name[:32] + ' @' + str(track[1]) + 's x' + format(mgain, '.3f') if track else 'none'} "
          f"| sfx {', '.join(p.stem for p in (whoosh, riser, hit) if p) or 'none'}", flush=True)

    ins = ["-ss", f"{start - pad:.2f}", "-t", str(pad + LEN + 1), "-i", str(rec)]
    if track:
        ins += ["-ss", str(track[1]), "-t", str(LEN + 1), "-i", str(track[0])]
    pops = []  # quiet pop on a few caption groups (max 6, >= 1.2 s apart)
    for g in groups(words):
        if g[0]["s"] > 0.3 and len(pops) < 6 and (not pops or g[0]["s"] - pops[-1] >= 1.2):
            pops.append(g[0]["s"])
    rdur = dur(riser) if riser else 0  # riser ENDS on the moment; (file, start s, volume, trim s)
    extras = [e for e in [(whoosh, 0.0, 0.8, 0.0), (hit, max(0.0, hl - 0.15), 1.0, 0.0), (shutter, hl, 0.5, 0.0),
              (riser, max(0.0, hl - rdur), 0.7, max(0.0, rdur - hl))] + [(pop, t, 0.22, 0.0) for t in pops] if e[0]]
    for p, *_ in extras:
        ins += ["-i", str(p)]
    mi, first = (1, 2) if track else (None, 1)  # input index of music / first extra

    if a.layout == "blur":  # full 16:9 frame over a blurred zoomed copy
        base = (f"[0:v]trim=start={pad}:duration={LEN},setpts=PTS-STARTPTS,fps={fps},split[a][b];"
                f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20:2,eq=brightness=-0.1[bg];"
                f"[b]scale={int(W * 1.07)}:-2:flags=lanczos,crop={W}:ih[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2-40[b0]")
    elif a.layout == "facecam":  # streamer cam on top, gameplay (center crop) below: shows reactions
        cx, cy, cw, ch = (float(v) for v in getattr(a, "cam", "0,0.42,0.205,0.235").split(","))
        cam_h = 520
        base = (f"[0:v]trim=start={pad}:duration={LEN},setpts=PTS-STARTPTS,fps={fps},split[c][g];"
                f"[c]crop=iw*{cw}:ih*{ch}:iw*{cx}:ih*{cy},scale={W}:{cam_h}:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop={W}:{cam_h}[cam];[g]scale=-2:{H - cam_h}:flags=lanczos,crop={W}:{H - cam_h}[game];"
                f"[cam][game]vstack[b0]")
    else:  # center crop, best when the action is in the middle (GTA third person)
        base = (f"[0:v]trim=start={pad}:duration={LEN},setpts=PTS-STARTPTS,fps={fps},"
                f"crop=trunc(ih*9/16/2)*2:ih,scale={W}:{H}:flags=lanczos[b0]")
    # --hide-subs: soft blur of the bottom strip where the GAME's own subtitles sit (profane / cut off); off by default
    hide = (",split[ha][hb];[hb]crop=iw:ih*0.14:0:ih*0.86,boxblur=45:6[hbl];[ha][hbl]overlay=0:H*0.86,"
            if getattr(a, "hide_subs", False) else ",")
    z = f"1+0.14*between(t,{hl:.2f},{hl + 0.5:.2f})*(1-(t-{hl:.2f})/0.5)"       # punch-in, decays
    sh = f"between(t,{hl:.2f},{hl + 0.4:.2f})"                                    # shake window
    fx = (f"[b0]scale=w='trunc({W}*({z})/2)*2':h='trunc({H}*({z})/2)*2':eval=frame,"
          f"crop={W}:{H}:x='(iw-{W})/2+{9 * K:.0f}*sin(t*90)*{sh}':y='(ih-{H})/2+{9 * K:.0f}*cos(t*77)*{sh}',"
          f"eq=contrast=1.08:saturation=1.25:brightness='0.3*between(t,{hl:.2f},{hl + 0.08:.2f})':eval=frame,"
          f"vignette=PI/7,cas=0.55{hide}ass=cap.ass,format=yuv420p[v]")  # no fades: frame 0 shows the hook; loops cleanly
    st = "aformat=sample_rates=48000:channel_layouts=stereo"
    au = [f"[0:a]atrim=start={pad}:duration={LEN},asetpts=PTS-STARTPTS,{st},volume={vup}dB" + (",asplit=2[va][sc]" if track else "[va]")]
    mix = ["[va]"]
    if track:  # music far under the voice, ducks further while the streamer talks; fades in/out
        au += [f"[{mi}:a]{st},volume={mgain:.4f},afade=t=in:d=0.3,afade=t=out:st={LEN - 1.5}:d=1.5[m0]",
               "[m0][sc]sidechaincompress=threshold=0.03:ratio=6:attack=10:release=400[m]"]
        mix.append("[m]")
    for k, (p, t, v, tr) in enumerate(extras):
        au.append(f"[{first + k}:a]{st},atrim=start={tr:.2f},asetpts=PTS-STARTPTS,volume={v},"
                  f"adelay=delays={int(t * 1000)}:all=1[s{k}]")
        mix.append(f"[s{k}]")
    au.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0,"
              f"loudnorm=I=-15:TP=-2:LRA=11,alimiter=limit=0.7:level=0[aout]")  # level=0: else auto-level undoes the ceiling
    FINAL.mkdir(exist_ok=True)
    stem = stem_for(clip, meta["chan"], hook_text)
    out = FINAL / f"{stem}.mp4"
    for enc in dict.fromkeys([a.enc, "x264"]):  # iGPU first, x264 fallback
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-threads", "2", *ins,
                            "-filter_complex", ";".join([base, fx] + au), "-map", "[v]", "-map", "[aout]",
                            "-t", str(LEN), *ENC[enc], "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                            str(out.resolve())], cwd=tmp, capture_output=True, text=True,
                           creationflags=0x4000 if os.name == "nt" else 0)
        if r.returncode == 0 and out.exists():
            cover = make_cover(out, hl, hook_text, RENDER / "covers" / f"{stem}.jpg")
            q = qc(out, RENDER / "qc")
            (RENDER / "meta").mkdir(parents=True, exist_ok=True)
            (RENDER / "meta" / f"{stem}.meta.json").write_text(json.dumps({  # the analyst joins this with views
                "clip": clip.stem, "stem": stem, "chan": meta["chan"], "hook": hook_text, "layout": a.layout,
                "moment": round(hl, 1), "music": track[0].name if track else None,
                "music_start": track[1] if track else None, "music_gain": round(mgain, 4), "voice_lufs": voice_l,
                "sfx": [p.stem for p in (whoosh, riser, hit) if p], "words": len(words), "qc": q,
                "rendered": time.strftime("%Y-%m-%d %H:%M:%S")}))
            tidy(stem)
            queue_add(out, meta, cover, hook_text, clip.stem)
            print(f"  QC {'ok' if q['ok'] else 'ISSUES: ' + '; '.join(q['issues'])} | {q['lufs']} LUFS, "
                  f"peak {q['peak']}", flush=True)
            print(f"OUT {out}\nCOVER {cover}\nQC {RENDER / 'qc' / (stem + '.qc.json')} | sheet "
                  f"{RENDER / 'qc' / (stem + '.qc.jpg')}\nMETA {RENDER / 'meta' / (stem + '.meta.json')}", flush=True)
            return out
    print("  render FAILED:", r.stderr.strip()[-600:])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--layout", choices=["crop", "blur", "facecam"], default="crop")
    ap.add_argument("--cam", default="0,0.42,0.205,0.235",
                    help="facecam box x,y,w,h as fractions of the frame; find it from one full frame of the stream (default: lower-left)")
    ap.add_argument("--hide-subs", action="store_true", help="blur the bottom strip where the game's own subtitles sit")
    ap.add_argument("--music", default=str(MUSIC_DIR), help='folder of your own licensed tracks, or "none"')
    ap.add_argument("--hook", help="hook text (default: the words spoken nearest the moment; the editor writes a better one)")
    ap.add_argument("--allow-adult", action="store_true", help="render even if the transcript has 18+ words (don't)")
    ap.add_argument("--model", default=CFG["whisper_model"], help="whisper: tiny|base|small (small = accurate captions)")
    ap.add_argument("--lang", default=None, help="force the transcript language, e.g. hi for Hinglish speakers")
    ap.add_argument("--enc", choices=list(ENC), default=CFG["encoder"])
    ap.add_argument("--fps", type=int, default=FPS, help="30 (default) or 60")
    ap.add_argument("--transcript-only", action="store_true",
                    help="print the English transcript and stop (the editor reads it to write a hook)")
    ap.add_argument("--preview", action="store_true", help="write clips/<name>.sheet.jpg (8 frames) and stop")
    ap.add_argument("--triage", action="store_true", help="cheap PASS/SKIP check (18+ words, flat audio) and stop")
    a = ap.parse_args()
    LANG = a.lang
    for c in a.clips:
        if a.triage:
            print("TRIAGE", triage(Path(c).resolve(), a.model))
            continue
        if a.transcript_only or a.preview:
            cp = Path(c).resolve()
            if a.preview:  # 8 frames of the quick cut: the hook must only promise what the clip SHOWS
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(cp), "-vf", f"fps=8/{LEN},scale=180:320,tile=4x2",
                                "-frames:v", "1", str(cp.with_suffix(".sheet.jpg"))], capture_output=True)
                print("sheet:", cp.with_suffix(".sheet.jpg"))
            if a.transcript_only:
                txt = " ".join(w["w"] for w in get_words(cp, a.model))
                print(txt[:800] or "(no speech)")
                if adult_flags(txt):
                    print("ADULT-FLAG:", ", ".join(adult_flags(txt)), "-> SKIP this clip unless the frames prove it harmless")
            continue
        t = time.time()
        out = render(Path(c).resolve(), a)
        if out:
            print(f"{out}  ({time.time() - t:.0f}s)")
