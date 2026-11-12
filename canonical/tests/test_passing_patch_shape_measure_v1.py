#!/usr/bin/env python3
"""The shapes of other people's test-passing patches: how a patch is read, when it is given a
shape, that looking inside one definition gives what the whole file gives, and the counts."""
from __future__ import annotations

import ast
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import fix_shape_v1 as fix_shape  # noqa: E402
from canonical.tools import fix_shape_census_measure_v1 as census  # noqa: E402
from canonical.tools import passing_patch_shape_measure_v1 as measure  # noqa: E402

BEFORE = '''import os

LIMIT = 3


def f(a, b):
    c = a
    return c


class C:
    def m(self, a):
        d = a
        return d

    def n(self, a):
        return a
'''


def diff(path: str, hunks: str, head: str = "") -> str:
    return f"diff --git a/{path} b/{path}\n{head}index 83a4f00..5f3a362 100644\n--- a/{path}\n+++ b/{path}\n{hunks}\n"


ONE_LINE = diff("pkg/mod.py", "@@ -6,3 +6,3 @@\n def f(a, b):\n-    c = a\n+    c = abs(a)\n     return c")
IN_A_METHOD = diff("pkg/mod.py", "@@ -11,4 +11,4 @@\n class C:\n     def m(self, a):\n-        d = a\n+        d = a + LIMIT\n         return d")
TWO_PLACES = diff("pkg/mod.py", "@@ -6,3 +6,3 @@\n def f(a, b):\n-    c = a\n+    c = abs(a)\n     return c\n@@ -12,3 +12,3 @@\n     def m(self, a):\n-        d = a\n+        d = a + LIMIT\n         return d")
ADDED = "diff --git a/reproduce.py b/reproduce.py\nnew file mode 100644\nindex 0000000..5c63bbd\n--- /dev/null\n+++ b/reproduce.py\n@@ -0,0 +1,1 @@\n+print(1)\n"
A_TEST = diff("tests/test_mod.py", "@@ -1,1 +1,2 @@\n x = 1\n+y = 2")


def record(**more) -> dict:
    return {"instance_id": "a__b-1", "repo": "a/b", "files": [{"path": "pkg/mod.py", "status": "modified", "before": BEFORE, "is_test": False, "is_python": True,
                                                              "patch": "@@ -6,3 +6,3 @@\n def f(a, b):\n-    c = a\n+    c = abs(a)\n     return c"}], **more}


def files() -> measure.Files:
    return measure.Files(record())


# --------------------------------------------------------------------------- #
# a patch as its files
# --------------------------------------------------------------------------- #
def test_files_of_reads_each_file_with_its_status_and_hunks():
    got = measure.files_of("some preamble\n" + ONE_LINE + ADDED)
    assert [(row["path"], row["status"]) for row in got] == [("pkg/mod.py", "modified"), ("reproduce.py", "added")]
    assert got[0]["patch"] == "@@ -6,3 +6,3 @@\n def f(a, b):\n-    c = a\n+    c = abs(a)\n     return c"
    assert got[1]["patch"] == "@@ -0,0 +1,1 @@\n+print(1)"


def test_files_of_knows_removed_and_renamed_files_and_an_empty_patch():
    removed = "diff --git a/x.py b/x.py\ndeleted file mode 100644\n--- a/x.py\n+++ /dev/null\n@@ -1,1 +0,0 @@\n-x = 1\n"
    renamed = "diff --git a/x.py b/y.py\nsimilarity index 100%\nrename from x.py\nrename to y.py\n"
    got = measure.files_of(removed + renamed)
    assert [(row["path"], row["status"], bool(row["patch"])) for row in got] == [("x.py", "removed", True), ("y.py", "renamed", False)]
    assert measure.files_of("") == [] and measure.files_of("not a patch at all") == []


def test_a_hunk_line_is_never_taken_for_a_new_file():
    tricky = diff("pkg/mod.py", "@@ -1,2 +1,2 @@\n-new file mode 100644\n+deleted file mode 100644\n x")
    got = measure.files_of(tricky)
    assert len(got) == 1 and got[0]["status"] == "modified" and "-new file mode 100644" in got[0]["patch"]


