#!/usr/bin/env python3
"""A writer acts on the files the sentence names, and on nothing else.

Two failures on 2026-11-02, both found by running a suite that had been green on
main, and both in the same class:

1. "Rename old_name to new_name in <repo>/canonical/.../lib.py." -- a Python
   SYMBOL rename -- selected `file.rename.v1` on the lexical overlap of
   "rename".  The pinned binder bound `output_path` to the stated lib.py, the
   world fallback filled `path` with an unrelated repository file
   (`.github/scripts/land_on_main.sh`), and the run MOVED that file and reported
   `output_verified: true`.  An ordinary sentence about one file renamed a
   different file, in the working tree, and PASSED.

2. "Copy <dir>/a.txt to <dir>/c.txt" bound `output_path` to
   `canonical/astra_runtime/tmp/spool_0_output.json`.  The copy landed there and
   reported success, so the destination the sentence named was never written --
   a PASS that produced no artifact where the user asked for one.

The guards that answer them are refusals, in four places, and this file pins all
four so that the cheap version of any of them (synonym matching, a synthesised
destination, a companion slot) cannot quietly return:

* the ranker does not offer a file-to-file writer for a sentence that states no
  destination file (`goal_front_compiler_v1.ranked_candidates`);
* a writing row gets no world-synthesised input at all
  (`goal_compiler._complete_inputs_via_world_binding`);
* a stated destination is never rebound to a spool artifact
  (`goal_front_compiler_v1.repair_output_collisions`);
* the adapter refuses a path the sentence does not name
  (`bound_capabilities/file_ops.py`).

The runs are real front-door runs over a world this file builds.
"""
from __future__ import annotations

import hashlib
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_composer_v1 as graph  # noqa: E402
from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime.bound_capabilities import file_ops  # noqa: E402

TMP = ROOT / "canonical/astra_runtime/tmp"
WORLD = TMP / "writer_names_its_file_v1"
UNRELATED = ROOT / ".github/scripts/land_on_main.sh"

LIB = '''"""Models."""


def norm(text, scale=1):
    return text.strip() * scale
'''


