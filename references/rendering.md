<!-- stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE. -->
# Rendering: layouts, captions, audio, QC⁠​‌​​​​​‌​‌‌​‌​‌‌​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​‌​​​​‌‌‌​​‌​​‌‌​‌‌​​‌‌​​​​‌​‌‌​​‌‌​⁠

## Command
```
python <skill>/scripts/finalize.py clips/<name>.mp4 --layout facecam --cam x,y,w,h --hook "HOOK" [--hide-subs] [--music none] [--lang hi]
```
Helpful extra modes: `--transcript-only` (print captions and stop), `--preview` (8-frame sheet of the cut),
`--triage` (cheap PASS/SKIP on 18+ words and flat audio).

## Layouts
- **facecam**: webcam on top (520 px), gameplay below and larger. Use it whenever the stream has a webcam: viewers
  come for the reaction. `--cam x,y,w,h` = the webcam box as fractions of the full frame; measure it on a full frame
  of this exact moment (cut.py and vod.py sheets), because overlays move between scenes.
- **blur**: the full 16:9 frame over a blurred copy; best for cinematic, wide scenes.
- **crop**: centre 9:16 crop for action in the middle of the screen.
- `--hide-subs`: soft blur of the bottom strip where the game's own subtitles sit (when they are profane or cut off).

## Quality
- Output size is the creator's choice: `resolution` 1080 (1080x1920), 1440 (1440x2560) or 2160 (4K, 2160x3840), at
  `fps` 60 or 30. Pick what the source and the PC support: a higher size than the source adds render time, not detail.
- Lanczos scaling, light sharpening, no black bars, layouts and captions scale with the size.
- Encoders: `x264` works everywhere; `qsv` (Intel) and `nvenc` (NVIDIA) are faster. Set `encoder` in sts.config.json.
- Higher bitrate is not better past a point: the platform re-encodes. Fix the source and the layout instead.

## Captions
- Transcribed from the SOURCE segment for the full length (not from the preview cut).
- English speech: plain transcription. Non-English: translated to English, or forced with `--lang`. Mixed
  languages (for example Hindi-English) often come out as gibberish on small models: use a larger model or render
  with no captions (write `[]` to `clips/<name>.words.json`).
- Low-confidence words are dropped, Whisper repeat-loops are cut to 2 repeats, strong profanity is softened.
- Animation: the spoken word pops in yellow (124 % then 108 %), each group slides up and fades in, thick outline and
  shadow. Hook box on top from frame 0 for 3.5 s, no fade-in.

## Audio
- Stream voice +3 dB when it is quiet; music is loudness-matched to sit 14 LU below the stream audio and ducks while
  the streamer talks; loudness normalised to -15 LUFS, true peak -2 dB, limiter without auto-level.
- Music: your own licensed tracks in `music/`. The renderer starts each track so its drop lands on the moment.
  `--music none` when the voice carries the clip.
- SFX: your own files in `sfx/whoosh`, `sfx/riser`, `sfx/hit`, `sfx/pop`, `sfx/shutter`. A whoosh opens, a riser ends
  on the moment, a hit lands on it, soft pops on caption groups. Missing folders are skipped.

## Effects at the moment
Punch-in zoom, a short shake and a white flash at the loudest point between 6 s and 24 s, plus a light grade and
vignette. No fades at the start: frame 1 must already show the hook.

## Length
Default `clip_seconds` 45 (20 s before the moment, 25 s after). A story with a payoff may need more: raise it for
that clip. QC accepts length +/- 2 s around the setting.

## QC (automatic) and your check
QC json: size, length, peak at most -1 dBFS, loudness -19 to -11 LUFS, no black frames, no silence over 1.5 s.
Then LOOK at `render/qc/<stem>.qc.jpg`: hook readable, captions off faces, the moment visible, nothing 18+.

## Blurring one segment (instead of dropping a good clip)
ffmpeg overlay of a strong box blur on the gameplay area for the bad seconds, for example the bottom 64 % for the
first 9 s: `split[a][b];[b]crop=iw:ih*0.64:0:ih*0.36,boxblur=50:6[bl];[a][bl]overlay=0:H*0.36:enable='lt(t,9)'`,
then re-encode and check the frames again.

---
*Part of stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE.*
