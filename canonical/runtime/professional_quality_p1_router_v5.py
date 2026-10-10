"""Professional-quality P1 Router V5: independently bound target handoff.

V4 content-addresses a caller-supplied target instance against the canonical
professional behavior contract. V5 closes the remaining semantic handoff seam:
the target instance may enter P1 only through the existing independently verified
R2 full goal-to-decision binding for the exact raw goal and exact decision
payload.

The caller may not supply a top-level target_instance and may not self-attest the
target-compilation workflow step. After the R2 binding authenticates the decision
payload, V5 extracts its professional_target_instance, validates it using V4,
injects the target-compilation PASS by construction, and delegates to V4/V3.

This is integration glue. It adds no natural-language interpreter and grants no
quality, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import general_adequate_decision_controller_v1 as decision
from canonical.runtime import professional_quality_p1_router_v4 as base

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V5"
TARGET_STEP = "COMPILE_TARGET_SPEC_AND_HARD_CONSTRAINTS"
TARGET_KEY = "professional_target_instance"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    out = base._base("FAIL_CLOSED", reason=reason)
    out["schema"] = SCHEMA
    out.update(extra)
    return out


def _open(reason: str, **extra: Any) -> dict[str, Any]:
    out = base._base(
        "ABSTAIN__P1_AUTHENTICATED_TARGET_REQUIRED",
        route="ABSTAIN",
        blocking_steps=[TARGET_STEP],
        blocking_reason=reason,
        target_instance_bound=False,
    )
    out["schema"] = SCHEMA
    out.update(extra)
    return out


def route(state: Mapping[str, Any], *, repo_root: str | Path | None = None) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        return _fail("STATE_NOT_OBJECT")

    if "target_instance" in state:
        return _fail("UNBOUND_TOP_LEVEL_TARGET_INSTANCE_FORBIDDEN")

    supplied = state.get("step_results", {})
    if not isinstance(supplied, Mapping):
        return _fail("STEP_RESULTS_NOT_OBJECT")
    if TARGET_STEP in supplied:
        return _fail("TARGET_COMPILATION_SELF_ATTESTATION_FORBIDDEN")

    goal = state.get("goal")
    payload = state.get("decision_payload")
    binding = state.get("goal_to_decision_binding")

    if not isinstance(goal, str) or not goal.strip():
        return _open("RAW_GOAL_REQUIRED")
    if not isinstance(payload, Mapping):
        return _open("DECISION_PAYLOAD_REQUIRED")
    if not isinstance(binding, Mapping):
        return _open("GOAL_TO_DECISION_BINDING_REQUIRED")

    target, target_error = base._validate_target_instance(payload.get(TARGET_KEY))
    if target_error is not None or target is None:
        return _fail(target_error or "BOUND_TARGET_INSTANCE_INVALID")

    root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    auth = decision._authenticate_goal_binding(
        binding,
        goal=goal.strip(),
        decision_payload=payload,
        repo_root=root,
    )
    if auth.get("pass") is not True:
        status = str(auth.get("status") or "")
        if status.startswith("OPEN__"):
            return _open(status, goal_to_decision_binding=deepcopy(auth))
        return _fail(
            "TARGET_GOAL_TO_DECISION_BINDING_INVALID",
            goal_to_decision_binding=deepcopy(auth),
        )

    # The shared R2 authenticator proves exact content binding and checks the
    # independent_verified flag.  For this professional-routing authority edge
    # we additionally require concrete, distinct producer/verifier identities so
    # a caller cannot satisfy "independent" with an anonymous self-assertion.
    try:
        receipt_doc, _, _ = decision._bound_json(
            binding.get("receipt"),
            repo_root=root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verify_doc, _, _ = decision._bound_json(
            binding.get("verification"),
            repo_root=root,
            prefixes=("canonical/verification/",),
        )
    except Exception as exc:
        return _fail(
            "TARGET_BINDING_IDENTITY_EVIDENCE_INVALID",
            identity_error=type(exc).__name__ + ":" + str(exc),
        )
    producer_id = receipt_doc.get("producer_id")
    verifier_id = verify_doc.get("independent_verifier_id")
    if not isinstance(producer_id, str) or not producer_id.strip():
        return _fail("TARGET_BINDING_PRODUCER_ID_REQUIRED")
    if not isinstance(verifier_id, str) or not verifier_id.strip():
        return _fail("TARGET_BINDING_INDEPENDENT_VERIFIER_ID_REQUIRED")
    if producer_id.strip() == verifier_id.strip():
        return _fail("TARGET_BINDING_PRODUCER_VERIFIER_NOT_INDEPENDENT")

    delegated = deepcopy(dict(state))
    delegated.pop("goal", None)
    delegated.pop("decision_payload", None)
    delegated.pop("goal_to_decision_binding", None)
    delegated["target_instance"] = target
    delegated_results = deepcopy(dict(supplied))
    delegated_results[TARGET_STEP] = "PASS"
    delegated["step_results"] = delegated_results

    out = base.route(delegated, repo_root=root)
    if not isinstance(out, Mapping):
        return _fail("V4_RESULT_NOT_OBJECT")

    result = deepcopy(dict(out))
    result["schema"] = SCHEMA
    result["goal_to_decision_binding"] = deepcopy(auth)
    result["target_instance_source"] = "AUTHENTICATED_DECISION_PAYLOAD"
    result["target_step_injected_by_authenticated_binding"] = True
    result["target_binding_producer_id"] = producer_id.strip()
    result["target_binding_independent_verifier_id"] = verifier_id.strip()
    result["target_compilation_self_attestation_allowed"] = False
    result["unbound_target_substitution_allowed"] = False
    result["semantic_truth_authority"] = False
    result["quality_authority"] = False
    result["acceptance_authority"] = False
    result["promotion_authority"] = False
    result["terminal_authority"] = False
    result["terminal_credit_delta"] = 0
    result["incremental_spend_usd"] = 0
    return result


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return route(args or {}, repo_root=root)
