#!/usr/bin/env python3
"""The anchor: admission must refuse a judge that reads the label, passes everything, or never fails.

CAN FAIL (mutations documented in the receipt ``tests.can_fail_mutations``):
  * ``LABEL_TOKENS`` loses ``replay_equals_live``      -> the leak test fails
  * ``ALWAYS_PASS_COLLAPSE`` not raised on the real known-false canaries
                                                       -> the collapse test fails
  * ``NEVER_FAILS_MIN_HISTORY`` changed without this file
                                                       -> the history test fails
  * any real record's ``status`` edited in the source receipt
                                                       -> the corpus pin fails
  * the honest site instrument refused (separation broken)
                                                       -> the honest-judge test fails

No number is re-measured here.  The anchor corpus is RE-READ from the merged real
receipt ``canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json`` --
228 measured replay pairs against this repository's own corpus at a pinned commit,
runner outcome as ground truth.  That is the honest form for an admission
mechanism: re-running the corpus would be re-testing what is already measured.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys_path_root = str(ROOT)
import sys

if sys_path_root not in sys.path:
    sys.path.insert(0, sys_path_root)

from canonical.runtime import verdict_anchor_admission_v1 as va  # noqa: E402

SOURCE_RECEIPT = ROOT / "canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json"
RECEIPT = ROOT / "canonical/verification/VERDICT_ANCHOR_ADMISSION_20261117_V1.json"

# Pinned by sha256: the anchor corpus is a merged measurement, not a live one.
SOURCE_RECEIPT_SHA256 = "1234766ba0bfa1f35c6c289e7deb2ad2f0e3e0a362526fb3b7bdf7704be16931"


def _records() -> list[dict]:
    return json.loads(SOURCE_RECEIPT.read_text())["records"]


def _anchor() -> list[dict]:
    return va.anchor_from_replay_records(_records())


def _honest(content: dict) -> str:
    """The site instrument: the recorded plan holds iff the site did not move."""
    return "PASS" if content["planned_line"] == content["live_line"] else "FAIL"


def _always_pass(content: dict) -> str:
    return "PASS"


def _always_fail(content: dict) -> str:
    return "FAIL"


def _leaky(content: dict) -> str:
    # Names the archived ground-truth label -- exactly what a judge must not read.
    return "PASS" if content["replay_equals_live"] else "FAIL"


def _make_endorser_at(false_index: int):
    state = {"i": 0}

    def _judge(content: dict) -> str:
        i = state["i"]
        state["i"] += 1
        if i == false_index:
            return "PASS"
        return "PASS" if content["planned_line"] == content["live_line"] else "FAIL"

    return _judge


def test_anchor_corpus_is_the_real_replay_receipt():
    assert hashlib.sha256(SOURCE_RECEIPT.read_bytes()).hexdigest() == SOURCE_RECEIPT_SHA256
    records = _records()
    assert len(records) == 228
    statuses = [r["status"] for r in records]
    assert statuses.count("REPLAY_MATCHES_LIVE") == 106
    assert statuses.count("REPLAY_DIFFERS_BUT_HOLDS") == 4
    assert statuses.count("REPLAY_DOES_NOT_PARSE") == 47
    assert statuses.count("SILENT_CORRUPTION") == 71
    cases = _anchor()
    assert len(cases) == 228
    assert sum(1 for c in cases if c["expected_verdict"] == "PASS") == 110
    assert sum(1 for c in cases if c["expected_verdict"] == "FAIL") == 118
    # The separation the honest instrument relies on, measured on the real pairs:
    # the site coordinates alone separate holds from not-holds, 228 of 228.
    for rec, case in zip(records, cases):
        site_unchanged = rec["planned_line"] == rec["live_line"]
        holds = case["expected_verdict"] == "PASS"
        assert site_unchanged == holds, case["case_id"]


def test_honest_site_instrument_is_admitted():
    errors = va.admission_errors(_honest, _anchor())
    assert errors == [], errors


def test_always_pass_is_refused_on_the_real_known_false_canaries():
    errors = va.admission_errors(_always_pass, _anchor())
    assert "ALWAYS_PASS_COLLAPSE" in errors, errors
    # The collapse name wins over per-case endorsement: every known-false passed.
    assert not any(e.startswith("ENDORSES_KNOWN_FALSE") for e in errors), errors


def test_label_reading_judge_is_refused_by_source_separation():
    errors = va.admission_errors(_leaky, _anchor())
    assert any(e.startswith("ANCHOR_READABLE_BY_JUDGE:replay_equals_live") for e in errors), errors


def test_single_false_endorsement_is_refused():
    records = _records()
    false_index = next(
        i for i, r in enumerate(records) if r["planned_line"] != r["live_line"]
    )
    judge = _make_endorser_at(false_index)
    errors = va.admission_errors(judge, _anchor())
    assert any(e.startswith("ENDORSES_KNOWN_FALSE:") for e in errors), errors
    assert "ALWAYS_PASS_COLLAPSE" not in errors, errors


def test_constant_fail_judge_is_refused():
    errors = va.admission_errors(_always_fail, _anchor())
    assert "ALWAYS_FAIL_COLLAPSE" in errors, errors


def test_anchor_without_negative_cases_is_refused():
    positives_only = [c for c in _anchor() if c["expected_verdict"] == "PASS"]
    errors = va.admission_errors(_honest, positives_only)
    assert "ANCHOR_WITHOUT_NEGATIVE_CASE" in errors, errors


def test_anchor_without_positive_cases_is_refused():
    negatives_only = [c for c in _anchor() if c["expected_verdict"] == "FAIL"]
    errors = va.admission_errors(_honest, negatives_only)
    assert "ANCHOR_WITHOUT_POSITIVE_CASE" in errors, errors


def test_never_fails_history_is_refused():
    errors = va.admission_errors(_honest, _anchor(), judge_history=["PASS", "PASS", "PASS"])
    assert "NEVER_FAILS_HISTORY" in errors, errors
    # Fewer than three prior verdicts carries no signature.
    ok = va.admission_errors(_honest, _anchor(), judge_history=["PASS", "PASS"])
    assert "NEVER_FAILS_HISTORY" not in ok, ok


def test_invalid_output_and_crashing_judges_are_refused():
    def _garbage(content: dict) -> str:
        return "MAYBE"

    def _crash(content: dict) -> str:
        raise RuntimeError("instrument lost the observation")

    e1 = va.admission_errors(_garbage, _anchor())
    assert any(e.startswith("JUDGE_OUTPUT_INVALID:") for e in e1), e1
    e2 = va.admission_errors(_crash, _anchor())
    assert any(e.startswith("JUDGE_ERROR:") for e in e2), e2


def test_receipt_pins_the_admission_outcomes():
    assert RECEIPT.is_file(), RECEIPT
    r = json.loads(RECEIPT.read_text())
    assert r["schema"] == "PROJECT_BRAIN_VERIFICATION_RECEIPT_V1"
    assert r["receipt_id"] == "VERDICT_ANCHOR_ADMISSION_20261117_V1"
    assert r["authority"].startswith("NONE__")
    assert r["corpus"]["source_receipt_sha256"] == SOURCE_RECEIPT_SHA256
    assert r["corpus"]["pairs"] == 228
    assert r["corpus"]["anchor_pass"] == 110
    assert r["corpus"]["anchor_fail"] == 118
    recorded = {j["name"]: j["errors"] for j in r["judges"]}
    anchor = _anchor()
    assert recorded["honest_site_instrument"] == va.admission_errors(_honest, anchor)
    assert recorded["always_pass"] == va.admission_errors(_always_pass, anchor)
    assert recorded["label_reading_judge"] == va.admission_errors(_leaky, anchor)
    assert recorded["never_fails_history"] == va.admission_errors(
        _honest, anchor, judge_history=["PASS", "PASS", "PASS"]
    )
    admitted = [j["name"] for j in r["judges"] if j["admitted"]]
    assert admitted == ["honest_site_instrument"], admitted
