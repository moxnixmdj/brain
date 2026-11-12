#!/usr/bin/env python3
"""Where a small passing patch stands in the lists built here: how a patch is cut to its definition,
that the place is counted the way the lists are walked, and the counts and the rule."""
from __future__ import annotations

import json
import pathlib
import sys
import warnings

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_choice_v1 as choice  # noqa: E402
from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.runtime import fix_shape_v1 as fix_shape  # noqa: E402
from canonical.runtime import take_out_v1 as take_out  # noqa: E402
from canonical.tools import passing_patch_shape_measure_v1 as passing  # noqa: E402
from canonical.tools import small_passing_patch_place_measure_v1 as measure  # noqa: E402

FILE = '''import os

LIMIT = 3


def f(a, b):
    c = a < b
    print(c)
    return c


class C:
    def m(self, a):
        d = a
        return d
'''
F_BEFORE = "def f(a, b):\n    c = a < b\n    print(c)\n    return c"


def diff(path: str, hunks: str) -> str:
    return f"diff --git a/{path} b/{path}\nindex 83a4f00..5f3a362 100644\n--- a/{path}\n+++ b/{path}\n{hunks}\n"


LEAF = diff("pkg/mod.py", "@@ -6,4 +6,4 @@\n def f(a, b):\n-    c = a < b\n+    c = a <= b\n     print(c)\n     return c")
OUT = diff("pkg/mod.py", "@@ -6,4 +6,3 @@\n def f(a, b):\n     c = a < b\n-    print(c)\n     return c")
FROM_THE_FILE = diff("pkg/mod.py", "@@ -12,3 +12,3 @@\n     def m(self, a):\n-        d = a\n+        d = a + LIMIT\n         return d")
TWO_PLACES = diff("pkg/mod.py", "@@ -6,4 +6,4 @@\n def f(a, b):\n-    c = a < b\n+    c = a <= b\n     print(c)\n     return c\n@@ -12,3 +12,3 @@\n     def m(self, a):\n-        d = a\n+        d = a + LIMIT\n         return d")
ADDED = "diff --git a/reproduce.py b/reproduce.py\nnew file mode 100644\nindex 0000000..5c63bbd\n--- /dev/null\n+++ b/reproduce.py\n@@ -0,0 +1,1 @@\n+print(1)\n"


def record(task: str = "a__b-1") -> dict:
    return {"instance_id": task, "repo": "a/b", "files": [{"path": "pkg/mod.py", "status": "modified", "before": FILE, "is_test": False, "is_python": True, "patch": ""}]}


def lessons() -> kinds.Lessons:
    taught = kinds.Lessons()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        taught.learn("one", "def f(x, y):\n    return x < y\n", "def f(x, y):\n    return x <= y\n")
        taught.learn("two", "def g(a):\n    return a + 1\n", "def g(a):\n    return abs(a) + 1\n")
    return taught


W_LEAF = measure.normal("def f(a, b):\n    c = a <= b\n    print(c)\n    return c")
W_OUT = measure.normal("def f(a, b):\n    c = a < b\n    return c")
W_NOWHERE = measure.normal("def f(a, b):\n    c = a > b\n    print(c)\n    return c")


# --------------------------------------------------------------------------- #
# a patch cut to its definition
# --------------------------------------------------------------------------- #
def test_parts_of_gives_the_definition_before_and_after():
    files = passing.Files(record())
    before, after, scope = measure.parts_of(files, LEAF)
    assert (before, scope) == (F_BEFORE, measure.ONE_DEFINITION) and after == F_BEFORE.replace("a < b", "a <= b")
    assert measure.parts_of(files, LEAF + ADDED)[0] == F_BEFORE                    # a script left behind changes nothing
    assert measure.parts_of(files, FROM_THE_FILE)[0].startswith("def m(self, a):")


def test_parts_of_gives_nothing_for_what_was_not_given_a_shape_and_the_whole_file_when_no_definition_holds_the_change():
    files = passing.Files(record())
    assert measure.parts_of(files, ADDED) is None and measure.parts_of(files, "") is None
    assert measure.parts_of(files, diff("pkg/other.py", "@@ -1,1 +1,1 @@\n-x = 1\n+x = 2")) is None
    assert measure.parts_of(files, LEAF + diff("pkg/other.py", "@@ -1,1 +1,1 @@\n-x = 1\n+x = 2")) is None
    assert measure.parts_of(files, diff("pkg/mod.py", "@@ -6,2 +6,2 @@\n def f(a, b):\n-    c = zz\n+    c = 1")) is None
    before, after, scope = measure.parts_of(files, TWO_PLACES)
    assert scope == measure.WHOLE_FILE and before == FILE and "a <= b" in after and "a + LIMIT" in after


