"""How much of a fix was seen before in other fixes: the cutting into pieces, the asking, the counting."""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.tools import expert_fix_repetition_measure_v1 as tool  # noqa: E402


def normal(source: str) -> str:
    return ast.unparse(ast.parse(source))


# --------------------------------------------------------------------------- #
# a fix as the pull request gives it
# --------------------------------------------------------------------------- #
FILE = "a\nb\nc\nd\ne\nf\ng\nh\n"


def test_apply_patch_changes_what_the_hunk_says():
    patch = "@@ -2,3 +2,4 @@ a\n b\n-c\n+C\n+c2\n d"
    assert tool.apply_patch(FILE, patch) == "a\nb\nC\nc2\nd\ne\nf\ng\nh\n"


def test_apply_patch_takes_several_hunks_and_a_hunk_at_either_end():
    patch = "@@ -1,2 +1,2 @@\n-a\n+A\n b\n@@ -7,2 +7,3 @@\n g\n h\n+i"
    assert tool.apply_patch(FILE, patch) == "A\nb\nc\nd\ne\nf\ng\nh\ni\n"


def test_apply_patch_adds_lines_to_an_empty_place():
    assert tool.apply_patch("x\ny\n", "@@ -1,0 +2,1 @@\n+new") == "x\nnew\ny\n"
    assert tool.apply_patch("", "@@ -0,0 +1,2 @@\n+one\n+two") == "one\ntwo\n"


def test_apply_patch_reads_a_count_left_out_as_one_and_skips_the_no_newline_note():
    assert tool.apply_patch("x\ny", "@@ -2 +2 @@\n-y\n\\ No newline at end of file\n+z\n\\ No newline at end of file") == "x\nz"


def test_apply_patch_takes_an_empty_line_of_the_hunk_as_an_unchanged_empty_line():
    assert tool.apply_patch("a\n\nb\n", "@@ -1,3 +1,3 @@\n a\n\n-b\n+B") == "a\n\nB\n"


def test_apply_patch_finds_the_lines_where_they_now_stand_and_says_how_far():
    moved: list[int] = []
    shifted = "new1\nnew2\n" + FILE
    assert tool.apply_patch(shifted, "@@ -2,3 +2,3 @@\n b\n-c\n+C\n d", moved) == "new1\nnew2\na\nb\nC\nd\ne\nf\ng\nh\n"
    assert moved == [2]
    nothing: list[int] = []
    tool.apply_patch(FILE, "@@ -2,3 +2,3 @@\n b\n-c\n+C\n d", nothing)
    assert nothing == []


def test_apply_patch_takes_the_nearest_of_several_places():
    text = "x\ny\n" * 4
    moved: list[int] = []
    assert tool.apply_patch(text, "@@ -6,2 +6,2 @@\n x\n-y\n+Y", moved) == "x\ny\nx\ny\nx\nY\nx\ny\n"      # stated line 6 is a y: the x-y pair at line 5 is nearest
    assert moved == [-1]


@pytest.mark.parametrize("patch, why", [
    ("@@ -2,3 +2,3 @@\n b\n-X\n+C\n d", "does not have the lines"),
    ("@@ -2,3 +2,3 @@\n b\n-c", "ends early"),
    ("@@ -2,2 +2,2 @@\n b\n-c\n+C\n d", "not a hunk header"),
    ("garbage", "not a hunk header"),
    ("@@ -2,3 +2,3 @@\n b\n*c\n+C\n d", "unexpected line"),
])
def test_apply_patch_refuses_what_does_not_belong_to_the_file(patch, why):
    with pytest.raises(ValueError, match=why):
        tool.apply_patch(FILE, patch)


def test_apply_patch_refuses_a_second_hunk_that_reaches_back_into_the_first():
    with pytest.raises(ValueError):
        tool.apply_patch(FILE, "@@ -3,2 +3,2 @@\n-c\n+C\n d\n@@ -1,2 +1,2 @@\n-a\n+A\n b")


# --------------------------------------------------------------------------- #
# a file as its units
# --------------------------------------------------------------------------- #
MODULE = '''
import os
LIMIT = 3

def top(a):
    def inner(b):
        return b
    return inner(a)

@decorated
class Box(Base):
    size = 1
    def get(self):
        return self.size
    class Lid:
        def open(self):
            return True
    def get(self, other):
        return other

async def later():
    pass
'''


def test_units_are_functions_class_lines_and_the_statements_outside_functions():
    found = tool.units(ast.parse(MODULE))
    assert sorted(found) == ["<module> (statements outside functions)", "Box (class line)", "Box (statements outside functions)", "Box.Lid (class line)",
                             "Box.Lid (statements outside functions)", "Box.Lid.open", "Box.get", "Box.get#2", "later", "top"]
    assert ast.unparse(found["<module> (statements outside functions)"]) == "import os\nLIMIT = 3"
    assert ast.unparse(found["Box (class line)"]) == "@decorated\nclass Box(Base):\n    pass"
    assert ast.unparse(found["Box (statements outside functions)"]) == "size = 1"
    assert "def inner(b)" in ast.unparse(found["top"])                                # a function inside a function belongs to it
    assert ast.unparse(found["Box.get#2"]).startswith("def get(self, other)")
    assert isinstance(found["later"], ast.AsyncFunctionDef)


