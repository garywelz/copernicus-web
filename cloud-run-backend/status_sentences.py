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


# The same words in the plural, for a clause that covers several sources at once: "Both are preprints, so they have not been peer
# reviewed" is how a person says it, and saying it once per source instead reads as a list. Only the two clauses that can sensibly be
# shared have a collective form; a Lean entry and a withdrawal are facts about one manuscript and are always stated singly.
COLLECTIVE_CLAUSES = {
    "a preprint, so it has not been peer reviewed": "preprints, so they have not been peer reviewed",
    "has not been peer reviewed or independently checked": "have not been peer reviewed or independently checked",
}
# What makes a sentence collective. Without one of these the plural wording is not read as covering anybody but its own subject.
COLLECTIVE_REF = re.compile(r"\b(?:both|these|those|all three|all four|all of them|all of these|each of them|neither|none of these|"
                            r"the others|the rest)\b", re.I)


def collective_clause_for(clause: str) -> Optional[str]:
    """The plural form of `clause`, or None where the fact belongs to one manuscript alone."""
    return COLLECTIVE_CLAUSES.get(clause)


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
    # A title carried whole decides, before any word counting: "A preprint paper 1" and "A preprint paper 2" differ only in a digit, and
    # the word comparison drops digits, so counting words cannot tell them apart while reading plainly can.
    flat = _flat(sentence)
    whole = [iid for iid, rec in results.items() if (rec.get("title") or "").strip() and _flat(rec["title"]) in flat]
    if len(whole) == 1:
        return whole[0] == item_id
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


def _collective_hits(req: Dict[str, Any], said: Sequence[str], flat: Sequence[str], results: Dict[str, Dict[str, Any]]) -> List[int]:
    """The sentences that state this source's status as one of several, or [] if there are none.

    A collective clause counts for every source it covers, and only if every source it refers to really has that status. The sources it
    refers to are the ones it NAMES; a sentence that names a source whose own clause is different - a peer-reviewed paper lumped in with
    preprints - covers nobody, and the sources it was meant to cover are reported as unstated. Judged on the record alone, as the "these
    manuscripts" Lean rule is.
    """
    plural = collective_clause_for(req["clause"])
    if not plural:
        return []
    want = _flat(plural)
    found = []
    for i, f in enumerate(flat):
        if want not in f or not COLLECTIVE_REF.search(said[i]):
            continue
        named = [iid for iid, rec in results.items() if cc.mentions(said[i], rec)]
        # Every source the sentence names must be one this clause is true of.
        if any(_clause_of(iid, results) != req["clause"] for iid in named):
            continue
        found.append(i)
    return found


def _clause_of(item_id: str, results: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """The clause a source requires, from the record carried on its result row."""
    rec = results.get(item_id) or {}
    return rec.get("_clause")


def check(script: str, run) -> List[Dict[str, Any]]:
    """Violations, deterministically: a status not stated, stated twice, or stated in words this module did not write.

    Takes no model and no randomness: the same script and list always give the same list of violations, in the same order.
    """
    want = required(run)
    said = list(_sentences(script))
    flat = [_flat(s) for s in said]
    results = {r["item_id"]: r for r in run.results()}
    # Each row carries the clause its source requires, so a collective sentence can be judged against every source it names - including a
    # peer-reviewed one, whose clause is None.
    by_id = {i["item_id"]: i for i in run.items}
    for iid, rec in results.items():
        rec["_clause"] = clause_for(by_id[iid], run.status_of(by_id[iid])) if iid in by_id else None
    out: List[Dict[str, Any]] = []

    for req in want:
        # The clause must appear VERBATIM, but it may sit inside the sentence that introduces the claim rather than stand alone: the
        # integrated form is what the published episodes use and what reads best aloud. Exactness is kept where it matters - the words
        # are the code's - while the sentence's shape is the writer's.
        # A singular hit must NAME this source. Two preprints share a clause word for word, so a sentence about one of them would
        # otherwise satisfy both, and a sentence each would look like a repeat to both.
        target = _flat(req["clause"])
        hits = [i for i, f in enumerate(flat) if target in f and _names_this_one(said[i], req["item_id"], results)]
        shared = _collective_hits(req, said, flat, results)
        if shared and not hits:
            hits = shared                               # covered by a clause that speaks for several sources at once
        elif shared and hits:
            out.append({"check": "status_sentence", "kind": "status_stated_twice", "pid": req["pid"], "find": said[shared[0]],
                        "message": f"The status of {req['pid']} is stated on its own and again in a sentence covering several sources. "
                                   f"Keep one of them: {req['sentence']}"})
            continue
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
    shared = sorted({collective_clause_for(r["clause"]) for r in want if collective_clause_for(r["clause"])})
    if shared:
        lines.append("Where several sources share a status you may say it once for all of them, with these words instead: "
                     + "; ".join(f"“... are {s}”" for s in shared)
                     + ". A sentence like that must cover only sources that really have that status.")
    return "\n".join(lines)
