"""Bounded source-span proof for the exact phrase class "loss-absorbing cushion".

This is deliberately not a general compound parser.  V1 recognizes only an
explicit allowlisted participial compound whose semantic contribution is
dispositional/generic loss absorption, never episodic "currently absorbs".
"""
from __future__ import annotations

import re
from hashlib import sha256
from typing import Any, Mapping

SCHEMA = "BRAIN_BOUNDED_PARTICIPIAL_DISPOSITION_V1"
SEMANTIC_ATOM = "DISPOSITION::LOSS_ABSORPTION"
_ALLOWED = {
    "loss-absorbing cushion": {
        "head": "cushion",
        "predicate": "absorb",
        "object": "loss",
        "reading": "DISPOSITIONAL",
    },
}
_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", text.strip()).casefold()


def verify_span(
    source_text: str,
    *,
    start: int,
    end: int,
) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SOURCE_TEXT_REQUIRED", "terminal_authority": False}
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start or end > len(source_text):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SPAN_INVALID", "terminal_authority": False}

    raw = source_text[start:end]
    key = _norm(raw)
    semantics = _ALLOWED.get(key)
    if semantics is None:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "reason": "OUTSIDE_EXACT_ALLOWLISTED_PARTICIPIAL_COMPOUND",
            "source_span": [start, end],
            "terminal_authority": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PROVED",
        "source_span": [start, end],
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "surface": raw,
        "semantic_graph": dict(semantics),
        "proved_constraint": {"op": "ATOM", "id": SEMANTIC_ATOM},
        "episodic_current_event_claimed": False,
        "concept_identity_claimed": False,
        "terminal_authority": False,
        "soundness_boundary": (
            "EXACT_ALLOWLISTED_SOURCE_SPAN_ONLY__PROVES_DISPOSITIONAL_LOSS_ABSORPTION__"
            "NO_CCOB_CCYB_TLAC_OR_OTHER_CONCEPT_IDENTITY__NO_CURRENT_EVENT_CLAIM"
        ),
    }
