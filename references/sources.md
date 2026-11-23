<!-- stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE. -->
# Sources: where moments come from⁠​‌​​​​​‌​‌‌​‌​‌‌​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​‌​​​​‌‌‌​​‌​​‌‌​‌‌​​‌‌​​​​‌​‌‌​​‌‌​⁠

## 1. Finished streams and videos (best signal) - `vod.py`
```
python <skill>/scripts/vod.py "<video url>" --n 6 --name <streamer> [--win 0:30:00-3:00:00] [--no-chat]
```
- Scores 10 s bins by the **most-replayed graph** (what viewers actually rewatched), the **chat replay** rate and hype
  words, and **loudness** above the rolling median; picks the top N at least 2 minutes apart, skipping the intro.
- For each pick: a 1080p section download, a preview cut and sidecar in `clips/`, a frame sheet in `logs/`, the
  transcript and the source bitrate. Then you look, choose and render.
- Refuses live streams (no replay graph yet): run it after the stream ends.
- Very long streams: pass `--win` to scan 1-3 hours at a time.
- Optional `clip_rules.json` in the work folder: `{"youtube:@handle": {"rule": "allowed|ask|no", "note": "..."}}`.
  "no" stops the run unless the user has permission.

## 2. Live channels - `clipwatcher.py` + `moments.py`
- `clipwatcher.py <channel> ... --stream-q best` records the stream (1080p60) and cuts on chat spikes
  (`--factor`, `--min`, `--cooldown`). On busy chats use a factor near 3 with 100+ messages per bucket.
- `moments.py <recording> <name> --cam x,y,w,h --last 45 --k 4` scores the streamer's voice loudness plus webcam
  motion (cutscenes never move the webcam), cuts the top K and writes a webcam contact sheet.
  `--frm <minute> --last <minutes>` scans a window of a long recording.
- Check every 10-20 minutes that the recording file still grows.
- Platforms rate-limit repeated requests (HTTP 429): back off for a few minutes.

## 3. Local files and given timestamps - `cut.py`
```
python <skill>/scripts/cut.py "<file>" 1:23:45 <streamer> [--before 20]
```
Writes the preview cut, the sidecar (pointing at the full-quality source) and an 8-frame sheet.

## Downloading sections fast and sharp
- Use MP4 formats for section downloads (vod.py's default prefers 1080p60 H.264 + AAC). Seeking inside long
  WebM/DASH streams can stall for tens of minutes.
- Test with a 60 s section first; confirm the file grows.
- Check the source bitrate: video sites often serve 1080p60 at about 3 Mbps; a live recording is often 6-8 Mbps.
- Never pass browser cookies to downloaders unless the user explicitly asks; it exposes their accounts.

## AI "ask about this video" panels
Useful for leads (timestamps to inspect), unreliable for content: they invent quotes and scene descriptions.
Verify every lead with the frame sheet and the transcript before writing a hook.

---
*Part of stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE.*
