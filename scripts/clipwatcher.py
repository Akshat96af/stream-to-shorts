#!/usr/bin/env python3
# stream-to-shorts by Akshat96af | Copyright (c) 2026 Akshat96af. All rights reserved.
# Free for personal use. No resale, re-upload, rebranding or redistribution of modified copies. See LICENSE.
"""clip-watcher: record Twitch streams, detect chat spikes, cut 9:16 clips + .srt.

    ./watch.sh chan1 [chan2 ...] [--min 15] [--factor 2.5] [--fast]
    python clipwatcher.py --selftest
    python clipwatcher.py --replay chat.log --min 15      # tune thresholds offline
"""
import argparse, asyncio, json, os, queue, statistics, subprocess, sys, threading, time
from collections import deque
from pathlib import Path

from common import WORK as ROOT, MUSIC_DIR
REC, CLIPS, LOGS = ROOT / "rec", ROOT / "clips", ROOT / "logs"  # final/ = finished renders (phase 2)
BUCKET, WINDOW, WARMUP = 10, 18, 6  # 18 x 10 s = 3 min baseline
PRE, POST = 20, 10                  # clip = 20 s before + 10 s after the spike
# iGPU encoders keep a weak CPU free; x264 is the safe default
ENC = {"x264": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"],
       "qsv": ["-c:v", "h264_qsv", "-global_quality", "25"],
       "amf": ["-c:v", "h264_amf", "-quality", "speed"]}


