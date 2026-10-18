# Live Jetson scout snapshot (2026-10-18)

SHA-256 digests of `/media/sdcard/scheduler/scout/` files as they ran on the
Jetson at snapshot time are in `LIVE_JETSON_SHA256SUMS.txt`.

Shell wrappers that differed in text from the repo are aligned to those live
bytes in the first commit (no behaviour change).

For `*.py`, live digests differ from repo digests **only by CRLF vs LF**. See
`LIVE_VS_REPO_PY.md`: we keep the repo LF blobs so the first HFS-based sync
rewrites live line endings without changing behaviour.
