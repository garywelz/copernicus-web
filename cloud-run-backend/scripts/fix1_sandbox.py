"""Sandbox harness for gap 3 fix 1: regenerate past topics with the new pipeline, publish nothing.

For each topic it runs, with the same code the job runs: the research phase (registry confirmation, numbered
papers, fail-early), the generate-and-check loop (naming check, regeneration, fail), and the description
post-processing (code-built References and Further reading, placeholder cleanup, the 4000-character limit).
Everything is written to local files under --out. It never touches Firestore, Cloud Storage, ElevenLabs, email,
the feed or the corpus, and it stops when the spend ceiling would be exceeded.

  python scripts/fix1_sandbox.py --topics topics.json --out OUT --ledger LEDGER.jsonl [--ceiling 4.0] [--only ID] [--stub]

--stub runs the whole flow offline with scripted fakes (no network, no keys): it is how the harness is tested.
Live mode needs Secret Manager access for the research and Google AI keys, and makes real registry and model calls.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from dataclasses import asdict
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The pipeline prints emoji; a Windows console or pipe defaults to cp1252 and would raise on them.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover
        pass

# The sandbox must never use the Vertex path or write anywhere: switch Vertex off before the service is imported.
os.environ["DISABLE_VERTEX_AI"] = "1"

try:  # the service imports psutil, which is not installed everywhere
    import psutil  # noqa: F401
except ImportError:  # pragma: no cover
    from unittest.mock import MagicMock
    sys.modules["psutil"] = MagicMock()

import named_work_check as nw
import paper_confirmation as pc
from models.podcast import PodcastRequest

PRICE = {"gemini-2.5-flash": (0.30, 2.50), "gemini-2.5-pro": (1.25, 10.00)}  # USD per million tokens (list prices, 2026-10-06)
SECRETS = {  # same names main.py loads at startup
    "PUBMED_API_KEY": "pubmed-api-key", "NASA_ADS_TOKEN": "nasa-ads-token", "ZENODO_API_KEY": "zenodo-api-key",
    "NEWS_API_KEY": "news-api-key", "YOUTUBE_API_KEY": "youtube-api-key", "CORE_API_KEY": "core-api-key",
    "GOOGLE_API_KEY": "GOOGLE_AI_API_KEY", "GOOGLE_AI_API_KEY": "GOOGLE_AI_API_KEY",
}


class CeilingReached(Exception):
    pass


class Ledger:
    """Append-only spend file shared with the checker scripts, so one ceiling covers the whole sandbox run."""

    def __init__(self, path: str, ceiling: float):
        self.path, self.ceiling = path, ceiling

    def spent(self) -> float:
        if not os.path.exists(self.path):
            return 0.0
        return sum(json.loads(l)["cost"] for l in open(self.path, encoding="utf-8") if l.strip())

    @staticmethod
    def price(model: str):
        m = model.split("/")[-1]
        return PRICE.get(m, PRICE["gemini-2.5-pro"])  # unknown model: assume the dearer price

    def guard(self, model: str, in_tokens: int, max_out: int) -> None:
        pin, pout = self.price(model)
        worst = (in_tokens * pin + max_out * pout) / 1e6
        if self.spent() + worst > self.ceiling:
            raise CeilingReached(f"spent ${self.spent():.4f} + worst case ${worst:.4f} would exceed the ${self.ceiling:.2f} ceiling")

    def record(self, model: str, tin: int, tout: int, tag: str) -> float:
        pin, pout = self.price(model)
        cost = (tin * pin + tout * pout) / 1e6
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": model, "in": tin, "out": tout, "cost": cost, "tag": tag}) + "\n")
        return cost


def install_metering(ledger: Ledger, tag_ref: Dict[str, str]) -> None:
    """Meter every Gemini call the research and generation code makes (the SDK path and the REST helper)."""
    import google.generativeai as genai
    import enhanced_research_service as ers

    orig = genai.GenerativeModel.generate_content

    def metered(self, contents, *a, **k):
        gc = k.get("generation_config")
        max_out = getattr(gc, "max_output_tokens", None) or 8192
        ledger.guard(self.model_name, int(len(str(contents)) / 3) + 50, max_out)
        r = orig(self, contents, *a, **k)
        u = getattr(r, "usage_metadata", None)
        if u is not None:
            ledger.record(self.model_name, getattr(u, "prompt_token_count", 0) or 0,
                          (getattr(u, "candidates_token_count", 0) or 0) + (getattr(u, "thoughts_token_count", 0) or 0), tag_ref.get("tag", ""))
        else:  # no usage reported: charge the worst case rather than nothing
            ledger.record(self.model_name, int(len(str(contents)) / 3), max_out, tag_ref.get("tag", "") + ":unmetered")
        return r
    genai.GenerativeModel.generate_content = metered

    async def metered_rest(self, prompt: str, max_tokens: int = 1000) -> str:
        import aiohttp
        ledger.guard("gemini-2.5-flash", int(len(prompt) / 3) + 50, max_tokens + 1024)
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.google_api_key}
        data = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7}}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    raise Exception(f"Google AI API error: {response.status}")
                result = await response.json()
                u = result.get("usageMetadata", {})
                ledger.record("gemini-2.5-flash", u.get("promptTokenCount", 0), (u.get("candidatesTokenCount") or 0) + (u.get("thoughtsTokenCount") or 0), tag_ref.get("tag", ""))
                return result["candidates"][0]["content"]["parts"][0]["text"]
    ers.EnhancedResearchService._call_google_ai = metered_rest


def load_secrets() -> str:
    """Put the research keys in the environment as main.py does; returns the Google AI key."""
    from google.cloud import secretmanager
    client = secretmanager.SecretManagerServiceClient()
    project = os.environ.get("GCP_PROJECT_ID", "regal-scholar-453620-r7")
    for env, name in SECRETS.items():
        if not os.environ.get(env):
            try:
                os.environ[env] = client.access_secret_version(request={"name": f"projects/{project}/secrets/{name}/versions/latest"}).payload.data.decode().strip()
            except Exception as e:
                print(f"  note: secret {name} not loaded ({type(e).__name__})", file=sys.stderr)
    return os.environ["GOOGLE_AI_API_KEY"]


def body_len(description: str, service) -> int:
    return len(service._description_body(description))


async def run_topic(spec: Dict[str, Any], out_dir: str, service, integrator, google_key: str, naming_llm_factory) -> Dict[str, Any]:
    """One topic, start to finish, no side effects outside ``out_dir``."""
    import services.podcast_generation_service as svc
    from content_fixes import validate_description_before_publish, DescriptionValidationError
    tid = spec["id"]
    d = os.path.join(out_dir, tid)
    os.makedirs(d, exist_ok=True)
    fields = {k: v for k, v in spec.items() if k in PodcastRequest.model_fields}
    request = PodcastRequest(**fields)
    res: Dict[str, Any] = {"id": tid, "topic": request.topic, "outcome": None, "message": None}
    t0 = time.time()
    try:
        ctx = await asyncio.wait_for(integrator.comprehensive_research_for_podcast(
            topic=request.topic, additional_context=request.additional_instructions or "", source_links=request.source_links or [],
            expertise_level=request.expertise_level, require_minimum_sources=3,
            required_paper=({"doi": request.paper_doi, "title": request.paper_title} if request.paper_title else None)), timeout=300)
    except (pc.InsufficientConfirmedPapers, pc.RegistryUnavailable, pc.PaperNotConfirmed) as e:
        res.update(outcome="failed_research", kind=type(e).__name__, message=str(e))
        if isinstance(e, pc.InsufficientConfirmedPapers):
            res["research"] = {"candidates_found": e.found, "confirmed": e.confirmed, "dropped_counts": e.drop_counts}
        res["seconds"] = round(time.time() - t0, 1)
        json.dump(res, open(os.path.join(d, "result.json"), "w", encoding="utf-8"), indent=1)
        return res
    res["research"] = {"candidates_found": len(ctx.confirmed_papers) + len(ctx.dropped_candidates),
                       "confirmed": len(ctx.confirmed_papers), "dropped_counts": _counts(ctx.dropped_candidates),
                       "confirmed_papers": [c.to_dict() for c in ctx.confirmed_papers], "dropped": [x.to_dict() for x in ctx.dropped_candidates]}
    try:
        content, naming_result, attempts = await service._generate_checked_content(request, ctx, google_key, f"sandbox-{tid}")
    except (nw.NamingViolationError, nw.NamingCheckUnavailable) as e:
        res.update(outcome="failed_naming" if isinstance(e, nw.NamingViolationError) else "failed_check", kind=type(e).__name__, message=str(e),
                   violations=getattr(e, "violations", None))
        res["naming_attempts"] = getattr(service, "_last_naming_attempts", None)
        res["seconds"] = round(time.time() - t0, 1)
        json.dump(res, open(os.path.join(d, "result.json"), "w", encoding="utf-8"), indent=1)
        return res
    raw_description = content.get("description", "")
    metrics = service._finalize_content(content, request, ctx, naming_result)
    try:
        validate_description_before_publish(content["description"])
        gate = "ok"
    except DescriptionValidationError as e:
        gate = f"rejected: {e}"
    refs = content["description"].split("## Further reading")[0].count("\n- ") if "## References" in content["description"] else 0
    further = content["description"].split("## Further reading")[1].split("## Hashtags")[0].count("\n- ") if "## Further reading" in content["description"] else 0
    res.update(outcome="generated", naming_attempts=attempts, regenerations=len(attempts) - 1 if attempts else 0,
               named_pids=naming_result.named_pids, limit=metrics, pre_publish_gate=gate,
               script_words=len((content.get("script") or "").split()), reference_lines=refs, further_reading_lines=further,
               raw_description_chars=len(raw_description))
    open(os.path.join(d, "script.txt"), "w", encoding="utf-8").write(content.get("script") or "")
    open(os.path.join(d, "description_raw.md"), "w", encoding="utf-8").write(raw_description)
    open(os.path.join(d, "description_final.md"), "w", encoding="utf-8").write(content["description"])
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(d, "result.json"), "w", encoding="utf-8"), indent=1)
    return res


def _counts(dropped) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for x in dropped:
        out[x.reason] = out.get(x.reason, 0) + 1
    return out


def build_live(ledger: Ledger, tag_ref: Dict[str, str]):
    google_key = load_secrets()
    install_metering(ledger, tag_ref)
    from podcast_research_integrator import PodcastResearchIntegrator
    import services.podcast_generation_service as svc
    service = svc.PodcastGenerationService()
    return service, PodcastResearchIntegrator(google_key), google_key, (lambda key: nw.make_gemini_llm_call(key))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topics", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--ceiling", type=float, default=4.0)
    ap.add_argument("--only", help="run a single topic id")
    ap.add_argument("--stub", action="store_true", help="offline, scripted fakes; no network and no keys")
    a = ap.parse_args(argv)
    specs = json.load(open(a.topics, encoding="utf-8"))
    if a.only:
        specs = [s for s in specs if s["id"] == a.only]
    os.makedirs(a.out, exist_ok=True)
    ledger = Ledger(a.ledger, a.ceiling)
    tag_ref: Dict[str, str] = {}
    if a.stub:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from fix1_sandbox_stub import build_stub  # noqa
        build = build_stub
    else:
        build = lambda: build_live(ledger, tag_ref)  # noqa: E731
    results = []
    for spec in specs:
        fp = os.path.join(a.out, spec["id"], "result.json")
        if os.path.exists(fp):
            results.append(json.load(open(fp, encoding="utf-8")))
            print(f"{spec['id']}: already done, skipped")
            continue
        tag_ref["tag"] = f"sandbox:{spec['id']}"
        service, integrator, key, llm_factory = build(spec) if a.stub else build()
        try:
            r = asyncio.run(run_topic(spec, a.out, service, integrator, key, llm_factory))
        except CeilingReached as e:
            print("CEILING REACHED:", e)
            results.append({"id": spec["id"], "outcome": "stopped_ceiling", "message": str(e)})
            break
        except Exception as e:
            traceback.print_exc()
            r = {"id": spec["id"], "outcome": "harness_error", "message": f"{type(e).__name__}: {e}"}
            os.makedirs(os.path.join(a.out, spec["id"]), exist_ok=True)
            json.dump(r, open(os.path.join(a.out, spec["id"], "result.json"), "w", encoding="utf-8"), indent=1)
        results.append(r)
        print(f"{spec['id']}: {r['outcome']}  spent ${ledger.spent():.4f}")
    json.dump({"results": results, "spent": ledger.spent(), "ceiling": a.ceiling, "stub": a.stub}, open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
