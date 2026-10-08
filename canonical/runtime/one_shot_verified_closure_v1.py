"""One-shot verified closure controller V1.

Externally this is one operation. Internally it runs the existing verified R2
decision fixed point and R3 compounding queue until the currently actionable
state is stable. Every normal return is totalized to exactly one of:

* VERIFIED_GOAL_SATISFIED
* IRREDUCIBLE_EXTERNAL_INFORMATION_REQUIRED

The second status is evidence-bearing. It is never used merely because a host
provider was omitted: the canonical native Root1 provider is always bound.

This is a closure mechanism over the Brain's current authenticated interfaces,
not a proof that arbitrary future reality is computably decidable.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import general_adequate_decision_totalized_v1 as r2
from canonical.runtime import r3_improvement_queue_driver_v1 as r3
from canonical.runtime import root1_default_acquisition_provider_v1 as root1
from canonical.runtime import autonomous_verified_self_improvement_v1 as learning

SCHEMA = "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1"
VERIFIED = "VERIFIED_GOAL_SATISFIED"
IRREDUCIBLE = "IRREDUCIBLE_EXTERNAL_INFORMATION_REQUIRED"
RETURN_STATES = frozenset({VERIFIED, IRREDUCIBLE})
ROOT = Path(__file__).resolve().parents[2]

class OneShotClosureError(RuntimeError):
    pass

def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value)).hexdigest()

def _state_fingerprint(state_path: str | Path) -> str:
    return _digest(learning.load_state(state_path))

def _residual_class(result: Mapping[str, Any]) -> str:
    action = str(result.get("r2_meta_action") or "")
    if action == r2.ACQUIRE_MINIMUM_INFORMATION:
        return "MISSING_FRESH_EXTERNAL_FACT"
    if action == r2.ACQUIRE_AUTHORITY_BINDING:
        return "MISSING_SOURCE_ALIGNED_PROOF_PRIMITIVE"
    if action == r2.REPAIR_ADEQUACY_COVER:
        return "MISSING_ADEQUATE_POLICY_OR_NEW_CAPABILITY"
    if action == r2.ABSTAIN_FAIL_CLOSED:
        return "MISSING_NEW_CAPABILITY_VERIFIER_OR_DISTINGUISHING_EVIDENCE"
    return "UNRESOLVED_AUTHENTICATED_DECISION_EDGE"

def _irreducible_certificate(
    *,
    task: Mapping[str, Any],
    r2_result: Mapping[str, Any],
    r3_result: Mapping[str, Any],
    root1_provider_id: str,
) -> dict[str, Any]:
    residual = _residual_class(r2_result)
    provider_results = []
    blockers = []
    for action in r3_result.get("actions") or []:
        if not isinstance(action, Mapping):
            continue
        candidate = action.get("provider_result")
        if isinstance(candidate, Mapping):
            provider_results.append(deepcopy(dict(candidate)))
        rows = action.get("blockers") or action.get("blockers_skipped") or []
        for row in rows:
            if isinstance(row, Mapping):
                blockers.append(deepcopy(dict(row)))

    reason = {
        "MISSING_FRESH_EXTERNAL_FACT":
            "THE_REQUIRED_POLICY_CHANGING_FACT_IS_NOT_PRESENT_IN_CURRENT_AUTHENTICATED_EVIDENCE",
        "MISSING_SOURCE_ALIGNED_PROOF_PRIMITIVE":
            "THE_REQUIRED_INDEPENDENT_AUTHORITY_BINDING_IS_NOT_PRESENT_IN_CURRENT_AUTHENTICATED_EVIDENCE",
        "MISSING_ADEQUATE_POLICY_OR_NEW_CAPABILITY":
            "NO_SOUND_ADEQUATE_POLICY_WAS_PROVED_AND_THE_CURRENT_NATIVE_ACQUISITION_FRONTIER_MADE_NO_VERIFIED_PROGRESS",
        "MISSING_NEW_CAPABILITY_VERIFIER_OR_DISTINGUISHING_EVIDENCE":
            "CURRENT_EVIDENCE_SUPPORTS_NO_SOUND_INTERNAL_ACTION__NEW_DISTINGUISHING_EVIDENCE_OR_AN_INDEPENDENTLY_VERIFIABLE_CAPABILITY_IS_REQUIRED",
    }.get(residual, "CURRENT_AUTHENTICATED_STATE_SUPPORTS_NO_SOUND_INTERNAL_ACTION")

    cert = {
        "schema": "PROJECT_BRAIN_IRREDUCIBLE_EXTERNAL_INFORMATION_CERTIFICATE_V1",
        "task_id": task.get("task_id"),
        "goal_sha256": _digest(str(task.get("goal") or "")),
        "residual_class": residual,
        "reason": reason,
        "r2_status": r2_result.get("status"),
        "r2_fixed_point_status": r2_result.get("r2_fixed_point_status"),
        "r2_meta_action": r2_result.get("r2_meta_action"),
        "r2_result_sha256": _digest(r2_result),
        "r3_status": r3_result.get("status"),
        "r3_result_sha256": _digest(r3_result),
        "root1_provider_id": root1_provider_id,
        "root1_provider_results": provider_results,
        "r3_blockers": blockers,
        "internal_provider_missing": False,
        "verified_goal_satisfaction": False,
        "claim_scope": "CURRENT_AUTHENTICATED_BRAIN_STATE_AND_SOUND_ROUTES_DERIVABLE_FROM_THE_DECLARED_NATIVE_ACQUISITION_FRONTIER",
        "universal_future_acquirability_claimed": False,
        "terminal_authority": False,
    }
    cert["certificate_sha256"] = _digest(cert)
    return cert

def _verified_result(
    task: Mapping[str, Any],
    result: Mapping[str, Any],
    r3_result: Mapping[str, Any],
) -> dict[str, Any]:
    if not (
        result.get("pass") is True
        and result.get("actual_goal_satisfaction_verified") is True
    ):
        raise OneShotClosureError("VERIFIED_RETURN_WITHOUT_VERIFIED_GOAL_SATISFACTION")
    return {
        "schema": SCHEMA,
        "status": VERIFIED,
        "pass": True,
        "task_id": task.get("task_id"),
        "goal_sha256": _digest(str(task.get("goal") or "")),
        "r2_result": deepcopy(dict(result)),
        "r3_compounding": deepcopy(dict(r3_result)),
        "postcondition_state": VERIFIED,
        "internal_provider_missing": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

def run(
    task: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    state_path: str | Path = learning.DEFAULT_STATE_PATH,
    information_provider: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
    execution_provider: Callable[..., Mapping[str, Any]] | None = None,
    episode_verification_provider=None,
    skill_verification_provider=None,
    success_episode_adapter_provider=None,
    verification_frontier_acquisition_provider=None,
    verification_frontier_acquisition_provider_id: str | None = None,
    max_r3_actions_per_round: int = 32,
) -> dict[str, Any]:
    """Reach the maximal verified fixed point exposed by current native interfaces."""
    if not isinstance(task, Mapping):
        raise OneShotClosureError("TASK_NOT_OBJECT")
    if not str(task.get("task_id") or "").strip():
        raise OneShotClosureError("TASK_ID_REQUIRED")
    if not str(task.get("goal") or "").strip():
        raise OneShotClosureError("GOAL_REQUIRED")
    if isinstance(max_r3_actions_per_round, bool) or not 1 <= int(max_r3_actions_per_round) <= 32:
        raise OneShotClosureError("MAX_R3_ACTIONS_PER_ROUND_INVALID")

    root = Path(repo_root)
    if information_provider is None:
        information_provider = root1.make_information_provider(repo_root=root)
    if proposal_provider is None:
        proposal_provider = root1.make_r2_proposal_provider(repo_root=root)
    if capability_expander is None:
        capability_expander = root1.make_r2_capability_expander(repo_root=root)

    frontier_provider = verification_frontier_acquisition_provider
    provider_id = verification_frontier_acquisition_provider_id
    if frontier_provider is None:
        frontier_provider = root1.make_frontier_provider(repo_root=root)
        provider_id = root1.PROVIDER_ID
    elif not provider_id:
        provider_id = "EXPLICIT_ROOT1_ACQUISITION_PROVIDER"

    seen: set[str] = set()
    rounds: list[dict[str, Any]] = []

    while True:
        before = _state_fingerprint(state_path)
        decision = r2.run(
            task,
            repo_root=root,
            information_provider=information_provider,
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
            execution_provider=execution_provider,
        )
        compounding = r3.drain(
            state_path=state_path,
            repo_root=root,
            episode_verification_provider=episode_verification_provider,
            skill_verification_provider=skill_verification_provider,
            success_episode_adapter_provider=success_episode_adapter_provider,
            verification_frontier_acquisition_provider=frontier_provider,
            verification_frontier_acquisition_provider_id=str(provider_id),
            max_actions=int(max_r3_actions_per_round),
        )
        after = _state_fingerprint(state_path)
        rounds.append({
            "round": len(rounds),
            "state_before_sha256": before,
            "state_after_sha256": after,
            "r2_status": decision.get("status"),
            "r2_meta_action": decision.get("r2_meta_action"),
            "r3_status": compounding.get("status"),
            "r3_progress_count": compounding.get("progress_count"),
        })

        if decision.get("pass") is True and decision.get("actual_goal_satisfaction_verified") is True:
            out = _verified_result(task, decision, compounding)
            out["closure_rounds"] = rounds
            out["fixed_point_reached"] = True
            return out

        signature = _digest({
            "state": after,
            "r2": decision,
            "r3_next": compounding.get("next_improvement_action"),
            "r3_progress": compounding.get("progress_count"),
        })
        no_progress = after == before and int(compounding.get("progress_count") or 0) == 0
        if no_progress or signature in seen:
            cert = _irreducible_certificate(
                task=task,
                r2_result=decision,
                r3_result=compounding,
                root1_provider_id=str(provider_id),
            )
            return {
                "schema": SCHEMA,
                "status": IRREDUCIBLE,
                "pass": False,
                "task_id": task.get("task_id"),
                "goal_sha256": _digest(str(task.get("goal") or "")),
                "r2_result": deepcopy(dict(decision)),
                "r3_compounding": deepcopy(dict(compounding)),
                "irreducible_certificate": cert,
                "closure_rounds": rounds,
                "fixed_point_reached": True,
                "postcondition_state": IRREDUCIBLE,
                "internal_provider_missing": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }
        seen.add(signature)