@pytest.mark.parametrize("name, owner", [("f", None), ("A.f", "A"), ("A.B.f", "A.B"), ("A (class line)", None), ("A.B (class line)", "A"),
                                         ("<module> (statements outside functions)", None), ("A (statements outside functions)", "A"),
                                         ("A.B (statements outside functions)", "A.B")])
def test_owner_class(name, owner):
    assert tool.owner_class(name) == owner


# --------------------------------------------------------------------------- #
# a change cut into pieces
# --------------------------------------------------------------------------- #
def cut(before: str, after: str):
    return tool.pieces_of(ast.parse(before).body[0], ast.parse(after).body[0])


def test_one_changed_place_is_one_piece():
    before = "def f(a, b):\n    if a <= b:\n        return a\n    return b\n"
    after = before.replace("<=", "<")
    assert cut(before, after) == [(normal(before), normal(after))]


def test_two_changed_places_are_two_pieces_each_with_the_other_already_made():
    before = "def f(a, b):\n    if a <= b:\n        return a\n    return b\n"
    after = "def f(a, b):\n    if a < b:\n        return a\n    return b + 1\n"
    pieces = cut(before, after)
    assert sorted(pieces) == sorted([(normal(after.replace("<", "<=")), normal(after)), (normal(after.replace("b + 1", "b")), normal(after))])


def test_statements_put_in_and_taken_out_are_one_piece_each():
    before = "def f(a):\n    a.sort()\n    x = a[0]\n    return x\n"
    after = "def f(a):\n    x = a[0]\n    check(x)\n    log(x)\n    return x\n"
    pieces = cut(before, after)
    assert len(pieces) == 3
    assert {pre for pre, _ in pieces} == {normal("def f(a):\n    a.sort()\n    x = a[0]\n    check(x)\n    log(x)\n    return x\n"),
                                           normal("def f(a):\n    x = a[0]\n    log(x)\n    return x\n"),
                                           normal("def f(a):\n    x = a[0]\n    check(x)\n    return x\n")}
    assert {post for _, post in pieces} == {normal(after)}


def test_arguments_and_elements_are_compared_place_by_place_and_statements_by_what_they_are():
    assert len(cut("def f(a, b):\n    return g(a, b, 1)\n", "def f(a, b):\n    return g(b, a, 1)\n")) == 2
    assert len(cut("def f(a, b):\n    return [a, b, 1]\n", "def f(a, b):\n    return [a, b, 1, 2]\n")) == 1
    # two statements changing places: one taken out, one put in -- not two statements each rewritten
    swapped = cut("def f(a):\n    a.sort()\n    a.reverse()\n    return a\n", "def f(a):\n    a.reverse()\n    a.sort()\n    return a\n")
    assert len(swapped) == 2


def test_a_name_a_constant_or_an_attribute_changed_is_the_whole_node():
    assert len(cut("def f(a):\n    return a.lower()\n", "def f(a):\n    return a.upper()\n")) == 1
    assert len(cut("def f(a):\n    return g(a, 1)\n", "def f(a):\n    return h(a, 2)\n")) == 2
    assert len(cut("def f(a):\n    return a.x.lower()\n", "def f(a):\n    return a.y.upper()\n")) == 1       # the outer attribute differs: one place


def test_something_wrapped_around_or_taken_off_is_one_piece():
    assert len(cut("def f(w, h):\n    return w * h + 1\n", "def f(w, h):\n    return w * h\n")) == 1
    assert len(cut("def f(x):\n    return g(x)\n", "def f(x):\n    return h(g(x))\n")) == 1
    assert len(cut("def f(x):\n    return x.a.b\n", "def f(x):\n    return x.a\n")) == 1
    wrapped = cut("def f(x):\n    if x:\n        go(x)\n", "def f(x):\n    if ready:\n        if x:\n            go(x)\n")
    assert len(wrapped) == 1


def test_a_statement_or_expression_written_anew_is_one_piece():
    assert len(cut("def f(a, b):\n    x = compute(a)\n    return x\n", "def f(a, b):\n    y = other(b, 3)\n    return x\n")) == 1
    assert len(cut("def f(a):\n    return first(a, 1) + 2\n", "def f(a):\n    return other.thing[a] + 2\n")) == 1
    # the same shape with most of it kept is looked into: two places
    assert len(cut("def f(a, b):\n    x = compute(a, b, 1)\n    return x\n", "def f(a, b):\n    x = compute(b, b, 2)\n    return x\n")) == 2
    assert tool.REWRITTEN_BELOW == 0.5


