from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime.capability_first_scheduler_v1 import rank_work

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = "canonical/governance/TB_SCIENCE_RANK20_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_20261010_V1.json"

SLOT = "terminal-bench-science/hysteretic-aquifer-control::trial-0"
DIGEST = "sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"

SOURCES = {
    "scheduler_activation": (
        "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V6.json",
        "73d91005b9cad71169b2ef506ae20cfcc8b612ef",
    ),
    "scheduler_runtime": (
        "canonical/runtime/capability_first_scheduler_v1.py",
        "6d2091cc1581b9aa1fd2c74e8a76519a41d9d957",
    ),
    "scheduler_residual_ledger": (
        "canonical/runtime/r2_semantic_residual_ledger_v1.py",
        "d7646a9f0113536ed52dd4f9c2e14e0190ed52a1",
    ),
    "frozen_manifest": (
        "canonical/governance/TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json",
        "6dfa880b1f68881531afbba6ca211681801fd19b",
    ),
    "rank19_ledger": (
        "canonical/governance/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261010_V41.json",
        "9b57fba46890146527970ee51a47081791341598",
    ),
    "rank19_result": (
        "canonical/verification/TB_SCIENCE_RANK19_RESULT_TRUTH_20261010_V1.json",
        "66b02049cc3d142cefe8c6bcc966fdcc4c5cb08b",
    ),
    "rank19_diagnosis": (
        "canonical/governance/TB_SCIENCE_RANK19_IDENTITY_SKEW_DIAGNOSIS_20261010_V1.json",
        "e4ce666de016716328ac577b4858a126f41126da",
    ),
    "agent_v13_identity_v2_repair_verification": (
        "canonical/verification/AGENT_V13_IDENTITY_V2_REPAIR_VERIFY_20261010_V1.json",
        "ec982a8cde737669d42abfb62a9f3cbdf0752434",
    ),
    "repaired_agent_v13": (
        "canonical/runtime/harbor_science_agent_v13.py",
        "470bfe079aeffaa07a3b92975b4edea17c9a20e1",
    ),
    "identity_v2": (
        "execution_guard/logical_attempt_identity_v2.py",
        "67ff638459af1bb50a094e9479fb4aa5e2a3de1c",
    ),
}


def _blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":OBJECT_REQUIRED")
    return value


