"""Count both receipt types without mistaking metadata for verified training data.

The old census missed verification records; a later one overcorrected and called
metadata counts training-ready examples. Preserve coverage of the real records,
while checking that absent fields and unverified claims are not promoted.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import verified_experience_census_20261112 as census  # noqa: E402

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = census.census()
    return _CACHE["r"]


def test_a_producer_receipt_does_not_claim_training_readiness():
    self_report = {"capability_id": "x", "observed": {"pass": True}, "ran_by": "the-producer",
                   "model_dependency_count": 0}
    row = census.classify(self_report)
    assert row["has_verdict"] is True
    assert row["declares_model_free"] is True
    assert "training_ready_alone" not in row


def test_absent_or_non_integer_dependency_count_is_not_model_free():
    for count in (None, False, "0", 1):
        assert census.classify({"model_dependency_count": count})["declares_model_free"] is False
        assert census.classify_verification({"model_dependency_count": count})["declares_model_free"] is False
    assert census.classify({})["declares_model_free"] is False
    assert census.classify({"observed": {"pass": 1}})["has_verdict"] is False


def test_a_verification_record_counts_only_when_it_names_a_run_and_reproduced():
    good = {"capability_id": "x", "reproduced": True, "model_dependency_count": 0,
            "independent_verifier": "github-actions:org/repo",
            "independent_run_reference": {"github_run_id": 39782195830}}
    assert census.classify_verification(good)["has_run_id"] is True
    assert "attested" not in census.classify_verification(good)
    no_run = dict(good, independent_run_reference=None)
    assert census.classify_verification(no_run)["has_run_id"] is False
    for invalid in (True, 0, "0", "garbage", ""):
        bad = dict(good, independent_run_reference={"github_run_id": invalid})
        assert census.classify_verification(bad)["has_run_id"] is False
    not_reproduced = dict(good, reproduced=False)
    assert census.classify_verification(not_reproduced)["reproduced"] is False


def test_the_census_reads_the_artefact_that_makes_round_15_wrong():
    report = _report()
    assert report["verification_records"] >= 250, report["verification_records"]
    assert report["verification_reproduced"] == report["verification_records"]
    assert report["verification_records_with_run_id"] == report["verification_records"]


def test_every_verification_record_joins_to_a_producer_receipt():
    report = _report()
    assert report["verification_orphans_without_producer_receipt"] == []
    assert report["joined"] == report["verification_records"]


def test_joined_metadata_is_counted_but_not_called_training_ready():
    report = _report()
    assert report["joined_reproduced_with_run_id_boolean_verdict_and_model_free_claims"] >= 100
    assert report["joined_matching_metadata_with_pass_true"] >= 80
    assert report["training_readiness_assessed"] is False
    assert report["independent_verification_performed"] is False
    assert "training_ready_examples" not in report
    assert "verdict" not in report


def test_names_claimed_verifiers_without_establishing_independence():
    report = _report()
    verifiers = report["distinct_verifiers_claimed"]
    assert verifiers
    assert all(v.startswith("github-actions:") for v in verifiers), verifiers
    assert not any("local-session" in v or "arena" in v for v in verifiers)
    assert report["independent_verification_performed"] is False


def test_census_does_not_claim_it_measured_underlying_instance_depth():
    report = _report()
    assert "instances_per_capability" not in report
    assert "depth_instances_missing" not in report
    assert any("underlying instances" in item for item in report["limitations"])


def test_the_rerun_receipts_are_honest_about_what_they_are():
    folder = ROOT / "canonical/astra_runtime/evidence/reproducibility"
    receipts = sorted(folder.glob("REPRODUCIBILITY__*__RECEIPT.json"))
    assert receipts, "run the census with --rerun to produce these"
    kinds = set()
    for path in receipts:
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["verified"] is False, "reproducibility must never be recorded as verification"
        assert record["independent_verifier"] is None
        assert record["verdict"] != "VERIFIED"
        assert record["as_designed"] is True, path.name
        kinds.add(record["kind_of_artefact"])
    assert kinds == {"fresh_case_verifier", "replayable_experience"}


def test_a_fresh_case_verifier_varies_and_a_replay_does_not():
    folder = ROOT / "canonical/astra_runtime/evidence/reproducibility"
    by_kind: dict[str, list] = {}
    for path in sorted(folder.glob("REPRODUCIBILITY__*__RECEIPT.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        by_kind.setdefault(record["kind_of_artefact"], []).append(record)
    for record in by_kind["fresh_case_verifier"]:
        assert record["identical"] is False, "a verifier that repeats itself has stopped being fresh"
    for record in by_kind["replayable_experience"]:
        assert record["identical"] is True, "an experience to train on must replay byte-for-byte"
