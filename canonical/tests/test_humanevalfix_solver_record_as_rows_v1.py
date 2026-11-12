"""The committed solver record gives back the rows the stream reads, and refuses what it cannot read."""
import json
import pathlib

import pytest

from canonical.tools import humanevalfix_experience_stream_measure_v1 as stream
from canonical.tools import humanevalfix_solver_record_as_rows_v1 as as_rows

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "canonical" / "verification" / "HUMANEVALFIX_REPAIR_SOLVER_20261112_V1.json"


def record(per_bug):
    return {"schema": as_rows.SCHEMA, "per_bug_key": as_rows.KEY, "per_bug": per_bug,
            "run": {"which": "scored", "timeout_s": 8, "wall_limit_s": 300, "nothing_taught": True}}


def test_a_repaired_row_keeps_its_lines_its_cost_and_its_judgement():
    out = as_rows.rows(record({"Python/1": [True, True, False, 8, 3.5, "PASS", ["a = 0"], ["a = 1"]]}))
    row = out["per_bug"]["Python/1"]
    assert row["repaired"] and row["right_as_far_as_checked"] and not row["is_the_published_fix"]
    assert row["lines"] == {"removed": ["a = 0"], "put_in": ["a = 1"]}
    assert stream.cost_of(row) == 8 and stream.one_line(row["lines"])
    assert (out["timeout_s"], out["wall_limit_s"], out["which"]) == (8, 300, "scored")


def test_a_bug_stopped_at_the_wall_limit_has_no_cost():
    row = as_rows.rows(record({"Python/2": [False, False, False, 77, 300.0, as_rows.AT_THE_WALL, None, None]}))["per_bug"]["Python/2"]
    assert not row["finished"] and row["stopped_at_the_wall_limit"] and row["status"] is None
    assert stream.cost_of(row) is None and row["lines"] is None


def test_a_bug_searched_in_vain_has_its_cost_and_no_lines():
    row = as_rows.rows(record({"Python/3": [False, False, False, 489, 145.8, "OPEN", None, None]}))["per_bug"]["Python/3"]
    assert row["finished"] and not row["repaired"] and stream.cost_of(row) == 489 and row["lines"] is None


def test_a_row_without_a_status_is_not_finished():
    row = as_rows.rows(record({"Python/4": [False, False, False, 5, 1.0, None, None, None]}))["per_bug"]["Python/4"]
    assert not row["finished"] and stream.cost_of(row) is None


def test_right_and_published_are_never_said_of_a_bug_that_was_not_repaired():
    row = as_rows.rows(record({"Python/5": [False, True, True, 5, 1.0, "OPEN", None, None]}))["per_bug"]["Python/5"]
    assert not row["right_as_far_as_checked"] and not row["is_the_published_fix"]


@pytest.mark.parametrize("change", [{"per_bug_key": "[something else]"}, {"schema": "ANOTHER"}])
def test_a_record_in_another_form_is_refused(change):
    with pytest.raises(ValueError):
        as_rows.rows(dict(record({}), **change))


def test_a_row_of_another_length_is_refused():
    with pytest.raises(ValueError):
        as_rows.rows(record({"Python/6": [True, True, False, 8, 3.5, "PASS", ["a = 0"]]}))


def test_repaired_and_stopped_at_the_wall_is_refused():
    with pytest.raises(ValueError):
        as_rows.rows(record({"Python/7": [True, True, False, 8, 300.0, as_rows.AT_THE_WALL, ["a = 0"], ["a = 1"]]}))


def test_the_committed_record_gives_the_counts_it_states(tmp_path):
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    out = as_rows.rows(committed)
    per_bug = out["per_bug"]
    repaired = [row for row in per_bug.values() if row["repaired"]]
    assert len(per_bug) == committed["summary"]["bugs"] == 100
    assert len(repaired) == committed["summary"]["repaired"] == 53
    assert sum(1 for row in repaired if row["right_as_far_as_checked"]) == committed["summary"]["right_as_far_as_checked"] == 36
    assert sum(1 for row in repaired if stream.one_line(row["lines"])) == committed["summary"]["repairs_that_change_one_line"]["count"] == 36
    costs = [stream.cost_of(row) for row in per_bug.values()]
    assert sum(1 for cost in costs if cost is not None) == committed["summary"]["processes_started_by_the_solver"]["bugs_it_finished"] == 98
    assert sum(cost for cost in costs if cost is not None) == committed["summary"]["processes_started_by_the_solver"]["in_all"]
    target = tmp_path / "rows.json"
    assert as_rows.main(["--record", str(COMMITTED), "--out", str(target)]) == 0
    assert json.loads(target.read_text())["per_bug"] == per_bug
