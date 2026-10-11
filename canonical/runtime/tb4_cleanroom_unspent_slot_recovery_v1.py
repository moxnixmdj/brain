from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TB4_CLEANROOM_UNSPENT_SLOT_RECOVERY_GATE_V1"
FROZEN_RELEASE_COMMIT = "452bf305c6daa62fc59061d22133a7cbc7c1572e"
TRIALS_PER_TASK = 5


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "recovered_creditable_slots": 0,
        "success_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _hex(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(ch in "0123456789abcdef" for ch in value)
    )


def evaluate(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping):
        return _fail("SPEC_NOT_MAPPING")
    if spec.get("frozen_release_commit") != FROZEN_RELEASE_COMMIT:
        return _fail("FROZEN_RELEASE_MISMATCH")

    task = spec.get("task")
    if not isinstance(task, str) or not task.strip():
        return _fail("TASK_INVALID")
    if not _hex(spec.get("task_tree_sha"), 40):
        return _fail("TASK_TREE_SHA_INVALID")

    roots = spec.get("preverifier_roots")
    if not isinstance(roots, Mapping):
        return _fail("PREVERIFIER_ROOTS_MISSING")
    if not _hex(roots.get("brain_commit_sha"), 40):
        return _fail("BRAIN_ROOT_INVALID")
    if not _hex(roots.get("runner_commit_sha"), 40):
        return _fail("RUNNER_ROOT_INVALID")
    if roots.get("predates_first_verifier_exposure") is not True:
        return _fail("PREVERIFIER_ORDER_UNPROVED")
    if roots.get("same_configured_route_as_original") is not True:
        return _fail("ROUTE_IDENTITY_UNPROVED")
    if roots.get("independently_verified") is not True:
        return _fail("PREVERIFIER_ROOTS_UNVERIFIED")
    if not _hex(roots.get("verification_receipt_sha256"), 64):
        return _fail("PREVERIFIER_ROOT_RECEIPT_INVALID")

    historical = spec.get("historical_consumption")
    if not isinstance(historical, Mapping):
        return _fail("HISTORICAL_CONSUMPTION_MISSING")
    consumed = historical.get("consumed_trial_indices")
    if (
        not isinstance(consumed, list)
        or any(isinstance(i, bool) or not isinstance(i, int) or i < 1 or i > TRIALS_PER_TASK for i in consumed)
        or len(consumed) != len(set(consumed))
    ):
        return _fail("CONSUMED_TRIAL_INDICES_INVALID")
    if historical.get("independently_verified") is not True:
        return _fail("HISTORICAL_CONSUMPTION_UNVERIFIED")
    if not _hex(historical.get("verification_receipt_sha256"), 64):
        return _fail("HISTORICAL_CONSUMPTION_RECEIPT_INVALID")

    requested = spec.get("requested_recovery_trial_indices")
    if (
        not isinstance(requested, list)
        or not requested
        or any(isinstance(i, bool) or not isinstance(i, int) or i < 1 or i > TRIALS_PER_TASK for i in requested)
        or len(requested) != len(set(requested))
    ):
        return _fail("REQUESTED_RECOVERY_INDICES_INVALID")
    if set(requested) & set(consumed):
        return _fail("RECOVERY_OVERLAPS_CONSUMED_SLOT")

    expected_remaining = set(range(1, TRIALS_PER_TASK + 1)) - set(consumed)
    if not set(requested).issubset(expected_remaining):
        return _fail("RECOVERY_OUTSIDE_UNSPENT_SLOTS")

    isolation = spec.get("cleanroom_isolation")
    if not isinstance(isolation, Mapping):
        return _fail("CLEANROOM_ISOLATION_MISSING")
    required_true = (
        "fresh_environment_from_preverifier_roots",
        "current_brain_tree_unavailable",
        "postresult_artifact_store_unavailable",
        "historical_verifier_outputs_unavailable",
        "hidden_verifier_unavailable_during_actor_phase",
        "actor_write_closed_before_verifier_phase",
        "cross_recovered_trial_result_propagation_disabled",
        "independently_verified",
    )
    for key in required_true:
        if isolation.get(key) is not True:
            return _fail("ISOLATION_" + key.upper() + "_UNPROVED")
    if not _hex(isolation.get("verification_receipt_sha256"), 64):
        return _fail("ISOLATION_RECEIPT_INVALID")

    trials = spec.get("recovery_trials")
    if not isinstance(trials, Sequence) or isinstance(trials, (str, bytes)):
        return _fail("RECOVERY_TRIALS_INVALID")
    if len(trials) != len(requested):
        return _fail("RECOVERY_TRIAL_COUNT_MISMATCH")

    seen_indices: set[int] = set()
    seen_attempts: set[str] = set()
    for row in trials:
        if not isinstance(row, Mapping):
            return _fail("RECOVERY_TRIAL_ROW_INVALID")
        idx = row.get("trial_index")
        attempt = row.get("attempt_id")
        if idx not in requested:
            return _fail("RECOVERY_TRIAL_INDEX_NOT_REQUESTED")
        if idx in seen_indices:
            return _fail("RECOVERY_TRIAL_INDEX_DUPLICATE")
        seen_indices.add(idx)
        if not isinstance(attempt, str) or not attempt.strip() or attempt in seen_attempts:
            return _fail("RECOVERY_ATTEMPT_ID_INVALID_OR_DUPLICATE")
        seen_attempts.add(attempt)
        if row.get("starts_from_exact_preverifier_roots") is not True:
            return _fail("TRIAL_ROOT_BINDING_UNPROVED")
        if row.get("postresult_information_available_to_actor") is not False:
            return _fail("POSTRESULT_INFORMATION_EXPOSURE_NOT_FALSE")
        if row.get("hidden_verifier_available_to_actor") is not False:
            return _fail("HIDDEN_VERIFIER_EXPOSURE_NOT_FALSE")
        if row.get("configuration_mutable_from_other_trial_results") is not False:
            return _fail("CROSS_TRIAL_CONFIGURATION_MUTABILITY_NOT_FALSE")

    if seen_indices != set(requested):
        return _fail("RECOVERY_TRIAL_SET_INCOMPLETE")

    recovered = len(requested)
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__UNSPENT_TRIAL_CAPACITY_RECOVERED__SUCCESS_STILL_UNPROVED",
        "reason": None,
        "task": task,
        "consumed_trial_indices": sorted(consumed),
        "recovered_trial_indices": sorted(requested),
        "recovered_creditable_slots": recovered,
        "success_credit_delta": 0,
        "requires_separate_official_verifier_receipt_per_recovered_slot": True,
        "same_task_identity_replay_rule_replaced_by_causal_no_leakage_rule": True,
        "execution_authority": False,
        "promotion_authority": False,
    }
