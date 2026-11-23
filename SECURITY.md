<!-- stream-to-shorts by Akshat96af. Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE. -->
# Security policy

**stream-to-shorts** runs entirely on your own computer. It does not send your files, keys or analytics anywhere.

- The dashboard listens on `127.0.0.1` only and refuses requests from other websites.
- The optional uploader drives your own signed-in browser; it never asks for or stores passwords.
- Downloads use `yt-dlp` and `streamlink`; browser cookies are never read unless you explicitly configure it.
- Before sharing a project folder, run `python scripts/privacy_scan.py <folder> --terms "your name,your channel"`.

## Reporting a vulnerability
Please open a private security advisory on this repository (Security tab > Report a vulnerability) with steps to
reproduce. Do not post exploit details in public issues. Reports are answered as quickly as possible.
