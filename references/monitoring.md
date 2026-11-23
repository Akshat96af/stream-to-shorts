<!-- stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE. -->
# Monitoring dashboard (optional)⁠​‌​​​​​‌​‌‌​‌​‌‌​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​‌​​​​‌‌‌​​‌​​‌‌​‌‌​​‌‌​​​​‌​‌‌​​‌‌​⁠

Ask at Step 0 whether the user wants it. It is never required and never starts on its own.

- `python <skill>/scripts/dash.py` serves the dashboard at http://127.0.0.1:8765 (this computer only; requests from
  other sites are refused, only the dashboard and the Shorts files are served).
- It shows the current stage and step tracker, uploads in the last 24 h against the cap, the time since the last
  post, every finished Short as a cover card (posted, queued or rendered, QC loudness, layout, music, SFX; click to
  play, "Frames" for the QC sheet), recordings with a live REC marker, and the latest log lines.
- **Delete** on a card moves that Short (video, cover, QC, metadata) to `render/trash/<name>/` and marks it trashed
  in the ledger; **Restore** puts it back. Nothing is deleted for good, and the platform is never touched.
- Opening `status.html` directly as a file works too, view-only.
- Keep it current while you work: `python <skill>/scripts/status.py <scan|render|upload|check|idle> "note"` at each
  stage, `python <skill>/scripts/status.py posted` after each publish, or `status.py loop` in the background.
- It uses about 25 MB of memory; stop it with Ctrl+C when not needed.

---
*Part of stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE.*
