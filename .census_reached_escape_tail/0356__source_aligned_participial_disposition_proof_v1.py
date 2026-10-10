"""Source-aligned proof for one bounded participial disposition primitive.

This verifier is intentionally independent of the numbered source semantic proof
lineage so concurrent V10/V11 work cannot collide. It proves only an exact,
allowlisted source span through bounded_participial_disposition_v1.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.bounded_participial_disposition_v1 import verify_span

SCHEMA = "BRAIN_SOURCE_ALIGNED_PARTICIPIAL_DISPOSITION_PROOF_V1"
KIND = "CERTIFIED_PARTICIPIAL_DISPOSITION"


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
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["SOURCE_TEXT_REQUIRED"],
            "terminal_authority": False,
        }
    if not isinstance(source_id, str) or not source_id.strip():
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["SOURCE_ID_REQUIRED"],
            "terminal_authority": False,
        }
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["CLAIMS_INVALID"],
            "terminal_authority": False,
        }

    accepted = []
    rejected = []
    proved = []
    seen = set()

    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": [f"CLAIM_NOT_OBJECT:{i}"],
                "terminal_authority": False,
            }
        cid = str(claim.get("claim_id") or "").strip()
        if not cid:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": [f"CLAIM_ID_MISSING:{i}"],
                "terminal_authority": False,
            }
        if cid in seen:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": [f"CLAIM_ID_DUPLICATE:{cid}"],
                "terminal_authority": False,
            }
        seen.add(cid)

        if claim.get("kind") != KIND:
            rejected.append({
                "claim_id": cid,
                "reason": "CLAIM_KIND_OUTSIDE_PARTICIPIAL_PROOF_SCOPE",
            })
            continue
        if set(claim) - {"claim_id", "kind", "start", "end", "semantic_graph"}:
            rejected.append({
                "claim_id": cid,
                "reason": "CLAIM_FIELD_SET_INVALID",
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

        expected = parsed["semantic_graph"]
        claimed = claim.get("semantic_graph")
        if claimed is not None and (
            not isinstance(claimed, Mapping)
            or dict(claimed) != expected
        ):
            rejected.append({
                "claim_id": cid,
                "reason": "PARTICIPIAL_DISPOSITION_SEMANTIC_MISMATCH",
                "expected": expected,
                "claimed": dict(claimed) if isinstance(claimed, Mapping) else claimed,
            })
            continue

        constraint = dict(parsed["proved_constraint"])
        accepted.append({
            "claim_id": cid,
            "kind": KIND,
            "source_span": list(parsed["source_span"]),
            "source_text_sha256": parsed["source_text_sha256"],
            "surface": parsed["surface"],
            "semantic_graph": dict(expected),
            "constraint": constraint,
            "episodic_current_event_claimed": False,
            "concept_identity_claimed": False,
        })
        proved.append(constraint)

    return {
        "schema": SCHEMA,
        "status": "PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id": source_id,
        "accepted_claims": accepted,
        "rejected_claims": rejected,
        "proved_constraints": proved,
        "terminal_authority": False,
        "soundness_boundary": (
            "EXACT_ALLOWLISTED_PARTICIPIAL_DISPOSITION_SPANS_ONLY;"
            "LOSS_ABSORPTION_DISPOSITION_DOES_NOT_PROVE_CCOB_CCYB_TLAC_IDENTITY;"
            "NO_GENERAL_COMPOUND_INTERPRETATION_RAW_PROSE_WSD_OR_SEMANTIC_COMPLETENESS"
        ),
    }