class Detector:
    """10 s buckets; fires when bucket >= max(factor * median(last 3 min), min_msgs)."""

    def __init__(self, factor=2.5, min_msgs=15, cooldown=30):
        self.factor, self.min, self.cooldown = factor, min_msgs, cooldown
        self.hist, self.cur, self.n, self.last = deque(maxlen=WINDOW), None, 0, -1e9

    def _close(self):
        end, n, hit = (self.cur + 1) * BUCKET, self.n, None
        if len(self.hist) >= WARMUP:  # no judgement until there is a baseline
            med = statistics.median(self.hist)
            # cooldown: one real moment makes 2-3 hot buckets in a row -> one clip
            if n >= max(self.min, self.factor * med) and end - self.last >= self.cooldown:
                hit, self.last = (end, n, med), end
        self.hist.append(n)
        self.cur, self.n = self.cur + 1, 0
        return hit

    def tick(self, ts):
        """Close every bucket that ended before ts -> list of (end_ts, count, median)."""
        b, hits = int(ts // BUCKET), []
        if self.cur is None or b - self.cur > WINDOW:  # first call, or a long gap
            self.cur, self.n = b, 0
            self.hist.clear()
        while self.cur < b:
            h = self._close()
            if h:
                hits.append(h)
        return hits

    def feed(self, ts):
        hits = self.tick(ts)
        self.n += 1
        return hits


def selftest():
    base = 1000.0  # bucket-aligned
    def run(d, stamps, until):
        hits = d.tick(base)  # start the clock so empty buckets build the baseline
        for t in sorted(stamps):
            hits += d.feed(t)
        return hits + d.tick(until)

    quiet = [base + s for s in range(0, 260, 2)]                  # 5 msgs / 10 s
    burst = [base + 180 + i * 0.25 for i in range(40)]            # bucket 180-190
    burst2 = [base + 190 + i * 0.25 for i in range(40)]           # bucket 190-200
    h = run(Detector(2.5, 15, 30), quiet + burst + burst2, base + 270)
    assert [x[0] for x in h] == [base + 190], h                   # one spike, cooldown eats the 2nd

    small = [base + 180 + i for i in range(9)]                    # 5+9=14: >2.5x median but < --min
    assert not run(Detector(2.5, 15, 30), quiet + small, base + 270)

    dead = [base + 180 + i * 0.5 for i in range(20)]              # median 0 -> --min decides
    assert len(run(Detector(2.5, 15, 30), dead, base + 200)) == 1
    assert not run(Detector(2.5, 15, 30), dead[:5], base + 200)

    assert not run(Detector(2.5, 15, 30), [base + s for s in range(100)], base + 100)  # warmup
    print("selftest ok")


def ts_srt(t):
    h, r = divmod(int(t * 1000), 3600000)
    m, r = divmod(r, 60000)
    return f"{h:02}:{m:02}:{r // 1000:02},{r % 1000:03}"


def srt(segs):
    return "".join(f"{i}\n{ts_srt(s.start)} --> {ts_srt(s.end)}\n{s.text.strip()}\n\n"
                   for i, s in enumerate(segs, 1))


def worker(q, a):
    """One slow worker: cut -> crop -> captions. Heavy work never overlaps."""
    CLIPS.mkdir(exist_ok=True)
    model = None
    while True:
        job = q.get()
        if job is None:
            return  # sentinel: queued clips are finished first, then exit
        chan, rec, t0, end, n, med = job[:6]
        label = job[6] if len(job) > 6 else f"x{n / max(med, 1):.1f} ({n} msgs)"
        time.sleep(max(0, end + POST + 3 - time.time()))  # let the file reach spike+10 s
        start = max(0, end - PRE - t0 + a.shift)
        pad = min(5, start)  # seek early then trim: mpegts seeks land mid-GOP and eat video
        out = CLIPS / f"{chan}_{time.strftime('%Y%m%d_%H%M%S', time.localtime(end))}.mp4"
        for enc in dict.fromkeys([a.enc, "x264"]):  # iGPU encoder first, x264 as fallback
            r = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-threads", "2",
                 "-ss", f"{start - pad:.2f}", "-i", str(rec), "-ss", f"{pad:.2f}",
                 "-t", str(PRE + POST),
                 "-vf", f"crop=trunc(ih*9/16/2)*2:ih,scale={a.size}:flags=lanczos",
                 *ENC[enc], "-threads", "2",
                 "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)],
                capture_output=True, text=True,
                creationflags=0x4000 if os.name == "nt" else 0)  # BELOW_NORMAL priority
            if r.returncode == 0 and out.exists():
                break
        else:
            print(f"  cut FAILED {out.name}: {r.stderr.strip()[-300:]}", flush=True)
            continue
        print(f"  clip  {out.name}  {label}", flush=True)  # score for the filter
        # sidecar: lets finalize.py re-cut the full 16:9 frame from the recording for the final render
        out.with_suffix(".json").write_text(json.dumps(
            {"chan": chan, "rec": str(rec), "start": round(start, 2), "end": end, "n": n, "med": med}))
        if getattr(a, "final", False):  # full edit (captions/music/sfx/effects) -> final/. Never uploads.
            try:
                import finalize
                done = finalize.render(out, a)
                print(f"  final {done.name if done else 'FAILED'}", flush=True)
            except Exception as e:
                print(f"  final FAILED {out.name}: {e}", flush=True)
            continue
        if a.model == "none":
            continue
        try:
            if model is None:
                from faster_whisper import WhisperModel
                model = WhisperModel(a.model, device="cpu", compute_type="int8", cpu_threads=2,
                                     download_root=str(ROOT / "models"))  # keep models in this folder
            # task=translate -> English subtitles whatever language the streamer speaks
            # (vad_filter: less silence-hallucination)
            segs, _ = model.transcribe(str(out), vad_filter=True, task="translate")
            out.with_suffix(".srt").write_text(srt(segs), encoding="utf-8")
            print(f"  srt   {out.with_suffix('.srt').name}", flush=True)
        except Exception as e:
            print(f"  whisper FAILED {out.name}: {e}", flush=True)


async def chat(chans, on_msg):
    delay = 1
    while True:
        try:
            r, w = await asyncio.open_connection("irc.chat.twitch.tv", 6667)
            w.write(("NICK justinfan12345\r\n" + "".join(f"JOIN #{c}\r\n" for c in chans)).encode())
            await w.drain()
            delay = 1
            while line := await r.readline():
                line = line.decode("utf-8", "ignore")
                if line.startswith("PING"):
                    w.write(("PONG " + line[5:]).encode())
                    await w.drain()
                elif " PRIVMSG #" in line:
                    on_msg(line.split(" PRIVMSG #", 1)[1].split(" ", 1)[0])
        except OSError as e:
            print(f"chat: {e}; retry in {delay}s", flush=True)
        await asyncio.sleep(delay)
        delay = min(delay * 2, 30)


async def record(chan, state, stream_q):
    REC.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    while True:
        path = REC / f"{chan}_{time.strftime('%Y%m%d_%H%M%S')}.ts"  # .ts: readable while growing
        state[chan] = path
        p = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "streamlink_cli", "--retry-streams", "15", "--twitch-low-latency",
            "-o", str(path), f"twitch.tv/{chan}", stream_q,  # python -m: works without Scripts on PATH
            stdout=subprocess.DEVNULL, stderr=open(LOGS / f"{chan}.log", "ab"))
        try:
            await p.wait()
        except asyncio.CancelledError:
            p.terminate()
            raise
        if path.exists() and path.stat().st_size == 0:
            path.unlink()
        await asyncio.sleep(5)  # stream ended / failed -> try again


