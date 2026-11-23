<!-- stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE. -->
# Lessons learned (read once per session)⁠​‌​​​​​‌​‌‌​‌​‌‌​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​‌​​​​‌‌‌​​‌​​‌‌​‌‌​​‌‌​​​​‌​‌‌​​‌‌​⁠

Every rule here was paid for with a real failure while running a clipping channel. Each entry: what went wrong,
why it matters, and the rule. Do not repeat them.

## Uploading and the channel
1. **A "test" upload went public and burned daily quota.** The platform counts every upload, even deleted ones.
   Rule: never upload anything as a test or demo; only approved, QC-passed Shorts go up.
2. **The script said "ok" but the Short stayed a draft.** Rule: success means the platform shows "published"; verify
   in the Studio Shorts list before marking it done in the ledger.
3. **Publishing before the copyright check finished** produced drafts and "you may get a strike" warnings.
   Rule: wait for "Checks complete. No issues found"; never click "publish anyway".
4. **A modal overlay swallowed real clicks**, so uploads timed out at the title box and the Next button.
   Rule: focus fields and click buttons through the page (the bundled uploader does this).
5. **Upload stuck at "Checks will begin when SD processing completes"**: usually the daily upload limit is hit.
   Rule: stop uploading, tell the user, retry after the limit resets.
6. **The agent raised the user's upload cap by itself.** Rule: never change a limit the user set; ask.
7. **Uploads were set public when the user wanted private (and the reverse).** Rule: ask once, record it in
   `sts.config.json`, default private.

## Picking moments
8. **Loud is not good.** Most loud spikes were cutscene audio, menus or tutorial voices. Rule: a moment needs a
   premise, a payoff and a real reaction from the streamer (face or voice).
9. **Busy chats spike all the time.** Chat ratios near 2x were noise. Rule: on big chats use about 3x with 100+
   messages, and confirm with frames.
10. **AI video summaries invented quotes and scenes.** Rule: AI answers are leads; verify with frames and audio.
11. **Speed-reading transcripts produced a fake hook.** A title quoted song lyrics from the in-game radio as if the
    streamer said them. Rule: repeated, rhyming or sing-song lines are lyrics; never quote them.
12. **The same idea was posted twice** (two Shorts about the same joke). Rule: check earlier hooks in `render/meta/`.
13. **Night driving and long cinematics were cut into Shorts** and went nowhere. Rule: skip them; say the window is
    dry instead of posting filler.

## Safety
14. **Frames were not checked once and a Short with nudity went public** on a channel that already had a warning.
    Rule: look at every frame sheet for every clip; blur that segment or skip the clip. Never skip this check, even
    when told to hurry.
15. **Clips were made from a streamer who may not allow clipping.** Rule: check the streamer's rules
    (`clip_rules.json` or their channel); credit them with their real name and a link.

## Captions and text
16. **Whisper looped on music** ("like him like him like him ..."). Rule: the renderer keeps at most 2 repeats; still
    read the captions.
17. **Translate mode mangled English speech.** Rule: plain transcription for English; translate only non-English.
18. **Small speech models produced gibberish on mixed-language speech** (Hindi-English). Rule: use a larger model
    or ship that clip without captions (music and SFX carry it).
19. **Captions stopped after 30 s on 45 s Shorts** because they were transcribed from the short preview cut.
    Rule: transcribe the source segment for the full length (the renderer does).
20. **Titles quoted a line of NPC dialogue** and the user hated them. Rule: lead with the creator's name and their
    reaction ("<Streamer> Reacts To ..."), describe what happens.
21. **Emoji titles crashed the ledger on Windows** (cp1252). Rule: read and write every text file as UTF-8.

## Video and audio
22. **Music drowned the streamer.** Rule: loudness-match music to sit 14 LU under the stream audio, duck it under the
    voice, limiter without auto-level.
23. **Soft, upscaled video and a black bar** came from 720p sources and a fixed crop. Rule: record or download
    1080p60, stack webcam over gameplay, scale with lanczos, no bars.
24. **The webcam box was wrong** because the overlay moved between scenes. Rule: measure the box on a full frame of
    the exact moment.
25. **Downloaded 1080p from a video site was 3 Mbps**, softer than a live recording at 8 Mbps. Rule: check source
    bitrate (vod.py prints it); prefer the best available format.
26. **Raising the export bitrate did nothing visible**: the platform re-encodes. Rule: spend effort on source
    quality and layout, not on huge files.

## Running the pipeline
27. **Two scans wrote the same file names at once** and corrupted every clip. Rule: one process per output name.
28. **A wrong argument started a live watcher** (a test word was taken as a channel name). Rule: run self-tests
    with the exact `--selftest` flag; check a command before starting it.
29. **A background job started with nohup inside a backgrounded shell died silently.** Rule: start long jobs
    directly in the background and confirm the output file grows.
30. **A section download from a long VOD stalled for 40 minutes** (seeking from the start in a webm stream).
    Rule: use the MP4 formats vod.py picks, test a 60 s section first, watch the file grow.
31. **Repeated requests got "429 Too Many Requests".** Rule: back off; do not hammer the site.
32. **A recorder stopped and nobody noticed for an hour.** Rule: check that recordings grow (the dashboard shows REC).
33. **Long silences: 30-60 minutes with no upload and no message.** Rule: keep the cadence or explain why not; give a
    short status at each step.
34. **A third-party clipping tool was close to being run blind.** Its self-updater could replace code from the
    internet and its AI runner disabled permission prompts. Rule: read any downloaded tool before running it
    (see `safety-and-rights.md`).

---
*Part of stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE.*