def _rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _world() -> pathlib.Path:
    if WORLD.exists():
        shutil.rmtree(WORLD)
    WORLD.mkdir(parents=True)
    (WORLD / "lib.py").write_text(LIB, encoding="utf-8")
    (WORLD / "a.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    return WORLD


def _solve(goal: str) -> dict:
    return door.solve({"task_id": "WRITER_NAMES_ITS_FILE", "goal": goal})


def _registry() -> dict:
    return graph.load_registry()


def test_a_symbol_rename_never_reaches_a_file_rename() -> None:
    _world()
    goal = "Rename norm to normalize in %s." % _rel(WORLD / "lib.py")
    before = (WORLD / "lib.py").read_bytes()
    unrelated_before = hashlib.sha256(UNRELATED.read_bytes()).hexdigest()

    ranked = [cid for _, _, cid, _ in front.ranked_candidates(goal, _registry())]
    assert "file.rename.v1" not in ranked, ranked
    assert "file.copy.v1" not in ranked, ranked

    result = _solve(goal)
    assert result.get("compiled_capability_id") != "file.rename.v1", result.get(
        "compiled_capability_id")
    # Whatever ran, no file left the working tree and nothing was moved.
    assert hashlib.sha256(UNRELATED.read_bytes()).hexdigest() == unrelated_before, (
        "a repository file the sentence never named was rewritten")
    assert sorted(p.name for p in WORLD.iterdir()) == ["a.txt", "lib.py"], (
        "a file was created or removed beside the sentence's source")
    assert (WORLD / "lib.py").exists() or result.get("pass") is True, (
        "the sentence's own file disappeared without the run succeeding")
    del before


def test_a_file_rename_still_reaches_the_file_rename() -> None:
    _world()
    compiled = front.compile_goal("Rename %s to moved.txt" % _rel(WORLD / "a.txt"),
                                  _registry(), ROOT)
    assert compiled.get("selected_capability") == "file.rename.v1", compiled.get(
        "selected_capability")
    assert compiled["inputs"]["output_path"] == _rel(WORLD / "moved.txt"), compiled["inputs"]
    assert compiled["inputs"]["path"] == _rel(WORLD / "a.txt"), compiled["inputs"]


def test_a_bare_destination_is_bound_beside_the_stated_source() -> None:
    _world()
    compiled = front.compile_goal("Copy %s to copy.txt" % _rel(WORLD / "a.txt"),
                                  _registry(), ROOT)
    assert compiled.get("selected_capability") == "file.copy.v1", compiled.get(
        "selected_capability")
    assert compiled["inputs"]["output_path"] == _rel(WORLD / "copy.txt"), compiled["inputs"]
    assert "spool" not in compiled["inputs"]["output_path"], compiled["inputs"]


def test_the_copy_lands_at_the_destination_the_sentence_named() -> None:
    _world()
    spool_before = {p.name for p in TMP.glob("spool_*")}
    result = _solve("Copy %s to copy.txt" % _rel(WORLD / "a.txt"))
    assert result.get("pass") is True, result.get("status")
    landed = WORLD / "copy.txt"
    assert landed.is_file(), "the stated destination was not written"
    assert landed.read_bytes() == (WORLD / "a.txt").read_bytes()
    invented = {p.name for p in TMP.glob("spool_*")} - spool_before
    assert not invented, "an artifact was invented beside the sentence: %s" % sorted(invented)


def test_a_stated_destination_is_not_rebound_to_a_spool_artifact() -> None:
    _world()
    existing = WORLD / "copy.txt"
    existing.write_text("OLD CONTENT THAT MUST SURVIVE\n", encoding="utf-8")
    goal = "Copy %s to %s" % (_rel(WORLD / "a.txt"), _rel(existing))
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["inputs"]["output_path"] == _rel(existing), compiled["inputs"]
    # ...and the run refuses for the reason that is true, instead of writing the
    # bytes somewhere else and reporting success.
    result = _solve(goal)
    assert result.get("pass") is not True, result.get("status")
    assert "DESTINATION_EXISTS" in str(result.get("status")), result.get("status")
    assert existing.read_text(encoding="utf-8") == "OLD CONTENT THAT MUST SURVIVE\n"


def test_a_writer_gets_no_world_synthesised_input() -> None:
    paths = gc._repo_paths("Rename old_name to new_name in %s" % _rel(WORLD / "lib.py"), ROOT)
    assert gc._bare_stated_destination(
        "Rename old_name to new_name in %s" % _rel(WORLD / "lib.py"), paths) is None
    entry = dict(_registry()["file.rename.v1"])
    entry["capability_id"] = "file.rename.v1"
    completed = gc._complete_inputs_via_world_binding(
        "Rename old_name to new_name in %s" % _rel(WORLD / "lib.py"),
        ROOT, "file.rename.v1", entry)
    assert completed is None, "a writer was handed inputs the world invented"


def test_the_adapter_refuses_a_source_the_sentence_does_not_name() -> None:
    world = _world()
    try:
        file_ops.run({"command": "copy", "path": _rel(world / "a.txt"),
                      "output_path": _rel(world / "x.txt"),
                      "goal": "Copy something_else.txt to x.txt"}, ROOT)
    except RuntimeError as exc:
        assert "PATH_NOT_STATED_IN_THE_SENTENCE" in str(exc), exc
    else:
        raise AssertionError("the adapter copied a file the sentence never named")
    assert not (world / "x.txt").exists(), "a copy was made anyway"


def test_the_repair_never_moves_a_writer_destination() -> None:
    world = _world()
    (world / "c.txt").write_text("present\n", encoding="utf-8")
    goal = "Copy %s to %s" % (_rel(world / "a.txt"), _rel(world / "c.txt"))
    inputs = {"goal": goal, "path": _rel(world / "a.txt"),
              "output_path": _rel(world / "c.txt")}
    rebound = front.repair_output_collisions(goal, inputs, ROOT,
                                             entry=_registry()["file.copy.v1"],
                                             cycle=0, spool=set())
    assert rebound == [], rebound
    assert inputs["output_path"] == _rel(world / "c.txt"), inputs


def main() -> int:
    tests = [value for key, value in sorted(globals().items())
             if key.startswith("test_") and callable(value)]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        else:
            print("ok   %s" % test.__name__)
    print("\n%d/%d passed" % (len(tests) - failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