def test_something_where_nothing_was_is_one_piece():
    assert len(cut("def f(a):\n    return\n", "def f(a):\n    return a\n")) == 1
    assert len(cut("def f(a):\n    return a\n", "def f(a) -> int:\n    return a\n")) == 1


def test_a_parameter_added_with_its_default_is_two_pieces():
    pieces = cut("def f(a):\n    return a\n", "def f(a, b=1):\n    return a\n")
    assert len(pieces) == 2
    assert all(post == normal("def f(a, b=1):\n    return a\n") for _, post in pieces)


def test_a_body_emptied_on_the_way_gets_pass():
    before = "def f(a):\n    if a:\n        a.pop()\n    return a\n"
    after = "def f(a):\n    if a:\n        a.clear()\n        a.sort()\n    return a\n"
    pieces = cut(before, after)                                # replace of unequal length: one taken out, two put in
    assert len(pieces) == 3
    for pre, post in pieces:
        ast.parse(pre)
        assert post == normal(after)


def test_the_pieces_add_up_to_the_change():
    before = "def f(a, b, c):\n    x = a + b\n    for i in c:\n        x += i\n    if x > 10:\n        return x\n    return 0\n"
    after = "def f(a, b, c, d=None):\n    x = a - b\n    for i in sorted(c):\n        x += i * 2\n        log(i)\n    return max(x, 0)\n"
    unit_before, unit_after = ast.parse(before).body[0], ast.parse(after).body[0]
    count = tool._Count()
    assert kinds.key(tool._merge(unit_before, unit_after, lambda i: False, count)) == kinds.key(unit_before)
    assert kinds.key(tool._merge(unit_before, unit_after, lambda i: True, tool._Count())) == kinds.key(unit_after)
    pieces = tool.pieces_of(unit_before, unit_after)
    assert len(pieces) == count.n >= 6
    assert ast.unparse(unit_before) == normal(before) and ast.unparse(unit_after) == normal(after)      # neither tree was touched


def test_no_change_is_no_piece_and_too_many_places_are_only_counted():
    same = "def f(a):\n    return a\n"
    assert cut(same, same) == []
    before = "def f():\n" + "".join(f"    x{i} = {i}\n" for i in range(12))
    after = "def f():\n" + "".join(f"    x{i} = {i + 100}\n" for i in range(12))
    assert tool.pieces_of(ast.parse(before).body[0], ast.parse(after).body[0], limit=5) == 12
    assert len(tool.pieces_of(ast.parse(before).body[0], ast.parse(after).body[0], limit=12)) == 12


# --------------------------------------------------------------------------- #
# one file of one fix
# --------------------------------------------------------------------------- #
BEFORE = '''
LIMIT = 3

def keep(a):
    return a

def first(xs):
    return xs[1]

class Box:
    size = 1
    def get(self):
        return self.size
    def old(self):
        return 0
'''
AFTER = '''
LIMIT = 4

def keep(a):
    return a

def first(xs):
    return xs[0]

def brand_new(x):
    return x

class Box:
    size = 1
    def get(self):
        return self.size + 1

class Fresh:
    kind = "new"
    def make(self):
        return 1
'''


def test_fix_as_pieces_names_the_units_that_changed_and_what_was_added_and_removed():
    out = tool.fix_as_pieces(BEFORE, AFTER)
    assert out["readable"] is True
    assert out["units_changed"] == ["<module> (statements outside functions)", "Box.get", "first"]
    assert [(p["unit"], p["pre"], p["post"]) for p in out["pieces"]] == [
        ("<module> (statements outside functions)", "LIMIT = 3", "LIMIT = 4"),
        ("Box.get", "def get(self):\n    return self.size", "def get(self):\n    return self.size + 1"),
        ("first", "def first(xs):\n    return xs[1]", "def first(xs):\n    return xs[0]")]
    # the new class counts once (by its class line), not once more for each thing inside it
    assert [d["unit"] for d in out["definitions_added"]] == ["Fresh (class line)", "brand_new"]
    assert [d["unit"] for d in out["definitions_removed"]] == ["Box.old"]
    assert out["units_changed_in_too_many_places"] == {}


def test_fix_as_pieces_says_when_a_file_is_not_python_3():
    assert tool.fix_as_pieces("print 'old'\n", "print('new')\n") == {"readable": False, "why": "SyntaxError"}


def test_only_layout_and_comments_changed_is_no_piece():
    out = tool.fix_as_pieces("def f(a):\n    return a  # one\n", "def f( a ):\n\n    return (a)  # two\n")
    assert out["pieces"] == [] and out["units_changed"] == []


