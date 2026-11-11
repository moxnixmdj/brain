"""A task shown once becomes a skill only if replaying it cannot destroy what it never read.

Measured 2026-11-11 through the front door (`live_brain_route_admission_v1.solve`), before this file:

* A rename shown as *the file after the rename* compiled into "replace the named file with the
  taught file". It passed the held-out run, the sabotage control and the ownership gate, because
  its postcondition -- "the file contains `def <new name>(`" -- was true of the taught file too.
  Asked to rename a routine in another file, the door replaced that file and answered PASS.
* The same rename shown as *a program* did the right thing on a new file -- on the host, with the
  caller's whole account: `solve_v1.act` could not import the sandbox from a package import and
  fell back, and the receipt said `confined: False`.

The rules pinned here:

1. A generalized `write_text` may create a file, fill an empty one, write the same text again, or
   update a file this same step wrote before. It may not replace anything else.
2. The rule holds where a skill is qualified (the second instance's world) and where it is recalled.
3. A taught program runs inside the namespace sandbox or it does not run, and that is decided before
   any earlier step has written anything.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as C

SHAPES = "import math\n\ndef area(r):\n    return math.pi * r * r\n\ndef twice(r):\n    return 2 * area(r)\n"
GEOM = "def area(w, h):\n    return w * h\n\ndef perimeter(w, h):\n    return 2 * (w + h)\n"
LEDGER = "def total(xs):\n    return sum(xs)\n\ndef mean(xs):\n    return total(xs) / len(xs)\n"
STORE = ("CACHE = {}\n\ndef load(key):\n    return CACHE.get(key)\n\n"
         "def load_many(keys):\n    return [load(k) for k in keys]\n")

RENAME_PROGRAM = (
    "import re, pathlib\n"
    "p = pathlib.Path('shapes.py')\n"
    "s = p.read_text()\n"
    "p.write_text(re.sub(r'\\b' + 'area' + r'\\b', 'surface', s))\n"
)


def _renamed(source: str, old: str, new: str) -> str:
    return re.sub(rf"\b{old}\b", new, source)


def _world(path: pathlib.Path, **files: str) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (path / name.replace("__", ".")).write_text(text)
    return path


def _teach_the_rename_as_the_edited_file(db: pathlib.Path, second_world: pathlib.Path) -> dict:
    return C.compile_and_qualify_skill(
        goal="relabel the routine 'area' as 'surface' in shapes.py",
        trace=[{"layer": "python_file_op", "op": "write_text", "path": "shapes.py",
                "content": _renamed(SHAPES, "area", "surface")}],
        postcondition={"kind": "file_contains", "path": "shapes.py", "contains": "def surface("},
        heldout_goal="relabel the routine 'area' as 'extent' in geom.py",
        heldout_cwd=second_world,
        db_path=db,
    )


def _teach_the_note(db: pathlib.Path) -> dict:
    """A task that really is 'create this file': every byte comes from the request."""
    return C.compile_and_qualify_skill(
        goal="leave the note 'ship on friday' in handover.txt",
        trace=[{"layer": "python_file_op", "op": "write_text", "path": "handover.txt",
                "content": "note: ship on friday\n"}],
        postcondition={"kind": "file_contains", "path": "handover.txt", "contains": "note: ship on friday"},
        heldout_goal="leave the note 'call the bank' in reminder.txt",
        db_path=db,
    )


# --------------------------------------------------------------------------- the wrong pass


def test_an_edit_shown_as_the_edited_file_is_not_accepted_as_a_skill(tmp_path: pathlib.Path) -> None:
    second = _world(tmp_path / "second", geom__py=GEOM)

    res = _teach_the_rename_as_the_edited_file(tmp_path / "w.sqlite", second)

    assert res["pass"] is False, res
    assert res["status"] == "FAIL_CLOSED__HELDOUT_WOULD_REPLACE_CONTENT_THE_SKILL_NEVER_READ", res
    assert res["path"] == "geom.py"
    # Refused before anything ran: the second instance's file is still the second instance's file.
    assert (second / "geom.py").read_text() == GEOM
    assert C.recall_and_execute_workflow(
        "relabel the routine 'area' as 'region' in geom.py", cwd=second, db_path=tmp_path / "w.sqlite") is None
    assert (second / "geom.py").read_text() == GEOM


def test_a_skill_taught_in_an_empty_world_cannot_replace_a_file_it_meets_later(tmp_path: pathlib.Path) -> None:
    """The second instance's world held no file, so the skill qualified as 'create'. Then it met one."""
    db = tmp_path / "w.sqlite"
    res = _teach_the_rename_as_the_edited_file(db, _world(tmp_path / "second"))
    assert res["pass"] is True, res

    world = _world(tmp_path / "world", geom__py=GEOM)
    recalled = C.recall_and_execute_workflow(
        "relabel the routine 'area' as 'region' in geom.py", cwd=world, db_path=db)

    assert recalled is None, recalled
    assert (world / "geom.py").read_text() == GEOM


