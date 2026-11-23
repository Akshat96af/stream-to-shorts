<!-- stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE. -->
# Changelog

All notable changes to **stream-to-shorts** (by Akshat96af). Versions follow [Semantic Versioning](https://semver.org).

## [1.0.0] - 2026-11-23
### Added
- Moment finders: most-replayed graph + chat replay + loudness for finished streams (`vod.py`), live chat spikes
  (`clipwatcher.py`), voice + webcam reactions (`moments.py`, `scan.py`), audio spikes for live streams (`audiowatch.py`).
- Renderer (`finalize.py`): hook on frame 1, word-pop / clean captions in 6 colours, facecam, full-width and centre
  layouts, beat-matched music, SFX, punch-in, shake and flash, loudness-normalised audio, 1080p / 1440p / 4K output.
- Automatic QC with an 8-frame check sheet; segment blur (`blur_segment.py`).
- Intake that learns the creator's channel, goals and style before making anything, saved as a profile.
- Optional live dashboard with play / delete / restore, optional YouTube Studio uploader with safety rules.
- 34 lessons learned from running a real clipping channel; editor, uploader and analyst agent briefs.
- Privacy scanner (`privacy_scan.py`) and a no-install web edition for chat apps (`stream-to-shorts-web.zip`).