# --------------------------------------------------------------------------- #
# stand-in tasks
# --------------------------------------------------------------------------- #
def hunk(before: str, after: str) -> str:
    import difflib
    lines = list(difflib.unified_diff(before.split("\n"), after.split("\n"), lineterm="", n=3))
    return "\n".join(lines[2:])


def pull(task: str, repo: str, files: dict[str, tuple[str, str]], extra: list[dict] | None = None) -> dict:
    rows = [{"path": path, "status": "modified", "patch": hunk(before, after), "before": before, "is_test": False, "is_python": True}
            for path, (before, after) in files.items()]
    return {"instance_id": task, "repo": repo, "files": rows + list(extra or [])}


LE = "def below(xs, top):\n    out = []\n    for x in xs:\n        if x <= top:\n            out.append(x)\n    return out\n"
LE2 = "def under(values, limit):\n    n = 0\n    for v in values:\n        if v <= limit:\n            n += 1\n    return n\n"
ODD = "def pick(rows):\n    return rows[1]\n"
TWO = "def area(w, h):\n    if w <= h:\n        return w * w\n    return w * h + 1\n"

PULLS = [
    pull("one__a-1", "one/a", {"pkg/a.py": (LE, LE.replace("<=", "<"))}),
    pull("one__a-2", "one/a", {"pkg/b.py": (LE2, LE2.replace("<=", "<"))}),
    pull("two__b-3", "two/b", {"lib/c.py": (ODD, ODD.replace("rows[1]", "rows[-1].value"))}),
    pull("two__b-4", "two/b", {"lib/d.py": (TWO, TWO.replace("w <= h", "w < h").replace("w * h + 1", "w * h"))},
         extra=[{"path": "docs/notes.rst", "status": "modified", "patch": "@@ -1 +1 @@\n-a\n+b", "is_test": False, "is_python": False},
                {"path": "tests/test_d.py", "status": "modified", "patch": "@@ -1 +1 @@\n-a\n+b", "is_test": True, "is_python": True}]),
]


@pytest.fixture(scope="module")
def measured():
    tasks = [tool.task_from_pull_request(record) for record in PULLS]
    return tasks, tool.measure(tasks)


def test_a_task_is_read_as_its_python_pieces_outside_tests(measured):
    tasks, _ = measured
    assert [(t["task"], t["repo"], len(t["pieces"]), t["files_python"], t["files_not_python"], t["problems"]) for t in tasks] == [
        ("one__a-1", "one/a", 1, 1, 0, []), ("one__a-2", "one/a", 1, 1, 0, []), ("two__b-3", "two/b", 1, 1, 0, []), ("two__b-4", "two/b", 2, 1, 1, [])]
    assert tasks[0]["pieces"][0] == {"where": "pkg/a.py::below", "pre": normal(LE), "post": normal(LE.replace("<=", "<"))}
    assert sorted(p["pre"] for p in tasks[3]["pieces"]) == sorted([normal(TWO.replace("w * h + 1", "w * h")), normal(TWO.replace("w <= h", "w < h"))])


def test_the_same_task_again_makes_every_piece(measured):
    _, out = measured
    for row in out["per_task"].values():
        for piece in row["pieces"]:
            assert piece["the_same_task_again"]["answer"] == tool.MADE
            assert piece["the_same_task_again"]["programs"] == 1


def test_a_piece_seen_in_another_task_is_made_and_one_never_seen_is_not(measured):
    _, out = measured
    below = out["per_task"]["one__a-1"]["pieces"][0]
    assert below["other_tasks"]["answer"] == tool.MADE and below["other_tasks"]["programs"] == 1
    assert below["other_tasks"]["openness"] == kinds.NAMES_OPEN                 # x <= top and v <= limit: the same once names are open
    assert below["other_tasks"]["operator"].startswith("replace: __N0__ <= __N1__  ->  __N0__ < __N1__")
    pick = out["per_task"]["two__b-3"]["pieces"][0]
    assert pick["other_tasks"] == {"answer": tool.NEVER} and pick["other_repositories"] == {"answer": tool.NEVER}
    area = {p["other_tasks"]["answer"] for p in out["per_task"]["two__b-4"]["pieces"]}
    assert area == {tool.MADE, tool.NEVER}                                      # the comparison was seen elsewhere, taking "+ 1" off was not


def test_lessons_of_other_repositories_are_asked_apart(measured):
    _, out = measured
    below = out["per_task"]["one__a-1"]["pieces"][0]
    assert below["other_repositories"]["answer"] == tool.MADE                   # two/b has the same comparison change
    assert below["other_repositories"]["openness"] == kinds.NAMES_OPEN
    only = [tool.task_from_pull_request(record) for record in PULLS[:3]]
    alone = tool.measure(only)["per_task"]["one__a-1"]["pieces"][0]
    assert alone["other_tasks"]["answer"] == tool.MADE and alone["other_repositories"] == {"answer": tool.NEVER}