def test_small_passing_patches_keeps_the_listable_ones_each_once_and_says_where_the_material_is():
    found = measure.small_passing_patches(record(), [LEAF, LEAF + ADDED, OUT, FROM_THE_FILE, TWO_PLACES, ADDED])
    assert [(row["shape"], row["times"], row["from_its_definition_alone"]) for row in found] == [
        (fix_shape.LEAF, 2, True), (fix_shape.TAKEN_OUT, 1, True), (fix_shape.PUT_IN, 1, False)]       # LIMIT stands in the file, not in the method
    assert found[0]["before"] == F_BEFORE and found[0]["wanted"] == W_LEAF and found[1]["wanted"] == W_OUT
    assert all(row["scope"] == measure.ONE_DEFINITION for row in found)


def test_targets_reads_only_patches_that_passed_and_only_the_tasks_asked():
    records = {"a__b-1": record(), "a__b-2": record("a__b-2")}
    resolved = {"s1": {"a__b-1", "a__b-2"}, "s2": {"a__b-1"}, "s3": {"a__b-9"}, "s4": set()}
    offered = {"s1": {"a__b-1": LEAF, "a__b-2": TWO_PLACES}, "s2": {"a__b-1": OUT, "a__b-2": LEAF}, "s3": {"a__b-9": LEAF}, "s4": {"a__b-1": FROM_THE_FILE}}
    asked_of: list[str] = []

    def proposals(name: str):
        asked_of.append(name)
        return offered[name]

    found = measure.targets(records, ["a__b-1", "a__b-2"], resolved, proposals)
    assert [row["shape"] for row in found["a__b-1"]] == [fix_shape.LEAF, fix_shape.TAKEN_OUT]         # s4's patch did not pass
    assert found["a__b-2"] == []                                                                     # s2's small patch there did not pass
    assert asked_of == ["s1", "s2"]                                                                  # a submission that resolved none of them is not read


def test_normal_is_the_text_the_lists_write_and_functions_are_counted():
    assert measure.normal("def f( a ):\n\n    return  a   # x\n") == "def f(a):\n    return a"
    assert measure.functions_in(FILE) == 2 and measure.functions_in("def (") is None and measure.nodes_of("x = 1") == 5


# --------------------------------------------------------------------------- #
# the place in the lists
# --------------------------------------------------------------------------- #
def test_places_are_counted_the_way_the_lists_are_walked():
    taught = lessons()
    found = measure.places(taught, F_BEFORE, [W_LEAF, W_OUT, W_NOWHERE])
    order = [text for text, _, _ in kinds.ranking(taught.votes(F_BEFORE)) if kinds.is_a_program(text)]
    pieces = [text for text, _, _ in take_out.candidates(F_BEFORE)]
    assert found["candidates"] == len(taught.votes(F_BEFORE)) and found["pieces"] == len(pieces)
    leaf, out, nowhere = found["places"]
    assert leaf[measure.LEARNER] == order.index(W_LEAF) + 1 and leaf[measure.TAKEN_OUT] is None
    assert out[measure.TAKEN_OUT] == pieces.index(W_OUT) + 1 and out[measure.LEARNER] is None
    turns = [item[0] for item in choice.in_turns([(text, 0.0, None) for text in order], [(text, 0.0, None) for text in pieces])]
    assert leaf[measure.IN_TURNS] == turns.index(W_LEAF) + 1 and out[measure.IN_TURNS] == turns.index(W_OUT) + 1
    assert nowhere == {measure.LEARNER: None, measure.TAKEN_OUT: None, measure.IN_TURNS: None}


def test_a_lesson_left_out_does_not_vote():
    taught = lessons()
    assert measure.places(taught, F_BEFORE, [W_LEAF])["places"][0][measure.LEARNER] is not None
    assert measure.places(taught, F_BEFORE, [W_LEAF], without=["one"])["places"][0][measure.LEARNER] is None


def test_a_candidate_that_does_not_compile_is_not_counted(monkeypatch):
    taught = lessons()
    honest = measure.places(taught, F_BEFORE, [W_LEAF])["places"][0][measure.LEARNER]
    real = kinds.ranking
    monkeypatch.setattr(kinds, "ranking", lambda votes, only=None: [("def (", 99.0, {})] + real(votes, only))
    assert measure.places(taught, F_BEFORE, [W_LEAF])["places"][0][measure.LEARNER] == honest


