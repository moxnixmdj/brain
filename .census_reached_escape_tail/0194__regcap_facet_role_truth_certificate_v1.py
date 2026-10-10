"""Semantic truth certificate for bounded reg-cap facet roles.

A projected facet role may yield TRUE. An unprojected role remains UNKNOWN.
Multiple roles may coexist for one clause; this certificate never claims a
single exclusive referent facet.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import regcap_facet_role_projection_v1 as facets

SCHEMA = "PROJECT_BRAIN_REGCAP_FACET_ROLE_TRUTH_CERTIFICATE_V1"
TRUTH_KIND = "REGCAP_FACET_ROLE"


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
        "facet_role_authority": False,
        "single_facet_reference_authority": False,
        "concept_identity_authority": False,
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
    target_facet_role: str,
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
    if not source_id:
        raise ValueError("SOURCE_ID_REQUIRED")
    if context_kind not in facets.KNOWN_CONTEXT_KINDS:
        raise ValueError("CONTEXT_KIND_INVALID")
    if target_facet_role not in facets.KNOWN_ROLES:
        raise ValueError("TARGET_FACET_ROLE_UNSUPPORTED")
    material = {
        "source_id": source_id,
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "source_span": [start, end],
        "context_kind": context_kind,
        "target_facet_role": target_facet_role,
        "projection_schema": facets.SCHEMA,
    }
    raw = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "regcap-facet-role-sha256:" + sha256(raw).hexdigest()


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
        "target_facet_role",
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
    context_kind = str(payload.get("context_kind") or "").strip()
    target = str(payload.get("target_facet_role") or "").strip()

    try:
        checked = checked_predicate_id(
            source_id=source_id,
            source_text=source_text,
            start=start,
            end=end,
            context_kind=context_kind,
            target_facet_role=target,
        )
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

    projection = facets.project(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        context_kind=context_kind,
    )
    if projection.get("status") == "FAIL_CLOSED":
        return _fail(
            "FACET_ROLE_PROJECTION_FAIL_CLOSED",
            projection_result=projection,
        )

    roles = projection.get("facet_roles") or []
    if projection.get("pass") is not True or target not in roles:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNKNOWN__REGCAP_FACET_ROLE_NOT_PROVED",
            "reason": "TARGET_ROLE_NOT_POSITIVELY_PROJECTED__ABSENCE_IS_NOT_NEGATION",
            "predicate_id": checked,
            "requested_predicate_id": requested,
            "requested_predicate_id_authority": False,
            "predicate_truth": "UNKNOWN",
            "target_facet_role": target,
            "projection_result": projection,
            "truthful_precommitment_observation": False,
            "semantic_truth_authority": False,
            "facet_role_authority": False,
            "single_facet_reference_authority": False,
            "concept_identity_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SOURCE_BOUND_REGCAP_FACET_ROLE_PROVED_TRUE",
        "predicate_id": checked,
        "requested_predicate_id": requested,
        "requested_predicate_id_authority": False,
        "predicate_truth": "TRUE",
        "target_facet_role": target,
        "projection_result": projection,
        "truthful_precommitment_observation": True,
        "semantic_truth_authority": True,
        "facet_role_authority": True,
        "single_facet_reference_authority": False,
        "concept_identity_authority": False,
        "global_identity_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "POSITIVE_TYPED_FACET_ROLE_ONLY__MULTIPLE_ROLES_MAY_COEXIST__"
            "UNPROJECTED_ROLE_REMAINS_UNKNOWN__NO_SINGLE_FACET_OR_CONCEPT_IDENTITY"
        ),
    }