# --------------------------------------------------------------------------- #
# looking inside one definition
# --------------------------------------------------------------------------- #
def test_spans_come_innermost_first_and_then_the_top_level_statements():
    spans = measure._spans(ast.parse(BEFORE))
    assert spans[:2] == [(12, 14), (16, 17)]                       # the two methods, deeper than the class
    assert (6, 8) in spans and (11, 17) in spans and spans.index((12, 14)) < spans.index((11, 17))
    assert spans[-5:] == [(1, 1), (3, 3), (6, 8), (11, 17)][-4:] or spans[-4:] == [(1, 1), (3, 3), (6, 8), (11, 17)]


def test_a_decorated_definition_begins_at_its_decorator():
    spans = measure._spans(ast.parse("@d\ndef f():\n    return 1\n"))
    assert spans[0] == (1, 3)


def test_narrowed_gives_the_one_definition_that_holds_the_change():
    after = BEFORE.replace("d = a", "d = a + LIMIT")
    parts = measure.narrowed(BEFORE, after, measure._spans(ast.parse(BEFORE)))
    assert parts == ("def m(self, a):\n    d = a\n    return d", "def m(self, a):\n    d = a + LIMIT\n    return d")


def test_narrowed_takes_the_class_when_two_of_its_methods_change_and_nothing_when_two_definitions_do():
    spans = measure._spans(ast.parse(BEFORE))
    two_methods = BEFORE.replace("d = a", "d = a + 1").replace("        return a\n", "        return a + 1\n")
    parts = measure.narrowed(BEFORE, two_methods, spans)
    assert parts is not None and parts[0].startswith("class C:")
    assert measure.narrowed(BEFORE, BEFORE.replace("c = a", "c = b").replace("d = a", "d = 1"), spans) is None


def test_lines_put_in_after_a_definition_do_not_count_as_inside_it():
    spans = measure._spans(ast.parse(BEFORE))
    sibling = BEFORE.replace("        return a\n", "        return a\n\n    def o(self):\n        return 1\n")
    parts = measure.narrowed(BEFORE, sibling, spans)
    assert parts is not None and parts[0].startswith("class C:")           # a new method: the class holds it, the method before it does not
    top = BEFORE + "\n\ndef k():\n    return 1\n"
    assert measure.narrowed(BEFORE, top, spans) is None


def test_narrowed_handles_a_top_level_statement():
    parts = measure.narrowed(BEFORE, BEFORE.replace("LIMIT = 3", "LIMIT = 4"), measure._spans(ast.parse(BEFORE)))
    assert parts == ("LIMIT = 3", "LIMIT = 4")


@pytest.mark.parametrize("old,new", [("c = a", "c = abs(a)"), ("d = a", "d = a + LIMIT"), ("LIMIT = 3", "LIMIT = 4"), ("        return a\n", "        return a.x\n"),
                                     ("    c = a\n", "    c = a\n    c = b\n"), ("    c = a\n    return c", "    return a"), ("def f(a, b):", "def f(a, b, k=None):")])
def test_inside_the_definition_the_shape_is_what_the_whole_files_give(old, new):
    after = BEFORE.replace(old, new)
    held = fix_shape.atoms(ast.parse(BEFORE))
    parts = measure.narrowed(BEFORE, after, measure._spans(ast.parse(BEFORE)))
    assert parts is not None
    near, far = fix_shape.shape(parts[0], parts[1], held=held), fix_shape.shape(BEFORE, after)
    assert [near[k] for k in ("shape", "kind", "needs", "nodes")] == [far[k] for k in ("shape", "kind", "needs", "nodes")]


