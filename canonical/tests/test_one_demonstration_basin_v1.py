#!/usr/bin/env python3
"""Pins what a single demonstration licenses, on a real repository, under different senses.

The laws these tests hold down, from `canonical/verification/ONE_DEMONSTRATION_BASIN_20261116_V1.json`:

  * the model is closed: 168 reachable states, 1680 real transitions, nothing truncated;
  * one demonstration of a real task has a domain strictly smaller than the environment, so "do it
    once" never covers the start states the environment actually offers;
  * under a status-level sense some states are undecidable: the demonstration fails where the agent
    perceives success, and no further demonstration can separate them;
  * reading ONE file removes only that file's share of the doubt, and reading every file removes all
    of it -- so the undecidable set is exactly the part of the goal the sense does not carry;
  * the shipped receipt is this run's numbers, not a memory of an older run.
"""
from __future__ import annotations

import functools
import json
import pathlib
import shutil
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # pragma: no cover - import wiring
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import one_demonstration_basin_v1 as basin  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "ONE_DEMONSTRATION_BASIN_20261116_V1.json"
PREMISE_TASK = "commit a.txt as two, b.txt still one (a premise the plan does not set)"


@functools.lru_cache(maxsize=1)
def _explored() -> dict[str, Any]:
    """One exact model of one real repository, built by executing every action everywhere."""
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="brain_basin_test_"))
    world = basin.GitWorld(scratch / "repo")
    model = basin.explore(world, basin.actions(), max_states=400)
    shutil.rmtree(scratch, ignore_errors=True)
    return model


@functools.lru_cache(maxsize=1)
def _scored() -> dict[str, dict[str, Any]]:
    model = _explored()
    plan = basin.best_demonstration(model, basin.distances(model, basin.goal_pair))
    out = {}
    for sense, _files, _staged in basin.SENSES:
        out[sense] = basin.analyse(model, sense, basin.goal_pair, label=PREMISE_TASK, plan=plan)
    return out


def test_the_model_is_closed_and_built_from_real_transitions() -> None:
    model = _explored()
    assert model["truncated"] is False
    assert len(model["states"]) == 168
    assert model["transitions"] == 1680
    root = model["probes"][model["root"]]
    assert root["head"] == "seed"
    assert "a.txt" in root["tracked"] and "b.txt" in root["tracked"]


def test_one_demonstration_covers_less_than_the_environment() -> None:
    model = _explored()
    for goal, domain in ((basin.goal_commit, 112), (basin.goal_pair, 56)):
        plan = basin.best_demonstration(model, basin.distances(model, goal))
        reachable = sum(1 for state in model["states"]
                        if basin.run_plan(model, state, plan, goal)[0])
        assert reachable == domain
        assert domain < len(model["states"])


def test_a_status_sense_leaves_a_measured_set_undecidable() -> None:
    row = _scored()["status"]
    assert row["states"] == 168
    assert row["licensed"] + row["lucky"] + row["silent_failure"] + row["clear_outside"] == 168
    assert row["licensed"] == 48
    assert row["lucky"] == 8
    assert row["silent_failure"] == 16
    assert row["undecidable"] == 24
    assert row["mixed_cells"] > 0


def test_reading_one_file_removes_only_its_own_share_of_the_doubt() -> None:
    partial = _scored()["status+content(a.txt)"]
    assert partial["undecidable"] == 16
    assert partial["silent_failure"] == 8
    assert 0 < partial["undecidable"] < _scored()["status"]["undecidable"]


def test_a_sense_that_carries_the_premise_licenses_the_whole_domain() -> None:
    whole = _scored()["status+content(all)"]
    assert whole["undecidable"] == 0
    assert whole["licensed"] == whole["plan_domain"] == 56
    assert whole["observations"] == 168


def test_the_shipped_receipt_is_this_run() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["schema"] == basin.SCHEMA
    assert receipt["environment"]["states"] == 168
    assert receipt["environment"]["executed_transitions"] == 1680
    assert receipt["environment"]["truncated"] is False
    rows = {(row["label"], row["sense"]): row for row in receipt["tasks"]}
    for sense, expected in (("status", 24), ("status+content(a.txt)", 16),
                            ("status+content(all)", 0)):
        assert rows[(PREMISE_TASK, sense)]["undecidable"] == expected
    assert rows[(PREMISE_TASK, "feedback(command output)")]["undecidable"] == 168
