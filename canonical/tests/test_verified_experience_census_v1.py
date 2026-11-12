"""Count the data before building the thing that learns from it.

Round 14 recommended a student channel: weights trained offline on this repo's verified receipts.
`verified_experience_census_20261112` checks the precondition instead of assuming it, and the
precondition fails: the tree holds hundreds of receipts and **none** that a second party ran.

Pinned here:

* a self-report is not a verification — `observed.pass == True` alone never makes an example
  training-ready, and the gate is not vacuous (a receipt that does name an independent run is
  accepted);
* no receipt in the tree currently names an independent run, so the training-ready count is 0 and the
  missing field is named;
* `--rerun` distinguishes the two properties that are easy to confuse: a **verifier** must produce
  fresh cases and therefore must vary, a **replayable experience** must be byte-identical. Neither is
  called verified, because two runs by one agent is reproducibility.
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


def test_a_self_report_is_not_a_verification():
    self_report = {"capability_id": "x", "observed": {"pass": True}, "ran_by": "the-producer",
                   "model_dependency_count": 0}
    row = census.classify(self_report)
    assert row["has_verdict"] is True
    assert row["training_ready"] is False, "a producer's own pass must never be trainable evidence"


def test_the_gate_is_not_vacuous():
    second_party = {"capability_id": "x", "observed": {"pass": True}, "ran_by": "the-producer",
                    "independent_run_reference": "sha256:deadbeef", "model_dependency_count": 0}
    assert census.classify(second_party)["training_ready"] is True
    with_model = dict(second_party, model_dependency_count=1)
    assert census.classify(with_model)["training_ready"] is False


def test_no_receipt_in_the_tree_names_an_independent_run():
    report = _report()
    assert report["receipts"] >= 500, report["receipts"]
    assert report["verdict_present"] >= 150, "most receipts carry no verdict at all"
    assert report["independent_run_recorded"] == 0
    assert report["training_ready_examples"] == 0
    assert any("INDEPENDENT_RUN_REFERENCE" in item for item in report["missing_to_train"])


def test_the_runners_recorded_are_all_the_producer_side():
    runners = _report()["distinct_runners"]
    assert runners, "the census must record who ran things"
    assert all(isinstance(name, str) for name in runners)
    assert not any("independent" in name.lower() for name in runners)


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
        assert record["model_dependency_count"] == 0
        kinds.add(record["kind"])
    assert kinds == {"fresh_case_verifier", "replayable_experience"}


def test_a_fresh_case_verifier_varies_and_a_replay_does_not():
    folder = ROOT / "canonical/astra_runtime/evidence/reproducibility"
    by_kind = {}
    for path in sorted(folder.glob("REPRODUCIBILITY__*__RECEIPT.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        by_kind.setdefault(record["kind"], []).append(record)
    for record in by_kind["fresh_case_verifier"]:
        assert record["identical"] is False, "a verifier that repeats itself has stopped being fresh"
    for record in by_kind["replayable_experience"]:
        assert record["identical"] is True, "an experience to train on must replay byte-for-byte"