def test_a_tasks_own_other_pieces_do_not_count_as_seen_before():
    twice = "def f(a, b, c, d):\n    if a <= b:\n        return 1\n    if c <= d:\n        return 2\n    return 0\n"
    record = pull("solo__x-1", "solo/x", {"m.py": (twice, twice.replace("<=", "<"))})
    out = tool.measure([tool.task_from_pull_request(record)])
    pieces = out["per_task"]["solo__x-1"]["pieces"]
    assert len(pieces) == 2
    assert all(p["other_tasks"] == {"answer": tool.NEVER} and p["the_same_task_again"]["answer"] == tool.MADE for p in pieces)


def test_an_operator_too_loose_to_apply_is_said_apart_from_never_seen(monkeypatch):
    big = "def f(" + ", ".join(f"v{i}" for i in range(30)) + "):\n" + "".join(f"    t{i} = v{i}\n" for i in range(30)) + "    return t0\n"
    small = "def g(p, q):\n    r = p\n    return r\n"
    records = [pull("x__x-1", "x/x", {"a.py": (big, big.replace("t3 = v3", "t3 = v4"))}),
               pull("y__y-2", "y/y", {"b.py": (small, small.replace("r = p", "r = q"))})]
    out = tool.measure([tool.task_from_pull_request(r) for r in records])
    in_big = out["per_task"]["x__x-1"]["pieces"][0]["other_tasks"]
    in_small = out["per_task"]["y__y-2"]["pieces"][0]["other_tasks"]
    # "a name becomes another name of the function": 2 programs in the small function (p becomes q or r), thousands in the big one
    assert in_small["answer"] == tool.MADE and in_small["openness"] == kinds.FROM_THE_PLACE and in_small["programs"] == 2
    assert in_big == {"answer": tool.TOO_LOOSE}


def test_whole_things_are_seen_before_only_when_the_same_thing_was_added_elsewhere():
    grow = BEFORE.replace("def keep", "def helper():\n    return 1\n\ndef keep")
    records = [pull("x__x-1", "x/x", {"a.py": (BEFORE, grow)}), pull("y__y-2", "y/y", {"b.py": (BEFORE, grow)}),
               pull("z__z-3", "z/z", {"c.py": (BEFORE, BEFORE.replace("def keep", "def another():\n    return 2\n\ndef keep"))})]
    out = tool.measure([tool.task_from_pull_request(r) for r in records])
    assert out["per_task"]["x__x-1"]["whole_things"] == [{"what": "definition added", "where": "a.py::helper", "seen_in_another_task": True}]
    assert out["per_task"]["z__z-3"]["whole_things"] == [{"what": "definition added", "where": "c.py::another", "seen_in_another_task": False}]


def test_files_added_removed_moved_and_broken_are_told_apart():
    record = {"instance_id": "x__x-1", "repo": "x/x", "files": [
        {"path": "new.py", "status": "added", "patch": "@@ -0,0 +1 @@\n+x = 1", "is_test": False, "is_python": True},
        {"path": "gone.py", "status": "removed", "patch": "@@ -1 +0,0 @@\n-x = 1", "before": "x = 1\n", "is_test": False, "is_python": True},
        {"path": "moved.py", "status": "renamed", "previous": "was.py", "patch": None, "before": "x = 1\n", "is_test": False, "is_python": True},
        {"path": "lost.py", "status": "modified", "patch": "@@ -1 +1 @@\n-x = 1\n+x = 2", "before": None, "is_test": False, "is_python": True},
        {"path": "wrong.py", "status": "modified", "patch": "@@ -1 +1 @@\n-y = 1\n+y = 2", "before": "x = 1\n", "is_test": False, "is_python": True},
        {"path": "old.py", "status": "modified", "patch": "@@ -1 +1 @@\n-print 'a'\n+print 'b'", "before": "print 'a'\n", "is_test": False, "is_python": True}]}
    task = tool.task_from_pull_request(record)
    assert [(t["what"], t["where"]) for t in task["whole_things"]] == [("file added", "new.py"), ("file removed", "gone.py")]
    assert task["files_python"] == 6 and task["pieces"] == []
    assert task["problems"] == ["lost.py: the file before or its hunks are missing", "wrong.py: the file does not have the lines of the hunk at line 1",
                                "old.py: not readable as Python 3 (SyntaxError)"]
    assert tool.task_from_pull_request({"instance_id": "y__y-2", "repo": "y/y", "error": "404"})["problems"] == ["the pull request could not be fetched"]


def test_hunks_found_at_another_line_are_counted():
    shifted = "# a line the branch gained\n" + LE
    record = pull("x__x-1", "x/x", {"a.py": (LE, LE.replace("<=", "<"))})
    record["files"][0]["before"] = shifted
    task = tool.task_from_pull_request(record)
    assert task["hunks_found_at_another_line"] == 1 and len(task["pieces"]) == 1 and task["problems"] == []


