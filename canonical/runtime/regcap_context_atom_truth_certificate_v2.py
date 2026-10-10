"""Truth certificate for bounded regulatory-capital contextual atoms.

This adapter exposes strict whole-span source-aligned regulatory-capital context
facts through the semantic truth dispatcher. It is deliberately positive-only:
a proved atom may yield TRUE, while an unproved atom remains UNKNOWN. Absence of
an atom never becomes FALSE, and contextual properties never become concept
identity.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import source_aligned_regcap_context_proof_v2 as context_proof

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXT_ATOM_TRUTH_CERTIFICATE_V2"
TRUTH_KIND = "REGCAP_CONTEXT_ATOM"

CONTEXT_KINDS = {
    context_proof.CCOB_KIND,
    context_proof.CCYB_KIND,
    context_proof.TLAC_KIND,
}
KNOWN_ATOMS = {
    context_proof.ATOM_CET1,
    context_proof.ATOM_ABOVE_MIN,
    context_proof.ATOM_2_5,
    context_proof.ATOM_RELEASE,
    context_proof.ATOM_LOSS,
    context_proof.ATOM_RECAP,
    context_proof.ATOM_RESOLUTION,
    context_proof.ATOM_GSIB,
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "predicate_id": None,
        "predicate_truth": "UNKNOWN",
        "truthful_precommitment_observation": False,
        "semantic_truth_authority": False,
        "semantic_identity_authority": False,
        "global_identity_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **detail,
    }


def checked_predicate_id(
    *,
    source_id: str,
    source_text: str,
    start: int,
    end: int,
    context_kind: str,
    target_atom_id: str,
) -> str:
    if (
        not isinstance(source_text, str)
        or not source_text
        or not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end <= start
        or end > len(source_text)
    ):
        raise ValueError("SOURCE_SPAN_INVALID")
    source_id = str(source_id or "").strip()
    context_kind = str(context_kind or "").strip()
    target_atom_id = str(target_atom_id or "").strip()
    if not source_id:
        raise ValueError("SOURCE_ID_REQUIRED")
    if context_kind not in CONTEXT_KINDS:
        raise ValueError("CONTEXT_KIND_INVALID")
    if target_atom_id not in KNOWN_ATOMS:
        raise ValueError("TARGET_ATOM_UNSUPPORTED")
    material = {
        "source_id": source_id,
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "source_span": [start, end],
        "source_span_sha256": sha256(source_text[start:end].encode("utf-8")).hexdigest(),
        "context_kind": context_kind,
        "target_atom_id": target_atom_id,
        "checker_schema": context_proof.SCHEMA,
    }
    raw = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "regcap-context-atom-sha256:" + sha256(raw).hexdigest()


def _unknown(
    *,
    checked_id: str,
    requested_id: str,
    context_kind: str,
    target_atom_id: str,
    reason: str,
    context_result: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNKNOWN__REGCAP_CONTEXT_ATOM_NOT_PROVED",
        "reason": reason,
        "predicate_id": checked_id,
        "requested_predicate_id": requested_id,
        "requested_predicate_id_authority": False,
        "predicate_truth": "UNKNOWN",
        "context_kind": context_kind,
        "target_atom_id": target_atom_id,
        "context_proof": dict(context_result),
        "truthful_precommitment_observation": False,
        "semantic_truth_authority": False,
        "semantic_identity_authority": False,
        "global_identity_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    allowed = {
        "truth_kind",
        "predicate_id",
        "source_text",
        "source_id",
        "start",
        "end",
        "context_kind",
        "target_atom_id",
    }
    extra = set(payload) - allowed
    if extra:
        return _fail("UNMODELED_FIELDS:" + ",".join(sorted(str(x) for x in extra)))
    if payload.get("truth_kind") not in (None, TRUTH_KIND):
        return _fail("TRUTH_KIND_INVALID")

    requested_id = str(payload.get("predicate_id") or "").strip()
    source_text = payload.get("source_text")
    source_id = str(payload.get("source_id") or "").strip()
    start = payload.get("start")
    end = payload.get("end")
    context_kind = str(payload.get("context_kind") or "").strip()
    target_atom_id = str(payload.get("target_atom_id") or "").strip()

    if not requested_id:
        return _fail("PREDICATE_ID_REQUIRED")
    try:
        checked = checked_predicate_id(
            source_id=source_id,
            source_text=source_text,
            start=start,
            end=end,
            context_kind=context_kind,
            target_atom_id=target_atom_id,
        )
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

    claim = {
        "claim_id": "selected-regcap-context",
        "kind": context_kind,
        "start": start,
        "end": end,
    }
    result = context_proof.verify_proof(
        source_text,
        source_id=source_id,
        claims=[claim],
    )
    if result.get("status") == "FAIL_CLOSED":
        return _fail(
            "REGCAP_CONTEXT_PROOF_FAIL_CLOSED",
            context_reason=result.get("errors"),
            context_proof=result,
        )

    accepted = [
        row
        for row in (result.get("accepted_claims") or [])
        if isinstance(row, Mapping)
        and row.get("claim_id") == "selected-regcap-context"
    ]
    if len(accepted) != 1:
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            context_kind=context_kind,
            target_atom_id=target_atom_id,
            reason="BOUND_CONTEXT_NOT_CERTIFIED",
            context_result=result,
        )

    row = accepted[0]
    proved = {
        str(x)
        for x in (row.get("proved_atom_ids") or [])
        if isinstance(x, str)
    }
    if target_atom_id not in proved:
        return _unknown(
            checked_id=checked,
            requested_id=requested_id,
            context_kind=context_kind,
            target_atom_id=target_atom_id,
            reason="TARGET_ATOM_NOT_POSITIVELY_PROVED__ABSENCE_IS_NOT_NEGATION",
            context_result=result,
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SOURCE_BOUND_REGCAP_CONTEXT_ATOM_PROVED_TRUE",
        "predicate_id": checked,
        "requested_predicate_id": requested_id,
        "requested_predicate_id_authority": False,
        "predicate_truth": "TRUE",
        "context_kind": context_kind,
        "target_atom_id": target_atom_id,
        "accepted_claim": dict(row),
        "context_proof": dict(result),
        "truthful_precommitment_observation": True,
        "semantic_truth_authority": True,
        "semantic_identity_authority": False,
        "global_identity_authority": False,
        "candidate_universe_complete": False,
        "open_world_ontology_complete": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "STRICT_WHOLE_SPAN_POSITIVE_SOURCE_BOUND_CONTEXT_ATOM_ONLY__UNPROVED_ATOM_REMAINS_UNKNOWN__"
            "CONTEXTUAL_PROPERTIES_DO_NOT_MINT_CONCEPT_IDENTITY__"
            "NO_OPEN_WORLD_COMPLETENESS_OR_POLICY_ADEQUACY"
        ),
    }
