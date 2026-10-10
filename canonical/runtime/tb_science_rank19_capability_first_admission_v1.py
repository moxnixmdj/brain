from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime.capability_first_scheduler_v1 import rank_work

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = "canonical/governance/TB_SCIENCE_RANK19_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_20261010_V1.json"
SLOT = "terminal-bench-science/diag-chipseq::trial-0"
DIGEST = "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
ATTEMPT = "def7e2921acf58d4ef03e3183512996c718a5a13069482cb825464c0c963a8b4"
PLANNER_SHA = "e5d6ab78b6cf5bacee568cd3701410a8745b9ce8"
AGENT_SHA = "8deede8adb960b6ebf7ee747a5e9ff1016238b7e"

SOURCES = {
    "scheduler_activation": (
        "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V3.json",
        "472c98a195c4b98d340e9bb397fa8766e3b47928",
    ),
    "development_scheduler": (
        "canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json",
        "6723cac2745e08147ec4efe2a887a53992b0c06a",
    ),
    "scheduler_runtime": (
        "canonical/runtime/capability_first_scheduler_v1.py",
        "b74f967038ae5f71d45468b4233452cd134fd699",
    ),
    "terminal_authority": (
        "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
        "57398d9a9ce84ab1897490995a0316206a4148d6",
    ),
    "rank18_diagnosis": (
        "canonical/verification/TB_SCIENCE_RANK18_PLANNER_TIMEOUT_CAUSAL_DIAGNOSIS_20261010_V1.json",
        "97697c3c7868644d36b317dc7e4e80dfd8f97647",
    ),
    "planner_v7_verification": (
        "canonical/verification/TB_SCIENCE_PLANNER_V7_ZERO_EXPOSURE_VERIFICATION_20261010_V1.json",
        "9797cc625e3e33bb905cf23fa6c79f66dc9794db",
    ),
    "rank19_one_slot_authority": (
        "canonical/governance/TB_SCIENCE_RANK19_ONE_SLOT_EXECUTION_AUTHORITY_20261010_V1.json",
        "ea76756ea30084c7f8291747ae9d204485a0186a",
    ),
    "rank19_ledger": (
        "canonical/governance/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261010_V38.json",
        "137a2f61d911321365bd80613e3806a77dbe7eca",
    ),
}


def _blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    obj = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(path + ":OBJECT_REQUIRED")
    return obj