# --------------------------------------------------------------------------- #
# the shape of one patch
# --------------------------------------------------------------------------- #
def test_a_one_line_patch_gets_its_shape_and_added_files_stand_beside_it():
    alone = measure.shape_of_patch(files(), ONE_LINE)
    assert (alone["shape"], alone["kind"], alone["needs"], alone["nodes"], alone["added_files"]) == (fix_shape.PUT_IN, "one inside", fix_shape.BUILT_IN, 2, 0)
    with_script = measure.shape_of_patch(files(), ONE_LINE + ADDED)
    assert (with_script["shape"], with_script["added_files"]) == (fix_shape.PUT_IN, 1)
    assert measure.smallness(alone) == {"listed": True, "listed_nothing_added": True, "one_statement": True, "one_statement_nothing_added": True}
    assert measure.smallness(with_script) == {"listed": True, "listed_nothing_added": False, "one_statement": True, "one_statement_nothing_added": False}


def test_held_is_what_the_whole_file_holds_not_only_the_definition():
    found = measure.shape_of_patch(files(), IN_A_METHOD)
    assert (found["shape"], found["needs"]) == (fix_shape.PUT_IN, fix_shape.HELD)          # LIMIT stands at the top of the file


def test_the_agents_own_tests_are_set_aside_like_the_experts():
    found = measure.shape_of_patch(files(), ONE_LINE + A_TEST)
    assert (found["shape"], found["added_files"], found["other_files"]) == (fix_shape.PUT_IN, 0, 0)


def test_what_is_not_given_a_shape():
    assert measure.shape_of_patch(files(), TWO_PLACES)["shape"] == fix_shape.SEVERAL_PLACES
    assert measure.shape_of_patch(files(), ONE_LINE + diff("pkg/other.py", "@@ -1,1 +1,1 @@\n-x = 1\n+x = 2"))["shape"] == census.SEVERAL_FILES
    assert measure.shape_of_patch(files(), diff("pkg/other.py", "@@ -1,1 +1,1 @@\n-x = 1\n+x = 2"))["shape"] == measure.ELSEWHERE
    assert measure.shape_of_patch(files(), ADDED)["shape"] == measure.NO_PYTHON
    assert measure.shape_of_patch(files(), A_TEST)["shape"] == measure.NO_PYTHON
    assert measure.shape_of_patch(files(), "")["shape"] == measure.NO_PYTHON
    wrong = measure.shape_of_patch(files(), diff("pkg/mod.py", "@@ -6,3 +6,3 @@\n def f(a, b):\n-    c = zz\n+    c = abs(a)\n     return c"))
    assert wrong["shape"] == measure.NOT_APPLIED and wrong["kind"]
    gone = "diff --git a/pkg/mod.py b/pkg/mod.py\ndeleted file mode 100644\n--- a/pkg/mod.py\n+++ /dev/null\n@@ -1,1 +0,0 @@\n-import os\n"
    assert measure.shape_of_patch(files(), gone)["shape"] == census.A_WHOLE_FILE
    docs = diff("docs/x.rst", "@@ -1,1 +1,1 @@\n-a\n+b")
    assert measure.shape_of_patch(files(), ONE_LINE + docs)["other_files"] == 1
    for name in (fix_shape.SEVERAL_PLACES, census.SEVERAL_FILES, measure.ELSEWHERE, measure.NO_PYTHON, measure.NOT_APPLIED, measure.NOT_EXAMINED, census.A_WHOLE_FILE):
        assert measure.smallness({"shape": name, "needs": None, "nodes": None}) == {"listed": False, "listed_nothing_added": False, "one_statement": False,
                                                                                    "one_statement_nothing_added": False}


def test_the_whole_file_way_gives_the_same_and_a_large_file_is_not_examined_outside_one_definition(monkeypatch):
    for patch in (ONE_LINE, IN_A_METHOD, TWO_PLACES):
        near, far = measure.shape_of_patch(files(), patch), measure.shape_of_patch(files(), patch, whole_file=True)
        assert [near[k] for k in ("shape", "kind", "needs", "nodes")] == [far[k] for k in ("shape", "kind", "needs", "nodes")]
    monkeypatch.setattr(measure, "WHOLE_FILE_AT_MOST_LINES", 3)
    assert measure.shape_of_patch(files(), TWO_PLACES)["shape"] == measure.NOT_EXAMINED
    assert measure.shape_of_patch(files(), ONE_LINE)["shape"] == fix_shape.PUT_IN                 # inside one definition: still looked at
    assert measure.shape_of_patch(files(), TWO_PLACES, whole_file=True)["shape"] == fix_shape.SEVERAL_PLACES


