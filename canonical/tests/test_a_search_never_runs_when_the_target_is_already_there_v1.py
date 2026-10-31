"""A search for a program is not run when the file it is looking for is already there.

`computer_env_v1.discover` has exactly one oracle: did a program MAKE `target` appear
(`is_goal = target in snapshot`).  When the goal names a file that already exists, that oracle
is satisfied before anything runs, so no action can be credited with producing it.  The route
knew two such refusals already -- "nothing in the goal says what to produce" and "the goal asks
to be told something, and this route only checks that a file appeared" -- and was missing the
third case of the same shape.

Measured 2026-10-29 on `f6f9c6f`, fresh tree, wall clock as the oracle::

    "Format <T>/pkg/calc.py"                        48.7 s -> 0.005 s
    "Replace the magic number 3 in <T>/pkg/calc.py" 33.4 s -> 0.000 s

The 48.7 s was 442 actions and 5,046 subprocesses, spent to conclude
`OPEN__NO_USABLE_PRIOR_EXPERIENCE` about a file that was sitting on disk the whole time.  These
tests pin both halves: the refusal is instant, and a goal that really does ask for a NEW file
still searches and still finds the program.
"""
from __future__ import annotations

import hashlib
import pathlib
import shutil
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import computer_env_v1 as cenv  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_discovery_target"
BROKEN = "def add(a, b):\n    return a - b\n"

# The stated refusal costs no CPU, so a generous ceiling still fails loudly if the whole
# exploration ever comes back.  The measured value is 5 ms; the failed value was 48,700 ms.
INSTANT_MS = 2_000


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/calc.py").write_text(BROKEN, encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ms(fn):
    started = time.monotonic()
    value = fn()
    return value, round((time.monotonic() - started) * 1000)


class ATargetThatIsAlreadyThereIsNotDiscovered(unittest.TestCase):
    def test_the_stated_refusal_fires_and_costs_nothing(self):
        base = _fresh("format")
        src = _rel(base / "pkg/calc.py")
        found, took = _ms(lambda: cenv.discover("Format %s." % src))
        self.assertEqual(found.get("status"), "OPEN__THE_TARGET_ALREADY_EXISTS")
        self.assertIs(found.get("closed"), False)
        self.assertLess(took, INSTANT_MS,
                        "the search still ran: %s ms for a file that was already there" % took)

    def test_a_magic_number_edit_is_refused_the_same_way(self):
        base = _fresh("magic")
        src = _rel(base / "pkg/calc.py")
        found, took = _ms(lambda: cenv.discover(
            "Replace the magic number 3 in %s with a named constant." % src))
        self.assertEqual(found.get("status"), "OPEN__THE_TARGET_ALREADY_EXISTS")
        self.assertLess(took, INSTANT_MS, "%s ms" % took)

    def test_a_file_that_really_is_missing_still_gets_the_search(self):
        """The positive control: this must NOT be short-circuited."""
        base = _fresh("missing")
        out = _rel(base / "pkg/notes.txt.gz")
        (base / "pkg/notes.txt").write_text("a\nb\n", encoding="utf-8")
        found = cenv.discover("Compress the file %s into %s"
                              % (_rel(base / "pkg/notes.txt"), out))
        self.assertNotEqual(found.get("status"), "OPEN__THE_TARGET_ALREADY_EXISTS",
                            "a genuine discovery request must still be searched")


class TheDoorIsFastAndLeavesTheFileAlone(unittest.TestCase):
    def test_format_refuses_quickly_and_does_not_touch_the_source(self):
        base = _fresh("door_format")
        src = base / "pkg/calc.py"
        before = _digest(src)
        result, took = _ms(lambda: door.solve(
            {"task_id": "FAST_FORMAT", "goal": "Format %s." % _rel(src)}))
        self.assertIs(result.get("pass"), False, result.get("status"))
        self.assertLess(took, 5_000, "the door took %s ms to refuse" % took)
        self.assertEqual(_digest(src), before, "the source was modified")

    def test_a_magic_number_edit_refuses_quickly(self):
        base = _fresh("door_magic")
        src = base / "pkg/calc.py"
        before = _digest(src)
        result, took = _ms(lambda: door.solve(
            {"task_id": "FAST_MAGIC", "goal":
             "Replace the magic number 3 in %s with a named constant." % _rel(src)}))
        self.assertIs(result.get("pass"), False, result.get("status"))
        self.assertLess(took, 5_000, "the door took %s ms to refuse" % took)
        self.assertEqual(_digest(src), before)


if __name__ == "__main__":
    unittest.main()
