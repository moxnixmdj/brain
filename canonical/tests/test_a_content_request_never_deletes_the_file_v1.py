"""A request to fix the CONTENTS of a file must never delete the file.

Measured 2026-10-30 on a fresh tree, before this test existed:

    goal   "Remove the dead code from <pkg>/calc.py."
    argv   ["rm", "<pkg>/calc.py"]                       (the composer's prose table)
    world  calc.py DELETED
    answer pass=True, PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED

The acceptance layer was not wrong: `rm` declares a deletion postcondition and the file was
deleted.  The defect is upstream, in reading the sentence.  "Remove ... from the file X" makes
the file the PLACE, not the object; the object is the dead code inside it.  The prose table
already refused "remove the duplicate LINES from the file X" for exactly this reason, but its
noun list was a list of things that can be READ inside a file, and the nouns an engineer uses
when asking for a CODE CHANGE -- dead code, unused imports, docstrings, comments, whitespace,
TODOs, statements, variables -- were not in it.

This module pins the rule at the level it belongs: the verb's object decides what is removed.
Both directions are asserted, because the cheap fix for a deletion bug is to stop deleting
anything, and that would break the one write the machine does perfectly.
"""

import pathlib
import shutil
import unittest
from time import perf_counter_ns

from canonical.runtime import composer_route_v1 as composer
from canonical.runtime import live_brain_route_admission_v1 as ra

ROOT = ra.ROOT
SCRATCH = "canonical/astra_runtime/tmp/content_not_file"

SOURCE = ("def add(a, b):\n    return a + b\n\n\ndef unused(x):\n    return x\n")

CONTENT_REQUESTS = (
    "Remove the dead code from %s/pkg/calc.py.",
    "Remove the unused imports from %s/pkg/calc.py.",
    "Remove the dead code in %s/pkg/calc.py.",
)


def _fresh(name):
    base = "%s/%s" % (SCRATCH, name)
    shutil.rmtree(ROOT / base, ignore_errors=True)
    (ROOT / base / "pkg").mkdir(parents=True)
    (ROOT / base / "pkg" / "calc.py").write_text(SOURCE, encoding="utf-8")
    (ROOT / base / "legacy.txt").write_text("x\n", encoding="utf-8")
    return base


def _solve(goal):
    return ra.solve({"task_id": "CF%d" % perf_counter_ns(), "goal": goal})


class TestTheObjectOfTheVerbDecidesWhatIsRemoved(unittest.TestCase):

    def test_a_content_request_never_deletes_the_file(self):
        base = _fresh("content")
        source = ROOT / base / "pkg" / "calc.py"
        for template in CONTENT_REQUESTS:
            goal = template % base
            result = _solve(goal)
            self.assertTrue(source.is_file(), "%r deleted the file it was asked to clean: %s"
                            % (goal, result.get("status")))
            self.assertFalse(result.get("pass"),
                             "%r was certified with the file unchanged: %s"
                             % (goal, result.get("status")))

    def test_the_composer_states_no_command_for_a_content_request(self):
        """The unit-level rule: no argv is invented from a content object."""
        for template in CONTENT_REQUESTS:
            goal = template % SCRATCH
            self.assertIsNone(composer.extract_argv(goal),
                              "a command was invented for %r" % goal)

    def test_deleting_the_file_it_named_still_deletes_it(self):
        """The direction that must keep working: the path IS the object of the verb."""
        base = _fresh("delete")
        legacy = ROOT / base / "legacy.txt"
        self.assertIsNotNone(composer.extract_argv("Delete %s/legacy.txt." % base),
                             "a request that names the file as its object stated no command")
        result = _solve("Delete %s/legacy.txt." % base)
        self.assertFalse(legacy.exists(), "an explicit delete did not delete: %s"
                         % result.get("status"))
        self.assertTrue(result.get("pass"), "an explicit delete was not certified: %s"
                        % result.get("status"))


if __name__ == "__main__":
    unittest.main()
