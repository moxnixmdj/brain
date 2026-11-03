#!/usr/bin/env python3
"""A copy sentence names its destination, with or without a preposition.

Measured 2026-11-02, before this file existed:

    "Make a copy of <a> named <b>"  -> FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT

The sentence settles `cp <a> <b>`, and `file.copy.v1` declares exactly that argv.
It was never even a CANDIDATE: the ranker's one-file-out rule asks whether the
sentence states a destination, and that predicate read only `to`/`into`/`onto`.
Everything downstream then behaved correctly -- a wrong row was ranked, it could
not bind, and the refusal named a sandbox that had nothing to do with it.

The two widening points are the only ones that were needed (a third attempt at
the role-phrase alias table was measured NOT to fix it and was reverted):

  * `goal_front_compiler_v1._states_a_file_destination` -- is this row a candidate
  * `goal_compiler._bare_stated_destination`             -- where does the file go

Both now read `named` and `called`, and both require WHITESPACE after the word.
That is not decoration: a destination whose own filename is `named.txt` was
measured to be read as a destination phrase when the word was matched loosely,
and a copy onto a file called named.txt failed closed for a reason that had
nothing to do with the request.  The tests below pin the guard, not the fix.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORLD = ROOT / "canonical/astra_runtime/tmp/a_copy_names_its_destination_v1"
SOURCE_BYTES = b"alpha\nbeta gamma\n"


def _world(extra: dict[str, bytes] | None = None) -> pathlib.Path:
    if WORLD.exists():
        shutil.rmtree(WORLD)
    WORLD.mkdir(parents=True)
    (WORLD / "a.txt").write_bytes(SOURCE_BYTES)
    for name, payload in (extra or {}).items():
        (WORLD / name).write_bytes(payload)
    return WORLD


def _rel(name: str) -> str:
    return (WORLD / name).relative_to(ROOT).as_posix()


def _ask(goal: str) -> dict:
    return door.solve({"task_id": "a_copy_names_its_destination", "goal": goal}) or {}


def test_both_destination_phrasings_copy_the_stated_file() -> None:
    for template in ("Make a copy of %s named %s", "Make a copy of %s called %s"):
        _world()
        result = _ask(template % (_rel("a.txt"), _rel("b.txt")))
        assert result.get("pass") is True, (template, result.get("status"))
        assert result.get("compiled_capability_id") == "file.copy.v1", (template, result)
        assert (WORLD / "b.txt").read_bytes() == SOURCE_BYTES, template
        # A copy keeps the source.  Anything else is a rename wearing its name.
        assert (WORLD / "a.txt").read_bytes() == SOURCE_BYTES, template


def test_a_destination_whose_name_starts_with_named_still_copies() -> None:
    """The word `named` may not be read out of a FILENAME.

    `named.txt` is `named` followed by a dot, so the grammars require whitespace
    after the word.  Measured without that: this exact copy failed closed with a
    destination refusal while the same sentence ending in `out.txt` passed.
    """
    _world()
    result = _ask("Make a copy of %s named %s" % (_rel("a.txt"), _rel("named.txt")))
    assert result.get("pass") is True, result.get("status")
    assert (WORLD / "named.txt").read_bytes() == SOURCE_BYTES


def test_the_destination_bindings_agree_with_the_sentence() -> None:
    """Both grammars must read the destination the sentence states, and only one."""
    from canonical.runtime import goal_compiler as gc
    from canonical.runtime import goal_front_compiler_v1 as front

    _world()
    goal = "Make a copy of %s named %s" % (_rel("a.txt"), _rel("fresh.txt"))
    assert front._states_a_file_destination(goal) is True, goal
    paths = gc._repo_paths(goal, ROOT)
    assert gc._bare_stated_destination(goal, paths) == _rel("fresh.txt"), paths

    # And a sentence that names no destination at all states none, so the row
    # stays out of the ranking for it.
    assert front._states_a_file_destination("Make a copy of %s" % _rel("a.txt")) is False


def test_a_symbol_rename_inside_a_file_is_still_not_a_file_rename() -> None:
    """The reason the destination predicate exists at all.

    "Rename old_name to new_name in lib.py" shares the word `rename` with a file
    rename, and the trailing file says the change is INSIDE it.  The predicate
    must keep declining that sentence, or the file row becomes a candidate and
    moves a file nobody named.
    """
    _world()
    goal = "Rename old_name to new_name in %s" % _rel("a.txt")
    assert __import__("canonical.runtime.goal_front_compiler_v1", fromlist=["x"])._states_a_file_destination(goal) is False, goal
    before = (WORLD / "a.txt").read_bytes()
    result = _ask(goal)
    assert result.get("pass") is not True, result
    assert (WORLD / "a.txt").read_bytes() == before
    assert sorted(path.name for path in WORLD.iterdir()) == ["a.txt"]


def test_a_copy_onto_an_existing_file_refuses_and_leaves_it_alone() -> None:
    _world({"taken.txt": b"PRECIOUS\n"})
    before = (WORLD / "taken.txt").read_bytes()
    result = _ask("Make a copy of %s named %s" % (_rel("a.txt"), _rel("taken.txt")))
    assert result.get("pass") is not True, result
    assert str(result.get("status")) == (
        "FAIL_CLOSED__CAPABILITY_REFUSED_DESTINATION_EXISTS_AND_THE_SENTENCE_"
        "DID_NOT_ASK_TO_OVERWRITE"), result.get("status")
    assert (WORLD / "taken.txt").read_bytes() == before


def test_a_copy_from_a_file_that_does_not_exist_writes_nothing() -> None:
    _world()
    result = _ask("Make a copy of %s named %s" % (_rel("missing.txt"), _rel("fresh.txt")))
    assert result.get("pass") is not True, result
    assert not (WORLD / "fresh.txt").exists(), "a refused copy created its destination"
    assert sorted(path.name for path in WORLD.iterdir()) == ["a.txt"]


def main() -> int:
    tests = [value for key, value in sorted(globals().items())
             if key.startswith("test_") and callable(value)]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - a harness reports, it does not hide
            failures += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        else:
            print("ok   %s" % test.__name__)
    print("\n%d/%d passed" % (len(tests) - failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
