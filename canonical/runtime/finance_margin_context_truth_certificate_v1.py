"""Truth certificate wrapper for bounded finance-margin context atoms."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import finance_margin_context_proof_v1 as proof

SCHEMA = "PROJECT_BRAIN_FINANCE_MARGIN_CONTEXT_TRUTH_CERTIFICATE_V1"
TRUTH_KIND = "FINANCE_MARGIN_CONTEXT_ATOM"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "predicate_truth": "UNKNOWN",
        "truthful_precommitment_observation": False,
        "semantic_truth_authority": False,
        "semantic_identity_authority": False,
        "policy_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def checked_predicate_id(
    *, source_id: str, source_text: str, start: int, end: int, target_atom_id: str
) -> str:
    if target_atom_id not in proof.ATOMS:
        raise ValueError("TARGET_ATOM_UNSUPPORTED")
    material = {
        "source_id": str(source_id or "").strip(),
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "source_span": [start, end],
        "source_span_sha256": sha256(source_text[start:end].encode("utf-8")).hexdigest(),
        "target_atom_id": target_atom_id,
        "proof_schema": proof.SCHEMA,
    }
    if not material["source_id"]:
        raise ValueError("SOURCE_ID_REQUIRED")
    return "finance-margin-context-sha256:" + sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    allowed = {
        "truth_kind", "predicate_id", "source_text", "source_id", "start", "end",
        "target_atom_id",
    }
    extra = set(payload) - allowed
    if extra:
        return _fail("UNMODELED_FIELDS:" + ",".join(sorted(str(x) for x in extra)))
    if payload.get("truth_kind") not in (None, TRUTH_KIND):
        return _fail("TRUTH_KIND_INVALID")

    requested = str(payload.get("predicate_id") or "").strip()
    source_text = payload.get("source_text")
    source_id = str(payload.get("source_id") or "").strip()
    start = payload.get("start", 0)
    end = payload.get("end")
    target = str(payload.get("target_atom_id") or "").strip()
    if not requested:
        return _fail("PREDICATE_ID_REQUIRED")
    if not isinstance(source_text, str) or not source_text:
        return _fail("SOURCE_TEXT_REQUIRED")
    if end is None:
        end = len(source_text)
    try:
        checked = checked_predicate_id(
            source_id=source_id,
            source_text=source_text,
            start=start,
            end=end,
            target_atom_id=target,
        )
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

    out = proof.verify_context(
        source_text, source_id=source_id, start=start, end=end
    )
    proved = set(out.get("proved_atom_ids") or [])
    if out.get("status") == "FAIL_CLOSED":
        return _fail(
            "MARGIN_CONTEXT_PROOF_FAIL_CLOSED",
            predicate_id=checked,
            requested_predicate_id=requested,
            context_proof=out,
        )
    if out.get("pass") is not True or target not in proved:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNKNOWN__FINANCE_MARGIN_CONTEXT_ATOM_NOT_PROVED",
            "reason": "TARGET_ATOM_NOT_POSITIVELY_PROVED__ABSENCE_IS_NOT_NEGATION",
            "predicate_id": checked,
            "requested_predicate_id": requested,
            "requested_predicate_id_authority": False,
            "predicate_truth": "UNKNOWN",
            "target_atom_id": target,
            "context_proof": out,
            "truthful_precommitment_observation": False,
            "semantic_truth_authority": False,
            "semantic_identity_authority": False,
            "policy_adequacy_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SOURCE_BOUND_FINANCE_MARGIN_CONTEXT_ATOM_PROVED_TRUE",
        "predicate_id": checked,
        "requested_predicate_id": requested,
        "requested_predicate_id_authority": False,
        "predicate_truth": "TRUE",
        "target_atom_id": target,
        "context_proof": out,
        "truthful_precommitment_observation": True,
        "semantic_truth_authority": True,
        "semantic_identity_authority": False,
        "policy_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "POSITIVE_BOUND_MARGIN_CONTEXT_ATOM_ONLY__NO_SENSE_OR_ONTOLOGY_IDENTITY__"
            "UNPROVED_ATOM_REMAINS_UNKNOWN"
        ),
    }
