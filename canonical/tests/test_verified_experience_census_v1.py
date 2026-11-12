"""Count both artefacts, or be wrong.

Round 15's census read only ``*RECEIPT.json`` and reported **zero** independently verified experience.
The verification records are a different artefact — ``CAPABILITY__*__INDEPENDENT_VERIFICATION.json``,
written by the GitHub runner under an OIDC-attested ``github_run_id`` — and there are hundreds of them.
The lesson is pinned here as a test: a census that sees one of two artefacts must not be able to
conclude zero while the other one is full.

Pinned:

* a producer's own pass is never training-ready — independence is the missing half;
* a verification record only counts when it names a run *and* reproduced the producer's result;
* the tree currently holds hundreds of attested reproductions and hundreds of joined, training-ready
  examples, each one instance deep;
* depth is the remaining gap: one instance per capability cannot be split into train and held-out;
* the re-run receipts are honest — reproducibility, never verification.
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


def test_a_producer_receipt_alone_is_never_training_ready():
    self_report = {"capability_id": "x", "observed": {"pass": True}, "ran_by": "the-producer",
                   "model_dependency_count": 0}
    row = census.classify(self_report)
    assert row["has_verdict"] is True
    assert row["training_ready_alone"] is False


def test_a_verification_record_counts_only_when_it_names_a_run_and_reproduced():
    good = {"capability_id": "x", "reproduced": True, "model_dependency_count": 0,
            "independent_verifier": "github-actions:org/repo",
            "independent_run_reference": {"github_run_id": 39782195830}}
    assert census.classify_verification(good)["attested"] is True
    no_run = dict(good, independent_run_reference=None)
    assert census.classify_verification(no_run)["attested"] is False
    not_reproduced = dict(good, reproduced=False)
    assert census.classify_verification(not_reproduced)["reproduced"] is False


def test_the_census_reads_the_artefact_that_makes_round_15_wrong():
    report = _report()
    assert report["verification_records"] >= 250, report["verification_records"]
    assert report["verification_reproduced"] == report["verification_records"]
    assert report["verification_attested_with_run_id"] == report["verification_records"]


def test_every_verification_record_joins_to_a_producer_receipt():
    report = _report()
    assert report["verification_orphans_without_producer_receipt"] == []
    assert report["joined"] == report["verification_records"]


def test_there_are_training_ready_examples_and_round_15_said_zero():
    report = _report()
    assert report["training_ready_examples"] >= 100, (
        "a census that reports 0 while verification records exist is blind, not rigorous")
    assert report["training_ready_with_pass_true"] >= 80
    assert report["verdict"] == "CORPUS_EXISTS_SHALLOW"


def test_the_verifier_is_somebody_else():
    verifiers = _report()["distinct_verifiers"]
    assert verifiers, "the census must name who verified"
    assert all(v.startswith("github-actions:") for v in verifiers), verifiers
    assert not any("local-session" in v or "arena" in v for v in verifiers)


def test_the_remaining_gap_is_depth_not_independence():
    report = _report()
    assert report["instances_per_capability"] == 1
    assert report["depth_target_per_capability"] == 8
    assert report["depth_instances_missing"] > 0
    assert any("DEPTH" in item for item in report["missing_to_train"])


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
