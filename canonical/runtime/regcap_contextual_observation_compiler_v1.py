"""Bounded source-aligned regulatory-capital observation compiler V1.

Compiles exact controlled context spans into observation outcomes already owned by
regcap_contrastive_discriminator_matrix_v1.

It does NOT classify a concept.  It proves only what the source span directly
states.  Weaker contextual clues remain unresolved.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXTUAL_OBSERVATION_COMPILER_V1"

_WS = re.compile(r"\s+")

_PATTERNS = [
    (
        "FUNCTIONAL_SIGNATURE_CLASS",
        "DRAWDOWN_AS_LOSSES_ARE_INCURRED",
        re.compile(
            r"^(?:the\\s+)?(?:buffer|cushion)\\s+(?:can\\s+be|is|was)\\s+"
            r"drawn\\s+down\\s+as\\s+losses\\s+are\\s+incurred[.]?$",
            re.I,
        ),
    ),
    (
        "FUNCTIONAL_SIGNATURE_CLASS",
        "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
        re.compile(
            r"^(?:the\\s+)?(?:buffer|cushion)\\s+(?:is|was)\\s+released\\s+"
            r"when\\s+system-wide\\s+risk\\s+(?:crystallises\\s+or\\s+dissipates|"
            r"dissipates\\s+or\\s+crystallises)[.]?$",
            re.I,
        ),
    ),
    (
        "FUNCTIONAL_SIGNATURE_CLASS",
        "G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
        re.compile(
            r"^(?:the\\s+)?(?:capacity|resource|cushion)\\s+(?:provides|has)\\s+"
            r"loss-absorbing\\s+and\\s+recapitalisation\\s+capacity\\s+"
            r"(?:available\\s+)?in\\s+resolution\\s+for\\s+(?:a\\s+)?"
            r"(?:failing\\s+)?g-sib[.]?$",
            re.I,
        ),
    ),
    (
        "STRUCTURAL_SIGNATURE_CLASS",
        "TWO_POINT_FIVE_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
        re.compile(
            r"^(?:the\\s+)?(?:buffer|cushion)\\s+(?:is|was)\\s+2[.]5%\\s+"
            r"cet1\\s+above\\s+(?:the\\s+)?regulatory\\s+minimum(?:\\s+capital\\s+requirement)?[.]?$",
            re.I,
        ),
    ),
    (
        "STRUCTURAL_SIGNATURE_CLASS",
        "EXTENDS_CCOB_AND_MET_WITH_CET1",
        re.compile(
            r"^(?:the\\s+)?(?:buffer|cushion)\\s+(?:extends|extended)\\s+"
            r"(?:the\\s+)?capital\\s+conservation\\s+buffer\\s+and\\s+"
            r"(?:is|was|must\\s+be)\\s+met\\s+with\\s+cet1[.]?$",
            re.I,
        ),
    ),
    (
        "RELEASABILITY_CLASS",
        "BASEL_DESIGNATED_RELEASABLE_BUFFER",
        re.compile(
            r"^(?:the\s+)?(?:buffer|cushion)\s+(?:is|was)\s+"
            r"(?:the\s+)?(?:only\s+)?designated\s+releasable\s+buffer\s+"
            r"in\s+the\s+basel\s+framework[.]?$",
            re.I,
        ),
    ),
    (
        "FRAMEWORK_CLASS",
        "BASEL_CAPITAL_BUFFER_ABOVE_REGULATORY_MINIMUM",
        re.compile(
            r"^(?:the\s+)?(?:buffer|cushion)\s+(?:is|was)\s+"
            r"(?:an?\s+)?(?:additional\s+)?layer\s+of\s+capital\s+above\s+"
            r"(?:the\s+)?regulatory\s+minimums?(?:,|\s+and)?\s+"
            r"(?:and\s+)?(?:must\s+be|is|was)\s+met\s+with\s+cet1[.]?$",
            re.I,
        ),
    ),
    (
        "FRAMEWORK_CLASS",
        "SEPARATE_MINIMUM_TLAC_REQUIREMENT",
        re.compile(
            r"^(?:the\s+)?(?:requirement|capacity|cushion)\s+(?:is|was)\s+"
            r"(?:a\s+)?separate\s+minimum\s+(?:external\s+)?"
            r"(?:total\s+loss-absorbing\s+capacity|tlac)\s+requirement\s+"
            r"alongside\s+(?:the\s+)?minimum\s+(?:basel\s+)?"
            r"regulatory\s+capital\s+requirements[.]?$",
            re.I,
        ),
    ),
]


def _norm(text: str) -> str:
    return _WS.sub(" ", text.strip())


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


def compile_span(
    source_text: str,
    *,
    start: int,
    end: int,
) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text:
        return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
    if (
        isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(end, bool)
        or not isinstance(end, int)
        or start < 0
        or end <= start
        or end > len(source_text)
    ):
        return _base("FAIL_CLOSED", reason="SPAN_INVALID")

    surface = source_text[start:end]
    normalized = _norm(surface)
    matches = []
    for observation_id, outcome, pattern in _PATTERNS:
        if pattern.fullmatch(normalized):
            matches.append((observation_id, outcome))

    if not matches:
        return _base(
            "UNRESOLVED__NO_CERTIFIED_CONTEXTUAL_OBSERVATION",
            source_span=[start, end],
            source_surface=surface,
        )
    if len(matches) != 1:
        return _base(
            "FAIL_CLOSED",
            reason="MULTIPLE_CONTEXTUAL_OBSERVATION_PATTERNS_MATCHED",
            matches=[list(x) for x in matches],
        )

    observation_id, outcome = matches[0]
    return _base(
        "PASS__CONTEXTUAL_OBSERVATION_CERTIFIED",
        passed=True,
        semantic_truth_authority=True,
        source_span=[start, end],
        source_text_sha256=sha256(source_text.encode("utf-8")).hexdigest(),
        source_surface=surface,
        observation_id=observation_id,
        outcome=outcome,
        concept_identity_authority=False,
        candidate_universe_complete=False,
        boundary=(
            "EXACT_CONTROLLED_CONTEXT_TO_OBSERVATION_ONLY__"
            "NO_CONCEPT_CLASSIFICATION__NO_REVERSE_PROPERTY_INFERENCE__"
            "NO_HYPOTHESIS_SET_COMPLETENESS_OR_TERMINAL_AUTHORITY"
        ),
    )
