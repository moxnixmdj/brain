"""Two lies in one sentence: a formatter nobody could reach, and a change reported as nothing.

Measured 2026-10-29 on this repository::

    "Format <a badly formatted .py>."          FAIL_CLOSED__NO_OBSERVED_EFFECT
      the chain ran `ruff format`, rewrote the file (28 -> 32 bytes, output_verified true),
      and the door then said nothing had happened -- because the compile-failure branch took
      its "before" snapshot AFTER the chain ran, so before == after by construction.

    the same sentence over an already-formatted file   indistinguishable from the above

`format` had **0** rows in the registry (V4 §F-1) and `ruff` could not be routed to at all.  Both
halves are fixed by mechanisms that were already here:

  * `_PROSE_COMMAND` routes a sentence to a program the verifier can judge, and the acceptance
    layer's `_MUTATING_POSTCONDITIONS` is what makes a program judgeable.  `ruff` joined it with
    `_post_ruff_format`, which re-derives the promise by asking the tool itself
    (`ruff format --check A`), so nothing is taken on the adapter's report.
  * the composed branch now snapshots the world BEFORE the chain, like the main path always has.

Known boundary, pinned below: formatting a file that is ALREADY formatted changes nothing, and
this door refuses a sentence that promises a change and leaves no evidence of one.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import composer_route_v1 as route  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_formatter"
REL = WORK.relative_to(ROOT).as_posix()
UNFORMATTED = "def add(a,b):\n    return a+b\n"

HAVE_RUFF = shutil.which("ruff") is not None


def _fresh(text: str = UNFORMATTED) -> pathlib.Path:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    (WORK / "calc.py").write_text(text, encoding="utf-8")
    return WORK


@unittest.skipUnless(HAVE_RUFF, "ruff is not installed")
class AFormatterIsAProgramTheVerifierCanJudge(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    def test_the_command_line_is_the_one_the_postcondition_is_stated_for(self):
        _fresh()
        self.assertEqual(route.extract_argv("Format %s/calc.py." % REL),
                         ["ruff", "format", REL + "/calc.py"])

    def test_a_conversion_is_not_a_format(self):
        _fresh()
        for goal in ("Convert the file %s/calc.py to markdown format." % REL,
                     "Convert %s/calc.py into a pdf." % REL):
            self.assertIsNone(route.extract_argv(goal), goal)

    def test_the_file_is_really_formatted_and_the_run_is_verified(self):
        _fresh()
        result = door.solve({"task_id": "TEST_FORMAT", "goal": "Format %s/calc.py." % REL})
        self.assertTrue(result.get("pass"), result.get("status"))
        self.assertEqual((WORK / "calc.py").read_text(encoding="utf-8"),
                         "def add(a, b):\n    return a + b\n")

    def test_an_already_formatted_file_reports_that_nothing_changed(self):
        """The boundary, stated rather than papered over: no evidence, no pass."""
        _fresh("def add(a, b):\n    return a + b\n")
        result = door.solve({"task_id": "TEST_FORMAT_NOOP", "goal": "Format %s/calc.py." % REL})
        self.assertFalse(result.get("pass"), result.get("status"))
        self.assertEqual(result.get("status"), "FAIL_CLOSED__NO_OBSERVED_EFFECT")


if __name__ == "__main__":
    unittest.main()
