from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CAPSULE_PATH = ROOT / "canonical/governance/TB_SCIENCE_EXECUTION_CAPSULE_V1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def evaluate(capsule: dict[str, Any] | None = None) -> dict[str, Any]:
    c = copy.deepcopy(capsule) if capsule is not None else _load(CAPSULE_PATH)
    errors: list[str] = []

    if c.get("schema") != "PROJECT_BRAIN_TB_SCIENCE_EXECUTION_CAPSULE_V1":
        errors.append("CAPSULE_SCHEMA_DRIFT")
    if c.get("target_family") != "AGENTIC_SCIENTIFIC_RESEARCH":
        errors.append("TARGET_FAMILY_DRIFT")
    if c.get("target_predicate") != "TB_SCIENCE_GE_58_7":
        errors.append("TARGET_PREDICATE_DRIFT")
    if c.get("execution_authority") is not False:
        errors.append("PREMATURE_EXECUTION_AUTHORITY")
    if c.get("promotion_authority") is not False:
        errors.append("PREMATURE_PROMOTION_AUTHORITY")
    if c.get("terminal_trials_executed") != 0:
        errors.append("TERMINAL_TRIALS_ALREADY_EXECUTED")
    if c.get("incremental_spend_usd") != 0:
        errors.append("NONZERO_INCREMENTAL_SPEND")

    bindings = c.get("exact_brain_bindings") or {}
    if not isinstance(bindings, dict) or not bindings:
        errors.append("EXACT_BINDINGS_MISSING")
    else:
        for rel, expected in sorted(bindings.items()):
            path = ROOT / rel
            if not path.is_file():
                errors.append(f"BOUND_PATH_MISSING:{rel}")
                continue
            observed = _git_blob_sha(path)
            if observed != expected:
                errors.append(f"BOUND_BLOB_MISMATCH:{rel}:{expected}:{observed}")

    manifest_path = ROOT / "canonical/governance/TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json"
    manifest = _load(manifest_path) if manifest_path.is_file() else {}
    acceptance = manifest.get("acceptance") or {}
    rules = manifest.get("execution_rules") or {}
    frozen = c.get("frozen_acceptance") or {}
    dataset = c.get("dataset_binding") or {}
    manifest_dataset = manifest.get("frozen_dataset") or {}

    expected_equalities = [
        ("BAR_PERCENT", frozen.get("bar_percent"), acceptance.get("frozen_bar_percent"), 58.7),
        ("SLOT_COUNT", frozen.get("slot_count"), manifest_dataset.get("slot_count"), 210),
        ("REQUIRED_SUCCESSES", frozen.get("required_successes"), acceptance.get("required_successes"), 124),
        ("FAIL_LOCK", frozen.get("irreversible_failure_count"), acceptance.get("irreversible_failure_count"), 87),
        ("TASK_COUNT", manifest_dataset.get("task_count"), 70, 70),
        ("TRIALS_PER_TASK", manifest_dataset.get("trials_per_task"), 3, 3),
    ]
    for name, a, b, expected in expected_equalities:
        if a != expected or b != expected:
            errors.append(f"{name}_DRIFT:{a}:{b}:{expected}")

    if dataset.get("package") != manifest_dataset.get("package"):
        errors.append("DATASET_PACKAGE_DRIFT")
    if dataset.get("source_commit") != manifest_dataset.get("source_commit"):
        errors.append("DATASET_SOURCE_COMMIT_DRIFT")
    if dataset.get("dataset_manifest_blob") != manifest_dataset.get("dataset_manifest_blob"):
        errors.append("DATASET_MANIFEST_BLOB_DRIFT")
    if dataset.get("content_hash") != manifest_dataset.get("content_hash"):
        errors.append("DATASET_CONTENT_HASH_DRIFT")

    if rules.get("retries_per_slot") != 0:
        errors.append("RETRY_POLICY_DRIFT")
    if rules.get("slot_replacement") is not False:
        errors.append("SLOT_REPLACEMENT_DRIFT")
    if rules.get("denominator_shrink") is not False:
        errors.append("DENOMINATOR_SHRINK_DRIFT")
    if rules.get("stop_on_pass_lock") != "successes>=124":
        errors.append("PASS_LOCK_RULE_DRIFT")
    if rules.get("stop_on_fail_lock") != "finalized_failures>=87":
        errors.append("FAIL_LOCK_RULE_DRIFT")
    if manifest.get("terminal_trials_executed") != 0:
        errors.append("MANIFEST_TERMINAL_TRIALS_NONZERO")
    if manifest.get("execution_authority") is not False:
        errors.append("MANIFEST_PREMATURE_EXECUTION_AUTHORITY")

    for receipt_rel in (
        "canonical/verification/TB_SCIENCE_210_SLOT_MANIFEST_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
        "canonical/verification/TB_SCIENCE_DEDICATED_PLANNER_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
        "canonical/verification/TB_SCIENCE_CONSERVATIVE_CENSORING_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    ):
        p = ROOT / receipt_rel
        receipt = _load(p) if p.is_file() else {}
        status = str(receipt.get("status") or "")
        if "INDEPENDENT" not in status or "PASS" not in status:
            errors.append(f"INDEPENDENT_RECEIPT_NOT_PASS:{receipt_rel}")
        if receipt.get("terminal_results_observed") != 0:
            errors.append(f"RECEIPT_TERMINAL_RESULTS_NONZERO:{receipt_rel}")
        if receipt.get("execution_authority") is not False:
            errors.append(f"RECEIPT_PREMATURE_EXECUTION_AUTHORITY:{receipt_rel}")

    return {
        "schema": "PROJECT_BRAIN_TB_SCIENCE_EXECUTION_CAPSULE_VERIFICATION_V1",
        "status": "PASS__CONTENT_ADDRESSED_ZERO_CASE_CAPSULE__EXECUTION_STILL_FALSE" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "bound_file_count": len(bindings),
        "terminal_results_observed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "next_if_independently_verified": "POINT_OF_USE_ZERO_INCREMENTAL_SPEND_CARRIER_ADMISSION__THEN_ONE_USE_AUTHORITY_BOUND_TO_EXACT_CAPSULE_HASH",
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