def test_asked_gives_the_same_with_one_worker_and_with_two_and_cuts_off_what_is_too_large(monkeypatch):
    taught = lessons()
    jobs = [("k", F_BEFORE, [W_LEAF, W_OUT], []), ("small", "x = 1", [measure.normal("x = 2")], [])]
    said: list[str] = []
    one = measure.asked(taught, jobs, workers=1, limit=20, say=said.append)
    two = measure.asked(taught, jobs, workers=2, limit=20)
    assert {key: row["places"] for key, row in one.items()} == {key: row["places"] for key, row in two.items()}
    assert one[("k", F_BEFORE)]["places"] == measure.places(taught, F_BEFORE, [W_LEAF, W_OUT])["places"] and len(said) == 2 and said[0].startswith("1 of 2: k")
    monkeypatch.setattr(measure, "MAX_NODES", 10)
    cut = measure.asked(taught, jobs, workers=1, limit=20)
    assert cut[("k", F_BEFORE)]["too_long"] is True and cut[("k", F_BEFORE)]["places"] == [{measure.LEARNER: None, measure.TAKEN_OUT: None, measure.IN_TURNS: None}] * 2
    assert "too_long" not in cut[("small", "x = 1")]


def test_a_learner_that_does_not_finish_counts_as_not_reached(monkeypatch):
    def slow(*_args, **_kwargs):
        raise measure.TooLong()
    monkeypatch.setattr(measure, "places", slow)
    found = measure.asked(lessons(), [("k", F_BEFORE, [W_LEAF], [])], workers=1, limit=5)[("k", F_BEFORE)]
    assert found["too_long"] is True and found["places"][0][measure.IN_TURNS] is None and found["candidates"] is None


# --------------------------------------------------------------------------- #
# the counts and the rule
# --------------------------------------------------------------------------- #
def place(turns, learner=None, out=None) -> dict:
    return {measure.IN_TURNS: turns, measure.LEARNER: learner, measure.TAKEN_OUT: out}


def patch(shape: str, alone: bool = True, scope: str = measure.ONE_DEFINITION) -> dict:
    return {"shape": shape, "kind": None, "needs": None, "nodes": 1, "times": 1, "scope": scope, "from_its_definition_alone": alone}


def definition(candidates=100, pieces=10, nodes=50, **more) -> dict:
    return {"nodes": nodes, "lines": 5, "candidates": candidates, "pieces": pieces, "seconds": 1.0, **more}


PER_TASK = {
    "t1": {"patches": [patch(fix_shape.LEAF), patch(fix_shape.TAKEN_OUT)], "places": [place(3, learner=2), place(400, out=200)], "definitions": [definition()], "functions_in_the_file": 10},
    "t2": {"patches": [patch(fix_shape.TAKEN_OUT)], "places": [place(150, out=75)], "definitions": [definition(300, 30, 70)], "functions_in_the_file": 30},
    "t3": {"patches": [patch(fix_shape.PUT_IN, alone=False)], "places": [place(None)], "definitions": [definition(500, 50, 90)], "functions_in_the_file": None},
    "t4": {"patches": [patch(fix_shape.PUT_IN, scope=measure.WHOLE_FILE)], "places": [place(None)], "definitions": [definition(None, None, 5000, too_long=True)], "functions_in_the_file": 20},
    "t5": {"patches": [patch(fix_shape.PUT_IN, alone=False)], "places": [place(900, learner=450)], "definitions": [definition(700, 70, 110)], "functions_in_the_file": 40},
}


def test_best_and_within():
    rows = [place(5, learner=3), place(None), place(2, out=1)]
    assert measure.best(rows, measure.IN_TURNS) == 2 and measure.best(rows, measure.LEARNER) == 3 and measure.best([place(None)], measure.IN_TURNS) is None
    assert measure.within([1, 10, 11, 200, 201, 5000, None]) == {"1": 1, "10": 2, "100": 3, "200": 4, "1000": 5, "at any place": 6, "in no place": 1}


