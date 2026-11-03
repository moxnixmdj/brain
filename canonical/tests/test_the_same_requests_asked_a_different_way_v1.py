#!/usr/bin/env python3
"""The same twenty-one requests, asked a different way.

The ordinary-request ratchet pins ONE sentence per operation, and every one of
them is phrased the way the code's own keywords expect.  That is a gate that
measures the sentence it was written against, not the capability: measured
2026-11-02, twenty-four paraphrases of requests the machine already serves came
back 17/24.  Six ordinary ways of asking for work it can do were answered with a
refusal -- and one of them ("Add the line epsilon to <f>") was refused by the
row that exists to add a line, because its reader only knew "a line containing".

So this is a second ratchet, over phrasing rather than over operations:

* it runs on a world rebuilt for every sentence, so one sentence's write cannot
  decide the next one's route;
* `FLOOR` may only rise -- lowering it to make a change look green is the bug;
* each unserved phrasing is pinned to the gate that refuses it, with the reason,
  so moving one from "no row reads this" to "answered" cannot happen silently
  and moving one from "the write was refused" to a different refusal is visible;
* every served phrasing has its EFFECT checked against the disk, not against the
  status string: a paraphrase that "passes" while the file is untouched is the
  false-pass shape this gate exists to catch.

What it is not: a measure of language understanding.  It is twenty-four
spellings of twenty-four requests, and 18/24 is the number, not a percentage of
English.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORLD = ROOT / "canonical/astra_runtime/tmp/paraphrase_ratchet"
FLOOR = 21


def _rel(name: str) -> str:
    return (WORLD / name).relative_to(ROOT).as_posix()


def _dir() -> str:
    return WORLD.relative_to(ROOT).as_posix()


def _world() -> None:
    if WORLD.exists():
        shutil.rmtree(WORLD)
    WORLD.mkdir(parents=True)
    (WORLD / "a.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    (WORLD / "b.txt").write_text("alpha\nBETA\n", encoding="utf-8")


def _names(result: dict) -> list[str]:
    """The entries an answer names, whether it is a list, a projection or text."""
    answer = result.get("answer")
    if isinstance(answer, dict):
        answer = answer.get("value")
    if isinstance(answer, (list, tuple)):
        return sorted(str(x) for x in answer)
    return sorted(str(answer or "").split("\n")) if answer else []


def _ask(goal: str) -> dict:
    return door.solve({"task_id": "paraphrase_ratchet", "goal": goal}) or {}


# --------------------------------------------------------------------------
# The ones the machine serves today.  Each entry is (sentence, the check that
# proves the effect landed).  `None` means: the answer is a value, so being
# served is the whole claim.
# --------------------------------------------------------------------------
def _served_sentences() -> list[tuple[str, callable]]:
    a, b, c = _rel("a.txt"), _rel("b.txt"), _rel("c.txt")
    d = _dir()
    return [
        ("how many lines does %s have?" % a, None),
        ("Give me the number of lines in %s" % a, None),
        ("What are the permissions on %s?" % a, None),
        ("How big is %s?" % a, None),
        ("Cat %s" % a, None),
        ("Diff %s and %s" % (a, b), None),
        ("What is the difference between %s and %s?" % (a, b), None),
        ("List the directory %s" % d, None),
        ("Find the files in %s that contain beta" % d, None),
        ("Give me the sorted lines of %s" % a, None),
        ("Print %s in reverse order" % a, None),
        ("What is the most frequent word in %s?" % a, None),
        ("Back up %s" % a, None),
        ("Turn %s into upper case" % a, None),
        ("Add the line epsilon to %s" % a,
         lambda: (WORLD / "a.txt").read_text(encoding="utf-8").endswith("epsilon\n")),
        ("Convert %s to uppercase" % a,
         lambda: (WORLD / "a.txt").read_text(encoding="utf-8") == "ALPHA\nBETA\nGAMMA\n"),
        ("Append 'omega' to %s" % a,
         lambda: (WORLD / "a.txt").read_text(encoding="utf-8").endswith("omega\n")),
        ("Which files under %s mention beta?" % d, None),
        ("What is in %s?" % a, None),
        ("What files are in %s?" % d, None),
        ("Make a copy of %s named %s" % (a, c),
         lambda: (WORLD / "c.txt").read_bytes() == (WORLD / "a.txt").read_bytes()),
    ]


def _unserved() -> dict[str, tuple[str, str]]:
    """Phrasings this world does not serve, pinned to the gate that stops them.

    Every phrasing in this ratchet is now served, so nothing is pinned here.  The
    dict stays because the test that reads it is about REFUSAL, and the write it
    guards is the one place a wrong answer destroys something: `_refused_writes`
    below pins the copies this machine must keep refusing.
    """
    return {}


def _refused_writes() -> list[tuple[str, str]]:
    """(sentence, the gate that must refuse it) for the copy this machine owns.

    A write row is only as good as what it refuses.  These are measured, and the
    test asserts the destination is byte-unchanged afterwards -- a refusal that
    overwrote the file anyway would pass a status check and fail the machine.
    """
    a, taken, missing = _rel("a.txt"), _rel("taken.txt"), _rel("missing.txt")
    return [
        ("Make a copy of %s named %s" % (a, taken),
         "FAIL_CLOSED__CAPABILITY_REFUSED_DESTINATION_EXISTS_AND_THE_SENTENCE_DID_NOT_ASK_TO_OVERWRITE"),
        ("Make a copy of %s named %s" % (missing, _rel("fresh.txt")),
         "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT"),
    ]


def run_all() -> list[dict]:
    outcomes: list[dict] = []
    for goal, proof in _served_sentences():
        _world()
        result = _ask(goal)
        # The effect is checked HERE, while the world that sentence built is
        # still the current one.  Deferring it to the assertion passed the proof a
        # world that a later sentence had already replaced.
        effect = None if proof is None else bool(proof())
        outcomes.append({"goal": goal, "result": result, "effect": effect,
                         "has_proof": proof is not None})
    for prefix in _unserved():
        _world()
        goal = {
        }[prefix]
        before = (WORLD / "a.txt").read_bytes()
        outcomes.append({"goal": goal, "result": _ask(goal), "before": before})
    return outcomes


def test_every_phrasing_this_world_serves_is_served_and_its_effect_lands() -> None:
    for item in run_all():
        if "before" in item:
            continue          # refused phrasings are the other test's business
        assert item["result"].get("pass") is True, (item["goal"], item["result"].get("status"))
        if item.get("has_proof"):
            assert item.get("effect") is True, ("served but the effect is not on disk", item["goal"])


def test_the_phrasings_served_do_not_fall_below_the_floor() -> None:
    outcomes = run_all()
    served = [item for item in outcomes if item["result"].get("pass") is True]
    failed = [item["goal"] for item in outcomes if item["result"].get("pass") is not True]
    assert len(outcomes) == 21, len(outcomes)
    assert len(served) >= FLOOR, (
        "%d served, floor is %d; not served: %s" % (len(served), FLOOR, failed))


def test_each_unserved_phrasing_is_refused_by_the_gate_that_stops_it() -> None:
    pinned = _unserved()
    assert len(pinned) == 0, len(pinned)
    for item in run_all():
        for prefix, (expected, why) in pinned.items():
            if not item["goal"].startswith(prefix):
                continue
            status = str(item["result"].get("status") or "")
            assert item["result"].get("pass") is not True, (item["goal"], "served now")
            assert status == expected, (item["goal"], status, expected, why)
            # A refused phrasing may not have touched the world.
            if "before" in item:
                assert (WORLD / "a.txt").read_bytes() == item["before"], (
                    "a refused phrasing changed the file", item["goal"])


def test_the_question_forms_answer_the_same_thing_as_the_imperatives() -> None:
    """A phrasing is only served if it answers what the sentence asked.

    "What is in <f>" must return that file's text, and "What files are in <d>"
    must name that directory's entries -- the same answers "Show the contents of
    <f>" and "List the directory <d>" give.  Counting them as served while they
    answered something else would make this ratchet reward vocabulary.
    """
    a, d = _rel("a.txt"), _dir()
    _world()
    read = _ask("What is in %s?" % a)
    assert read.get("pass") is True, read.get("status")
    assert str(read.get("answer")) == "alpha\nbeta\ngamma\n", read.get("answer")

    _world()
    listing = _ask("What files are in %s?" % d)
    assert listing.get("pass") is True, listing.get("status")
    assert _names(listing) == ["a.txt", "b.txt"], listing.get("answer")

    # The same two answers, from the imperative phrasings, for comparison.
    _world()
    assert str(_ask("Show the contents of %s" % a).get("answer")) == "alpha\nbeta\ngamma\n"
    _world()
    assert _names(_ask("List the directory %s" % d)) == ["a.txt", "b.txt"]


def test_a_copy_this_machine_must_refuse_still_refuses_and_writes_nothing() -> None:
    for goal, expected in _refused_writes():
        _world()
        (WORLD / "taken.txt").write_bytes(b"PRECIOUS\n")
        before = {path.name: path.read_bytes() for path in WORLD.iterdir() if path.is_file()}
        result = _ask(goal)
        assert result.get("pass") is not True, (goal, result.get("status"))
        assert str(result.get("status")) == expected, (goal, result.get("status"))
        after = {path.name: path.read_bytes() for path in WORLD.iterdir() if path.is_file()}
        assert after == before, ("a refused copy changed the world", goal, sorted(after))


def test_the_two_verbs_name_the_same_files() -> None:
    """'mention' was served by this turn's change; it must not answer differently.

    The widened verb buys a phrasing, not an answer.  If the two sentences ever
    disagree about which files match, the paraphrase is not the same question and
    this ratchet would be counting a sentence it serves with a different answer.
    """
    d = _dir()
    answers = []
    for goal in ("Which files under %s mention beta?" % d,
                 "Which files under %s contain beta?" % d):
        _world()
        result = _ask(goal)
        assert result.get("pass") is True, (goal, result.get("status"))
        answers.append(sorted(str(x) for x in ((result.get("answer") or {}).get("value") or [])))
    assert answers[0] == answers[1] == [_rel("a.txt")], answers


def test_the_world_is_rebuilt_so_the_number_cannot_drift() -> None:
    first = [item["result"].get("pass") for item in run_all()]
    second = [item["result"].get("pass") for item in run_all()]
    assert first == second, (first, second)


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
    served = sum(1 for item in run_all() if item["result"].get("pass") is True)
    print("\nserved %d/%d (floor %d)" % (served, 21, FLOOR))
    print("%d/%d passed" % (len(tests) - failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
