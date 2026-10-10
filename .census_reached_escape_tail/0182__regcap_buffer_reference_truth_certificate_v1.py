"""Semantic truth certificate for bounded definite regulatory-capital buffer reference."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import regcap_definite_buffer_reference_v1 as reference
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap

SCHEMA = "PROJECT_BRAIN_REGCAP_BUFFER_REFERENCE_TRUTH_CERTIFICATE_V1"
TRUTH_KIND = "REGCAP_BUFFER_REFERENCE_IDENTITY"
TARGETS = {regcap.CCOB, regcap.CCYB}


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
        "reference_identity_authority": False,
        "global_identity_authority": False,
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
    target_concept_id: str,
) -> str:
    if (
        not isinstance(source_text, str)
        or not source_text
        or isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(end, bool)
        or not isinstance(end, int)
        or start < 0
        or end <= start
        or end > len(source_text)
    ):
        raise ValueError("SOURCE_SPAN_INVALID")
    source_id = str(source_id or "").strip()
    target = str(target_concept_id or "").strip()
    if not source_id:
        raise ValueError("SOURCE_ID_REQUIRED")
    if target not in TARGETS:
        raise ValueError("TARGET_CONCEPT_UNSUPPORTED")
    material = {
        "source_id": source_id,
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "reference_span": [start, end],
        "reference_sha256": sha256(source_text[start:end].encode("utf-8")).hexdigest(),
        "target_concept_id": target,
        "resolver_schema": reference.SCHEMA,
    }
    raw = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "regcap-buffer-reference-sha256:" + sha256(raw).hexdigest()


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
        "target_concept_id",
    }
    extra = set(payload) - allowed
    if extra:
        return _fail("UNMODELED_FIELDS:" + ",".join(sorted(str(x) for x in extra)))
    if payload.get("truth_kind") not in (None, TRUTH_KIND):
        return _fail("TRUTH_KIND_INVALID")

    requested = str(payload.get("predicate_id") or "").strip()
    if not requested:
        return _fail("PREDICATE_ID_REQUIRED")
    source_text = payload.get("source_text")
    source_id = str(payload.get("source_id") or "").strip()
    start = payload.get("start")
    end = payload.get("end")
    target = str(payload.get("target_concept_id") or "").strip()

    try:
        checked = checked_predicate_id(
            source_id=source_id,
            source_text=source_text,
            start=start,
            end=end,
            target_concept_id=target,
        )
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

    result = reference.resolve_reference(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
    )
    if result.get("status") == "FAIL_CLOSED":
        return _fail(
            "BUFFER_REFERENCE_RESOLUTION_FAIL_CLOSED",
            reference_result=result,
        )

    if result.get("pass") is not True or not result.get("selected_concept_id"):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNKNOWN__REGCAP_BUFFER_REFERENCE_IDENTITY_NOT_PROVED",
            "reason": str(
                result.get("status")
                or result.get("reason")
                or "REFERENCE_NOT_RESOLVED"
            ),
            "predicate_id": checked,
            "requested_predicate_id": requested,
            "requested_predicate_id_authority": False,
            "predicate_truth": "UNKNOWN",
            "target_concept_id": target,
            "reference_result": result,
            "truthful_precommitment_observation": False,
            "semantic_truth_authority": False,
            "reference_identity_authority": False,
            "global_identity_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    selected = str(result["selected_concept_id"])
    if selected != target:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNKNOWN__DIFFERENT_LOCAL_REFERENCE_IDENTITY",
            "reason": (
                "DIFFERENT_PROVED_REFERENCE_IDENTITY_DOES_NOT_BY_ITSELF_PROVE_NEGATION"
            ),
            "predicate_id": checked,
            "requested_predicate_id": requested,
            "requested_predicate_id_authority": False,
            "predicate_truth": "UNKNOWN",
            "target_concept_id": target,
            "selected_concept_id": selected,
            "reference_result": result,
            "truthful_precommitment_observation": False,
            "semantic_truth_authority": False,
            "reference_identity_authority": False,
            "global_identity_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SOURCE_BOUND_REGCAP_BUFFER_REFERENCE_PROVED_TRUE",
        "predicate_id": checked,
        "requested_predicate_id": requested,
        "requested_predicate_id_authority": False,
        "predicate_truth": "TRUE",
        "target_concept_id": target,
        "selected_concept_id": selected,
        "reference_result": result,
        "truthful_precommitment_observation": True,
        "semantic_truth_authority": True,
        "reference_identity_authority": True,
        "global_identity_authority": False,
        "open_world_coreference_complete": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "OCCURRENCE_LOCAL_the_buffer_REFERENCE_ONLY__UNIQUE_AUTHENTICATED_"
            "ANTECEDENT_REQUIRED__NO_GLOBAL_BUFFER_ALIAS_OR_OPEN_WORLD_COREFERENCE_COMPLETENESS"
        ),
    }
