"""Each source's status, in one sentence, written by this module and not by the model.

The model used to be given the wording as a constraint and asked to reproduce it. It reproduced it loosely and often twice: one episode
said "A company release has not been peer reviewed. OpenAI's own manuscript, not independently checked, is titled ..." as two sentences
where one would do, another said the same thing three times about the same manuscript, and a third attached the wording to the wrong
manuscript. Every one of those passed the checks, because the checks asked only that forbidden terms were absent.

So the sentence is built here, from the item's RECORD and nothing else - its class, the company that released it, whether the catalogue
lists a Lean formalization for it, and whether a notice withdraws it - and the script must carry that sentence, for each source, exactly
once. A sentence that mentions a source and makes a status claim in any other words is refused, and so is a second copy of the right one.

Nothing here calls a model, so the same script and the same list always give the same verdict.
"""
import re
from typing import Any, Dict, List, Optional, Sequence

import curated_checks as cc
import curated_sources as cs

# The vocabulary that makes a sentence a STATUS claim about a source. A sentence that names a source and uses any of it is making a claim
# about how that source stands, and must be the one sentence this module wrote.
STATUS_CUES = re.compile(
    r"\bpeer[- ]review\w*\b|\bindependently\s+(?:checked|verified|confirmed|reviewed)\b|\blean\s+formali[sz]ation\b"
    r"|\bcatalogu?e\b|\breview status\b|\bunchecked\b|\bunverified\b|\bwithdr(?:awn|ew|awal)\b|\bretract\w*\b"
    r"|\bnot been (?:checked|verified|reviewed)\b|\bown manuscript\b|\bown paper\b", re.I)


def _title(item: Dict[str, Any]) -> str:
    """The title as it is SAID. A prompt and a spoken sentence never carry LaTeX: "$`\\Re s\\gt 7/8`$" is read as words."""
    from speakable import speakable
    return speakable((item.get("title") or "").strip())


def _company(item: Dict[str, Any]) -> str:
    import curated_mode
    return curated_mode.company_of(item)


def _withdrawal_date(item: Dict[str, Any]) -> str:
    basis = (item.get("status_basis") or {}).get("withdrawal") or {}
    return str(basis.get("withdrawn_on") or "").strip()


def clause_for(item: Dict[str, Any], status: str) -> Optional[str]:
    """The CLAUSE that states this item's status, or None where the class carries no warning to give.

    Built from the record alone, and written to sit inside the sentence that introduces the claim as readily as to stand alone:

        "The irrationality exponent of pi is 2", which has not been peer reviewed or independently checked, claims to prove it.
         ^ the clause begins here ------------------------------------------^

    A PEER-REVIEWED source gets none. Its status is the ordinary case, the thing a listener assumes, and the existing checks already stop a
    script calling it verified or proved; demanding a sentence of its own produced four stilted lines in a row for one episode's four
    journal papers. The warning statuses - a company release, a preprint, a Lean entry, a withdrawal - are what a listener must be told, and
    those are written here.
    """
    company = _company(item)
    klass = item.get("class")
    if klass in (cs.COMMENTARY, cs.PEER_REVIEWED):
        return None
    # The clause is the PREDICATE alone, with no subject and no word order imposed, so the writer may put the title first ("X has not been
    # peer reviewed...") or the company first ("OpenAI's manuscript X, which has not been peer reviewed..."). Both forms carry the code's
    # words unchanged; only the arrangement is the writer's.
    if klass == cs.PREPRINT:
        return "a preprint, so it has not been peer reviewed"
    if klass == cs.COMPANY_RELEASE:
        if status == cc.STATUS_WITHDRAWN:
            when = _withdrawal_date(item)
            return f"withdrawn by {company}{f' on {when}' if when else ''}"
        if status == cc.STATUS_HAS_LEAN:
            return (f"has not been peer reviewed, and {company}'s catalogue lists a Lean formalization for it with its review status "
                    f"unchecked")
        if status == cc.STATUS_CHECKED:
            return f"has not been peer reviewed, and a cited source reports that it was checked"
        return "has not been peer reviewed or independently checked"
    return None


def sentence_for(item: Dict[str, Any], status: str) -> Optional[str]:
    """The clause as a sentence that can stand on its own, for the prompt and for a message that says what to write."""
    clause = clause_for(item, status)
    if clause is None:
        return None
    verb = "was" if clause.startswith("withdrawn") else ("is" if clause.startswith("a preprint") else "")
    return f"“{_title(item)}” {verb + ' ' if verb else ''}{clause}."


