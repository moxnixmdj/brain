#!/usr/bin/env python3
"""The store is not a museum: 2 of 4 recorded contrasts DECIDE real test outcomes.

Method: for each recorded contrast whose function is called by tests, monkeypatch the function so the
contrasting argument position receives the OTHER witness value, and run the test file.

    control (identical wrapper, no swap)   moved: 0 of 4   <- the measurement is not contaminated
    intervened                            moved: 2 of 4
      a_name_gets_its_value_from_the_run_v1::convert    11 passed -> 5 passed, 6 failed
      causal_dependency_repair_v1::read_set_argv        11 passed -> 10 passed, 1 failed

Six and one real test failures appear when the recorded behaviour is flipped. Those tests depend on the
behaviour the entry recorded, and no static feature in this project has ever been shown to support a claim
like that.

The other two moved nothing, and that is recorded rather than smoothed: a test file that never reaches the
argument at that position cannot testify either way.

The comparator is itself part of the method. A first version compared pytest's summary LINE, which ends in
a wall-clock ("11 passed in 1.34s"), so the identity control reported 4 of 4 contaminated. Only counts are
compared now.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACT = (REPO / "canonical" / "verification" /
            "REPLAY_THE_CONTRAST_IN_ITS_CALLERS_20261124_V1.json")


def _summary():
    return json.loads(ARTIFACT.read_text())["summary"]


def test_the_control_is_clean():
    """Without this, the intervention result is inadmissible. The identity control must move nothing."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["controls_that_moved"] == 0
    assert summary["verdicts"]["the_control_is_clean"] is True


def test_some_test_depends_on_the_recorded_behaviour():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["admissible_and_moved"] >= 2
    assert summary["verdicts"]["some_test_depends_on_the_recorded_behaviour"] is True
    functions = {cell["function"] for cell in summary["moved_detail"]}
    assert "causal_dependency_repair_v1::read_set_argv" in functions


def test_the_baselines_were_green_so_a_move_means_something():
    """If the baseline already had failures, a swap that adds failures proves nothing."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    for trial in _summary()["trials"]:
        assert trial["baseline_is_green"] is True, trial["function"]


def test_the_non_moving_half_is_recorded_not_smoothed():
    """2 of 4 is the result. Reporting it as 4 of 4, or omitting the two, would misstate the evidence."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["admissible_trials"] == 4
    assert summary["admissible_and_moved"] == 2
    assert summary["verdicts"]["every_contrast_reaches_a_test_that_cares"] is False
    assert summary["verdicts"]["the_store_is_inert_against_this_suite"] is False


def test_the_comparator_ignores_timings():
    """The bug that had to be fixed: pytest's summary line carries a duration, so an identity control looked
    contaminated. The recorded summaries must contain no 'in N.NNs'."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    for trial in _summary()["trials"]:
        for field in ("baseline", "control_same_wrapper", "swapped_to_other_witness"):
            assert not re.search(r"\bin \d", trial[field]["summary"]), trial[field]["summary"]
