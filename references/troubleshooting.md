<!-- stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE. -->
# Troubleshooting⁠​‌​​​​​‌​‌‌​‌​‌‌​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​‌​​​​‌‌‌​​‌​​‌‌​‌‌​​‌‌​​​​‌​‌‌​​‌‌​⁠

| Symptom | Cause | Fix |
|---|---|---|
| `check_setup.py` says ffmpeg missing | not installed or not on PATH | install it, open a new terminal |
| faster-whisper import error about `av` | incompatible PyAV | `pip install "av>=14,<17"` |
| Render is very slow | x264 on a weak CPU | set `encoder` to `qsv` (Intel) or `nvenc` (NVIDIA) |
| Captions stop before the end | old cache from a short cut | delete `clips/<name>.words.json`, render again |
| Captions show song lyrics or repeats | music in the audio | edit `clips/<name>.words.json`, render again |
| Captions are gibberish | mixed-language speech, small model | larger model, or `[]` in words.json (no captions) |
| Webcam shows the wrong area | overlay moved | measure the box on a full frame of this moment |
| Section download stuck at a few KB | WebM/DASH seek from the start | use vod.py's MP4 formats; test 60 s first |
| HTTP 429 from the video site | rate limit | wait a few minutes, fewer requests |
| Scan output empty or corrupt clips | two processes wrote the same names | run one scan at a time, delete the broken cuts |
| Upload times out on the title box or Next | an overlay intercepts clicks | the uploader focuses fields; finish in the open dialog |
| Upload stuck at "Checks will begin..." | daily upload limit reached | stop, retry after it resets |
| Ledger crash with an emoji | non-UTF-8 read | the scripts use UTF-8; do the same in your own edits |
| Dashboard shows "loading..." | opened in a preview pane that blocks local files | open it in a normal browser or via dash.py |

---
*Part of stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE.*