# --------------------------------------------------------------------------- #
# what it came to
# --------------------------------------------------------------------------- #
def test_summarise_counts_pieces_and_tasks(measured):
    _, out = measured
    summary = tool.summarise(out["per_task"])
    assert (summary["tasks"], summary["tasks_counted"], summary["pieces"], summary["whole_things"]) == (4, 4, 5, {})
    assert summary["tasks_that_also_change_files_that_are_not_python"] == 1
    assert summary["pieces_and_whole_things_per_task"] == {"least": 1, "middle": 1, "most": 2, "tasks_with_one": 3, "tasks_with_at_most_three": 4,
                                                           "tasks_with_more_than_ten": 0}
    again = summary["the_same_task_again"]
    assert (again["pieces_made_exactly"], again["of_pieces"], again["tasks_with_every_piece_made_exactly"], again["of_tasks"]) == (5, 5, 4, 4)
    others = summary["other_tasks"]
    assert (others["pieces_made_exactly"], others["pieces_never_seen"], others["pieces_only_by_an_operator_too_loose_to_apply"]) == (3, 2, 0)
    assert others["pieces_made_by_how_exact_the_operator_is"] == {"names_open": 3}
    assert others["pieces_made_as_one_of_at_most"] == {"1": 3, "10": 3, "100": 3, "300": 3}
    assert others["tasks_with_every_piece_made_exactly"] == 2                   # the two tasks whose whole fix is the comparison
    assert others["tasks_with_every_piece_made_by_an_exact_or_names_open_operator"] == 2
    assert others["tasks_with_pieces_of_which_none_is_made"] == 1 and others["tasks_with_no_piece_only_whole_things"] == 0
    assert others["whole_fixes_to_try_where_every_piece_is_made"] == {"tasks": 2, "middle": 1, "one": 2, "at_most_10": 2, "at_most_1000": 2, "more_than_a_million": 0}
    assert others["operators_that_made_the_most_pieces"] == [{"operator": "replace: __N0__ <= __N1__  ->  __N0__ < __N1__", "pieces": 3}]
    assert summary["other_repositories"]["pieces_made_exactly"] == 3
    assert summary["by_repository"] == {
        "one/a": {"tasks": 2, "pieces": 2, "pieces_made_exactly_from_other_tasks": 2, "tasks_with_every_piece_made_exactly_from_other_tasks": 2},
        "two/b": {"tasks": 2, "pieces": 3, "pieces_made_exactly_from_other_tasks": 1, "tasks_with_every_piece_made_exactly_from_other_tasks": 0}}


def test_summarise_leaves_out_tasks_with_a_problem_and_names_them():
    per_task = {"a": {"repo": "r", "pieces": [], "whole_things": [], "files_python": 1, "files_not_python": 0, "problems": ["x"]},
                "b": {"repo": "r", "pieces": [], "whole_things": [], "files_python": 0, "files_not_python": 2, "problems": []},
                "c": {"repo": "r", "pieces": [], "whole_things": [{"what": "definition added", "where": "m.py::f", "seen_in_another_task": False}],
                      "files_python": 1, "files_not_python": 0, "problems": []}}
    summary = tool.summarise(per_task)
    assert summary["tasks_with_a_problem"] == ["a"] and summary["tasks_whose_fix_has_no_python_change_outside_tests"] == ["b"]
    assert summary["tasks_counted"] == 1 and summary["whole_things"] == {"definition added": 1} and summary["tasks_with_a_whole_thing"] == 1
    assert summary["other_tasks"]["tasks_with_every_piece_made_exactly"] == 0     # a definition nobody else added is not seen before
    assert summary["the_same_task_again"]["tasks_with_every_piece_made_exactly"] == 1
    assert summary["other_tasks"]["tasks_with_pieces_of_which_none_is_made"] == 0 and summary["other_tasks"]["tasks_with_no_piece_only_whole_things"] == 1


def test_a_whole_fix_is_as_many_tries_as_its_pieces_multiply_to():
    def made(programs):
        return {"answer": tool.MADE, "programs": programs, "openness": kinds.FROM_THE_PLACE, "surroundings": "alone", "operator": "o"}
    piece = lambda n: {"where": "m.py::f", "the_same_task_again": made(1), "other_tasks": made(n), "other_repositories": {"answer": tool.NEVER}}  # noqa: E731
    per_task = {"a": {"repo": "r", "pieces": [piece(200), piece(150), piece(100)], "whole_things": [], "files_python": 1, "files_not_python": 0, "problems": []},
                "b": {"repo": "r", "pieces": [piece(4), piece(2)], "whole_things": [], "files_python": 1, "files_not_python": 0, "problems": []}}
    cell = tool.summarise(per_task)["other_tasks"]
    assert cell["whole_fixes_to_try_where_every_piece_is_made"] == {"tasks": 2, "middle": 3000000, "one": 0, "at_most_10": 1, "at_most_1000": 1, "more_than_a_million": 1}
    assert cell["tasks_with_every_piece_made_as_one_of_at_most_10"] == 1
    assert cell["tasks_with_every_piece_made_by_an_exact_or_names_open_operator"] == 0
    assert cell["pieces_made_as_one_of_at_most"] == {"1": 0, "10": 2, "100": 3, "300": 5}


