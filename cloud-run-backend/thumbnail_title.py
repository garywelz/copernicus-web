"""A thumbnail title the series template can actually set, derived from the episode's own words.

The template never cuts a word: a title it cannot set legibly is refused, the episode falls back to the channel's cover, and nobody sees it
until the feed is read. It happened twice in two days:

    ever-math-260018  "OpenAI's counterexample to Kaplansky's direct-finiteness conjecture"                      (6 words)
    ever-math-260020  "OpenAI says it has proved the Mezard-Parisi formula for diluted spin glasses. Has it?"   (14 words)

Both were fixed by hand with the same two moves, so those moves are written down here: split at the episode's own colon, or take the
subject and put the rest in the subtitle. Only the episode's words are used - nothing is invented, and no word is cut from the part that
is kept; a part that is dropped moves into the subtitle, where the template sets it in a smaller face.

Where nothing fits, the caller is told so and logs an ERROR naming the episode. The fallback to the default cover stays - an episode still
gets made - but it can no longer happen quietly.
"""
import re
from typing import Callable, List, Optional, Tuple

# A trailing question or aside the cover does not need: the title still asks it, the cover need not.
_TRAILING_ASIDE = re.compile(r"(?<=[.,;:?])\s*(?:has it|is it|does it|did it|do they|are they|can it|will it|really)\s*\??\s*$", re.I)
# A leading attribution: who says it belongs in the subtitle, the claim belongs on the cover.
_LEADING_CLAIM = re.compile(r"^\s*(?P<who>[A-Z][\w.'&-]*(?:\s+[A-Z][\w.'&-]*)?)\s+"
                            r"(?P<verb>says|said|claims|claimed|reports|reported|announces|announced)\s+"
                            r"(?P<rest>.+)$")
# "OpenAI's counterexample to Kaplansky's direct-finiteness conjecture": what the episode is ABOUT follows the preposition, and what was
# done to it - and by whom - belongs underneath.
_POSSESSIVE_CLAIM = re.compile(r"^\s*(?P<who>[A-Z][\w.&-]*['’]s)\s+(?P<what>[\w-]+)\s+(?:to|of|for|on|about)\s+(?P<rest>.+)$")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().strip(" .,;:")


def candidates(title: str) -> List[Tuple[str, str]]:
    """(title, subtitle) pairs to try, in order, all built from `title` itself.

    The order is the order a person would try: the whole thing; the whole thing without a trailing aside; the colon split; the claim with
    its attribution moved to the subtitle; and then the shorter and shorter heads of the remaining phrase, each with the rest kept in the
    subtitle so no word of the episode's title is thrown away.
    """
    out: List[Tuple[str, str]] = []
    whole = _clean(title)
    if not whole:
        return out
    out.append((whole, ""))
    trimmed = _clean(_TRAILING_ASIDE.sub("", whole))
    base = trimmed or whole
    later: List[Tuple[str, str]] = []
    if trimmed and trimmed != whole:
        # Tried after the splits below: a cover should carry the subject, not a whole sentence about it. "OpenAI says it has proved the
        # Mezard-Parisi formula for diluted spin glasses" does fit as one wrapped line, but it reads as a paragraph.
        later.append((trimmed, ""))

    # "Main words: the subtitle" - the template's own split, done explicitly so it is tried before anything is moved about.
    if ":" in base:
        head, _, tail = base.partition(":")
        head, tail = _clean(head), _clean(tail)
        if head and tail:
            out.append((head, tail))
            out.append((tail, head))               # the subject is often after the colon

    # "OpenAI says it has proved X" -> X on the cover, "OpenAI says it has a proof" underneath.
    m = _LEADING_CLAIM.match(base)
    if m:
        rest = _clean(re.sub(r"^(?:it\s+has\s+|that\s+|the\s+)?", "", m.group("rest"), flags=re.I))
        rest = _clean(re.sub(r"^(?:proved|proven|solved|found|shown|disproved)\s+(?:the\s+|a\s+|an\s+)?", "", rest, flags=re.I))
        who = _clean(m.group("who"))
        if rest and who:
            out.append((rest, f"{who} {_clean(m.group('verb'))} it has a proof" if "prov" in m.group("rest").lower()
                        else f"{who} {_clean(m.group('verb'))} so"))

    # "OpenAI's counterexample to Kaplansky's conjecture" -> the conjecture on the cover, whose counterexample underneath. The thing the
    # episode is ABOUT comes after the preposition; what was done to it, and by whom, goes below.
    m = _POSSESSIVE_CLAIM.match(base)
    if m:
        rest, who, what = _clean(m.group("rest")), _clean(m.group("who")), _clean(m.group("what"))
        if rest and who and what:
            out.append((rest, f"{who} {what}"))

    out += later                                       # the whole sentence, once the splits have had their turn

    # Shorter and shorter heads, with every remaining word kept in the subtitle.
    words = base.split()
    for keep in range(min(7, len(words) - 1), 1, -1):
        head, tail = _clean(" ".join(words[:keep])), _clean(" ".join(words[keep:]))
        if head and tail:
            out.append((head, tail))

    seen, unique = set(), []
    for pair in out:
        if pair not in seen:
            seen.add(pair)
            unique.append(pair)
    return unique


def fits(title: str, renders: Callable[[str, str], None]) -> Optional[Tuple[str, str]]:
    """The first candidate the template can set, or None. `renders(title, subtitle)` raises TitleDoesNotFit when it cannot be set.

    ONLY that exception is a miss. Anything else - a missing font, an unreadable template, a bug - is a real failure and must travel, or
    the caller reports "no title fits" when the truth is that nothing could be drawn at all.
    """
    import series_thumbnail

    for t, sub in candidates(title):
        try:
            renders(t, sub)
            return t, sub
        except series_thumbnail.TitleDoesNotFit:
            continue
    return None


def derive(title: str) -> Optional[Tuple[str, str]]:
    """The first candidate the real template can set, or None. Renders both sizes, because a title can fit one and not the other."""
    import series_thumbnail

    def renders(t: str, sub: str) -> None:
        series_thumbnail.render_16x9(t, subtitle=sub) if sub else series_thumbnail.render_16x9(t)
        series_thumbnail.render_square(t, subtitle=sub) if sub else series_thumbnail.render_square(t)

    return fits(title, renders)
