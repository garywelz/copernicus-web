"""What to tell people when a podcast job fails (gap 3 fix 1, C8).

The requester gets a plain explanation and what they can do; the raw error text is for the administrator only, so
internals (stack messages, model errors) never reach a subscriber. Pure functions, no network.
"""
from __future__ import annotations

from typing import Dict, Optional

from paper_confirmation import InsufficientConfirmedPapers, PaperNotConfirmed, RegistryUnavailable
from named_work_check import NamingCheckUnavailable, NamingViolationError


def describe_failure(exc: BaseException) -> Dict[str, Optional[str]]:
    """Returns {'kind', 'summary', 'what_to_do'}; summary and what_to_do are safe to show to the requester."""
    if isinstance(exc, InsufficientConfirmedPapers):
        return {
            "kind": "insufficient_confirmed_papers",
            "summary": (f"We found {exc.found} possible research sources for this topic, but only {exc.confirmed} could be confirmed "
                        f"as real published papers (PubMed, arXiv or Crossref), and at least {exc.needed} are needed. "
                        "No episode was generated or published."),
            "what_to_do": ("Try a broader or differently worded topic, or add links to specific papers (their arXiv, PubMed or DOI links) "
                           "to the request."),
        }
    if isinstance(exc, RegistryUnavailable):
        return {
            "kind": "registry_unavailable",
            "summary": ("We could not reach the paper registries (" + ", ".join(exc.registries) + ") to confirm the research papers, "
                        "so no episode was generated."),
            "what_to_do": "This is usually temporary. Please try again later.",
        }
    if isinstance(exc, PaperNotConfirmed):
        return {
            "kind": "requested_paper_not_confirmed",
            "summary": f"The paper you asked about could not be confirmed: {exc}.",
            "what_to_do": "Check that the DOI (or arXiv/PubMed link) is correct and try again.",
        }
    if isinstance(exc, NamingViolationError):
        return {
            "kind": "naming_violation",
            "summary": ("The script kept naming research that is not among the papers we confirmed for this episode, even after being "
                        "asked to rewrite it, so no episode was published."),
            "what_to_do": "Please try again; a different wording of the topic, or links to specific papers, can help.",
        }
    if isinstance(exc, NamingCheckUnavailable):
        return {
            "kind": "naming_check_unavailable",
            "summary": "The check that makes sure an episode names only confirmed research could not run, so no episode was published.",
            "what_to_do": "This is usually temporary. Please try again later.",
        }
    return {
        "kind": "generation_failed",
        "summary": "Something went wrong while generating this episode, and no episode was published. The team has been notified.",
        "what_to_do": "Please try again, or contact support if the problem continues.",
    }
