"""Bounded contextual fact compiler for three regulatory-capital profiles.

This module proves only source-faithful contextual facts from exact controlled
surface patterns. It does NOT infer CCoB, CCyB, TLAC, or any other concept id.

Supported V1 profiles:
- CCOB-like structural profile:
  2.5% + CET1 + above regulatory minimum
- CCYB-like release profile:
  released when system-wide risk crystallises or dissipates
- TLAC-like resolution profile:
  loss-absorbing + recapitalisation capacity available in resolution for a G-SIB

The compiler is deliberately narrow. Unrecognized or partially matching prose
remains unresolved.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXTUAL_FACT_COMPILER_V1"

FACT_CCOB_25 = "QUANTITY::2_5_PERCENT"
FACT_CET1 = "COMPOSITION::CET1"
FACT_ABOVE_MIN = "POSITION::ABOVE_REGULATORY_MINIMUM"
FACT_RELEASE = "RELEASE::SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES"
FACT_GSIB = "SCOPE::G_SIB"
FACT_LOSS = "FUNCTION::LOSS_ABSORPTION"
FACT_RECAP = "FUNCTION::RECAPITALISATION"
FACT_RESOLUTION = "REGIME::RESOLUTION"

_WS = re.compile(r"\s+")
_CCOB = re.compile(
    r"\b2\.5\s*%.*\b(?:common\s+equity\s+tier\s+1|cet1)\b.*"
    r"\babove\s+(?:the\s+)?(?:regulatory\s+)?minimum(?:\s+capital\s+requirement)?\b",
    re.I | re.S,
)
_CCYB = re.compile(
    r"\breleased\s+when\s+system[- ]wide\s+risk\s+"
    r"(?:crystallises|crystallizes)\s+or\s+dissipates\b",
    re.I,
)
_TLAC = re.compile(
    r"\b(?:g[- ]?sib|global\s+systemically\s+important\s+bank)\b.*"
    r"\bloss[- ]absorbing\b.*\brecapitali[sz]ation\b.*"
    r"\b(?:available\s+)?in\s+resolution\b",
    re.I | re.S,
)


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "concept_identity_authority": False,
        "candidate_universe_complete": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def compile_context(source_text: str, *, source_id: str) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text.strip():
        return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
    if not isinstance(source_id, str) or not source_id.strip():
        return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")

    normalized = _WS.sub(" ", source_text.strip())
    matches = []
    facts: list[str] = []

    if _CCOB.search(normalized):
        matches.append("CCOB_STRUCTURAL_PROFILE")
        facts.extend([FACT_CCOB_25, FACT_CET1, FACT_ABOVE_MIN])

    if _CCYB.search(normalized):
        matches.append("CCYB_RELEASE_PROFILE")
        facts.append(FACT_RELEASE)

    if _TLAC.search(normalized):
        matches.append("TLAC_RESOLUTION_PROFILE")
        facts.extend([FACT_GSIB, FACT_LOSS, FACT_RECAP, FACT_RESOLUTION])

    unique_facts = sorted(set(facts))
    if not unique_facts:
        return _base(
            "UNRESOLVED__NO_BOUND_CONTEXT_PROFILE",
            source_id=source_id.strip(),
            source_text_sha256=sha256(source_text.encode("utf-8")).hexdigest(),
            proved_facts=[],
            matched_profiles=[],
        )

    return _base(
        "PASS__BOUND_CONTEXT_FACTS_COMPILED",
        passed=True,
        semantic_truth_authority=True,
        source_id=source_id.strip(),
        source_text_sha256=sha256(source_text.encode("utf-8")).hexdigest(),
        proved_facts=unique_facts,
        matched_profiles=sorted(matches),
        exact_profile_identity_claimed=False,
        boundary=(
            "BOUNDED_CONTEXT_FACTS_ONLY__NO_CCOB_CCYB_TLAC_IDENTITY__"
            "NO_REVERSE_NECESSARY_PROPERTY_INFERENCE__NO_OPEN_WORLD_COMPLETENESS"
        ),
    )