def verify() -> dict[str, Any]:
    errors: list[str] = []
    candidate = _load(CANDIDATE)

    bindings = candidate.get("source_bindings")
    if not isinstance(bindings, dict):
        errors.append("SOURCE_BINDINGS_MISSING")
        bindings = {}

    for key, (path, expected) in SOURCES.items():
        actual = _blob(path)
        if actual != expected:
            errors.append(f"SOURCE_DRIFT:{key}:{actual}")
        row = bindings.get(key)
        if not isinstance(row, dict) or row.get("path") != path or row.get("git_blob_sha") != expected:
            errors.append("CANDIDATE_SOURCE_BINDING_DRIFT:" + key)

    activation = _load(SOURCES["scheduler_activation"][0])
    terminal = _load(SOURCES["terminal_authority"][0])
    diagnosis = _load(SOURCES["rank18_diagnosis"][0])
    planner_verify = _load(SOURCES["planner_v7_verification"][0])
    authority = _load(SOURCES["rank19_one_slot_authority"][0])
    ledger = _load(SOURCES["rank19_ledger"][0])

    allowed_roles = (
        activation.get("primary_work_rule", {}).get("allowed_benchmark_roles", [])
        if isinstance(activation.get("primary_work_rule"), dict)
        else []
    )
    if "NEW_CAPABILITY_VALIDATION" not in allowed_roles:
        errors.append("NEW_CAPABILITY_VALIDATION_NOT_ALLOWED")
    if activation.get("terminal_autopilot_policy", {}).get(
        "new_dispatch_requires_explicit_capability_first_checkpoint_admission"
    ) is not True:
        errors.append("EXPLICIT_CHECKPOINT_ADMISSION_POLICY_MISSING")

    live_truth = terminal.get("live_truth")
    open_count = (
        live_truth.get("independent_open_acceptance_obligations")
        if isinstance(live_truth, dict)
        else None
    )
    if not isinstance(open_count, int) or isinstance(open_count, bool) or open_count < 0:
        errors.append("OPEN_OBLIGATION_COUNT_INVALID")
        open_count = 0

    work = candidate.get("scheduler_work_item")
    scheduler_row: dict[str, Any] = {}
    try:
        ranking = rank_work([work], checkpoint_open_obligation_count=open_count)
        rows = ranking.get("ranked", [])
        scheduler_row = rows[0] if isinstance(rows, list) and len(rows) == 1 else {}
        if scheduler_row.get("eligibility") != "ELIGIBLE":
            errors.append("SCHEDULER_NOT_ELIGIBLE")
        if scheduler_row.get("benchmark_role") != "NEW_CAPABILITY_VALIDATION":
            errors.append("SCHEDULER_ROLE_MISMATCH")
    except Exception as exc:
        errors.append("SCHEDULER_EVALUATION_FAILED:" + type(exc).__name__ + ":" + str(exc))

    if diagnosis.get("pass") is not True:
        errors.append("RANK18_DIAGNOSIS_NOT_PASS")
    if diagnosis.get("causal_proof", {}).get("root_class") != "PLANNER_TIMEOUT_UNDERBUDGET":
        errors.append("RANK18_DEFECT_CLASS_DRIFT")
    if diagnosis.get("repair_candidate", {}).get("planner_git_blob_sha") != PLANNER_SHA:
        errors.append("DIAGNOSIS_PLANNER_SHA_DRIFT")
    if diagnosis.get("repair_candidate", {}).get("agent_git_blob_sha") != AGENT_SHA:
        errors.append("DIAGNOSIS_AGENT_SHA_DRIFT")

    if planner_verify.get("pass") is not True:
        errors.append("PLANNER_V7_VERIFICATION_NOT_PASS")
    real = planner_verify.get("real_public_verification")
    if not isinstance(real, dict) or real.get("conclusion") != "success":
        errors.append("REAL_QWEN_VERIFICATION_NOT_SUCCESS")
    else:
        if real.get("task_read") is not False or real.get("task_started") is not False:
            errors.append("ZERO_EXPOSURE_VIOLATED")
        if real.get("benchmark_trials_consumed") != 0:
            errors.append("ZERO_EXPOSURE_TRIAL_COUNT_NONZERO")
        if real.get("exact_planner_git_blob_sha") != PLANNER_SHA:
            errors.append("REAL_QWEN_PLANNER_SHA_DRIFT")
    cand_runtime = planner_verify.get("candidate")
    if not isinstance(cand_runtime, dict):
        errors.append("PLANNER_CANDIDATE_MISSING")
    else:
        if cand_runtime.get("planner", {}).get("git_blob_sha") != PLANNER_SHA:
            errors.append("PLANNER_SHA_DRIFT")
        if cand_runtime.get("agent", {}).get("git_blob_sha") != AGENT_SHA:
            errors.append("AGENT_SHA_DRIFT")

    slot = authority.get("slot")
    logical = authority.get("logical_attempt")
    controls = authority.get("controls")
    state = authority.get("state")
    if not isinstance(slot, dict) or slot.get("id") != SLOT or slot.get("digest") != DIGEST:
        errors.append("RANK19_AUTHORITY_SLOT_DRIFT")
    if not isinstance(logical, dict) or logical.get("id") != ATTEMPT:
        errors.append("RANK19_LOGICAL_ATTEMPT_DRIFT")
    if authority.get("execution_authority") is not True or authority.get("execution_authority_effective") is not False:
        errors.append("RANK19_STAGED_AUTHORITY_STATE_DRIFT")
    if not isinstance(controls, dict):
        errors.append("RANK19_CONTROLS_MISSING")
    else:
        if controls.get("logical_attempts_authorized_total") != 1:
            errors.append("LOGICAL_ATTEMPT_COUNT_NOT_ONE")
        if controls.get("retries_authorized") != 0:
            errors.append("RETRY_AUTHORITY_NONZERO")
        if controls.get("replacement_allowed") is not False:
            errors.append("REPLACEMENT_AUTHORITY_PRESENT")
        if controls.get("model_reasoning_before_durable_start_forbidden") is not True:
            errors.append("PRESTART_REASONING_NOT_FORBIDDEN")
        if controls.get("task_start_requires_prestart_guard_agent_ready_and_durable_start_cas") is not True:
            errors.append("START_BARRIER_NOT_REQUIRED")
        if controls.get("uncertain_effect_replay_authority") is not False:
            errors.append("UNCERTAIN_EFFECT_REPLAY_AUTHORIZED")
    if not isinstance(state, dict) or state.get("task_read_history") is not False or state.get("task_started") is not False or state.get("benchmark_trials_consumed") != 0:
        errors.append("RANK19_NOT_FRESH")

    counts = ledger.get("counts")
    next_slot = ledger.get("next_slot")
    scheduler = ledger.get("scheduler")
    if not isinstance(counts, dict) or counts.get("benchmark_trials_consumed") != 18 or counts.get("consumed_failures_final") != 18:
        errors.append("RANK19_LEDGER_PREDECESSOR_COUNT_DRIFT")
    if not isinstance(next_slot, dict):
        errors.append("RANK19_LEDGER_NEXT_SLOT_MISSING")
    else:
        if next_slot.get("slot_id") != SLOT or next_slot.get("task_digest") != DIGEST:
            errors.append("RANK19_LEDGER_SLOT_DRIFT")
        if next_slot.get("logical_attempt_id") != ATTEMPT:
            errors.append("RANK19_LEDGER_ATTEMPT_DRIFT")
        if next_slot.get("task_read_history") is not False or next_slot.get("task_started") is not False:
            errors.append("RANK19_LEDGER_EXPOSURE_DRIFT")
        if next_slot.get("start_cas_acquired") is not False or next_slot.get("benchmark_trials_consumed") != 0:
            errors.append("RANK19_LEDGER_CONSUMPTION_DRIFT")
    if not isinstance(scheduler, dict) or scheduler.get("rank19_execution_authority_effective") is not False:
        errors.append("RANK19_LEDGER_AUTHORITY_STATE_DRIFT")

    expected = {
        "schema": "PROJECT_BRAIN_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_V1",
        "authorized": True,
        "decision": "ADMIT_CHECKPOINT_AUDIT_EXECUTION",
        "authorized_scope": "CHECKPOINT_AUDIT_DISPATCH_ONLY",
        "benchmark_role": "NEW_CAPABILITY_VALIDATION",
        "slot_id": SLOT,
        "task_digest": DIGEST,
        "logical_attempt_id": ATTEMPT,
        "logical_attempts_authorized_total": 1,
        "retries_authorized": 0,
        "replacement_allowed": False,
        "task_read": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "checkpoint_dispatch_admission": True,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
    for key, value in expected.items():
        if candidate.get(key) != value:
            errors.append("CANDIDATE_FIELD_DRIFT:" + key)

    validation = candidate.get("validation_target")
    if not isinstance(validation, dict):
        errors.append("VALIDATION_TARGET_MISSING")
    else:
        if validation.get("defect_class") != "PLANNER_TIMEOUT_UNDERBUDGET":
            errors.append("VALIDATION_DEFECT_CLASS_DRIFT")
        if validation.get("planner_git_blob_sha") != PLANNER_SHA:
            errors.append("VALIDATION_PLANNER_SHA_DRIFT")
        if validation.get("agent_git_blob_sha") != AGENT_SHA:
            errors.append("VALIDATION_AGENT_SHA_DRIFT")
        if validation.get("prior_zero_exposure_real_local_qwen_pass") is not True:
            errors.append("PRIOR_REAL_ZERO_EXPOSURE_PASS_MISSING")

    ok = not errors
    return {
        "schema": "PROJECT_BRAIN_TB_SCIENCE_RANK19_CAPABILITY_FIRST_ADMISSION_VERIFIER_V1",
        "status": "PASS__RANK19_ONE_SHOT_NEW_CAPABILITY_VALIDATION_ADMITTED__ZERO_EXECUTION_CREDIT" if ok else "FAIL_CLOSED",
        "pass": ok,
        "errors": sorted(errors),
        "scheduler_eligibility": scheduler_row.get("eligibility"),
        "benchmark_role": scheduler_row.get("benchmark_role"),
        "checkpoint_open_obligation_count": open_count,
        "slot_id": SLOT,
        "task_digest": DIGEST,
        "logical_attempt_id": ATTEMPT,
        "task_read": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "execution_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