def test_a_file_that_cannot_be_read_is_said():
    broken = measure.Files({"repo": "a/b", "files": [{"path": "pkg/mod.py", "before": "def (\n", "is_test": False, "is_python": True}]})
    assert measure.shape_of_patch(broken, diff("pkg/mod.py", "@@ -1,1 +1,1 @@\n-def (\n+def )"))["shape"] == fix_shape.UNREADABLE


def test_class_of_an_experts_fix():
    assert measure.class_of({"shape": fix_shape.TAKEN_OUT, "needs": fix_shape.NOTHING, "nodes": 1}) == "can be listed"
    assert measure.class_of({"shape": fix_shape.LEAF, "needs": fix_shape.NEW, "nodes": 1}) == "one statement, not listable"
    assert measure.class_of({"shape": fix_shape.EXPRESSION, "needs": fix_shape.HELD, "nodes": 5}) == "one statement, not listable"
    assert measure.class_of({"shape": fix_shape.ONE_PLACE}) == fix_shape.ONE_PLACE
    assert measure.class_of({"shape": fix_shape.SEVERAL_PLACES}) == fix_shape.SEVERAL_PLACES
    assert measure.class_of({"shape": census.SEVERAL_FILES}) == census.SEVERAL_FILES and measure.class_of({"shape": census.A_WHOLE_FILE}) == census.SEVERAL_FILES
    assert set(measure.CLASSES) == {"can be listed", "one statement, not listable", fix_shape.ONE_PLACE, fix_shape.SEVERAL_PLACES, census.SEVERAL_FILES}


# --------------------------------------------------------------------------- #
# the counts
# --------------------------------------------------------------------------- #
EXPERT = {"t1": "can be listed", "t2": "one statement, not listable", "t3": fix_shape.SEVERAL_PLACES, "t4": fix_shape.SEVERAL_PLACES, "t5": census.SEVERAL_FILES}
RESOLVED = {"s1": {"t1", "t2", "t3", "t9"}, "s2": {"t1", "t2"}, "s3": {"t1", "t3", "t5"}, "s4": {"t1"}}


def test_by_verdicts_counts_the_share_of_submissions_for_each_class():
    told = measure.by_verdicts(EXPERT, RESOLVED)
    assert (told["submissions"], told["best_submission"], told["best_resolves"], told["middle_submission_resolves"], told["least"]) == (4, "s1", 3, 3, 1)
    rows = told["by_class_of_the_experts_fix"]
    assert rows["can be listed"] == {"tasks": 1, "mean_share_of_submissions_that_resolve": 1.0, "resolved_by_none": 0, "resolved_by_the_best_submission": 1}
    assert rows[fix_shape.SEVERAL_PLACES] == {"tasks": 2, "mean_share_of_submissions_that_resolve": 0.25, "resolved_by_none": 1, "resolved_by_the_best_submission": 1}
    assert rows[census.SEVERAL_FILES]["mean_share_of_submissions_that_resolve"] == 0.25 and rows[fix_shape.ONE_PLACE]["tasks"] == 0
    assert told["mean_share_at_most_one_statement"] == 0.75 and told["tasks_resolved_by_none"] == 1
    assert measure.by_verdicts(EXPERT, {})["best_submission"] is None


def test_the_rule_asks_for_a_fall_of_five_points_at_each_step():
    told = measure.by_verdicts(EXPERT, RESOLVED)                       # 0.75, 0.25, 0.25: the second step does not fall
    assert measure.rule_shapes_track_difficulty(told) == {"at most one statement, several places, several files": [0.75, 0.25, 0.25],
                                                          "falls_by_at_least_5_points_each_step": False}
    falls = measure.by_verdicts(EXPERT, {**RESOLVED, "s3": {"t1", "t3"}})
    assert measure.rule_shapes_track_difficulty(falls)["falls_by_at_least_5_points_each_step"] is True
    assert measure.rule_shapes_track_difficulty(measure.by_verdicts(EXPERT, {}))["falls_by_at_least_5_points_each_step"] is False


