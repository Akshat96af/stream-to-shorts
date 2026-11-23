<!-- stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE. -->
# Safety, rights and third-party code⁠​‌​​​​​‌​‌‌​‌​‌‌​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​‌​​​​‌‌‌​​‌​​‌‌​‌‌​​‌‌​​​​‌​‌‌​​‌‌​⁠

## Content filter (the creator chooses: `content_filter` in sts.config.json)
| Setting | What it does | For |
|---|---|---|
| `strict` (default) | the renderer skips clips whose transcript has sexual words, and you blur or skip any frame with nudity or sexual content | most channels, family-friendly platforms, channels with warnings |
| `standard` | same transcript gate; you judge frames by the target platform's own rules | general gaming channels |
| `off` | no automatic gate; only the platform's rules apply | mature channels on platforms that allow it |
Ask at intake which one fits. Platforms enforce their own rules regardless: a channel with warnings can be removed
by one more violation, so recommend `strict` when in doubt. Whatever the setting, keep other people's private data
(addresses, phone numbers, private messages) out of clips.

## Keep YOUR data out of what you share
Before publishing a project, a skill copy or a support bundle, run
`python <skill>/scripts/privacy_scan.py <folder> --terms "your name,your channel,@handle"`. It finds e-mails, channel
ids, user names in paths, API keys, phone numbers, IP addresses and your listed words, and exits non-zero on a hit.

## Clipping permission and credit
- Clip only creators who allow it or who gave permission; some forbid reposting or ask you to wait until their
  own editors have posted. Keep their rules in `clip_rules.json` and follow "no".
- Always credit the creator by their real name and link the source stream or video in the description.

## Music and SFX rights
- The skill ships no music or sound effects. Use tracks you own or that are licensed for your use. Copyrighted
  music may be muted, claimed or blocked; treat "music vs no music" as an experiment and watch for claims.

## Platform rules
- Respect the platform's upload limits and terms; do not automate around a limit or a verification step.
- Never type passwords or handle payment details; the user signs in themselves.

## Third-party tools and skills
Before running any downloaded clipping tool or skill, read its code. Refuse to run, or disable, parts that:
- download and replace their own code from the internet (self-updaters without a real signature),
- start AI agents with permission prompts turned off over untrusted text (transcripts, chat),
- read browser cookies or saved passwords,
- send your files or keys to third-party services you did not choose.

---
*Part of stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE.*
