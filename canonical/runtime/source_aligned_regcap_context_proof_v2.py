"""Strict whole-span source-aligned regulatory-capital context proof V2.

V2 preserves the V1 public atom/kind API but removes substring-search authority.
A context fact is proved only when the selected source span as a whole matches one
of the bounded affirmative clause grammars below.

This deliberately rejects negated, attributed, quoted, hypothetical, and
otherwise unmodelled nearby language rather than allowing a positive substring
inside it to mint semantic truth.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_SOURCE_ALIGNED_REGCAP_CONTEXT_PROOF_V2"

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

_CCOB_PATTERNS = (
    re.compile(
        r"^(?:a|the|this) 2\.5% (?:buffer|cushion) comprised of "
        r"(?:common equity tier 1 \(cet1\)|cet1) above (?:the )?"
        r"regulatory minimum(?: capital requirement)?\.?$"
    ),
    re.compile(
        r"^(?:a|the|this) 2\.5% cet1 (?:buffer|cushion) above (?:the )?"
        r"regulatory minimum(?: capital requirement)?\.?$"
    ),
    re.compile(
        r"^(?:the|this) (?:buffer|cushion) is 2\.5% cet1 above (?:the )?"
        r"regulatory minimum(?: capital requirement)?\.?$"
    ),
)

_CCYB_RE = re.compile(
    r"^(?:the|this|a) (?:buffer|cushion) is released when "
    r"system(?:-| )wide risk "
    r"(?:crystalli[sz]es(?: or dissipates)?|dissipates)\.?$"
)

_TLAC_PATTERNS = (
    re.compile(
        r"^sufficient loss-absorbing and recapitali[sz]ation capacity "
        r"available in resolution\.?$"
    ),
    re.compile(
        r"^(?:a )?failing g-sib has sufficient loss-absorbing and "
        r"recapitali[sz]ation capacity available in resolution\.?$"
    ),
    re.compile(
        r"^loss-absorbing and recapitali[sz]ation capacity available in "
        r"resolution for (?:a )?g-sib\.?$"
    ),
    re.compile(
        r"^(?:the|this) (?:resource|capacity|cushion) (?:has|provides) "
        r"loss-absorbing and recapitali[sz]ation capacity available in "
        r"resolution for (?:a )?g-sib\.?$"
    ),
    re.compile(
        r"^if a g-sib fails it has sufficient loss-absorbing and "
        r"recapitali[sz]ation capacity available in resolution\.?$"
    ),
)

_GSIB_RE = re.compile(
    r"\b(?:g-sib|g sib|global systemically important bank)s?\b"
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
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }


def _prove_kind(kind: str, surface: str) -> tuple[list[str], str | None]:
    normalized = _norm(surface)

    if kind == CCOB_KIND:
        if not any(p.fullmatch(normalized) for p in _CCOB_PATTERNS):
            return [], "CCOB_STRUCTURE_CONTEXT_NOT_CERTIFIED"
        return [ATOM_2_5, ATOM_CET1, ATOM_ABOVE_MIN], None

    if kind == CCYB_KIND:
        if _CCYB_RE.fullmatch(normalized) is None:
            return [], "CCYB_RELEASE_CONTEXT_NOT_CERTIFIED"
        return [ATOM_RELEASE], None

    if kind == TLAC_KIND:
        if not any(p.fullmatch(normalized) for p in _TLAC_PATTERNS):
            return [], "TLAC_RESOLUTION_CONTEXT_NOT_CERTIFIED"
        atoms = [ATOM_LOSS, ATOM_RECAP, ATOM_RESOLUTION]
        if _GSIB_RE.search(normalized) is not None:
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
            "proof_mode": "STRICT_WHOLE_SPAN_AFFIRMATIVE_GRAMMAR_V2",
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
        "semantic_truth_authority": bool(accepted),
        "terminal_authority": False,
        "soundness_boundary": (
            "STRICT_WHOLE_SPAN_AFFIRMATIVE_BOUNDED_REGCAP_CONTEXT_FACTS_ONLY__"
            "NEGATED_ATTRIBUTED_QUOTED_HYPOTHETICAL_OR_UNMODELED_LANGUAGE_REMAINS_UNPROVED__"
            "NO_CCOB_CCYB_TLAC_IDENTITY__NO_REVERSE_PROPERTY_CLASSIFICATION__"
            "NO_GENERAL_FINANCE_WSD_OR_OPEN_WORLD_COMPLETENESS"
        ),
    }
