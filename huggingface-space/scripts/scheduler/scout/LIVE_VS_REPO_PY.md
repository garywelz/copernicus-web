# Live Jetson vs repo digests — scout `*.py` (2026-10-18)

Recorded so the first attended sync is not a silent content overwrite.

## Finding

Every listed live file under `/media/sdcard/scheduler/scout/*.py` differs in
**SHA-256** from the repo blob on `origin/main`, but the difference is
**CRLF vs LF only**. After LF-normalisation the texts are identical.

| File | Live SHA-256 (Jetson `/media/sdcard/...`) | Repo SHA-256 (`origin/main` blob) |
|------|-------------------------------------------|-----------------------------------|
| `scout_common.py` | `a88da6c0612deeee70291bc09431fa125dde73a7657dbeeddb26cf8e07b71ae7` | `5a89f07dbcf3c99779a416033d0582c6d605f9f53a9a997dffd9c57e379f3479` |
| `scout_arxiv.py` | `25f8fa4fc4eee2cdd719d1d190a7de824813b26de0d2f630d95fcbcfe6baa59d` | `bd0971ba0270b841fa882141b79adf6e5a6cd0c868f79062e31208be42486dc8` |
| `scout_biorxiv.py` | `c3fdc12b129c389c5afe4ff6c1b51f39cdd6852c799981f47ef104a44db32fd3` | `e2db5bcb5f4ef45fdb6f9109f765ef046516578dfedb19230657ad4930eeb81c` |
| `scout_pubmed.py` | `c67af1612a734ac2c3b3d13e6891c9677662d32b178796973c920fcf534d436b` | `bff313fe5bb4caceb93214b0f548304a449de5fd4480ab4f3f70ecd5403e3ac1` |
| `query_terms.py` | `6be754d03f806ef0d4ea45c29c5089af7ac5ba3be87bf84c718b59dd917b18cb` | `123b0748ff9b7221c0f3e0d19ef10a7f1c7e85c8f9b11e047afcdda2df2b0d20` |
| `glmp_pubmed_supplement.py` | `ac99b34028544e3d18eb97180f69bb334ad7f9b60dc00f8b10938bafec73bde0` | `eef53500771de78f6d07cb336be98bd6b04b129e2a1309749a7b1a0d623dd887` |

Jetson HFS checkout (`/home/gdubs/copernicus-web-public/.../scout/`) already
matches the **repo** digests (LF).

## What live has that the repo lacks

Carriage returns (`\r`) before each newline. No unique statements, imports,
or control flow.

## What the repo has that live lacks

LF-only newlines (no `\r`). Same source text otherwise.

## Decision (explicit, not silent)

**Keep the repo LF blobs** (`5a89f07…` for `scout_common.py`, etc.). Do **not**
import live CRLF into git. Python on the Jetson runs either form; git SoT and
the HFS tree must stay LF (`*.py text eol=lf`). The first attended
`sync_to_jetson.sh` after this PR copies HFS → live and rewrites live digests
from the `a88da6c0…` family to the repo family — **line endings only**, no
behaviour change.