# --------------------------------------------------------------------------- #
# the command line
# --------------------------------------------------------------------------- #
def test_main_reads_the_pull_requests_and_writes_the_record(tmp_path, capsys):
    where = tmp_path / "pulls"
    where.mkdir()
    for record in PULLS:
        (where / f"{record['instance_id']}.json").write_text(json.dumps(record))
    assert tool.main(["--pull-requests-dir", str(where), "--out", str(tmp_path / "out.json")]) == 0
    record = json.loads((tmp_path / "out.json").read_text())
    assert (record["schema"], record["authority"], record["model_calls"]) == (tool.SCHEMA, tool.AUTHORITY, 0)
    assert record["summary"]["tasks_counted"] == 4 and record["summary"]["other_tasks"]["pieces_made_exactly"] == 3
    assert sorted(record["per_task"]) == ["one__a-1", "one__a-2", "two__b-3", "two__b-4"]
    assert record["programs_one_operator_may_make_of_one_function"] == kinds.MAX_CANDIDATES_OF_ONE
    assert len(record["pull_requests_sha256"]) == 64 and set(record["code_sha256"]) == {
        "canonical/runtime/edit_kind_learning_v1.py", "canonical/tools/expert_fix_repetition_measure_v1.py"}
    assert "4 tasks read as pieces" in capsys.readouterr().out
    assert tool.main(["--pull-requests-dir", str(where), "--out", str(tmp_path / "some.json"), "--tasks", "one__a-1", "two__b-3"]) == 0
    assert sorted(json.loads((tmp_path / "some.json").read_text())["per_task"]) == ["one__a-1", "two__b-3"]


# --------------------------------------------------------------------------- #
# the collector, with a stand-in for api.github.com
# --------------------------------------------------------------------------- #
from canonical.tools import expert_fix_pull_request_collector_v1 as collector  # noqa: E402


@pytest.mark.parametrize("repo, path, test", [
    ("django/django", "django/db/models/query.py", False), ("django/django", "tests/queries/tests.py", True),
    ("django/django", "django/test/client.py", True), ("sympy/sympy", "sympy/core/tests/test_basic.py", True),
    ("sympy/sympy", "sympy/utilities/runtests.py", True), ("scikit-learn/scikit-learn", "sklearn/utils/testing.py", True),
    ("pytest-dev/pytest", "src/_pytest/capture.py", False), ("pytest-dev/pytest", "src/_pytest/unittest.py", False),
    ("pytest-dev/pytest", "testing/test_capture.py", True), ("psf/requests", "requests/models.py", False)])
def test_what_counts_as_a_test_file(repo, path, test):
    assert collector.is_test(repo, path) is test


@pytest.mark.parametrize("name, expected", [("django__django-11099", ("django", "django", 11099)),
                                            ("scikit-learn__scikit-learn-10297", ("scikit-learn", "scikit-learn", 10297)),
                                            ("pytest-dev__pytest-5262", ("pytest-dev", "pytest", 5262)), ("a__b__c-7", ("a", "b__c", 7))])
def test_a_task_name_is_owner_repository_and_pull_request(name, expected):
    assert collector.parts(name) == expected


def test_a_text_that_is_no_task_name():
    with pytest.raises(ValueError):
        collector.parts("django-11099")


class Github:
    """Answers the three questions the collector asks, from a table; keeps what was asked."""

    def __init__(self, files, contents, pages=None):
        self.files, self.contents, self.pages, self.asked = files, contents, pages, []

    def __call__(self, path, raw=False):
        self.asked.append((path, raw))
        if path.endswith("/pulls/7"):
            return json.dumps({"base": {"sha": "abc123"}, "merged": True, "state": "closed", "merge_commit_sha": "def456", "title": "Fix it",
                               "changed_files": len(self.files)}).encode()
        if "/pulls/7/files" in path:
            page = int(path.rsplit("page=", 1)[1])
            size = collector.PAGE
            return json.dumps(self.files[(page - 1) * size:page * size]).encode()
        if "/contents/" in path:
            name = path.split("/contents/", 1)[1].split("?ref=")[0]
            assert path.endswith("?ref=abc123") and raw
            if name not in self.contents:
                raise RuntimeError("Not Found")
            return self.contents[name].encode()
        raise AssertionError(path)


