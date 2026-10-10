"""Bounded source-aligned regulatory-capital contextual facts V1.

Recognizes only three deliberately narrow context families:
- CCoB-like structural facts: 2.5% + CET1 + above regulatory minimum;
- CCyB-like release facts: released when system-wide risk crystallises/dissipates;
- TLAC-like resolution facts: loss-absorbing + recapitalisation capacity in resolution.

The verifier proves source facts only. It does NOT assert CCoB, CCyB, TLAC, or
any other concept identity.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_SOURCE_ALIGNED_REGCAP_CONTEXT_PROOF_V1"

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

_WS = re.compile(r"\s+")

_CCOB_RE = re.compile(
    r"(?is)\b2\.5\s*%.{0,160}\b(?:common\s+equity\s+tier\s+1|cet1)\b"
    r".{0,160}\babove\s+(?:the\s+)?regulatory\s+minimum(?:\s+capital\s+requirement)?\b"
)

_CCYB_RE = re.compile(
    r"(?is)\breleased?\s+when\s+system[-\s]wide\s+risk\s+"
    r"(?:crystalli[sz]es(?:\s+or\s+dissipates)?|dissipates)\b"
)

_TLAC_RE = re.compile(
    r"(?is)\bloss[-\s]absorbing\s+and\s+recapitali[sz]ation"
    r"\s+capacity\b.{0,180}\b(?:available\s+)?in\s+resolution\b"
)

_GSIB_RE = re.compile(
    r"(?is)\b(?:g[-\s]?sib|global\s+systemically\s+important\s+bank)s?\b"
)


def _norm(text: str) -> str:
    return _WS.sub(" ", text.strip()).casefold()


def _atom(atom_id: str) -> dict[str, Any]:
    return {"op": "ATOM", "id": atom_id}


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": [reason],
        "accepted_claims": [],
        "rejected_claims": [],
        "proved_constraints": [],
        "concept_identity_claimed": False,
        "terminal_authority": False,
    }


def _prove_kind(kind: str, surface: str) -> tuple[list[str], str | None]:
    if kind == CCOB_KIND:
        if _CCOB_RE.search(surface) is None:
            return [], "CCOB_STRUCTURE_CONTEXT_NOT_CERTIFIED"
        return [ATOM_2_5, ATOM_CET1, ATOM_ABOVE_MIN], None

    if kind == CCYB_KIND:
        if _CCYB_RE.search(surface) is None:
            return [], "CCYB_RELEASE_CONTEXT_NOT_CERTIFIED"
        return [ATOM_RELEASE], None

    if kind == TLAC_KIND:
        if _TLAC_RE.search(surface) is None:
            return [], "TLAC_RESOLUTION_CONTEXT_NOT_CERTIFIED"
        atoms = [ATOM_LOSS, ATOM_RECAP, ATOM_RESOLUTION]
        if _GSIB_RE.search(surface) is not None:
            atoms.append(ATOM_GSIB)
        return atoms, None

    return [], "CLAIM_KIND_OUTSIDE_REGCAP_CONTEXT_SCOPE"


def verify_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
    typed_context: Mapping[str, Any] | None = None,
    expected_typed_context_sha256: str | None = None,
    fact_source: str | bytes | None = None,
    fact_source_id: str | None = None,
) -> dict[str, Any]:
    del typed_context, expected_typed_context_sha256, fact_source, fact_source_id

    if not isinstance(source_text, str) or not source_text:
        return _fail("SOURCE_TEXT_REQUIRED")
    if not isinstance(source_id, str) or not source_id.strip():
        return _fail("SOURCE_ID_REQUIRED")
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return _fail("CLAIMS_INVALID")

    accepted = []
    rejected = []
    proved = []
    seen = set()

    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            return _fail(f"CLAIM_NOT_OBJECT:{i}")
        cid = str(claim.get("claim_id") or "").strip()
        if not cid:
            return _fail(f"CLAIM_ID_MISSING:{i}")
        if cid in seen:
            return _fail(f"CLAIM_ID_DUPLICATE:{cid}")
        seen.add(cid)

        if set(claim) - {"claim_id", "kind", "start", "end"}:
            rejected.append({
                "claim_id": cid,
                "reason": "CLAIM_FIELD_SET_INVALID",
            })
            continue

        start = claim.get("start")
        end = claim.get("end")
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
            or start < 0
            or end <= start
            or end > len(source_text)
        ):
            rejected.append({
                "claim_id": cid,
                "reason": "SOURCE_SPAN_INVALID",
            })
            continue

        surface = source_text[start:end]
        atoms, reason = _prove_kind(str(claim.get("kind") or ""), surface)
        if reason is not None:
            rejected.append({
                "claim_id": cid,
                "reason": reason,
                "source_span": [start, end],
            })
            continue

        constraints = [_atom(x) for x in atoms]
        accepted.append({
            "claim_id": cid,
            "kind": str(claim["kind"]),
            "source_span": [start, end],
            "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
            "surface": surface,
            "proved_atom_ids": list(atoms),
            "constraints": constraints,
            "concept_identity_claimed": False,
        })
        proved.extend(constraints)

    dedup = []
    seen_atoms = set()
    for row in proved:
        atom_id = row["id"]
        if atom_id in seen_atoms:
            continue
        seen_atoms.add(atom_id)
        dedup.append(row)

    return {
        "schema": SCHEMA,
        "status": "PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id": source_id,
        "accepted_claims": accepted,
        "rejected_claims": rejected,
        "proved_constraints": dedup,
        "concept_identity_claimed": False,
        "semantic_truth_authority": True if accepted else False,
        "terminal_authority": False,
        "soundness_boundary": (
            "EXACT_BOUNDED_REGCAP_CONTEXT_FACTS_ONLY__NO_CCOB_CCYB_TLAC_IDENTITY__"
            "NO_REVERSE_NECESSARY_PROPERTY_CLASSIFICATION__NO_GENERAL_FINANCE_WSD"
        ),
    }