def verify() -> dict[str, Any]:
    errors: list[str] = []
    candidate = _load(CANDIDATE)
    bindings = candidate.get("source_bindings")
    if not isinstance(bindings, dict):
        errors.append("SOURCE_BINDINGS_MISSING")
        bindings = {}

    for key, (path, expected_sha) in SOURCES.items():
        actual_sha = _blob(path)
        if actual_sha != expected_sha:
            errors.append(f"SOURCE_DRIFT:{key}:{actual_sha}")
        row = bindings.get(key)
        if not isinstance(row, dict):
            errors.append("CANDIDATE_SOURCE_BINDING_MISSING:" + key)
        elif row.get("path") != path or row.get("git_blob_sha") != expected_sha:
            errors.append("CANDIDATE_SOURCE_BINDING_DRIFT:" + key)

    activation = _load(SOURCES["scheduler_activation"][0])
    manifest = _load(SOURCES["frozen_manifest"][0])
    ledger = _load(SOURCES["rank19_ledger"][0])
    result = _load(SOURCES["rank19_result"][0])
    diagnosis = _load(SOURCES["rank19_diagnosis"][0])
    repair = _load(SOURCES["agent_v13_identity_v2_repair_verification"][0])

    allowed_roles = (
        activation.get("primary_work_rule", {}).get("allowed_benchmark_roles", [])
        if isinstance(activation.get("primary_work_rule"), dict)
        else []
    )
    if "NEW_CAPABILITY_VALIDATION" not in allowed_roles:
        errors.append("NEW_CAPABILITY_VALIDATION_NOT_ALLOWED")
    if activation.get("status") != "ACTIVE_PRIMARY_CAPABILITY_FIRST_DEVELOPMENT_SCHEDULER__REUSE_FIRST_RESIDUAL_ADMISSION_MECHANICALLY_ENFORCED":
        errors.append("SCHEDULER_ACTIVATION_STATUS_DRIFT")

    work = candidate.get("scheduler_work_item")
    scheduler_row: dict[str, Any] = {}
    try:
        ranking = rank_work([work], checkpoint_open_obligation_count=0)
        rows = ranking.get("ranked", [])
        scheduler_row = rows[0] if isinstance(rows, list) and len(rows) == 1 else {}
        if scheduler_row.get("eligibility") != "ELIGIBLE":
            errors.append("SCHEDULER_NOT_ELIGIBLE")
        if scheduler_row.get("benchmark_role") != "NEW_CAPABILITY_VALIDATION":
            errors.append("SCHEDULER_ROLE_MISMATCH")
        if scheduler_row.get("claims_new_primitive") is not False:
            errors.append("UNEXPECTED_NEW_PRIMITIVE_CLAIM")
        if scheduler_row.get("new_primitive_proof_complete") is not True:
            errors.append("NON_NEW_PRIMITIVE_SHOULD_NOT_REQUIRE_NEW_PRIMITIVE_PROOF")
    except Exception as exc:
        errors.append("SCHEDULER_EVALUATION_FAILED:" + type(exc).__name__ + ":" + str(exc))

    slots = manifest.get("slots")
    matching = [
        row for row in slots or []
        if isinstance(row, dict)
        and row.get("schedule_order") == 19
        and row.get("attempt_index") == 0
    ]
    if len(matching) != 1:
        errors.append("FROZEN_MANIFEST_RANK20_SLOT_NOT_UNIQUE")
    else:
        row = matching[0]
        if row.get("task_rank") != 19:
            errors.append("FROZEN_MANIFEST_TASK_RANK_DRIFT")
        if row.get("slot_id") != SLOT or row.get("task_digest") != DIGEST:
            errors.append("FROZEN_MANIFEST_SLOT_OR_DIGEST_DRIFT")
        if row.get("standard_public_storage_feasible") is not True:
            errors.append("FROZEN_MANIFEST_SLOT_NOT_STORAGE_FEASIBLE")

    if manifest.get("terminal_task_content_read") != 0:
        errors.append("FROZEN_MANIFEST_TASK_CONTENT_READ_NONZERO")
    if manifest.get("execution_authority") is not False:
        errors.append("FROZEN_MANIFEST_EXECUTION_AUTHORITY_PRESENT")
    rules = manifest.get("execution_rules") or {}
    if rules.get("task_content_used_for_scheduling") is not False:
        errors.append("TASK_CONTENT_USED_FOR_SCHEDULING")
    if rules.get("scheduling_basis") != "FROZEN_RESOURCE_METADATA_ONLY":
        errors.append("SCHEDULING_BASIS_DRIFT")

    if result.get("status") != "PREEXPOSURE_ABORT_NONCONSUMING":
        errors.append("RANK19_RESULT_CLASS_DRIFT")
    if result.get("task_started") is not False or result.get("start_cas_acquired") is not False:
        errors.append("RANK19_START_STATE_DRIFT")
    if result.get("benchmark_trials_consumed") != 0:
        errors.append("RANK19_NONCONSUMING_STATE_DRIFT")
    if result.get("retry_authority") is not False or result.get("replacement_authority") is not False:
        errors.append("RANK19_RETRY_OR_REPLACEMENT_REOPENED")

    counts = ledger.get("counts") or {}
    if counts.get("benchmark_trials_consumed") != 18 or counts.get("consumed_failures_final") != 18:
        errors.append("LEDGER_COUNTS_DRIFT")
    retired = ledger.get("retired_nonconsuming_exposed_slot") or {}
    if retired.get("slot_id") != "terminal-bench-science/diag-chipseq::trial-0":
        errors.append("RANK19_RETIRED_SLOT_DRIFT")
    if retired.get("task_read_history") is not True or retired.get("task_started") is not False:
        errors.append("RANK19_RETIRED_EXPOSURE_STATE_DRIFT")
    if retired.get("retry_authority") is not False or retired.get("replacement_authority") is not False:
        errors.append("RANK19_RETIRED_AUTHORITY_DRIFT")

    if diagnosis.get("status") != "PROVED_PRESTART_TRANSPORT_VERSION_SKEW":
        errors.append("RANK19_DIAGNOSIS_STATUS_DRIFT")
    if diagnosis.get("cause") != "RUNNER_CARRIES_V2_CLAIM_BOUND_ID__AGENT_V13_RECOMPUTES_V1_SLOT_TASK_ONLY_ID":
        errors.append("RANK19_DIAGNOSIS_CAUSE_DRIFT")
    if diagnosis.get("retry_authority") is not False or diagnosis.get("replacement_authority") is not False:
        errors.append("RANK19_DIAGNOSIS_AUTHORITY_DRIFT")

    if repair.get("status") != "PASS__PUBLIC_NO_TASK_REPLAY__PYCOMPILE__5_OF_5__ZERO_EXPOSURE":
        errors.append("IDENTITY_V2_REPAIR_NOT_VERIFIED")
    public = repair.get("public_verification") or {}
    if public.get("conclusion") != "success" or public.get("tests") != 5:
        errors.append("IDENTITY_V2_PUBLIC_VERIFICATION_DRIFT")
    if public.get("task_read") is not False or public.get("task_started") is not False or public.get("benchmark_trials_consumed") != 0:
        errors.append("IDENTITY_V2_REPAIR_NOT_ZERO_EXPOSURE")
    exact = repair.get("exact_blobs") or {}
    if exact.get("execution_guard_v2") != SOURCES["identity_v2"][1]:
        errors.append("IDENTITY_V2_BLOB_DRIFT")
    if exact.get("agent_v13_repaired") != SOURCES["repaired_agent_v13"][1]:
        errors.append("REPAIRED_AGENT_BLOB_DRIFT")

    slot = candidate.get("slot") or {}
    if slot.get("ledger_schedule_rank") != 20 or slot.get("frozen_manifest_schedule_order") != 19 or slot.get("task_rank") != 19:
        errors.append("CANDIDATE_RANK_METADATA_DRIFT")
    if slot.get("slot_id") != SLOT or slot.get("task_digest") != DIGEST:
        errors.append("CANDIDATE_SLOT_DRIFT")
    if slot.get("task_content_read") is not False:
        errors.append("CANDIDATE_TASK_CONTENT_READ")

    identity = candidate.get("logical_attempt_identity") or {}
    if identity.get("version") != "V2":
        errors.append("IDENTITY_VERSION_DRIFT")
    if identity.get("identity_basis") != "SLOT_ID_PLUS_TASK_DIGEST_PLUS_EXECUTION_CLAIM_BINDING_DIGEST":
        errors.append("IDENTITY_BASIS_DRIFT")
    if identity.get("execution_claim_binding_digest") is not None:
        errors.append("PRECLAIM_EXECUTION_CLAIM_DIGEST_FABRICATED")
    if identity.get("logical_attempt_id") is not None:
        errors.append("PRECLAIM_LOGICAL_ATTEMPT_ID_FABRICATED")
    if identity.get("minted") is not False:
        errors.append("PRECLAIM_IDENTITY_MINTED")
    if identity.get("admission_can_mint_identity") is not False:
        errors.append("ADMISSION_IMPROPERLY_MINTS_IDENTITY")
    if identity.get("legacy_v1_fallback_allowed") is not False:
        errors.append("LEGACY_V1_FALLBACK_ALLOWED")

    expected = {
        "schema": "PROJECT_BRAIN_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_V2",
        "authorized": True,
        "decision": "ADMIT_CHECKPOINT_AUDIT_EXECUTION",
        "authorized_scope": "CHECKPOINT_AUDIT_DISPATCH_ONLY",
        "benchmark_role": "NEW_CAPABILITY_VALIDATION",
        "task_read": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "checkpoint_dispatch_admission": True,
        "execution_claim_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
    for key, value in expected.items():
        if candidate.get(key) != value:
            errors.append("CANDIDATE_FIELD_DRIFT:" + key)

    controls = candidate.get("controls") or {}
    if controls.get("logical_attempts_authorized_total") != 1:
        errors.append("LOGICAL_ATTEMPT_COUNT_NOT_ONE")
    if controls.get("retries_authorized") != 0 or controls.get("replacement_allowed") is not False:
        errors.append("RETRY_OR_REPLACEMENT_AUTHORITY_PRESENT")
    if controls.get("task_read_before_public_reseal_and_live_preflight_forbidden") is not True:
        errors.append("PRE_RESEAL_TASK_READ_NOT_FORBIDDEN")
    if controls.get("rank19_replay_forbidden") is not True:
        errors.append("RANK19_REPLAY_NOT_FORBIDDEN")

    ok = not errors
    return {
        "schema": "PROJECT_BRAIN_TB_SCIENCE_RANK20_CAPABILITY_FIRST_ADMISSION_VERIFIER_V1",
        "status": "PASS__RANK20_UNEXPOSED_IDENTITY_V2_VALIDATION_ADMITTED__PRECLAIM__ZERO_EXECUTION_CREDIT" if ok else "FAIL_CLOSED",
        "pass": ok,
        "errors": sorted(errors),
        "scheduler_eligibility": scheduler_row.get("eligibility"),
        "benchmark_role": scheduler_row.get("benchmark_role"),
        "claims_new_primitive": scheduler_row.get("claims_new_primitive"),
        "slot_id": SLOT,
        "task_digest": DIGEST,
        "task_read": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "logical_attempt_id_minted": False,
        "execution_claim_binding_digest_present": False,
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
