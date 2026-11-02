#!/usr/bin/env python3
"""An ordinary file request is served, or it says why -- and the count is a ratchet.

This is the acceptance that the ordinary-request work has been measured against
since it started at 5 of 25. Every step of that work was scored by running a
scratch probe over one world; the scratch probe lived in `/tmp`, so nothing in
this repository would have noticed if the number went backwards. Twice it did:
a capability that took a sentence it did not own, and a compress that deleted the
file and wrote the wrong archive. Both were caught by measuring, not by a gate.

So the probe is now a test, and it is a RATCHET:

* each of the 25 sentences has an expected outcome, written down;
* a sentence expected to be served must be served BY THE CAPABILITY THAT OWNS IT
  -- a PASS from somewhere else is the false-pass shape, not a pass;
* a sentence expected to be refused must be refused AND must leave the world
  exactly as it was, which is checked on the bytes;
* the served total may not fall below the floor. Adding a capability raises the
  floor; it is never lowered to make a change look green.

The world is rebuilt from scratch on every run, because the probe was not
idempotent: a destination created by run one made run two's copy refuse. A gate
that reports a different number on its second run is not a gate.

Sentences are run in order over ONE world, which is what an ordinary session
looks like: a copy lands, a rename moves a file, an edit changes bytes. The order
below is part of the contract, and the state checked after each phase is the
reason for it.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORLD = ROOT / "canonical/astra_runtime/tmp/ordinary_request_ratchet"
A = "a.txt"
B = "b.txt"
C = "c.txt"
D = "d.txt"
OUT = "out.txt"

#: The floor. The measured served count at the commit that added this file.
FLOOR = 20


def _rel(name: str) -> str:
    return (WORLD / name).relative_to(ROOT).as_posix()


def _world() -> None:
    """Rebuild the world every run, so the number does not drift."""
    if WORLD.exists():
        shutil.rmtree(WORLD)
    WORLD.mkdir(parents=True)
    (WORLD / A).write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    (WORLD / B).write_text("alpha\nBETA\n", encoding="utf-8")


def _solve(goal: str) -> dict:
    return door.solve({"task_id": "ordinary_request_ratchet", "goal": goal}) or {}


def _served(goal: str) -> dict:
    result = _solve(goal)
    assert result.get("pass") is True, (goal, result.get("status"), result.get("reason"))
    return result


def _refused(goal: str) -> dict:
    result = _solve(goal)
    assert result.get("pass") is not True, (goal, result.get("status"))
    return result


def run_all() -> list[dict]:
    """Run the 25 sentences in order and return what each one did."""
    _world()
    served: list[dict] = []
    refused: list[dict] = []

    # ---- the file's facts, on a world nothing has touched yet ---------------
    for goal in (
        f"Count the lines in {_rel(A)}",
        f"How many lines are in {_rel(A)}?",
        f"What are the file permissions of {_rel(A)}?",
        f"What is the size of {_rel(A)}?",
        f"Show me the contents of {_rel(A)}",
        f"Read {_rel(A)}",
        f"Compare {_rel(A)} and {_rel(B)}",
        f"Find the differences between {_rel(A)} and {_rel(B)}",
        f"Search {WORLD.relative_to(ROOT).as_posix()} for the word beta",
        f"Which files in {WORLD.relative_to(ROOT).as_posix()} contain beta?",
        f"List the files in {WORLD.relative_to(ROOT).as_posix()}",
        f"Sort the lines of {_rel(A)}",
        f"Reverse the lines of {_rel(A)}",
        f"What is the most common word in {_rel(A)}?",
    ):
        served.append({"goal": goal, "result": _served(goal)})

    # ---- requests that change the world, in a stated order -----------------
    served.append({"goal": f"Copy {_rel(A)} to {_rel(C)}",
                   "result": _served(f"Copy {_rel(A)} to {_rel(C)}")})
    assert (WORLD / C).read_bytes() == (WORLD / A).read_bytes(), "the copy is not the file"

    served.append({"goal": f"Write the text hello to {_rel(OUT)}",
                   "result": _served(f"Write the text hello to {_rel(OUT)}")})
    assert (WORLD / OUT).read_text(encoding="utf-8") == "hello"

    served.append({"goal": f"Add a line containing delta to {_rel(A)}",
                   "result": _served(f"Add a line containing delta to {_rel(A)}")})
    assert (WORLD / A).read_text(encoding="utf-8").endswith("delta\n")

    served.append({"goal": f"Uppercase every line in {_rel(A)}",
                   "result": _served(f"Uppercase every line in {_rel(A)}")})
    assert (WORLD / A).read_text(encoding="utf-8") == "ALPHA\nBETA\nGAMMA\nDELTA\n"

    served.append({"goal": f"Make a backup of {_rel(A)}",
                   "result": _served(f"Make a backup of {_rel(A)}")})
    assert (WORLD / (A + ".bak")).read_bytes() == (WORLD / A).read_bytes()

    served.append({"goal": f"Rename {_rel(B)} to {_rel(D)}",
                   "result": _served(f"Rename {_rel(B)} to {_rel(D)}")})
    assert not (WORLD / B).exists() and (WORLD / D).is_file()

    # ---- and the ones that must not be served ------------------------------
    before = (WORLD / A).read_bytes()
    refused.append({"goal": f"Delete the last line of {_rel(A)}",
                    "result": _refused(f"Delete the last line of {_rel(A)}")})
    # A deletion by position leaves nothing on disk that can answer for it
    # afterwards, which is the repository's own standard, not a preference.
    assert (WORLD / A).read_bytes() == before, "a refused deletion changed the file"

    refused.append({"goal": f"Compress {_rel(A)} into {WORLD.relative_to(ROOT).as_posix()}/a.tar.gz",
                    "result": _refused(
                        f"Compress {_rel(A)} into {WORLD.relative_to(ROOT).as_posix()}/a.tar.gz")})
    # `extract_argv` reads that sentence as `gzip <a>`, and gzip deletes the
    # source: serving it would write a.gz and destroy a while the named archive
    # was never created. It is refused, and nothing moved.
    assert (WORLD / A).read_bytes() == before, "a refused compress changed the file"
    assert not (WORLD / "a.tar.gz").exists(), "an archive nobody asked for was written"
    assert not (WORLD / (A + ".gz")).exists(), "an invented archive was written"

    for goal in (f"Tell me what changed in {WORLD.relative_to(ROOT).as_posix()} today",
                 f"Summarise {_rel(A)}",
                 f"Convert {_rel(A)} to JSON"):
        refused.append({"goal": goal, "result": _refused(goal)})

    return served + refused


def test_every_sentence_that_should_be_served_is_served_by_the_row_that_owns_it() -> None:
    """A PASS from an unrelated row is the false-pass shape, not a pass.

    Each sentence is run on its OWN fresh world, so one sentence's write cannot
    decide the next one's route. The order-dependent session is checked by the
    floor test; this one asks only "who answered this sentence".
    """
    expected = {
        "Count the lines in": "file.line_count.v1",
        "How many lines are in": "file.line_count.v1",
        "What are the file permissions of": "file.stat.v1",
        "What is the size of": "file.stat.v1",
        "Show me the contents of": "file.contents.v1",
        "Read ": "file.contents.v1",
        "Compare ": "file.diff.v1",
        "Find the differences between": "file.diff.v1",
        "Search ": "file.directory_search.v1",
        "Which files in": "file.directory_search.v1",
        "List the files in": "file.directory_listing.v1",
        "Sort the lines of": "file.sorted.v1",
        "Reverse the lines of": "file.reversed.v1",
        "What is the most common word in": "file.word_frequency.v1",
        "Copy ": "file.copy.v1",
        "Add a line containing": "file.line.appended.v1",
        "Uppercase every line in": "file.uppercased.v1",
        "Make a backup of": "file.backup.v1",
        "Rename ": "file.rename.v1",
        # Served by the runtime's writer through composition, which names no
        # compiled capability; the bytes are checked in `run_all`.
        "Write the text hello to": None,
    }
    checked = 0
    for prefix, cid in sorted(expected.items(), key=lambda item: -len(item[0])):
        matches = [goal for goal in _GOALS if goal.startswith(prefix)]
        assert matches, "no sentence starts with " + prefix
        for goal in matches:
            _world()
            result = _served(goal)
            got = result.get("compiled_capability_id")
            if cid is not None:
                assert got == cid, (goal, got, cid)
            checked += 1
    expected_served = sum(1 for goal in _GOALS if _is_expected_served(goal))
    assert checked == expected_served, (checked, expected_served)


def _is_expected_served(goal: str) -> bool:
    return not goal.startswith(("Delete the last line", "Compress ", "Tell me what changed",
                                "Summarise ", "Convert "))


_GOALS = [
    f"Count the lines in {_rel(A)}",
    f"How many lines are in {_rel(A)}?",
    f"What are the file permissions of {_rel(A)}?",
    f"What is the size of {_rel(A)}?",
    f"Show me the contents of {_rel(A)}",
    f"Read {_rel(A)}",
    f"Compare {_rel(A)} and {_rel(B)}",
    f"Find the differences between {_rel(A)} and {_rel(B)}",
    f"Search {WORLD.relative_to(ROOT).as_posix()} for the word beta",
    f"Which files in {WORLD.relative_to(ROOT).as_posix()} contain beta?",
    f"List the files in {WORLD.relative_to(ROOT).as_posix()}",
    f"Sort the lines of {_rel(A)}",
    f"Reverse the lines of {_rel(A)}",
    f"What is the most common word in {_rel(A)}?",
    f"Copy {_rel(A)} to {_rel(C)}",
    f"Write the text hello to {_rel(OUT)}",
    f"Add a line containing delta to {_rel(A)}",
    f"Uppercase every line in {_rel(A)}",
    f"Make a backup of {_rel(A)}",
    f"Rename {_rel(B)} to {_rel(D)}",
    f"Delete the last line of {_rel(A)}",
    f"Compress {_rel(A)} into {WORLD.relative_to(ROOT).as_posix()}/a.tar.gz",
    f"Tell me what changed in {WORLD.relative_to(ROOT).as_posix()} today",
    f"Summarise {_rel(A)}",
    f"Convert {_rel(A)} to JSON",
]


def test_the_ordinary_requests_served_do_not_fall_below_the_floor() -> None:
    """The ratchet itself. Lowering FLOOR to make a change look green is the bug."""
    outcomes = run_all()
    served = [item for item in outcomes if item["result"].get("pass") is True]
    failed = [item["goal"] for item in outcomes if item["result"].get("pass") is not True]
    assert len(served) >= FLOOR, (
        "%d served, floor is %d; not served: %s" % (len(served), FLOOR, failed))
    assert len(outcomes) == 25, len(outcomes)
    # Every sentence is either served with a named capability or refused with a
    # named status -- a sentence that reaches nothing has no status to show.
    for item in outcomes:
        status = str(item["result"].get("status") or "")
        assert status, ("no status at all", item["goal"])
        if item["result"].get("pass") is True:
            # A composed answer names no compiled capability, so the status is
            # what shows it ran: either a compiled front-local execution, or a
            # composition whose exact semantic acceptance was verified.
            assert (item["result"].get("compiled_capability_id")
                    or "EXECUTED" in status), ("served without saying what ran", item["goal"])


def test_the_world_is_rebuilt_so_the_number_cannot_drift() -> None:
    """Two runs, same number. The scratch probe failed this and was not a gate."""
    first = run_all()
    second = run_all()
    assert sum(1 for i in first if i["result"].get("pass")) == \
           sum(1 for i in second if i["result"].get("pass")), "the count drifted between runs"


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
    outcomes = run_all()
    served = sum(1 for item in outcomes if item["result"].get("pass"))
    print("\nserved %d/%d (floor %d)" % (served, len(outcomes), FLOOR))
    print("%d/%d passed" % (len(tests) - failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
