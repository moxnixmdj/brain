"""Independent verifier for bounded regulatory-capital contextual-fact extraction.

This implementation intentionally does not import the producer proof module.
It independently re-derives the three bounded context families from raw source
text and compares the complete emitted property set. It never infers concept
identity from those properties.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXTUAL_FACT_INDEPENDENT_VERIFY_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXTUAL_FACT_EXTRACTION_V1"

CCOB_KIND = "CERTIFIED_REGCAP_CCOB_STRUCTURE_CONTEXT"
CCYB_KIND = "CERTIFIED_REGCAP_CCYB_RELEASE_CONTEXT"
TLAC_KIND = "CERTIFIED_REGCAP_TLAC_RESOLUTION_CONTEXT"

ATOM_CET1 = "COMPOSITION::CET1"
ATOM_ABOVE_MIN = "POSITION::ABOVE_REGULATORY_MINIMUM"
ATOM_2_5 = "AMOUNT::2.5_PERCENT"
ATOM_RELEASE = "RELEASE::SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES"
ATOM_LOSS = "FUNCTION::LOSS_ABSORPTION"
ATOM_RECAP = "FUNCTION::RECAPITALISATION"
ATOM_RESOLUTION = "REGIME::RESOLUTION"
ATOM_GSIB = "SCOPE::G_SIB"

_CCOB = re.compile(
    r"(?is)\b2\.5\s*%.{0,160}\b(?:common\s+equity\s+tier\s+1|cet1)\b"
    r".{0,160}\babove\s+(?:the\s+)?regulatory\s+minimum(?:\s+capital\s+requirement)?\b"
)
_CCYB = re.compile(
    r"(?is)\breleased?\s+when\s+system[-\s]wide\s+risk\s+"
    r"(?:crystalli[sz]es(?:\s+or\s+dissipates)?|dissipates)\b"
)
_TLAC = re.compile(
    r"(?is)\bloss[-\s]absorbing\s+and\s+recapitali[sz]ation"
    r"\s+capacity\b.{0,180}\b(?:available\s+)?in\s+resolution\b"
)
_GSIB = re.compile(
    r"(?is)\b(?:g[-\s]?sib|global\s+systemically\s+important\s+bank)s?\b"
)

def derive(source_text: str) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text:
        raise ValueError("SOURCE_TEXT_REQUIRED")
    contexts: list[str] = []
    atoms: set[str] = set()
    if _CCOB.search(source_text):
        contexts.append(CCOB_KIND)
        atoms.update((ATOM_2_5, ATOM_CET1, ATOM_ABOVE_MIN))
    if _CCYB.search(source_text):
        contexts.append(CCYB_KIND)
        atoms.add(ATOM_RELEASE)
    if _TLAC.search(source_text):
        contexts.append(TLAC_KIND)
        atoms.update((ATOM_LOSS, ATOM_RECAP, ATOM_RESOLUTION))
        if _GSIB.search(source_text):
            atoms.add(ATOM_GSIB)
    return {
        "matched_context_kinds": sorted(contexts),
        "proved_atom_ids": sorted(atoms),
    }

def expected_payload(source_text: str, *, source_id: str, source_path: str) -> dict[str, Any]:
    derived = derive(source_text)
    return {
        "schema": OUTPUT_SCHEMA,
        "status": "VERIFIED_BOUNDED_REGCAP_CONTEXT_FACTS",
        "source_id": source_id,
        "source_path": source_path,
        "source_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "matched_context_kinds": derived["matched_context_kinds"],
        "proved_atom_ids": derived["proved_atom_ids"],
        "concept_identity_claimed": False,
        "reverse_property_to_concept_classification_authorized": False,
        "open_world_semantic_closure": False,
    }

def verify(
    source_text: str,
    *,
    source_id: str,
    source_path: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        if not isinstance(candidate, Mapping):
            raise ValueError("CANDIDATE_NOT_OBJECT")
        expected = expected_payload(
            source_text,
            source_id=source_id,
            source_path=source_path,
        )
        if not expected["matched_context_kinds"]:
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "OPEN__NO_BOUNDED_CONTEXT_FACT_RECOGNIZED",
                "producer_independent": True,
                "semantic_acceptance_complete": False,
                "terminal_authority": False,
            }
        if dict(candidate) != expected:
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED__CONTEXT_FACT_OUTPUT_MISMATCH",
                "producer_independent": True,
                "semantic_acceptance_complete": False,
                "expected": expected,
                "terminal_authority": False,
            }
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__INDEPENDENT_REGCAP_CONTEXT_FACT_REDERIVATION",
            "producer_independent": True,
            "semantic_acceptance_complete": True,
            "source_sha256": expected["source_sha256"],
            "matched_context_kinds": expected["matched_context_kinds"],
            "proved_atom_ids": expected["proved_atom_ids"],
            "concept_identity_claimed": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "producer_independent": True,
            "semantic_acceptance_complete": False,
            "terminal_authority": False,
        }
