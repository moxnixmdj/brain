"""Default minimum-information evidence acquisition provider V1.

This provider closes an architectural hole without inventing external facts.

It accepts only decision-bound acquisition requests. A broad residual such as
"finance semantic adequacy tail" is not itself an observation target, so the
provider returns a content-addressed fail-closed decline identifying the exact
missing precondition: a concrete predicate/source/observation target.

It performs no network access, no broad crawl, no verification-authority
mutation, and grants no success/terminal authority. Explicit callers may still
supply a stronger evidence_acquisition_provider to one_shot_reality_closure_v2.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_MINIMUM_INFORMATION_EVIDENCE_ACQUISITION_PROVIDER_V1"
MINIMUM_INFORMATION_SCHEMA = (
    "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_CONTRACT_V1"
)
NO_CONCRETE_TARGET_STATUS = (
    "OPEN__PENDING_ACQUISITION_OR_EXPERIMENT__"
    "CONCRETE_DECISION_BOUND_TARGET_REQUIRED"
)
SOURCE_ADAPTER_REQUIRED_STATUS = (
    "OPEN__PENDING_ACQUISITION_OR_EXPERIMENT__"
    "SOURCE_SPECIFIC_EVIDENCE_ACQUISITION_ADAPTER_REQUIRED"
)

_CONCRETE_KEYS = (
    "predicate_id",
    "observation_id",
    "source_id",
    "source_url",
    "task_id",
    "target_fact_id",
    "target_assertion_id",
)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _requests(request: Mapping[str, Any]) -> list[dict[str, Any]]:
    minimum = request.get("minimum_information_contract")
    if not isinstance(minimum, Mapping):
        return []
    if minimum.get("schema") != MINIMUM_INFORMATION_SCHEMA:
        return []
    raw = minimum.get("requests")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    return [deepcopy(dict(x)) for x in raw if isinstance(x, Mapping)]


def _concrete_coordinates(row: Mapping[str, Any]) -> dict[str, str]:
    coords: dict[str, str] = {}
    for key in _CONCRETE_KEYS:
        value = row.get(key)
        if _nonempty(value):
            coords[key] = str(value).strip()
    target = row.get("target")
    if isinstance(target, Mapping):
        for key in _CONCRETE_KEYS:
            value = target.get(key)
            if _nonempty(value):
                coords.setdefault(key, str(value).strip())
    return coords


def is_sound_nonactionable_decline(result: Any) -> bool:
    return (
        isinstance(result, Mapping)
        and result.get("pass") is False
        and result.get("status") in {
            NO_CONCRETE_TARGET_STATUS,
            SOURCE_ADAPTER_REQUIRED_STATUS,
        }
        and result.get("frontier_changed") is False
        and result.get("verification_authority_mutated") is False
        and result.get("broad_acquisition_attempted") is False
        and isinstance(result.get("receipt_sha256"), str)
        and len(result.get("receipt_sha256")) == 64
    )


def acquire(
    request: Mapping[str, Any],
    *,
    repo_root=None,
) -> dict[str, Any]:
    """Return a sound acquisition result or a precise non-actionable decline.

    V1 intentionally does not invent a generic external crawler. New evidence
    can only be acquired after the current decision exposes a concrete target.
    """
    if not isinstance(request, Mapping):
        payload = {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__REQUEST_MAPPING_REQUIRED",
            "pass": False,
            "reason": "REQUEST_MAPPING_REQUIRED",
            "frontier_changed": False,
            "verification_authority_mutated": False,
            "broad_acquisition_attempted": False,
            "acquisition_or_experiment_attempted": False,
            "terminal_authority": False,
        }
        payload["receipt_sha256"] = _sha(payload)
        return payload

    rows = _requests(request)
    concrete = [
        {
            "request_id": row.get("request_id"),
            "kind": row.get("kind"),
            "coordinates": _concrete_coordinates(row),
        }
        for row in rows
        if _concrete_coordinates(row)
    ]

    if not rows or not concrete:
        payload = {
            "schema": SCHEMA,
            "status": NO_CONCRETE_TARGET_STATUS,
            "pass": False,
            "reason": (
                "MINIMUM_INFORMATION_CONTRACT_HAS_NO_CONCRETE_"
                "DECISION_BOUND_PREDICATE_SOURCE_OR_OBSERVATION_TARGET"
            ),
            "minimum_information_request_count": len(rows),
            "concrete_target_count": len(concrete),
            "concrete_targets": concrete,
            "required_next_input": (
                "CONCRETE_POLICY_CHANGING_PREDICATE_SOURCE_OR_OBSERVATION_TARGET"
            ),
            "proof_or_existing_receipt_precedes_new_reality": True,
            "broad_acquisition_forbidden_without_minimality_proof": True,
            "broad_acquisition_attempted": False,
            "acquisition_or_experiment_attempted": False,
            "frontier_changed": False,
            "verification_authority_mutated": False,
            "candidate_generation_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        payload["receipt_sha256"] = _sha(payload)
        return payload

    payload = {
        "schema": SCHEMA,
        "status": SOURCE_ADAPTER_REQUIRED_STATUS,
        "pass": False,
        "reason": (
            "V1_PROVES_TARGET_CONCRETENESS_BUT_DOES_NOT_OWN_A_GENERIC_"
            "SOURCE_SPECIFIC_EXTERNAL_ACQUISITION_ADAPTER"
        ),
        "minimum_information_request_count": len(rows),
        "concrete_target_count": len(concrete),
        "concrete_targets": concrete,
        "proof_or_existing_receipt_precedes_new_reality": True,
        "broad_acquisition_forbidden_without_minimality_proof": True,
        "broad_acquisition_attempted": False,
        "acquisition_or_experiment_attempted": False,
        "frontier_changed": False,
        "verification_authority_mutated": False,
        "candidate_generation_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    payload["receipt_sha256"] = _sha(payload)
    return payload