def test_passing_patches_counts_only_what_passed_and_each_different_patch_once():
    records = {"a__b-1": record(), "a__b-2": record(instance_id="a__b-2")}
    resolved = {"s1": {"a__b-1", "a__b-2"}, "s2": {"a__b-1"}, "s3": {"a__b-1"}, "s4": set()}
    offered = {"s1": {"a__b-1": TWO_PLACES, "a__b-2": TWO_PLACES}, "s2": {"a__b-1": ONE_LINE + ADDED, "a__b-2": ONE_LINE},
               "s3": {"a__b-1": TWO_PLACES}, "s4": {"a__b-1": ONE_LINE}}
    said: list[str] = []
    found = measure.passing_patches(records, resolved, lambda name: offered[name], check_whole_file=10, progress=said.append)
    assert found["passing_patches"] == 4 and found["different_passing_patches"] == 3
    assert found["by_shape"] == {fix_shape.SEVERAL_PLACES: 3, fix_shape.PUT_IN: 1}
    first, second = found["per_task"]["a__b-1"], found["per_task"]["a__b-2"]
    assert (first["passing"], first["listed"], first["listed_nothing_added"], first["one_statement"], first["one_statement_nothing_added"]) == (3, True, False, True, False)
    assert (second["passing"], second["listed"], second["one_statement"]) == (1, False, False)     # s2 proposed a small one there, but it did not pass
    assert found["checked_as_whole_files"] == 3 and found["the_two_ways_apart"] == [] and len(said) == 4


def test_a_whole_file_way_that_disagrees_is_named(monkeypatch):
    honest = measure.shape_of_patch
    monkeypatch.setattr(measure, "shape_of_patch", lambda f, d, whole_file=False: {**honest(f, d, whole_file), "nodes": 99} if whole_file else honest(f, d))
    found = measure.passing_patches({"a__b-1": record()}, {"s1": {"a__b-1"}}, lambda name: {"a__b-1": ONE_LINE}, check_whole_file=5)
    assert found["the_two_ways_apart"] == ["s1/a__b-1"]


def test_summarise_by_the_class_of_the_experts_fix():
    per_task = {"t1": {"passing": 3, "listed": True, "listed_nothing_added": True, "one_statement": True, "one_statement_nothing_added": True},
                "t2": {"passing": 2, "listed": False, "listed_nothing_added": False, "one_statement": True, "one_statement_nothing_added": False},
                "t3": {"passing": 1, "listed": True, "listed_nothing_added": False, "one_statement": True, "one_statement_nothing_added": False},
                "t4": {"passing": 0, "listed": False, "listed_nothing_added": False, "one_statement": False, "one_statement_nothing_added": False},
                "t5": {"passing": 1, "listed": False, "listed_nothing_added": False, "one_statement": False, "one_statement_nothing_added": False}}
    told = measure.summarise(EXPERT, per_task)
    assert (told["tasks"], told["with_a_passing_patch"], told["some_passing_patch_listed"], told["some_passing_patch_listed_nothing_added"]) == (5, 4, 2, 1)
    assert (told["some_passing_patch_one_statement"], told["some_passing_patch_one_statement_nothing_added"]) == (3, 1)
    assert told["by_class_of_the_experts_fix"][fix_shape.SEVERAL_PLACES] == {"tasks": 2, "with_a_passing_patch": 1, "some_passing_patch_listed": 1,
                                                                             "some_passing_patch_listed_nothing_added": 0, "some_passing_patch_one_statement": 1,
                                                                             "some_passing_patch_one_statement_nothing_added": 0}


