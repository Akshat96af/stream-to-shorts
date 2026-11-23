<!-- stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE. -->
# Optional YouTube Studio uploader⁠​‌​​​​​‌​‌‌​‌​‌‌​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​‌​​​​‌‌‌​​‌​​‌‌​‌‌​​‌‌​​​​‌​‌‌​​‌‌​⁠

Opt-in only. Use it only when the user chose it at Step 0. It drives the user's own signed-in browser through a
browser automation tool (for example a Playwright MCP server); it never handles passwords.

## Setup
1. In `sts.config.json`: `"studio_url": "https://studio.youtube.com/channel/<their channel id>"`, `"visibility"`
   (`private` by default), `"daily_cap"`.
2. The browser profile must already be signed in. If a sign-in page appears, stop and ask the user to sign in.

## Flow
1. Each render appends an item to `uploader/queue.json` with `approved: false`.
2. Write the title, description and tags into the item (editorial.md) and set `approved: true` only for clips you
   checked (QC ok, frames clean).
3. `python <skill>/scripts/uploader/make_run.py build [--not-before "YYYY-MM-DD HH:MM"]` writes `uploader/run.js` with
   the approved items that fit under the daily cap. Public items need `--not-before` (a release time that has passed).
4. Run `uploader/run.js` with the browser tool (for Playwright MCP: browser_run_code_unsafe with that filename).
5. For every "ok" line, verify the Short in Studio (Content > Shorts) shows as published, then
   `python <skill>/scripts/uploader/make_run.py done "<final mp4>"`.

## Rules (each from a real failure)
- Never upload as a test or demo. Never re-upload an item that already returned ok.
- Wait for "Checks complete. No issues found" before publishing. If issues are found, stop: never "publish anyway".
- Stay under the daily cap; deleted uploads still count. If the dialog sits at "Checks will begin when SD
  processing completes", the platform limit is likely reached: stop and tell the user.
- If the script fails mid-way, the upload dialog is usually still open: finish it in that dialog (focus fields and
  click through the page) instead of uploading again, which would create a duplicate.
- Never change visibility or the cap without the user's go-ahead.

---
*Part of stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE.*
