"""The voices an episode may use, keyed by voice id.

A role used to be worked out from a speaker's NAME: the service held a six-entry map from voice id to name, looked the chosen ids up in it,
and matched those names against the script. Any voice outside those six fell back silently to "Matilda" and "Adam", so the host's lines could
be read in the expert's voice. A roster keyed by id removes the guesswork: the id names the voice, and the script's own HOST:/EXPERT: label
names the role.

Each entry records what the roster was chosen for - gender, age and accent - so a mix can be seen at a glance and a replacement can be picked
on purpose. Every voice here is an ElevenLabs premade voice, not a community one.
"""
from typing import Dict, Optional

HOST, EXPERT = "host", "expert"

# voice_id -> (spoken name, gender, age, accent, what it is for)
ROSTER: Dict[str, Dict[str, str]] = {
    # the anchor host
    "XrExE9yKIg1WjnnlVkGX": {"name": "Matilda", "gender": "female", "age": "middle aged", "accent": "american",
                             "note": "the anchor host: knowledgeable, professional"},
    # expert roster
    "Xb7hH8MSUJpSbSDYk0k2": {"name": "Alice", "gender": "female", "age": "middle aged", "accent": "british",
                             "note": "clear, engaging educator"},
    "onwK4e9ZLuTAKqWW03F9": {"name": "Daniel", "gender": "male", "age": "middle aged", "accent": "british",
                             "note": "steady broadcaster"},
    "JBFqnCBsd6RMkjVDRZzb": {"name": "George", "gender": "male", "age": "middle aged", "accent": "british",
                             "note": "warm, captivating storyteller"},
    "pqHfZKP75CvOlQylNhV4": {"name": "Bill", "gender": "male", "age": "old", "accent": "american",
                             "note": "wise, mature, balanced"},
    "cjVigY5qzO86Huf0OWal": {"name": "Eric", "gender": "male", "age": "middle aged", "accent": "american",
                             "note": "smooth, trustworthy"},
    "SAz9YHcvj6GT2YYXdXww": {"name": "River", "gender": "neutral", "age": "middle aged", "accent": "american",
                             "note": "relaxed, neutral, informative"},
    "hpp4J3VqNfWAUOO0d1Us": {"name": "Bella", "gender": "female", "age": "middle aged", "accent": "american",
                             "note": "bright, professional"},
    "IKne3meq5aSn9XLyUdCD": {"name": "Charlie", "gender": "male", "age": "young", "accent": "australian",
                             "note": "deep, confident"},
    # voices the service already knew, kept so an episode recorded with one still resolves
    "EXAVITQu4vr4xnSDxMaL": {"name": "Sarah", "gender": "female", "age": "young", "accent": "american",
                             "note": "mature, reassuring (recorded as Bella in older episodes)"},
    "pNInz6obpgDQGcFmaJgB": {"name": "Adam", "gender": "male", "age": "middle aged", "accent": "american",
                             "note": "the former default expert"},
}

DEFAULT_HOST_ID = "XrExE9yKIg1WjnnlVkGX"
DEFAULT_EXPERT_ID = "cjVigY5qzO86Huf0OWal"       # Eric: calm and measured, the roster's default expert

EXPERT_IDS = tuple(vid for vid in ROSTER if vid != DEFAULT_HOST_ID)


def name_for(voice_id: Optional[str], default: str = "") -> str:
    """The spoken name of a voice. An id outside the roster returns `default`, never another voice's name."""
    if not voice_id:
        return default
    entry = ROSTER.get(voice_id)
    return entry["name"] if entry else default


def is_known(voice_id: Optional[str]) -> bool:
    return bool(voice_id) and voice_id in ROSTER


def role_for_label(label: str) -> Optional[str]:
    """The role a script line belongs to, from its own label. This is what decides which voice reads a line; a name decides nothing."""
    if not label:
        return None
    flat = label.strip().rstrip(":").strip().lower()
    if flat in ("host", "questioner", "interviewer"):
        return HOST
    if flat in ("expert", "correspondent", "guest"):
        return EXPERT
    return None


def voice_for_role(role: str, host_voice_id: Optional[str] = None, expert_voice_id: Optional[str] = None) -> str:
    """The voice id that reads a role's lines: what the request asked for, else the roster's default."""
    if role == HOST:
        return host_voice_id or DEFAULT_HOST_ID
    return expert_voice_id or DEFAULT_EXPERT_ID


def describe(voice_id: str) -> str:
    e = ROSTER.get(voice_id)
    if not e:
        return f"{voice_id} (not in the roster)"
    return f"{e['name']} ({e['gender']}, {e['age']}, {e['accent']}): {e['note']}"


def id_to_name() -> Dict[str, str]:
    """The id-to-name map the voice service needs, built from the roster rather than written out again."""
    return {vid: e["name"] for vid, e in ROSTER.items()}
