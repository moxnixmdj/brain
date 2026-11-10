"""The 37-verb track: the first real capability number.

MEASURED 2026-11-09, after r40 closed the path loop:
    23 of the 33 installed read verbs complete the full loop --
    demonstrate once -> compile + qualify on an untouched held-out instance and a sabotage
    control -> recall on a THIRD instance and return the right number.

    0 learner failures. Every non-pass is one of two things, named rather than hidden:
      NOT_EXERCISED (10) -- no demonstration constructed: the verb needs two input files
        (comm, diff, join), takes no file at all (seq, realpath, dirname, basename, stat),
        or reads stdin rather than a path (tr).
      UNREACHABLE (1, in NOT_EXERCISED) -- `awk` is ADMITTED by the table and the sandbox
        cannot execute it: `awk 1 d.txt` exits 0 natively under the worker's exact env and
        fails inside the confined worker with no stderr surfaced, while `true`, `cat` and
        `grep` all run in the same carrier.

Two of the original three failures were MY demonstrations, not the system:
  * `tr a-z A-Z <path>` -- tr takes no filename operand; the carrier correctly refused
    `tr: extra operand`.
  * `awk '{print $0}'` -- replaced with `awk 1`, then found to be carrier-blocked.
That distinction matters: a per-verb track is only honest if a bad demonstration is
recorded as a bad demonstration.

WHY THIS IS THE FIRST REAL NUMBER
---------------------------------
Before r40 every attempt failed on a path, so the count was not computable and "it learns"
could not be checked against anything. The ceiling is 37 read verbs (r38); this says how
many of them the learner can actually carry.
"""
from __future__ import annotations

import pytest

from canonical.tools.read_verb_track_v1 import SPEC, run_track
from canonical.runtime.admitted_confinement_execution_v1 import READ_ONLY_PROGRAMS
import shutil


@pytest.fixture(scope="module")
def track():
    return run_track()


def test_the_track_covers_every_installed_verb():
    installed = [p for p in READ_ONLY_PROGRAMS if "never" not in p and shutil.which(p)]
    assert track_verbs() == sorted(installed)


def track_verbs():
    return sorted(SPEC)


def test_no_verb_fails_to_learn(track):
    """A verb that is demonstrated correctly must not fail the learner. If this ever fires,
    the cause is a real regression -- not a bad fixture, which is why the two known bad
    demonstrations are excluded by construction."""
    failures = [r for r in track["rows"] if r["verdict"] in ("NOT_TAUGHT", "TAUGHT_ERROR",
                                                             "TAUGHT_NOT_RECALLED")]
    assert failures == [], failures


def test_the_pass_count_does_not_silently_drop(track):
    """Pinned so a regression in any single verb shows up as a number, not a vibe."""
    passed = [r["verb"] for r in track["rows"] if r["verdict"] == "PASS"]
    assert len(passed) == 23, passed


def test_at_least_one_verb_of_each_shape_works(track):
    """Sanity that the track is not passing everything trivially."""
    by_verb = {r["verb"]: r for r in track["rows"]}
    for verb, expected in (("sort", 4), ("wc", 1), ("cat", 5), ("grep", 4), ("uniq", 5)):
        assert by_verb[verb]["verdict"] == "PASS", by_verb[verb]
        assert by_verb[verb]["answer"] == expected, by_verb[verb]


def test_awk_is_recorded_as_unreachable_not_passing():
    """The nearest world: a verb the table admits and the sandbox cannot run must never be
    counted as a success anywhere in the track."""
    assert SPEC["awk"] == (None, None)


def test_tr_is_recorded_as_stdin_only():
    """`tr` takes no filename operand. Recording it as a path-taking verb produced
    `tr: extra operand` -- a demonstration of a command that does not exist."""
    assert SPEC["tr"] == (None, None)
