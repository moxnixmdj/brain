"""Bounded source-native contextual facts for the finance term margin.

This module closes only three exact, independently re-readable context signatures:
- margin as an add-on to an index/base/benchmark rate;
- margin as broker collateral deposited to finance a securities purchase;
- margin as net sales minus cost of goods/services sold.

It deliberately does not select an open-world lexical sense or ontology concept.
A bare or otherwise unsupported occurrence such as "Margin increased." remains
UNKNOWN. Multiple simultaneously matching signatures fail closed.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_MARGIN_CONTEXT_PROOF_V1"
KIND = "CERTIFIED_FINANCE_MARGIN_CONTEXT"

ATOM_RATE = "FINANCE_MARGIN_CONTEXT::INDEX_RATE_ADD_ON"
ATOM_COLLATERAL = "FINANCE_MARGIN_CONTEXT::BROKER_COLLATERAL_DEPOSIT"
ATOM_GROSS_PROFIT = "FINANCE_MARGIN_CONTEXT::GROSS_PROFIT_FORMULA"
ATOMS = frozenset({ATOM_RATE, ATOM_COLLATERAL, ATOM_GROSS_PROFIT})

OEWN_RELEASE_SHA256 = "7d749f6e2c39e6970e4997839dcf6e42fd281f3c2fae0171d2192bae8cfa4b51"
OEWN_COLLATERAL_SENSE_ID = "margin%1:21:01::"
OEWN_COLLATERAL_DEFINITION_SHA256 = "1a4840c1eecc0caabb286b56b2ff8d268eb2313118a3059e2b299304a144e76d"
OEWN_GROSS_PROFIT_SENSE_ID = "margin%1:21:02::"
OEWN_GROSS_PROFIT_DEFINITION_SHA256 = "2703b2b763b125f0d19469a781181cb7aa9906a9abe5738fda1ae9bcd65c72d5"

FIBO_UPSTREAM_COMMIT = "f59157fe156e3d91b1c045222d0a7dc06b7d78a2"
FIBO_SOURCE_PATH = "SEC/Debt/DebtInstruments.rdf"
FIBO_SOURCE_GIT_BLOB_SHA = "62bff6e22db37379856e6f13f4e5f39c6b57dde4"
FIBO_MARGIN_CONCEPT_ID = (
    "https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DebtInstruments/Margin"
)
FIBO_MARGIN_DEFINITION_SHA256 = "3e2f48e1a56a9152003bff533b571ab9376f9732edbce93b67f7a883e05bb0a0"

_MAX_SPAN = 1000

_RATE_PATTERNS = (
    re.compile(
        r"\bmargin\b\s+(?:is\s+)?(?:a\s+variable\s+that\s+is\s+)?"
        r"added\s+to\s+(?:a\s+|the\s+|a\s+specified\s+|the\s+specified\s+|specified\s+)?"
        r"(?:index|benchmark|base)\s+rate\b"
    ),
    re.compile(
        r"\b(?:index|benchmark|base)\s+rate\b[^.!?]{0,100}"
        r"\bplus\b[^.!?]{0,40}\b(?:the\s+)?margin\b"
    ),
)
_COLLATERAL_PATTERNS = (
    re.compile(
        r"\bmargin\b\s+(?:is\s+)?(?:the\s+)?amount\s+of\s+collateral\b"
        r"[^.!?]{0,100}\bdeposits?\s+with\s+(?:a\s+|the\s+)?broker\b"
        r"[^.!?]{0,140}\bbuy\s+securities\b"
    ),
    re.compile(
        r"\bmargin\b\s+(?:is\s+)?(?:a\s+)?collateral\s+deposit\b"
        r"[^.!?]{0,120}\b(?:broker|buy\s+securities)\b"
    ),
)
_GROSS_PATTERNS = (
    re.compile(
        r"\b(?:gross\s+profit\s+)?margin\b\s+(?:is\s+)?(?:the\s+)?"
        r"net\s+sales\s+(?:minus|less)\s+(?:the\s+)?"
        r"cost\s+of\s+goods(?:\s+and\s+services)?\s+sold\b"
    ),
)


def _base(status: str, passed: bool, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "semantic_identity_authority": False,
        "candidate_universe_complete": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _normalize(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def _match(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(p.search(text) is not None for p in patterns)


def verify_context(
    source_text: str,
    *,
    source_id: str,
    start: int = 0,
    end: int | None = None,
) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text:
        return _base("FAIL_CLOSED", False, reason="SOURCE_TEXT_REQUIRED")
    source_id = str(source_id or "").strip()
    if not source_id:
        return _base("FAIL_CLOSED", False, reason="SOURCE_ID_REQUIRED")
    if end is None:
        end = len(source_text)
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end <= start
        or end > len(source_text)
    ):
        return _base("FAIL_CLOSED", False, reason="SOURCE_SPAN_INVALID")

    raw = source_text[start:end]
    if len(raw.encode("utf-8")) > _MAX_SPAN:
        return _base("FAIL_CLOSED", False, reason="SOURCE_SPAN_TOO_LARGE")
    text = _normalize(raw)
    if "margin" not in text:
        return _base(
            "OPEN__NO_BOUND_FINANCE_MARGIN_CONTEXT_FACT",
            False,
            source_id=source_id,
            source_span_chars=[start, end],
            proved_atom_ids=[],
        )

    matched: list[str] = []
    if _match(_RATE_PATTERNS, text):
        matched.append(ATOM_RATE)
    if _match(_COLLATERAL_PATTERNS, text):
        matched.append(ATOM_COLLATERAL)
    if _match(_GROSS_PATTERNS, text):
        matched.append(ATOM_GROSS_PROFIT)

    if len(matched) > 1:
        return _base(
            "FAIL_CLOSED",
            False,
            reason="MULTIPLE_MARGIN_CONTEXT_SIGNATURES_MATCH_ONE_BOUND_SPAN",
            source_id=source_id,
            source_span_chars=[start, end],
            matched_atom_ids=sorted(matched),
        )
    if not matched:
        return _base(
            "OPEN__NO_BOUND_FINANCE_MARGIN_CONTEXT_FACT",
            False,
            source_id=source_id,
            source_span_chars=[start, end],
            source_span_sha256=sha256(raw.encode("utf-8")).hexdigest(),
            proved_atom_ids=[],
        )

    atom = matched[0]
    authority: Mapping[str, Any]
    if atom == ATOM_RATE:
        authority = {
            "authority_family": "PINNED_FIBO_Q2_2026",
            "upstream_commit": FIBO_UPSTREAM_COMMIT,
            "source_path": FIBO_SOURCE_PATH,
            "source_git_blob_sha": FIBO_SOURCE_GIT_BLOB_SHA,
            "concept_id": FIBO_MARGIN_CONCEPT_ID,
            "definition_sha256": FIBO_MARGIN_DEFINITION_SHA256,
        }
    elif atom == ATOM_COLLATERAL:
        authority = {
            "authority_family": "OEWN_2025_JSON",
            "release_sha256": OEWN_RELEASE_SHA256,
            "sense_id": OEWN_COLLATERAL_SENSE_ID,
            "definition_sha256": OEWN_COLLATERAL_DEFINITION_SHA256,
        }
    else:
        authority = {
            "authority_family": "OEWN_2025_JSON",
            "release_sha256": OEWN_RELEASE_SHA256,
            "sense_id": OEWN_GROSS_PROFIT_SENSE_ID,
            "definition_sha256": OEWN_GROSS_PROFIT_DEFINITION_SHA256,
        }

    constraint = {"op": "ATOM", "id": atom}
    return _base(
        "PASS__BOUND_SOURCE_NATIVE_FINANCE_MARGIN_CONTEXT_FACT",
        True,
        semantic_truth_authority=True,
        source_id=source_id,
        source_span_chars=[start, end],
        source_span_sha256=sha256(raw.encode("utf-8")).hexdigest(),
        context_kind=KIND,
        proved_atom_ids=[atom],
        proved_constraints=[constraint],
        authority_binding=dict(authority),
        concept_identity_claimed=False,
        open_world_margin_sense_completeness_claimed=False,
        boundary=(
            "ONE_POSITIVE_BOUND_CONTEXT_FACT_ONLY__NO_LEXICAL_OR_ONTOLOGY_IDENTITY__"
            "NO_NEGATION_FROM_ABSENCE__NO_OPEN_WORLD_MARGIN_SENSE_COMPLETENESS"
        ),
    )