def test_collect_keeps_the_fix_and_the_files_as_they_were():
    files = [{"filename": "pkg/a.py", "status": "modified", "patch": "@@ -1 +1 @@\n-x = a[0][1]\n+x = a[1][0]", "additions": 1, "deletions": 1},
             {"filename": "tests/test_a.py", "status": "modified", "patch": "@@ -1 +1 @@\n-a\n+b"},
             {"filename": "docs/a.rst", "status": "added", "patch": "@@ -0,0 +1 @@\n+text"},
             {"filename": "pkg/new.py", "status": "added", "patch": "@@ -0,0 +1 @@\n+y = 1"},
             {"filename": "pkg/moved.py", "status": "renamed", "previous_filename": "pkg/was.py", "patch": "@@ -1 +1 @@\n-z = 1\n+z = 2"},
             {"filename": "pkg/lost.py", "status": "modified", "patch": "@@ -1 +1 @@\n-q = 1\n+q = 2"}]
    github = Github(files, {"pkg/a.py": "x = a[0][1]\n", "pkg/was.py": "z = 1\n"})
    record = collector.collect("own__proj-7", github)
    assert {k: record[k] for k in ("schema", "instance_id", "repo", "pull", "base_sha", "merged", "changed_files")} == {
        "schema": collector.SCHEMA, "instance_id": "own__proj-7", "repo": "own/proj", "pull": 7, "base_sha": "abc123", "merged": True, "changed_files": 6}
    rows = {r["path"]: r for r in record["files"]}
    assert rows["pkg/a.py"]["before"] == "x = a[0][1]\n" and rows["pkg/a.py"]["patch"] == "@@ -1 +1 @@\n-x = a[0][1]\n+x = a[1][0]"   # '][' untouched
    assert rows["pkg/a.py"]["is_test"] is False and rows["pkg/a.py"]["is_python"] is True
    assert rows["tests/test_a.py"]["is_test"] is True and "before" not in rows["tests/test_a.py"]
    assert rows["docs/a.rst"]["is_python"] is False and "before" not in rows["docs/a.rst"]
    assert "before" not in rows["pkg/new.py"]                                    # it did not exist before
    assert rows["pkg/moved.py"]["before"] == "z = 1\n" and rows["pkg/moved.py"]["previous"] == "pkg/was.py"
    assert rows["pkg/lost.py"]["before"] is None and "Not Found" in rows["pkg/lost.py"]["fetch_error"]
    assert "error" not in record
    # and what it kept reads as a task
    task = tool.task_from_pull_request(record)
    assert [p["where"] for p in task["pieces"]] == ["pkg/a.py::<module> (statements outside functions)"] * 2 + [
        "pkg/moved.py::<module> (statements outside functions)"]                  # the two indexes changed places: two pieces
    assert task["problems"] == ["pkg/lost.py: the file before or its hunks are missing"]


def test_collect_asks_for_every_page_of_changed_files():
    files = [{"filename": f"docs/{n}.rst", "status": "added", "patch": None} for n in range(collector.PAGE + 3)]
    github = Github(files, {})
    record = collector.collect("own__proj-7", github)
    assert len(record["files"]) == collector.PAGE + 3
    assert [path for path, _ in github.asked if "/files" in path] == [f"repos/own/proj/pulls/7/files?per_page={collector.PAGE}&page=1",
                                                                     f"repos/own/proj/pulls/7/files?per_page={collector.PAGE}&page=2"]
    exactly = Github(files[:collector.PAGE], {})
    collector.collect("own__proj-7", exactly)
    assert len([1 for path, _ in exactly.asked if "/files" in path]) == 2          # a full page: one more is asked for, and it is empty


def test_collect_says_when_the_pull_request_cannot_be_had():
    def nothing(path, raw=False):
        raise RuntimeError("HTTP 404: Not Found")
    record = collector.collect("own__proj-7", nothing)
    assert "Not Found" in record["error"] and "files" not in record
    assert tool.task_from_pull_request(record)["problems"] == ["the pull request could not be fetched"]


def test_collector_main_writes_one_file_per_task_and_does_not_fetch_twice(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(collector, "collect", lambda name: calls.append(name) or {"instance_id": name, "files": []})
    ids = tmp_path / "ids.json"
    ids.write_text(json.dumps(["a__b-1", "a__b-2"]))
    assert collector.main(["--ids-file", str(ids), "--out-dir", str(tmp_path / "out"), "--workers", "1"]) == 0
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["a__b-1.json", "a__b-2.json"] and sorted(calls) == ["a__b-1", "a__b-2"]
    assert collector.main(["--ids-file", str(ids), "--out-dir", str(tmp_path / "out"), "--workers", "1"]) == 0
    assert len(calls) == 2
    monkeypatch.setattr(collector, "collect", lambda name: {"instance_id": name, "error": "x"})
    ids.write_text(json.dumps(["a__b-3"]))
    assert collector.main(["--ids-file", str(ids), "--out-dir", str(tmp_path / "out"), "--workers", "1"]) == 1
