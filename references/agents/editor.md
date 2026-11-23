<!-- stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE. -->
# Editor agent brief (one clip per run)⁠​‌​​​​​‌​‌‌​‌​‌‌​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​‌​​​​‌‌‌​​‌​​‌‌​‌‌​​‌‌​​​​‌​‌‌​​‌‌​⁠

Use when the main agent hands clips to sub-agents. Input: a clip name `<name>` (clips/<name>.mp4 + .json exist).
Goal: one premium Short that beats the previous one. Never upload; never edit the uploader ledger's approval fields.
1. Read `learnings/latest.md` if it exists (what worked, what failed) and `references/lessons-learned.md`.
2. `python <skill>/scripts/finalize.py clips/<name>.mp4 --transcript-only --preview`: read the transcript and LOOK at
   `clips/<name>.sheet.jpg`. Apply the creator's content filter; when unsure, skip and say why.
3. Worth posting only with premise + payoff + a real reaction, understandable cold (references/editorial.md).
4. Write 3 hooks from what you SAW and HEARD, pick the best (max 6 words, caps, only what the clip shows).
5. Render with the right layout and the creator's settings; then check the QC json and the QC sheet; fix at most twice.
6. Report in at most 8 lines: file, hook, layout, QC, why it can perform, one title idea. Or SKIP + reason.

---
*Part of stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE.*
