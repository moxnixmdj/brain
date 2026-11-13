"""Synthetic records exercise the census, not external model training."""
import json

import verified_experience_census_20261112 as census


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_counts_claims_without_promoting_missing_model_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(census, "EVIDENCE", tmp_path)
    producer = {"capability_id": "sample", "observed": {"pass": True}, "ran_by": "producer"}
    verification = {"capability_id": "sample", "reproduced": True, "model_dependency_count": 0,
                    "independent_verifier": "other", "independent_run_reference": {"github_run_id": 12}}
    _write(tmp_path / "CAPABILITY__sample__EXECUTION_RECEIPT.json", producer)
    _write(tmp_path / "CAPABILITY__sample__INDEPENDENT_VERIFICATION.json", verification)
    report = census.census()
    assert report["joined"] == 1
    assert report["joined_reproduced_with_run_id_boolean_verdict_and_model_free_claims"] == 0
    assert report["training_readiness_assessed"] is False
    assert report["independent_verification_performed"] is False
    producer["model_dependency_count"] = 0
    _write(tmp_path / "CAPABILITY__sample__EXECUTION_RECEIPT.json", producer)
    report = census.census()
    assert report["joined_reproduced_with_run_id_boolean_verdict_and_model_free_claims"] == 1
    assert report["joined_matching_metadata_with_pass_true"] == 1
    assert report["training_readiness_assessed"] is False


def test_duplicate_ids_and_malformed_files_are_visible(tmp_path, monkeypatch):
    monkeypatch.setattr(census, "EVIDENCE", tmp_path)
    receipt = {"capability_id": "sample", "model_dependency_count": 0}
    _write(tmp_path / "a_RECEIPT.json", receipt)
    _write(tmp_path / "b_RECEIPT.json", receipt)
    _write(tmp_path / "bad_RECEIPT.json", [])
    _write(tmp_path / "other_RECEIPT.json", {"kind": "unrelated"})
    report = census.census()
    assert report["producer_receipts"] == 1
    assert report["duplicate_producer_capability_ids"] == ["sample"]
    assert report["unreadable_or_invalid_records"] == ["bad_RECEIPT.json"]
    assert report["ignored_without_capability_id"] == ["other_RECEIPT.json"]
    assert report["training_readiness_assessed"] is False
