import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "canonical/governance/LIVEBENCH_2026_06_25_IFBENCH58_SCORER_ROUTE_RECONCILIATION_20261005_V1.json"
ACTIVATION = ROOT / "canonical/governance/LIVEBENCH_TERMINAL_SCORER_SCOPE_ACTIVATION_V1.json"
RECEIPT = ROOT / "canonical/verification/LIVEBENCH_ACTIVE_SCORER_FAMILY_INDEPENDENT_VERIFICATION_20261004_V1.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_snapshot_date_cannot_replace_per_question_release_date():
    candidate = _load(CANDIDATE)
    activation = _load(ACTIVATION)
    receipt = _load(RECEIPT)

    assert candidate["status"].startswith("FALSIFIED__TARGET_SNAPSHOT_DATE_WAS_CONFUSED")
    assert activation["status"].startswith("ACTIVE__INDEPENDENTLY_VERIFIED")
    assert activation["activated_scheduler_truth"]["active_scorer_family"] == "LEGACY_IFEVAL_ONLY"
    assert activation["activated_scheduler_truth"]["active_population_count"] == 200
    assert activation["activated_scheduler_truth"]["modern_ifbench_checker_count_on_exact_frozen_critical_path"] == 0

    vr = receipt["verified_result"]
    assert vr["active_population_count"] == 200
    assert vr["active_release_date_histogram"] == {"2024-11-25": 200}
    assert vr["legacy_ifeval_active_rows"] == 200
    assert vr["modern_ifbench_active_rows"] == 0

    falsifier = candidate["falsification"]
    assert falsifier["exact_counterexample"]["target_snapshot_date"] == "2026-06-25"
    assert falsifier["exact_counterexample"]["dispatch_boundary"] == "2025-11-25"
    assert "QUESTION_LIVEBENCH_RELEASE_DATE" in falsifier["root_cause"]
    assert candidate["branch_reclassification"]["legacy25_union25_for_target_predicate"] == "LOAD_BEARING"
    assert "DO_NOT_DELETE_LEGACY25_WORK" in candidate["scheduler_rule"]


def test_ifbench58_reactivation_requires_identity_change_or_content_addressed_contradiction():
    candidate = _load(CANDIDATE)
    gate = candidate["independent_verification_gate"]
    assert gate["state"] == "VOIDED_BY_STRONGER_PREEXISTING_INDEPENDENT_METADATA_RECEIPT"
    assert gate["required_if_reopened"] == [
        "CHANGE_IN_FROZEN_DATASET_BYTES_OR_DISPATCH_IDENTITY",
        "CONTENT_ADDRESSED_CONTRADICTION_TO_200_LEGACY_0_MODERN_RECEIPT",
    ]