def required(run) -> List[Dict[str, Any]]:
    """Every source that must have its status stated, with the sentence it must be stated in, in list order."""
    out = []
    for item in run.items:
        clause = clause_for(item, run.status_of(item))
        if clause:
            out.append({"pid": run.pids[item["item_id"]], "item_id": item["item_id"], "title": _title(item), "clause": clause,
                        "sentence": sentence_for(item, run.status_of(item)), "status": run.status_of(item), "class": item["class"]})
    return out


def _flat(text: str) -> str:
    """A sentence as it is compared: one space between words, no quotation shapes, case-folded. The script may use straight or curly
    quotes and the model may rewrap a line; neither changes what the sentence says."""
    t = re.sub(r"[“”‘’\"']", "", text or "")
    t = t.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", t).strip().lower()


def _sentences(script: str):
    """Each spoken sentence of the script, with its speaker label removed."""
    for line in (script or "").splitlines():
        line = re.sub(r"^\s*(HOST|EXPERT)\s*:\s*", "", line.strip(), flags=re.I)
        if not line:
            continue
        for s in re.findall(r"[^.!?]+[.!?]+", line) or [line]:
            s = s.strip()
            if s:
                yield s


def _names_this_one(sentence: str, item_id: str, results: Dict[str, Dict[str, Any]]) -> bool:
    """Whether `sentence` names THIS source rather than a sibling whose title shares its words. Of every source the sentence could be
    read as naming, the one whose title it carries most of wins; a tie names none of them, so nothing is charged on a guess."""
    scored = []
    said = set(cc.words(sentence))
    for iid, rec in results.items():
        if cc.mentions(sentence, rec):
            scored.append((len(said & set(cc.words(rec.get("title") or ""))), iid))
    if not scored:
        return False
    scored.sort(reverse=True)
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return False
    return scored[0][1] == item_id


def check(script: str, run) -> List[Dict[str, Any]]:
    """Violations, deterministically: a status not stated, stated twice, or stated in words this module did not write.

    Takes no model and no randomness: the same script and list always give the same list of violations, in the same order.
    """
    want = required(run)
    said = list(_sentences(script))
    flat = [_flat(s) for s in said]
    results = {r["item_id"]: r for r in run.results()}
    out: List[Dict[str, Any]] = []

    for req in want:
        # The clause must appear VERBATIM, but it may sit inside the sentence that introduces the claim rather than stand alone: the
        # integrated form is what the published episodes use and what reads best aloud. Exactness is kept where it matters - the words
        # are the code's - while the sentence's shape is the writer's.
        target = _flat(req["clause"])
        hits = [i for i, f in enumerate(flat) if target in f]
        if not hits:
            out.append({"check": "status_sentence", "kind": "status_not_stated", "pid": req["pid"], "find": req["sentence"],
                        "message": f"The status of {req['pid']} is never stated. Say it once, in these words, either as a sentence of its "
                                   f"own or inside the sentence that introduces the claim: {req['sentence']}"})
        elif len(hits) > 1:
            out.append({"check": "status_sentence", "kind": "status_stated_twice", "pid": req["pid"], "find": said[hits[1]],
                        "message": f"The status of {req['pid']} is stated {len(hits)} times. Keep the first and remove the others: "
                                   f"{req['sentence']}"})
        # Any OTHER sentence that names this source and makes a status claim is the model's own wording, and is refused. A sentence is
        # charged to ONE source: two titles in a family share most of their words ("Sequence modeling ... with Evo" and "Genome modeling
        # ... with Evo 2"), and `cc.mentions` answers yes for both, which charged a peer-reviewed paper's sentence to a preprint.
        record = results.get(req["item_id"]) or {}
        for i, s in enumerate(said):
            if i in hits or not STATUS_CUES.search(s):
                continue
            if _names_this_one(s, req["item_id"], results):
                out.append({"check": "status_sentence", "kind": "status_in_other_words", "pid": req["pid"], "find": s,
                            "message": f"{s!r} states the standing of {req['pid']} in words of its own. Exactly one sentence may do "
                                       f"that, and it reads: {req['sentence']}"})
    return out


def prompt_block(run) -> str:
    """The sentences the script must carry, given to the writer verbatim."""
    want = required(run)
    if not want:
        return ""
    lines = ["**THE STATUS WORDING (written for you; use each one ONCE, word for word, and write no other sentence about how a source "
             "stands). The words in bold may stand as a sentence of their own or sit inside the sentence that introduces the claim, but "
             "they may not be changed:**"]
    for r in want:
        lines.append(f"- [{r['pid']}] {r['sentence']}")
        lines.append(f"      the exact words: “{r['title']}” **{r['clause']}**")
    return "\n".join(lines)
