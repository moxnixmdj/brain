"""Source-aligned semantic proof checker V10.

V10 preserves V9 and adds one narrow primitive:
CERTIFIED_PARTICIPIAL_DISPOSITION.

The primitive accepts only an exact source span independently recomputed by
bounded_participial_disposition_v1. V10 currently proves only the
dispositional loss-absorption atom for the exact allowlisted phrase
"loss-absorbing cushion".
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v9 import verify_proof as verify_v9
from canonical.runtime.bounded_participial_disposition_v1 import verify_span

SCHEMA = "BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V10"
_KIND = "CERTIFIED_PARTICIPIAL_DISPOSITION"


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
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["CLAIMS_INVALID"],
            "terminal_authority": False,
        }

    base_claims = []
    disposition_claims = []
    seen = set()
    errors = []
    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            errors.append(f"CLAIM_NOT_OBJECT:{i}")
            continue
        cid = str(claim.get("claim_id") or "").strip()
        if not cid:
            errors.append(f"CLAIM_ID_MISSING:{i}")
            continue
        if cid in seen:
            errors.append(f"CLAIM_ID_DUPLICATE:{cid}")
            continue
        seen.add(cid)
        if claim.get("kind") == _KIND:
            disposition_claims.append(claim)
        else:
            base_claims.append(claim)

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "terminal_authority": False,
        }

    base = verify_v9(
        source_text,
        source_id=source_id,
        claims=base_claims,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
        fact_source=fact_source,
        fact_source_id=fact_source_id,
    )
    if base.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["V9_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof": base,
            "terminal_authority": False,
        }

    accepted = list(base.get("accepted_claims") or [])
    rejected = list(base.get("rejected_claims") or [])
    proved = list(base.get("proved_constraints") or [])

    for claim in disposition_claims:
        cid = str(claim["claim_id"])
        allowed_fields = {"claim_id", "kind", "start", "end", "semantic_graph"}
        if set(claim) - allowed_fields:
            rejected.append({
                "claim_id": cid,
                "reason": "PARTICIPIAL_DISPOSITION_CLAIM_FIELD_SET_INVALID",
            })
            continue

        parsed = verify_span(
            source_text,
            start=claim.get("start"),
            end=claim.get("end"),
        )
        if parsed.get("status") != "PROVED":
            rejected.append({
                "claim_id": cid,
                "reason": "PARTICIPIAL_DISPOSITION_NOT_CERTIFIABLY_PARSED",
                "parse_status": parsed.get("status"),
                "parse_reason": parsed.get("reason"),
            })
            continue

        claimed_graph = claim.get("semantic_graph")
        expected_graph = parsed["semantic_graph"]
        if claimed_graph is not None and (
            not isinstance(claimed_graph, Mapping)
            or dict(claimed_graph) != expected_graph
        ):
            rejected.append({
                "claim_id": cid,
                "reason": "PARTICIPIAL_DISPOSITION_SEMANTIC_MISMATCH",
                "expected": expected_graph,
                "claimed": (
                    dict(claimed_graph)
                    if isinstance(claimed_graph, Mapping)
                    else claimed_graph
                ),
            })
            continue

        constraint = dict(parsed["proved_constraint"])
        accepted.append({
            "claim_id": cid,
            "kind": _KIND,
            "source_span": list(parsed["source_span"]),
            "source_text_sha256": parsed["source_text_sha256"],
            "surface": parsed["surface"],
            "semantic_graph": dict(expected_graph),
            "constraint": constraint,
            "episodic_current_event_claimed": False,
            "concept_identity_claimed": False,
        })
        proved.append(constraint)

    return {
        "schema": SCHEMA,
        "status": (
            "PROOF_CHECKED"
            if not rejected
            else "PROOF_CHECKED_WITH_REJECTIONS"
        ),
        "source_id": source_id,
        "accepted_claims": accepted,
        "rejected_claims": rejected,
        "proved_constraints": proved,
        "terminal_authority": False,
        "soundness_boundary": (
            "V10_ADDS_ONLY_EXACT_ALLOWLISTED_PARTICIPIAL_DISPOSITION_SPANS;"
            "LOSS_ABSORPTION_DISPOSITION_DOES_NOT_PROVE_CCOB_CCYB_TLAC_IDENTITY;"
            "NO_GENERAL_COMPOUND_INTERPRETATION_RAW_PROSE_WSD_OR_SEMANTIC_COMPLETENESS"
        ),
    }