def test_the_guard_names_the_file_and_leaves_other_steps_alone(tmp_path: pathlib.Path) -> None:
    world = _world(tmp_path, geom__py=GEOM)
    abstract = [
        {"layer": "python_file_op", "op": "append_text", "path": "?path0", "content": "x\n"},
        {"layer": "sqlite_exec", "db_path": "d.sqlite", "sql": "select 1"},
        {"layer": "python_file_op", "op": "write_text", "path": "?path0", "content": "def ?str0(r):\n    return r\n"},
    ]
    inst = C._instantiate_obj(abstract, {"?path0": "geom.py", "?str0": "region"})

    assert C.content_a_generalized_write_would_destroy(abstract, inst, cwd=world) == "geom.py"
    assert C.content_a_generalized_write_would_destroy(abstract[:2], inst[:2], cwd=world) is None


def test_a_directory_or_bytes_that_are_not_text_are_never_replaced(tmp_path: pathlib.Path) -> None:
    abstract = [{"layer": "python_file_op", "op": "write_text", "path": "?path0", "content": "note: ?str0\n"}]
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00\x01binary")
    (tmp_path / "folder").mkdir()
    for name in ("blob.bin", "folder"):
        inst = C._instantiate_obj(abstract, {"?path0": name, "?str0": "v"})
        assert C.content_a_generalized_write_would_destroy(abstract, inst, cwd=tmp_path) == name


# --------------------------------------------------------------------------- what must still work


