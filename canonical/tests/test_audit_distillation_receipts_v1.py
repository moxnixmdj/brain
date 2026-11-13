import json

from canonical.tools.audit_distillation_receipts_v1 import audit


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _pair(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    receipt_path = evidence / "CAPABILITY__one__EXECUTION_RECEIPT.json"
    verification_path = evidence / "CAPABILITY__one__INDEPENDENT_VERIFICATION.json"
    receipt = {
        "capability_id": "one", "ran_by": "producer", "module_sha256": "a" * 64,
        "result_sha256": "b" * 64, "observed": {"pass": True}, "invoked_args": {},
    }
    verification = {
        "producer_receipt_path": str(receipt_path.relative_to(tmp_path)),
        "capability_id": "one", "producer_ran_by": "producer", "independent_verifier": "verifier",
        "module_sha256": "a" * 64, "producer_result_sha256": "b" * 64,
        "verifier_result_sha256": "b" * 64, "reproduced": True,
        "independent_run_reference": {"github_run_id": 123},
    }
    _write(receipt_path, receipt)
    _write(verification_path, verification)
    return evidence, receipt_path, verification_path, receipt, verification


def test_summary_receipt_is_not_a_trajectory(tmp_path):
    evidence, _, _, _, _ = _pair(tmp_path)
    result = audit(evidence, tmp_path)
    assert result["counts"]["consistent_reproduction_metadata"] == 1
    assert result["counts"]["producer_pass"] == 1
    assert result["counts"]["structured_trajectory_present"] == 0
    assert result["counts"]["passing_with_trajectory_and_consistent_metadata"] == 0


def test_candidate_shape_is_not_promoted_when_reproduction_mismatches(tmp_path):
    evidence, receipt_path, verification_path, receipt, verification = _pair(tmp_path)
    receipt.update(task="fix a module", trajectory=[{"observation": "error", "action": "edit"}])
    _write(receipt_path, receipt)
    assert audit(evidence, tmp_path)["counts"]["passing_with_trajectory_and_consistent_metadata"] == 1
    verification["verifier_result_sha256"] = "c" * 64
    _write(verification_path, verification)
    counts = audit(evidence, tmp_path)["counts"]
    assert counts["structured_trajectory_present"] == 1
    assert counts["consistent_reproduction_metadata"] == 0
    assert counts["passing_with_trajectory_and_consistent_metadata"] == 0


def test_path_escape_and_bad_json_are_counted_without_following(tmp_path):
    evidence, _, verification_path, _, verification = _pair(tmp_path)
    verification["producer_receipt_path"] = "../outside/CAPABILITY__other__EXECUTION_RECEIPT.json"
    _write(verification_path, verification)
    (evidence / "CAPABILITY__bad__INDEPENDENT_VERIFICATION.json").write_text("{", encoding="utf-8")
    counts = audit(evidence, tmp_path)["counts"]
    assert counts["verification_records"] == 2
    assert counts["unreadable_or_invalid_links"] == 2
    assert counts["linked_records"] == 0


def test_incomplete_turn_and_non_boolean_verdict(tmp_path):
    evidence, receipt_path, _, receipt, _ = _pair(tmp_path)
    receipt.update(task="fix", trajectory=[{"observation": "error", "action": ""}], observed={"pass": 1})
    _write(receipt_path, receipt)
    counts = audit(evidence, tmp_path)["counts"]
    assert counts["structured_trajectory_present"] == 0
    assert counts["boolean_producer_verdict"] == 0
    assert counts["producer_pass"] == 0