# --------------------------------------------------------------------------- #
# the recordings on disk
# --------------------------------------------------------------------------- #
def cache(tmp_path: pathlib.Path) -> pathlib.Path:
    for ref, with_patches in ((measure.TO_THIS_DAY, False), (measure.WITH_PATCHES, True)):
        for name, resolved in (("s1", ["a__b-1"]), ("s2", [])):
            folder = tmp_path / ref[:10] / name
            folder.mkdir(parents=True)
            (folder / "results.json").write_text(json.dumps({"resolved": resolved, "no_generation": []}))
            if with_patches and name == "s1":
                rows = [{"instance_id": "a__b-1", "model_patch": ONE_LINE + ADDED, "model_name_or_path": "s1"}, {"instance_id": "a__b-2", "model_patch": None},
                        {"instance_id": "a__b-3", "model_patch": "   "}]
                (folder / "all_preds.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\nnot json\n\n")
    (tmp_path / measure.TO_THIS_DAY[:10] / "s3").mkdir()
    (tmp_path / measure.TO_THIS_DAY[:10] / "s3" / "results.json").write_text("not json")
    return tmp_path


def test_verdicts_and_patches_are_read_from_the_cache(tmp_path):
    where = cache(tmp_path)
    assert measure.verdicts(where, measure.TO_THIS_DAY) == {"s1": {"a__b-1"}, "s2": set()}          # s3 cannot be read: left out, not guessed
    assert measure.patches(where, "s1") == {"a__b-1": ONE_LINE + ADDED} and measure.patches(where, "s2") == {}


def test_fetch_asks_for_every_submission_and_keeps_what_it_gets(tmp_path):
    asked: list[tuple[str, str]] = []

    def ask(path: str, ref: str, raw: bool = True) -> bytes:
        asked.append((path, ref))
        if path == "evaluation/verified":
            return json.dumps([{"name": "s1", "type": "dir"}, {"name": "README.md", "type": "file"}]).encode()
        if path.endswith("all_preds.jsonl") and ref == measure.WITH_PATCHES:
            raise RuntimeError("Not Found")
        return b'{"resolved": []}'

    tally = measure.fetch(tmp_path, workers=1, ask=ask)
    assert tally == {"fetched results.json": 2, "missing all_preds.jsonl": 1}
    assert (tmp_path / measure.TO_THIS_DAY[:10] / "s1" / "results.json").read_text() == '{"resolved": []}'
    assert json.loads((tmp_path / measure.WITH_PATCHES[:10] / "names.json").read_text()) == ["s1"]
    assert measure.fetch(tmp_path, workers=1, ask=ask) == {"already there": 2, "missing all_preds.jsonl": 1}


def test_what_was_expected_holds_ranges_and_two_rules():
    assert set(measure.EXPECTED["rules"]) == {"do the shapes track difficulty", "was a tenth wrong"}
    assert "at least 100 of the 500" in measure.EXPECTED["rules"]["was a tenth wrong"]
    shares = measure.EXPECTED["share of submissions that resolve a task, mean over the tasks of a class of the expert's fix"]
    assert set(shares) == set(measure.CLASSES) and all(low < high for low, high in shares.values())


def test_main_writes_a_record_and_runs_nothing(tmp_path, capsys):
    where = cache(tmp_path / "cache")
    pulls = tmp_path / "pulls"
    pulls.mkdir()
    (pulls / "a__b-1.json").write_text(json.dumps(record()))
    out = tmp_path / "record.json"
    assert measure.main(["--cache-dir", str(where), "--pull-requests-dir", str(pulls), "--out", str(out), "--check-whole-file", "5"]) == 0
    got = json.loads(out.read_text())
    assert got["schema"] == measure.SCHEMA and (got["model_calls"], got["programs_run"], got["tests_run"]) == (0, 0, 0)
    assert got["from_the_verdicts_alone"]["submissions"] == 2 and got["from_the_verdicts_alone"]["best_resolves"] == 1
    assert got["the_passing_patches"]["submissions_with_patches"] == 1 and got["the_passing_patches"]["passing_patches"] == 1
    assert got["the_passing_patches"]["some_passing_patch_listed"] == 1 and got["the_passing_patches"]["some_passing_patch_listed_nothing_added"] == 0
    assert got["per_task"]["a__b-1"] == ["can be listed", 1, True, False, True, False]
    assert got["expected_before"] == measure.EXPECTED and "WROTE" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        measure.main(["--cache-dir", str(where)])
