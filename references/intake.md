<!-- stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE. -->
# Intake: learn what the user wants⁠​‌​​​​​‌​‌‌​‌​‌‌​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​‌​​​​‌‌‌​​‌​​‌‌​‌‌​​‌‌​​​​‌​‌‌​​‌‌​⁠

Ask only what the conversation and `sts.profile.json` do not already answer. Group the questions in one message,
offer the defaults, and accept short answers. Save the answers (profile keys below) to `sts.profile.json` in the work
folder and the settings to `sts.config.json`, then confirm them in one or two lines.

## 1. About the user (profile)
| Question | Why it matters | Profile key | Default |
|---|---|---|---|
| Channel name and niche (gaming, IRL, sports, podcasts...) | tone of hooks and titles, hashtags | `channel`, `niche` | ask |
| Platform: YouTube Shorts, TikTok, Instagram Reels, several | length, safe zones, title and hashtag style | `platform` | YouTube Shorts |
| Audience language and region | caption and title language | `language` | English |
| Their own handle to mention in descriptions, if any | description template | `handle` | none |

## 2. Source and content
| Question | Maps to | Default |
|---|---|---|
| Source: live channel, finished stream or video link, local file | Step 2 path (live / vod.py / cut.py) | ask, never guess |
| Which streamers, games or videos | `--name`, credits, clip_rules.json | ask |
| Kinds of moments wanted: funny, rage, clutch, fails, story, reactions, scenery | what you keep in Step 3 | big reactions + funny |
| Anything to avoid (topics, words, people, spoilers) | Step 3 filter | 18+ always avoided |
| Do they have permission to clip these creators | safety-and-rights.md | ask when unclear |

## 3. Look and quality
| Question | Config key / flag | Options | Default |
|---|---|---|---|
| Quality vs speed | `quality` | high (slower, sharper) / balanced / fast (drafts) | balanced |
| Frame rate | `fps` | 60 (smooth) / 30 (smaller, faster) | 60 |
| Length | `clip_seconds` | 20-60 s; longer only for a story with a payoff | 45 |
| Layout | `--layout` | facecam (webcam on top) / blur (full width) / crop (centre) | facecam if a webcam is visible |
| Encoder | `encoder` | x264 / qsv (Intel) / nvenc (NVIDIA) | from check_setup |

## 4. Captions and text
| Question | Config key | Options | Default |
|---|---|---|---|
| Caption style | `caption_style` | pop (word pops and slides in) / clean (colour change only) / none | pop |
| Highlight colour | `caption_color` | yellow / green / cyan / red / orange / white | yellow |
| Case | `caption_case` | upper / normal | upper |
| Position | `caption_position` | low / middle | low |
| Hook style | your writing | question, bold claim, name + moment; max 6 words | name + moment |
| Title and hashtag style | your writing (editorial.md) | creator name first + what happens, 2-3 tags in the title | that |

## 5. Sound
| Question | Config key / flag | Default |
|---|---|---|
| Music: their own licensed tracks, or none | `music_dir`, `--music none` | none until they add tracks |
| SFX: their own files (whoosh, riser, hit, pop, shutter) | `sfx_dir` | skipped when missing |

## 6. Volume and delivery
| Question | Maps to | Default |
|---|---|---|
| How many Shorts now, and how often after that | the run plan / cadence | 6 now, no cadence |
| Upload kit only, or the optional Studio uploader | Step 6 (uploading.md) | upload kit only |
| If uploading: private or public, daily cap | `visibility`, `daily_cap` | private, 10 |
| Live dashboard while working | Step 0 monitor (monitoring.md) | no |

## Example of a good intake message
"Before I start, a few quick choices (defaults in brackets, just reply 'defaults' to use them):
1. Your channel name and niche, and the platform? (YouTube Shorts)
2. Source link or file, and which streamer? 3. What kind of moments? (big reactions + funny)
4. Quality? high / balanced / fast (balanced) 5. Captions: pop, clean or none, colour? (pop, yellow)
6. Music: your own folder or none? (none) 7. How many Shorts? (6)
8. Upload kit, or should I upload for you? (kit) 9. Want the live dashboard? (no)"

---
*Part of stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE.*
