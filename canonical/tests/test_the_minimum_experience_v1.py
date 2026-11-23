"""Tests for `canonical/tools/the_minimum_experience_v1.py`. Plain-tree, no pins or patched loaders.

The receipt test is a regression guard against overclaiming: it also pins the *failed* first run
(V0) so the criterion correction cannot be quietly rewritten as an unbroken success.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
for path in (str(TOOLS), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import the_minimum_experience_v1 as tool  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "THE_MINIMUM_EXPERIENCE_20261123_V1.json"
V0 = ROOT / "canonical" / "verification" / "THE_MINIMUM_EXPERIENCE_20261123_V0_SUPERSEDED_M4_MISDESIGNED.json"


def test_fit_sequences_counts_real_action_sequences_and_is_monotone():
    one = {"TARBALL": 1, "FILESYSTEM": 1, "SQLITE": 1}
    deep = {"TARBALL": 1, "FILESYSTEM": 3, "SQLITE": 1}
    full = {"TARBALL": 5, "FILESYSTEM": 4, "SQLITE": 4}
    assert tool.fit_sequences(one) == 4 + 5 + 4
    assert tool.fit_sequences(deep) > tool.fit_sequences(one)
    assert tool.fit_sequences(full) > tool.fit_sequences(deep)


def test_active_collapse_is_bounded_and_only_judges_runs():
    candidates = tool.answers.gate.from_predicates([
        ("r1", lambda trace: len(trace[-1]) >= 1),
        ("r2", lambda trace: len(trace[-1]) >= 2),
        ("r3", lambda trace: len(trace[-1]) >= 3),
        ("r4", lambda trace: len(trace[-1]) >= 4),
    ])
    traces = [((("a", "x"),) * n,) for n in (1, 2, 3, 4)]
    seen = []

    def judge(trace):
        seen.append(trace)
        return len(trace[-1]) >= 3

    answer = tool.collapse_with_judgments(candidates, traces, judge)
    assert answer["judgments"] <= answer["budget"] == 2
    assert answer["class"] == 1
    assert answer["action"] == "COLLAPSED"
    assert all(isinstance(trace, tuple) for trace in seen)
    assert len(seen) == answer["judgments"]


def test_receipt_keeps_the_correction_the_failure_and_the_verified_criteria():
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert data["schema"] == tool.SCHEMA
    assert data["declared_before_the_run"] == tool.DECLARED_BEFORE_THE_RUN
    assert data["criteria_declared_after_a_first_run_for_M4"] is True
    assert "first run falsified it" in data["criterion_correction"]
    assert data["all_criteria_met"] is True
    assert all(row["MET"] is True for row in data["verdict"].values())
    # the failed first phrasing is preserved, not deleted
    v0 = json.loads(V0.read_text(encoding="utf-8"))
    assert v0["all_criteria_met"] is False
    assert v0["verdict"]["M4_more_breadth_buys_no_extra_correctness"]["MET"] is False
    # the shallow failure and the cheap success are both real measurements
    ladder = data["ladder"]
    assert any(row["held_out"].get("false_accepts", 0) > 0 for row in ladder)
    strong = next(row for row in ladder if row["strong_residual"])
    assert strong["depths"] == {"TARBALL": 1, "FILESYSTEM": 3, "SQLITE": 1}
    assert strong["fit_runs"] < data["full_fit_cited_not_re_run"]["runs"]
    assert strong["fit_sequences"] < data["full_fit_cited_not_re_run"]["sequences"]
    assert strong["seconds"] < data["full_fit_cited_not_re_run"]["seconds"]
    assert strong["held_out"]["false_accepts"] == 0
    assert strong["held_out"]["false_rejects"] == 0
    assert strong["held_out"]["abstentions"] == 0
    assert strong["discarded_wrong_on_held_out"] > 0
    # every rung's judgments stay inside the declared information budget
    assert all(row["question"]["judgments"] <= row["question"]["budget"]
               for row in ladder if row["status"] == "MEASURED")
    assert data["cost"]["model_calls"] == 0
    assert data["cost"]["parameters_stored"] == 0
    assert data["cost"]["network_calls_at_run_time"] == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