def test_creating_filling_repeating_and_updating_are_still_possible(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "w.sqlite"
    assert _teach_the_note(db)["pass"] is True
    world = _world(tmp_path / "world", empty__txt="", blank__txt="  \n")

    def ask(text: str, name: str):
        return C.recall_and_execute_workflow(f"leave the note '{text}' in {name}", cwd=world, db_path=db)

    # create
    assert ask("first", "new.txt")["pass"] is True
    assert (world / "new.txt").read_text() == "note: first\n"
    # the same text again
    assert ask("first", "new.txt")["pass"] is True
    # update a file this same step wrote before: nothing in it was ever anybody else's
    assert ask("second", "new.txt")["pass"] is True
    assert (world / "new.txt").read_text() == "note: second\n"
    # fill a file that holds nothing
    assert ask("third", "empty.txt")["pass"] is True
    assert ask("fourth", "blank.txt")["pass"] is True
    assert (world / "blank.txt").read_text() == "note: fourth\n"


def test_a_file_somebody_else_wrote_is_not_replaced_by_the_note(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "w.sqlite"
    assert _teach_the_note(db)["pass"] is True
    diary = "monday: rain\ntuesday: sun\n"
    one_line = "password=hunter2\n"
    world = _world(tmp_path / "world", diary__txt=diary, secret__txt=one_line)

    assert C.recall_and_execute_workflow("leave the note 'x' in diary.txt", cwd=world, db_path=db) is None
    assert C.recall_and_execute_workflow("leave the note 'x' in secret.txt", cwd=world, db_path=db) is None
    assert (world / "diary.txt").read_text() == diary
    assert (world / "secret.txt").read_text() == one_line


def test_appending_is_never_a_replacement(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "w.sqlite"
    res = C.compile_and_qualify_skill(
        goal="stamp the report first.txt with the reviewer 'Omar'",
        trace=[{"layer": "python_file_op", "op": "append_text", "path": "first.txt",
                "content": "Reviewed by Omar\n"}],
        postcondition={"kind": "file_contains", "path": "first.txt", "contains": "Reviewed by Omar"},
        heldout_goal="stamp the report second.txt with the reviewer 'Sara'",
        heldout_cwd=_world(tmp_path / "second", second__txt="a report somebody wrote\n"),
        db_path=db,
    )
    assert res["pass"] is True, res

    world = _world(tmp_path / "world", third__txt="third report\n")
    recalled = C.recall_and_execute_workflow(
        "stamp the report third.txt with the reviewer 'Lina'", cwd=world, db_path=db)
    assert recalled is not None and recalled["pass"] is True
    assert (world / "third.txt").read_text() == "third report\nReviewed by Lina\n"


@pytest.mark.parametrize("template,text,expected", [
    ("note: ?str0\n", "note: hello there\n", True),
    ("note: ?str0\n", "note: \n", True),
    ("note: ?str0\n", "note: a\nb\n", False),          # a value is one line
    ("note: ?str0\n", "memo: hello\n", False),
    ("?str0=?str0\n", "a=a\n", True),
    ("?str0=?str0\n", "a=b\n", False),                 # one hole, one value
    ("?path0 -> ?str1 (?num0)\n", "x.py -> y (3)\n", True),
    ("plain text\n", "plain text\n", True),
    ("plain text\n", "plain text!\n", False),
    ("a.b ?str0\n", "aXb v\n", False),                 # the fixed part is literal, not a pattern
])
def test_what_counts_as_text_the_same_step_could_have_written(template: str, text: str, expected: bool) -> None:
    holes = re.findall(r"\?[a-z]+\d+", template)
    assert C._text_a_skill_could_have_written(template, holes, text) is expected


# --------------------------------------------------------------------------- the taught program

needs_sandbox = pytest.mark.skipif(
    C._sandbox_for_taught_programs() is None, reason="this machine cannot start the namespace sandbox")


@needs_sandbox
def test_an_edit_shown_as_a_program_is_learned_and_runs_inside_the_sandbox(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "w.sqlite"
    res = C.compile_and_qualify_skill(
        goal="relabel the routine 'area' as 'surface' in shapes.py",
        trace=[{"layer": "confined_python_exec", "code": RENAME_PROGRAM}],
        postcondition={"kind": "file_contains", "path": "shapes.py", "contains": "def surface("},
        heldout_goal="relabel the routine 'total' as 'summed' in ledger.py",
        heldout_cwd=_world(tmp_path / "second", ledger__py=LEDGER),
        db_path=db,
    )
    assert res["pass"] is True, res

    world = _world(tmp_path / "world", store__py=STORE)
    recalled = C.recall_and_execute_workflow(
        "relabel the routine 'load' as 'fetch' in store.py", cwd=world, db_path=db)

    assert recalled is not None and recalled["pass"] is True, recalled
    assert (world / "store.py").read_text() == _renamed(STORE, "load", "fetch")
    assert "load_many" in (world / "store.py").read_text()
    assert [r["confined"] for r in recalled["step_receipts"]] == [True]


@needs_sandbox
def test_a_taught_program_cannot_write_outside_the_project(tmp_path: pathlib.Path) -> None:
    project = _world(tmp_path / "project", inside__txt="x\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "marker.txt"
    program = f"open({str(marker)!r}, 'w').write('escaped')\n"

    res = C.execute_compiled_steps([{"layer": "confined_python_exec", "code": program}], cwd=project)

    assert res["ok"] is False, res
    assert not marker.exists(), "the taught program wrote outside the project it was given"


def test_without_a_sandbox_a_taught_program_is_refused_before_any_step_runs(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(C, "_sandbox_for_taught_programs", lambda: None)
    marker = tmp_path / "ran.txt"
    steps = [
        {"layer": "python_file_op", "op": "write_text", "path": "first.txt", "content": "written\n"},
        {"layer": "confined_python_exec", "code": f"open({str(marker)!r}, 'w').write('ran')\n"},
    ]

    res = C.execute_compiled_steps(steps, cwd=tmp_path)

    assert res["ok"] is False
    assert res["status"] == boundary.STATUS and res["failed_step"] == 1, res
    assert not marker.exists(), "the program ran on the host"
    assert not (tmp_path / "first.txt").exists(), "an earlier step wrote before the refusal"


@needs_sandbox
def test_act_reaches_the_sandbox_from_a_package_import(tmp_path: pathlib.Path) -> None:
    from canonical.runtime import solve_v1

    res = solve_v1.act(str(tmp_path), "print('inside')", timeout=60)

    assert res["exit"] == 0 and "inside" in res["out"], res
    assert res["confined"] is True, "act fell back to the host although a sandbox is available"
