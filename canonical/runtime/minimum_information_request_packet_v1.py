"""Build one minimum policy-changing information request packet.

The packet carries non-authoritative proof-target context to an information
provider. It never upgrades that context into semantic truth. Any returned
payload must still pass the downstream truth certificate.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_REQUEST_V1"


def _digest(value: Any) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + sha256(body).hexdigest()


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "information_authority": False,
        "semantic_truth_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def build(
    *,
    task_id: str,
    goal: str,
    decision_payload: Mapping[str, Any],
    predicate_id: str,
    reason: str,
    acquisition_plan: Mapping[str, Any],
    proof_requests: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    if not isinstance(task_id, str) or not task_id.strip():
        return _fail("TASK_ID_REQUIRED")
    if not isinstance(goal, str) or not goal:
        return _fail("GOAL_REQUIRED")
    if not isinstance(decision_payload, Mapping):
        return _fail("DECISION_PAYLOAD_REQUIRED")
    if not isinstance(predicate_id, str) or not predicate_id:
        return _fail("PREDICATE_ID_REQUIRED")
    if not isinstance(reason, str) or not reason:
        return _fail("REASON_REQUIRED")
    if not isinstance(acquisition_plan, Mapping):
        return _fail("ACQUISITION_PLAN_REQUIRED")
    if (
        not isinstance(proof_requests, Sequence)
        or isinstance(proof_requests, (str, bytes))
        or any(not isinstance(x, Mapping) for x in proof_requests)
    ):
        return _fail("PROOF_REQUESTS_INVALID")

    normalized_requests = [deepcopy(dict(x)) for x in proof_requests]
    return {
        "schema": SCHEMA,
        "pass": True,
        "task_id": task_id.strip(),
        "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
        "decision_payload_sha256": _digest(decision_payload),
        "predicate_id": predicate_id,
        "reason": reason,
        "acquisition_plan": deepcopy(dict(acquisition_plan)),
        "proof_requests": normalized_requests,
        "external_research_authorized": (
            acquisition_plan.get("external_research_authorized") is True
        ),
        "information_authority": False,
        "semantic_truth_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "PROOF_REQUESTS_ARE_DISCOVERY_CONTEXT_ONLY__PROVIDER_OUTPUT_MUST_PASS_"
            "DOWNSTREAM_TRUTH_AUTHENTICATION"
        ),
    }