def test_summarise_counts_tasks_by_their_best_place():
    told = measure.summarise(PER_TASK)
    assert (told["tasks"], told["small_passing_patches"], told["definitions"]) == (5, 6, 5)
    assert told["tasks_by_best_place"][measure.IN_TURNS] == {"1": 0, "10": 1, "100": 1, "200": 2, "1000": 3, "at any place": 3, "in no place": 2}
    assert told["tasks_by_best_place"][measure.LEARNER]["10"] == 1 and told["tasks_by_best_place"][measure.TAKEN_OUT]["200"] == 2
    shapes = told["by_shape_of_the_passing_patch"]
    assert shapes[fix_shape.TAKEN_OUT] == {"tasks_with_such_a_passing_patch": 2, "within_200_in_turns": 1, "within_200_learner": 0, "within_200_taken_out": 2,
                                           "in_either_list_at_any_place": 2}
    assert shapes[fix_shape.PUT_IN]["tasks_with_such_a_passing_patch"] == 3 and shapes[fix_shape.PUT_IN]["within_200_in_turns"] == 0
    assert shapes[fix_shape.PUT_IN]["in_either_list_at_any_place"] == 1 and shapes[fix_shape.LEAF]["within_200_in_turns"] == 1
    assert told["median_place_in_turns_where_there_is_one"] == 150 and told["median_learner_candidates_for_the_definition"] == 400
    assert told["median_pieces_taken_out_of_the_definition"] == 40 and told["median_nodes_of_the_definition"] == 90
    assert told["definitions_the_learner_did_not_finish"] == 1 and told["patches_whose_scope_is_the_whole_file"] == 1
    assert told["tasks_with_a_small_passing_patch_from_its_definition_alone"] == 3
    assert told["tasks_within_budget_whose_patch_there_is_from_its_definition_alone"] == 2
    assert told["median_functions_in_the_changed_file"] == 25


@pytest.mark.parametrize("came,verdict", [(40, "worth building"), (39, "undecided: no run on this count alone"), (20, "undecided: no run on this count alone"),
                                          (19, "not reached: no run"), (0, "not reached: no run")])
def test_the_rule_has_two_edges(came, verdict):
    summary = {"tasks": 80, "tasks_by_best_place": {measure.IN_TURNS: {"200": came}}}
    assert measure.rule(summary) == {"tasks_within_the_first_200_in_turns": came, "of": 80, "verdict": verdict}


def test_put_together_gives_each_patch_its_own_place_and_each_definition_once():
    targets = {"t": [{"before": "B1", "wanted": "W1", "shape": fix_shape.LEAF, "scope": measure.ONE_DEFINITION},
                     {"before": "x = 1", "wanted": "W2", "shape": fix_shape.PUT_IN, "scope": measure.ONE_DEFINITION},
                     {"before": "B1", "wanted": "W3", "shape": fix_shape.TAKEN_OUT, "scope": measure.ONE_DEFINITION}]}
    answers = {("t", "B1"): {"candidates": 7, "pieces": 3, "seconds": 0.5, "places": [place(1, learner=1), place(4, out=2)]},
               ("t", "x = 1"): {"candidates": None, "pieces": None, "seconds": 0.0, "too_long": True, "places": [place(None)]}}
    got = measure.put_together(targets, answers, {"t": 12})["t"]
    assert got["places"] == [place(1, learner=1), place(None), place(4, out=2)]
    assert [row["shape"] for row in got["patches"]] == [fix_shape.LEAF, fix_shape.PUT_IN, fix_shape.TAKEN_OUT] and "before" not in got["patches"][0]
    assert got["definitions"] == [{"nodes": measure.nodes_of("B1"), "lines": 1, "candidates": 7, "pieces": 3, "seconds": 0.5},
                                  {"nodes": 5, "lines": 1, "candidates": None, "pieces": None, "seconds": 0.0, "too_long": True}]
    assert got["functions_in_the_file"] == 12


def test_what_was_expected_holds_ranges_and_a_rule_with_two_edges():
    ranges = [value for key, value in measure.EXPECTED.items() if key not in ("written", "rule")]
    assert len(ranges) == 6 and all(low < high for low, high in ranges)
    assert "at least 40 of the 80" in measure.EXPECTED["rule"] and "fewer than 20" in measure.EXPECTED["rule"]
    assert set(measure.code_sha256()) >= {"canonical/tools/small_passing_patch_place_measure_v1.py", "canonical/runtime/edit_kind_learning_v1.py"}


