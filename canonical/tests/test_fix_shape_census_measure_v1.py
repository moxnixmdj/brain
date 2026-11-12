#!/usr/bin/env python3
"""The census of fix shapes: what a pull request's fix is taken to be, how the count is made, the
check against the full list, and that the scored bugs are never handed out."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import fix_shape_v1 as fix_shape  # noqa: E402
from canonical.tools import fix_shape_census_measure_v1 as census  # noqa: E402

BEFORE = "def f(a, b):\n    c = a\n    return c\n"
PATCH = "@@ -1,3 +1,3 @@\n def f(a, b):\n-    c = a\n+    c = abs(a)\n     return c"


def changed(path: str = "pkg/mod.py", **more) -> dict:
    return {"path": path, "status": "modified", "patch": PATCH, "before": BEFORE, "is_test": False, "is_python": path.endswith(".py"), **more}


# --------------------------------------------------------------------------- #
# one pull request
# --------------------------------------------------------------------------- #
def test_one_python_file_changed_gets_the_shape_of_its_change():
    found = census.of_pull_request({"instance_id": "a__b-1", "files": [changed()]})
    assert (found["shape"], found["kind"], found["needs"], found["nodes"]) == (fix_shape.PUT_IN, "one inside", fix_shape.BUILT_IN, 2)
    assert (found["python_files"], found["other_files"]) == (1, 0)


def test_tests_are_set_aside_and_other_files_are_counted_beside_the_shape():
    files = [changed(), changed("tests/test_mod.py", is_test=True), {"path": "docs/changes.rst", "status": "modified", "is_test": False, "is_python": False}]
    found = census.of_pull_request({"files": files})
    assert found["shape"] == fix_shape.PUT_IN and (found["python_files"], found["other_files"]) == (1, 1)


def test_more_than_one_python_file_is_several_files():
    found = census.of_pull_request({"files": [changed(), changed("pkg/other.py")]})
    assert found["shape"] == census.SEVERAL_FILES and found["python_files"] == 2 and found["needs"] is None


@pytest.mark.parametrize("status", ["added", "removed"])
def test_a_file_added_or_removed_is_a_whole_file(status):
    found = census.of_pull_request({"files": [changed(status=status)]})
    assert (found["shape"], found["kind"]) == (census.A_WHOLE_FILE, status)


def test_what_cannot_be_read_is_said_and_not_guessed():
    assert census.of_pull_request({"error": "404", "files": []})["shape"] == fix_shape.UNREADABLE
    assert census.of_pull_request({"files": [changed("docs/x.rst")]})["shape"] == census.NO_PYTHON
    assert census.of_pull_request({"files": []})["shape"] == census.NO_PYTHON
    assert census.of_pull_request({"files": [changed(before=None)]})["shape"] == fix_shape.UNREADABLE
    assert census.of_pull_request({"files": [changed(patch=None)]})["shape"] == fix_shape.UNREADABLE
    wrong = census.of_pull_request({"files": [changed(before="something else\n")]})
    assert wrong["shape"] == fix_shape.UNREADABLE and wrong["kind"]
    assert census.of_pull_request({"files": [changed(before="def (\n", patch="@@ -1,1 +1,1 @@\n-def (\n+def )")]})["shape"] == fix_shape.UNREADABLE


# --------------------------------------------------------------------------- #
# the count
# --------------------------------------------------------------------------- #
def rows() -> dict:
    program = "def f(a, b):\n    c = a\n    g(a)\n    return c\n"
    return {
        "taken out": fix_shape.shape(program, program.replace("    g(a)\n", "")),
        "put in, small, built in": fix_shape.shape(program, program.replace("c = a", "c = abs(a)")),
        "put in, small, new": fix_shape.shape(program, program.replace("c = a", "c = a + 17")),
        "put in, large": fix_shape.shape(program, program.replace("    return c", "    if c < 0:\n        return 0\n    return c")),
        "leaf, held": fix_shape.shape(program, program.replace("c = a", "c = b")),
        "leaf, new": fix_shape.shape(program, program.replace("c = a", "c = zz")),
        "expression": fix_shape.shape(program, program.replace("c = a", "c = b * b")),
        "several places": fix_shape.shape(program, program.replace("c = a", "c = b").replace("return c", "return a")),
        "same": fix_shape.shape(program, program),
        "unreadable": fix_shape.shape(program, "def ("),
        "several files": {"shape": census.SEVERAL_FILES, "kind": None, "needs": None, "nodes": None},
    }


def test_summarise_counts_each_shape_and_sets_aside_what_was_not_read():
    told = census.summarise(rows())
    assert told["fixes"] == 11 and told["counted"] == 9
    assert told["set_aside"] == {fix_shape.SAME: 1, fix_shape.UNREADABLE: 1}
    assert told["by_shape"] == {fix_shape.TAKEN_OUT: 1, fix_shape.PUT_IN: 3, fix_shape.LEAF: 2, fix_shape.EXPRESSION: 1,
                                fix_shape.SEVERAL_PLACES: 1, census.SEVERAL_FILES: 1}
    assert list(told["by_shape"]) == [name for name in census.SHAPES if name in told["by_shape"]]
    assert told["share_by_shape"][fix_shape.PUT_IN] == round(3 / 9, 4)
    assert told["at_most_one_statement"] == 7 and told["share_at_most_one_statement"] == round(7 / 9, 4)


def test_summarise_says_what_can_be_listed():
    told = census.summarise(rows())
    assert told["can_be_listed"] == 3 and told["share_can_be_listed"] == round(3 / 9, 4)
    assert told["can_be_listed_by_shape"] == {fix_shape.TAKEN_OUT: 1, fix_shape.PUT_IN: 1, fix_shape.LEAF: 1}
    assert told["put_in_small_and_nothing_new"] == 1
    assert told["put_in_by_size_and_what_it_needs"] == {"2": {fix_shape.BUILT_IN: 1}, "3": {fix_shape.NEW: 1}, "7 to 12": {fix_shape.BUILT_IN: 1}}
    assert told["leaf_by_kind_and_what_it_needs"] == {"a name": {fix_shape.HELD: 1, fix_shape.NEW: 1}}
    assert told["taken_out_by_kind"] == {"a statement": 1}
    assert told["put_in_by_kind"] == {"one inside": 2, "a statement": 1}
    assert told["what_the_rest_needs"] == {fix_shape.HELD: 2}
    assert told["too_large_to_ask_take_out"] == 0


def test_summarise_of_nothing():
    told = census.summarise({})
    assert told["counted"] == 0 and told["share_can_be_listed"] is None and told["by_shape"] == {}


def test_sizes():
    assert [census._size(n) for n in (1, 2, 3, 4, 6, 7, 12, 13, 500)] == ["1", "2", "3", "4 to 6", "4 to 6", "7 to 12", "7 to 12", "13 or more", "13 or more"]


# --------------------------------------------------------------------------- #
# the check against the full list
# --------------------------------------------------------------------------- #
PAIRS = {
    "a": ("x = a + 1\n", "x = a\n"),
    "b": ("x = a\n", "x = abs(a)\n"),
    "c": ("x = a\n", "x = b\n"),
    "d": ("def f(a):\n    g(a)\n    return a\n", "def f(a):\n    return a\n"),
    "e": ("x = a\n", "x = a\n"),
    "f": ("def (\n", "x = a\n"),
}


def test_the_short_way_and_the_long_way_agree():
    told = census.against_the_full_list(PAIRS)
    assert told == {"pairs": 4, "said_the_long_way": {fix_shape.TAKEN_OUT: 2, fix_shape.PUT_IN: 1, "neither": 1}, "the_two_ways_apart": []}
    assert census.against_the_full_list(PAIRS, 2)["pairs"] == 2                 # "a" and "d": spread over the names, not the first two
    assert census.against_the_full_list(PAIRS, 2)["said_the_long_way"] == {fix_shape.TAKEN_OUT: 2}
    assert census.against_the_full_list(PAIRS, 0)["pairs"] == 0


def test_a_short_way_that_is_wrong_is_named(monkeypatch):
    honest = fix_shape.shape
    monkeypatch.setattr(fix_shape, "shape", lambda buggy, fixed: {**honest(buggy, fixed), "shape": fix_shape.TAKEN_OUT} if "abs" in fixed or "b" in fixed else honest(buggy, fixed))
    assert census.against_the_full_list(PAIRS)["the_two_ways_apart"] == ["b", "c"]


# --------------------------------------------------------------------------- #
# what is read and what is not
# --------------------------------------------------------------------------- #
def test_the_scored_bugs_are_never_handed_out(tmp_path):
    """Three bugs nobody read before the draw: all three are drawn as scored, so none comes out."""
    lines = [json.dumps({"task_id": f"Python/{900 + n}", "entry_point": "f", "bug_type": "value misuse", "declaration": "def f(a):\n",
                         "buggy_solution": "    return a + 1\n", "canonical_solution": "    return a\n", "test": "def check(f):\n    assert f(1) == 1\ncheck(f)"})
             for n in range(3)]
    path = tmp_path / "bugs.jsonl"
    path.write_text("\n".join(lines) + "\n")
    assert census.humanevalfix_development(path) == {}


def test_what_was_expected_was_written_with_ranges_and_two_rules():
    assert set(census.EXPECTED["rules"]) == {"one piece put in", "real projects"}
    assert "at least 6 of the 64" in census.EXPECTED["rules"]["one piece put in"]
    assert "at least 50 of the 500" in census.EXPECTED["rules"]["real projects"]
    for name in ("humanevalfix_development_of_64", "condefects_share_of_2864", "swe_bench_verified_of_500"):
        ranges = [value for value in census.EXPECTED[name].values() if isinstance(value, list)]
        assert ranges and all(low <= high for low, high in ranges)


def test_main_writes_a_record_and_runs_nothing(tmp_path, capsys):
    pulls = tmp_path / "pulls"
    pulls.mkdir()
    (pulls / "a__b-1.json").write_text(json.dumps({"instance_id": "a__b-1", "repo": "a/b", "files": [changed()]}))
    (pulls / "a__b-2.json").write_text(json.dumps({"instance_id": "a__b-2", "repo": "a/b", "files": [changed(), changed("pkg/other.py")]}))
    (pulls / "c__d-3.json").write_text(json.dumps({"instance_id": "c__d-3", "repo": "c/d", "files": [changed(), {"path": "x.rst", "status": "modified", "is_test": False, "is_python": False}]}))
    out = tmp_path / "record.json"
    assert census.main(["--pull-requests-dir", str(pulls), "--out", str(out)]) == 0
    record = json.loads(out.read_text())
    assert record["schema"] == census.SCHEMA and record["authority"].startswith("NONE")
    assert (record["model_calls"], record["programs_run"], record["tests_run"]) == (0, 0, 0)
    told = record["sets"]["swe_bench_verified"]
    assert told["by_shape"] == {fix_shape.PUT_IN: 2, census.SEVERAL_FILES: 1} and told["can_be_listed"] == 2
    assert told["that_also_change_files_that_are_not_python"] == 1
    assert told["by_project"] == {"a/b": {fix_shape.PUT_IN: 1, census.SEVERAL_FILES: 1}, "c/d": {fix_shape.PUT_IN: 1}}
    assert told["can_be_listed_by_project"] == {"a/b": 1, "c/d": 1}
    assert record["per_fix"]["swe_bench_verified"]["a__b-1"] == [fix_shape.PUT_IN, "one inside", fix_shape.BUILT_IN, 2]
    assert record["expected_before"] == census.EXPECTED and set(record["code_sha256"]) >= {"canonical/runtime/fix_shape_v1.py"}
    assert "WROTE" in capsys.readouterr().out
