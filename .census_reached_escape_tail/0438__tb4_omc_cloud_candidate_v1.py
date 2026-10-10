from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_TB4_OMC_CLOUD_CANDIDATE_REDUCER_V1"
CUT = "canonical/governance/TB4_MINIMUM_CARRIER_RECOVERY_CUT_V1.json"
CAND = "canonical/governance/TB4_OMC_CLOUD_FREE_TRIAL_CARRIER_CANDIDATE_20261004_V1.json"

def load(path: str):
    return json.loads((ROOT / path).read_text())

def evaluate():
    cut = load(CUT)
    cand = load(CAND)
    env = cand["candidate_envelope"]
    req = cut["minimum_carrier_envelope"]
    errors = []
    if env["nominal_vcpus"] < req["cpus_at_least"]:
        errors.append("CPU_DOCUMENTARY_MISS")
    if env["nominal_memory_mb"] < req["usable_memory_mb_at_least"]:
        errors.append("NOMINAL_MEMORY_DOCUMENTARY_MISS")
    if env["storage_mb"] < req["free_storage_mb_at_least"]:
        errors.append("STORAGE_DOCUMENTARY_MISS")
    if req["docker_required"] and not env["docker_documented"]:
        errors.append("DOCKER_DOCUMENTARY_MISS")
    if req["docker_compose_required"] and not env["docker_compose_documented"]:
        errors.append("DOCKER_COMPOSE_DOCUMENTARY_MISS")
    if env["monthly_list_price_usd"] > env["trial_configuration_ceiling_usd"]:
        errors.append("TRIAL_VALUE_CEILING_MISS")
    if env["payment_method_required_for_trial"]:
        errors.append("PAYMENT_METHOD_REQUIRED")
    if env["automatic_paid_overage_without_payment_method"]:
        errors.append("AUTOMATIC_PAID_OVERAGE")
    d = cand["documentary_deduction"]
    for key in [
        "usable_memory_fit_proved",
        "material_account_access_proved",
        "runtime_shape_identity_proved",
        "protocol_equivalence_proved",
        "attainability_reopened",
    ]:
        if d[key] is not False:
            errors.append("OVERCLAIM_" + key.upper())
    if cand["execution_authority"] is not False:
        errors.append("EXECUTION_AUTHORITY_OVERCLAIM")
    if cand["fresh_reality_authority"] is not False:
        errors.append("FRESH_REALITY_OVERCLAIM")
    ok = not errors
    return {
        "schema": SCHEMA,
        "status": "PASS__DOCUMENTARY_CARRIER_CANDIDATE__RUNTIME_PREFLIGHT_REQUIRED__ZERO_CREDIT" if ok else "FAIL_CLOSED",
        "pass": ok,
        "errors": errors,
        "minimum_recovery_task_count": len(cut["minimum_recovery_set"]),
        "additional_creditable_tasks_needed": cut["frozen_score_math"]["additional_creditable_tasks_needed"],
        "runtime_preflight_required": True,
        "usable_memory_must_be_observed_inside_guest": True,
        "attainability_recompile_required_after_runtime_pass": True,
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