# --------------------------------------------------------------------------- #
# the whole of it, on a made-up benchmark
# --------------------------------------------------------------------------- #
def humanevalfix_file(where: pathlib.Path) -> pathlib.Path:
    rows = [{"task_id": "Python/0", "entry_point": "f", "bug_type": "operator misuse", "declaration": "def f(x, y):\n", "buggy_solution": "    return x < y\n",
             "canonical_solution": "    return x <= y\n", "test": "def check(f):\n    assert f(1, 1)\ncheck(f)"},
            {"task_id": "Python/1", "entry_point": "g", "bug_type": "operator misuse", "declaration": "def g(p, q):\n", "buggy_solution": "    return p < q\n",
             "canonical_solution": "    return p <= q\n", "test": "def check(g):\n    assert g(1, 1)\ncheck(g)"}]
    path = where / "humanevalpack.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    return path


def test_lessons_of_shows_every_humanevalfix_fix_once(tmp_path):
    taught, shown = measure.lessons_of(humanevalfix_file(tmp_path), None)
    assert shown["humanevalfix_fixes_shown"] == 2 and shown["condefects_fixes_shown"] == 0 and shown["lessons_that_taught_something"] == 2
    assert shown["operators"] == len(taught.operators) > 0 and shown["condefects_commit"] is None


def test_lessons_of_takes_the_first_condefects_fixes_of_the_seeded_order(tmp_path):
    for number in range(4):
        folder = tmp_path / "cd" / "Code" / f"task{number}" / "Python" / "1"
        folder.mkdir(parents=True)
        (folder / "faultyVersion.py").write_text(f"x = {number} + 1\nprint(x)\n")
        (folder / "correctVersion.py").write_text(f"x = {number} - 1\nprint(x)\n")
    taught, shown = measure.lessons_of(humanevalfix_file(tmp_path), tmp_path / "cd", n=3)
    assert shown["condefects_fixes_shown"] == 3 and sum(1 for name in taught.lessons + taught.taught_nothing if name.startswith("condefects/")) == 3


def test_main_writes_a_record_and_runs_nothing(tmp_path, capsys):
    cache = tmp_path / "cache" / passing.WITH_PATCHES[:10]
    for name, resolved, offered in (("s1", ["a__b-1"], {"a__b-1": LEAF + ADDED}), ("s2", ["a__b-1"], {"a__b-1": OUT}), ("s3", [], {"a__b-1": FROM_THE_FILE})):
        (cache / name).mkdir(parents=True)
        (cache / name / "results.json").write_text(json.dumps({"resolved": resolved}))
        (cache / name / "all_preds.jsonl").write_text("\n".join(json.dumps({"instance_id": task, "model_patch": text}) for task, text in offered.items()) + "\n")
    pulls = tmp_path / "pulls"
    pulls.mkdir()
    (pulls / "a__b-1.json").write_text(json.dumps(record()))
    passing_record = tmp_path / "passing.json"
    passing_record.write_text(json.dumps({"per_task": {"a__b-1": ["can be listed", 2, True, True, True, True], "a__b-2": ["several places", 1, False, False, False, False]}}))
    out = tmp_path / "record.json"
    assert measure.main(["--cache-dir", str(tmp_path / "cache"), "--pull-requests-dir", str(pulls), "--humanevalfix", str(humanevalfix_file(tmp_path)),
                         "--passing-record", str(passing_record), "--workers", "1", "--out", str(out)]) == 0
    got = json.loads(out.read_text())
    assert got["schema"] == measure.SCHEMA and (got["model_calls"], got["programs_run"], got["tests_run"]) == (0, 0, 0)
    assert (got["tasks_asked"], got["tasks_with_a_small_passing_patch"], got["submissions_with_patches"]) == (1, 1, 3)
    task = got["per_task"]["a__b-1"]
    assert [row["shape"] for row in task["patches"]] == [fix_shape.LEAF, fix_shape.TAKEN_OUT] and len(task["definitions"]) == 1 and task["functions_in_the_file"] == 2
    assert task["places"][0][measure.LEARNER] == 1 and task["places"][1][measure.TAKEN_OUT] is not None      # both fixes of the made-up lessons exchange < for <=
    assert got["summary"]["tasks_by_best_place"][measure.IN_TURNS]["10"] == 1 and got["rule"]["verdict"] == "not reached: no run"
    control = got["control_humanevalfix_development"]
    assert control["bugs"] == 1 and control[measure.LEARNER]["1"] == 1                # Python/0, its own fix left out, is taught by Python/1
    assert got["expected_before"] == measure.EXPECTED and "WROTE" in capsys.readouterr().out
