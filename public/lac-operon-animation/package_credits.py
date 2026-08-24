"""Append a silent credits end-still + player chrome opt-in.

Call this at package time for EVERY NEW animated podcast. There is no
Cloud Run cues pipeline — Cantor/Gödel/lac/GAL were packed by hand —
so this is the hook the next episode must run before GCS upload.

Do NOT run against locked existing episodes (ever-math-260001..260006,
ever-bio-260009, ever-bio-260010). Do not commit the PNG.

Writes (into --out, which should be the episode pack dir, not git):
  - credits.png  (silent end still)
  - cues.json    with "credits": true and a last cue role=credits
  - player.html  copy of the shared player (for per-episode GCS upload)

Usage:
  python package_credits.py --cues /tmp/new-ep/cues.json --out /tmp/new-ep
  python package_credits.py --self-test
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PLAYER_HTML = HERE / "player.html"

CHROME_LINE = (
    "CopernicusAI briefing · AI-written script, ElevenLabs voice, "
    "human-published. Player code: MIT. Audio, voice, and discussed papers are not."
)

STILL_LINES = (
    "A CopernicusAI briefing · Gary Welz",
    "Sources named in the player.",
    "Code for the player is MIT. This audio is not a public-license release.",
)

CREDITS_STILL_NAME = "credits.png"
CREDITS_CUE_ID = "credits"
CREDITS_CUE_LABEL = "Credits"

# Existing animated episodes. Never attach credits or upload a still onto these.
LOCKED_EPISODES = frozenset(
    {
        "ever-math-260001",
        "ever-math-260002",
        "ever-math-260003",
        "ever-math-260004",
        "ever-math-260005",
        "ever-math-260006",
        "ever-bio-260009",
        "ever-bio-260010",
    }
)


class LockedEpisodeError(RuntimeError):
    """Raised when a pack targets an existing episode that must stay unchanged."""


def episode_opts_in(data: dict[str, Any] | None) -> bool:
    """Same contract as player.html: chrome only when the pack opts in."""
    if not data:
        return False
    if data.get("credits") is True:
        return True
    for cue in data.get("cues") or []:
        if _is_credits_cue(cue):
            return True
    return False


def _is_credits_cue(cue: Any) -> bool:
    if not isinstance(cue, dict):
        return False
    if cue.get("role") == "credits":
        return True
    image = str(cue.get("image") or "")
    name = image.split("?", 1)[0].rsplit("/", 1)[-1]
    return name.lower() == CREDITS_STILL_NAME


def assert_unlocked(episode: str) -> None:
    if episode in LOCKED_EPISODES:
        raise LockedEpisodeError(
            f"{episode} is a locked existing episode. Credits are future-only."
        )


def infer_image_prefix(data: dict[str, Any]) -> str:
    for cue in data.get("cues") or []:
        image = str(cue.get("image") or "")
        if "/" in image:
            return image.split("?", 1)[0].rsplit("/", 1)[0]
    episode = data.get("episode") or "episode"
    return (
        "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage"
        f"/animations/{episode}"
    )


def infer_duration(data: dict[str, Any], override: float | None = None) -> float:
    if override is not None:
        return float(override)
    for key in ("duration", "estimated_duration_s"):
        value = data.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    cues = data.get("cues") or []
    times = [float(c["t"]) for c in cues if isinstance(c, dict) and "t" in c]
    if not times:
        raise ValueError("cues.json has no duration and no cue times")
    return max(times)


def credits_cue(image_url: str, t: float) -> dict[str, Any]:
    return {
        "id": CREDITS_CUE_ID,
        "t": float(t),
        "label": CREDITS_CUE_LABEL,
        "role": "credits",
        "image": image_url,
    }


def attach_credits(
    data: dict[str, Any],
    *,
    image_url: str,
    duration: float | None = None,
) -> dict[str, Any]:
    """Return a copy of cues.json with chrome opt-in and a last credits cue.

    Does not write files. Refuses locked episodes. Idempotent if already attached.
    """
    episode = str(data.get("episode") or "")
    assert_unlocked(episode)

    out = json.loads(json.dumps(data))
    cues = list(out.get("cues") or [])
    t = infer_duration(out, duration)

    if cues and _is_credits_cue(cues[-1]):
        cues[-1] = credits_cue(image_url, t)
    else:
        cues = [c for c in cues if not _is_credits_cue(c)]
        cues.append(credits_cue(image_url, t))

    out["cues"] = cues
    out["credits"] = True
    return out


def render_credits_still(path: Path, dpi: int = 140) -> Path:
    """Render the silent end still. Output is for GCS, not git."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12.0, 6.75), facecolor="#F8FAFC")
    ax.set_facecolor("#F8FAFC")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.plot([0.18, 0.82], [0.72, 0.72], color="#CBD5E1", lw=1, solid_capstyle="butt")
    ax.text(
        0.5,
        0.58,
        STILL_LINES[0],
        ha="center",
        va="center",
        fontsize=18,
        color="#0F172A",
        fontname="DejaVu Sans",
    )
    ax.text(
        0.5,
        0.44,
        STILL_LINES[1],
        ha="center",
        va="center",
        fontsize=13,
        color="#334155",
        fontname="DejaVu Sans",
    )
    ax.text(
        0.5,
        0.32,
        STILL_LINES[2],
        ha="center",
        va="center",
        fontsize=12,
        color="#475569",
        fontname="DejaVu Sans",
        wrap=True,
    )
    fig.savefig(path, dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return path


def package_credits(
    cues_path: Path,
    out_dir: Path,
    *,
    episode: str | None = None,
    duration: float | None = None,
    image_prefix: str | None = None,
    copy_player: bool = True,
    write_still: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    data = json.loads(Path(cues_path).read_text(encoding="utf-8"))
    if episode:
        data["episode"] = episode
    episode_id = str(data.get("episode") or "")
    assert_unlocked(episode_id)

    prefix = (image_prefix or infer_image_prefix(data)).rstrip("/")
    image_url = f"{prefix}/{CREDITS_STILL_NAME}"
    updated = attach_credits(data, image_url=image_url, duration=duration)

    if dry_run:
        return updated

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if write_still:
        render_credits_still(out_dir / CREDITS_STILL_NAME)
    (out_dir / "cues.json").write_text(
        json.dumps(updated, indent=2) + "\n", encoding="utf-8"
    )
    if copy_player:
        if not PLAYER_HTML.is_file():
            raise FileNotFoundError(f"shared player missing: {PLAYER_HTML}")
        shutil.copy2(PLAYER_HTML, out_dir / "player.html")
    return updated


def _self_test() -> None:
    legacy = {
        "episode": "ever-math-260002",
        "duration": 542.5,
        "cues": [
            {"id": "t0", "t": 0.0, "label": "Title", "image": "https://example.test/t0.png"}
        ],
    }
    assert not episode_opts_in(legacy)
    try:
        attach_credits(legacy, image_url="https://example.test/credits.png")
    except LockedEpisodeError:
        pass
    else:
        raise AssertionError("locked episode must be refused")

    future = {
        "episode": "ever-math-260099",
        "duration": 120.0,
        "cues": [
            {
                "id": "f0",
                "t": 0.0,
                "label": "Science",
                "image": "https://example.test/animations/ever-math-260099/f0.png",
            },
            {
                "id": "f1",
                "t": 40.0,
                "label": "More science",
                "image": "https://example.test/animations/ever-math-260099/f1.png",
            },
        ],
    }
    assert not episode_opts_in(future)
    attached = attach_credits(
        future, image_url="https://example.test/animations/ever-math-260099/credits.png"
    )
    assert episode_opts_in(attached)
    assert attached["credits"] is True
    assert attached["cues"][-1]["role"] == "credits"
    assert attached["cues"][-1]["t"] == 120.0
    assert attached["cues"][-1]["id"] == "credits"
    assert not _is_credits_cue(attached["cues"][0])
    again = attach_credits(
        attached, image_url="https://example.test/animations/ever-math-260099/credits.png"
    )
    assert sum(1 for c in again["cues"] if _is_credits_cue(c)) == 1

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cues_path = tmp_path / "cues.json"
        cues_path.write_text(json.dumps(future), encoding="utf-8")
        packaged = package_credits(cues_path, tmp_path)
        assert (tmp_path / CREDITS_STILL_NAME).is_file()
        assert (tmp_path / "player.html").is_file()
        on_disk = json.loads((tmp_path / "cues.json").read_text(encoding="utf-8"))
        assert on_disk["credits"] is True
        assert on_disk["cues"][-1]["role"] == "credits"
        assert packaged["cues"][-1]["image"].endswith("/credits.png")

    print("package_credits self-test ok")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cues", help="Existing cues.json to copy and extend")
    parser.add_argument("--out", help="Episode pack directory (PNG + cues; not for git)")
    parser.add_argument("--episode", help="Override episode id on the written pack")
    parser.add_argument("--duration", type=float, help="Audio duration in seconds")
    parser.add_argument("--image-prefix", dest="image_prefix", help="GCS URL prefix for frames")
    parser.add_argument(
        "--no-player",
        action="store_true",
        help="Do not copy player.html into the pack",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the opted-in cues.json; write nothing",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        _self_test()
        return

    if not args.cues:
        parser.error("--cues is required (or pass --self-test)")
    cues_path = Path(args.cues)
    out_dir = Path(args.out) if args.out else cues_path.parent
    updated = package_credits(
        cues_path,
        out_dir,
        episode=args.episode,
        duration=args.duration,
        image_prefix=args.image_prefix,
        copy_player=not args.no_player,
        write_still=not args.dry_run,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        sys.stdout.write(json.dumps(updated, indent=2) + "\n")
        return
    print(f"Wrote credits pack in {out_dir}")
    print(f"  credits.png  last cue t={updated['cues'][-1]['t']}")
    print("  cues.json    credits=true")
    if not args.no_player:
        print("  player.html  copied from shared player")


if __name__ == "__main__":
    main()