def birth(p):
    s = p.stat()
    return getattr(s, "st_birthtime", s.st_ctime)  # ~ when the first byte was written


async def run(a):
    q, state = queue.Queue(), {}
    dets = {c: Detector(a.factor, a.min, a.cooldown) for c in a.channels}
    log = open(a.log, "a", buffering=1) if a.log else None
    th = threading.Thread(target=worker, args=(q, a))  # non-daemon: never drop a queued clip
    th.start()

    def spike(c, hit):
        end, n, med = hit
        print(f"[{time.strftime('%H:%M:%S', time.localtime(end))}] {c}: SPIKE {n} msgs "
              f"(median {med:g})", flush=True)
        p = state.get(c)
        if p and p.exists() and p.stat().st_size:
            q.put((c, p, birth(p), end, n, med))
        else:
            print(f"  no recording for {c} yet, skipped", flush=True)

    def on_msg(c):
        if c in dets:
            now = time.time()
            if log:
                log.write(f"{now:.1f} {c}\n")
            for h in dets[c].feed(now):
                spike(c, h)

    async def ticker():
        while True:
            await asyncio.sleep(1)
            for c, d in dets.items():
                for h in d.tick(time.time()):
                    spike(c, h)

    print(f"watching {', '.join(a.channels)}  (factor {a.factor}, min {a.min}, "
          f"whisper {a.model}, enc {a.enc}, {a.stream_q})", flush=True)
    try:
        await asyncio.gather(chat(a.channels, on_msg), ticker(),
                             *(record(c, state, a.stream_q) for c in a.channels))
    finally:
        q.put(None)
        th.join()  # drain queued clips NOW: whisper's thread pool dies once the interpreter starts exiting


def replay(a):
    dets, n = {}, 0
    for line in open(a.replay):
        t, c = line.split()
        d = dets.setdefault(c, Detector(a.factor, a.min, a.cooldown))
        for end, cnt, med in d.feed(float(t)):
            n += 1
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end))}] {c}: "
                  f"SPIKE {cnt} msgs (median {med:g})")
    print(f"{n} spikes")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("channels", nargs="*")
    ap.add_argument("--min", type=int, default=15, help="min messages per 10 s to count as a spike")
    ap.add_argument("--factor", type=float, default=2.5, help="x the 3-min median")
    ap.add_argument("--cooldown", type=int, default=30, help="seconds between clips per channel")
    ap.add_argument("--model", default="base", help="whisper model: tiny|base|small|none")
    ap.add_argument("--fast", action="store_true", help="day-1 preset: factor 2.0, whisper tiny")
    ap.add_argument("--enc", choices=list(ENC), default="qsv",
                    help="qsv (Intel iGPU, default; falls back to x264) | x264 | amf (AMD)")
    ap.add_argument("--size", default="720:1280", help="output WxH (720:1280 easy on a weak CPU)")
    ap.add_argument("--shift", type=float, default=0, help="move clip window later (+) / earlier (-) s")
    ap.add_argument("--stream-q", default="best", help="streamlink quality (best = 1080p60 source; 720p60 was soft)")
    ap.add_argument("--log", help="append every chat msg timestamp here (for --replay)")
    ap.add_argument("--replay", help="run the detector over a --log file and exit")
    ap.add_argument("--final", action="store_true",
                    help="also render the full edit into final/ (captions, music, sfx, effects; never uploads)")
    ap.add_argument("--layout", choices=["crop", "blur"], default="crop", help="--final layout")
    ap.add_argument("--music", default=str(MUSIC_DIR),
                    help='--final music folder, or "none"')
    ap.add_argument("--hook", help="--final hook text (default: random from a short list)")
    ap.add_argument("--minutes", type=float, help="stop after N minutes (default: until Ctrl-C)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    a.channels = [c.lstrip("#").lower() for c in a.channels]
    if a.fast:
        a.factor, a.model = 2.0, "tiny"
    if a.selftest:
        selftest()
    elif a.replay:
        replay(a)
    elif a.channels:
        try:
            asyncio.run(asyncio.wait_for(run(a), a.minutes * 60 if a.minutes else None))
        except (KeyboardInterrupt, asyncio.TimeoutError):  # cancel -> streamlink children terminated
            print("stopped", flush=True)
    else:
        ap.error("give at least one channel")
