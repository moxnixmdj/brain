"""The wrong KIND of row cannot certify the work.

Three fabricated PASSes were measured on this tree on 2026-10-30.  Each one satisfied its own
``expect`` field perfectly (``output_verified == true``) while the world stayed exactly as it was,
and none of them could be caught by the effect table, because the defect is not "this effect is
unserved" but "this row is the wrong kind of row for this sentence":

    "Split the function mul in <pkg>/calc.py into smaller functions."
        -> python.source.audit.ast (a READER), pass=True, calc.py byte-identical
    "Find every caller of the function load_verified_registry in canonical/runtime."
        -> software.repair.choreograph.crossfile.v1 (a MUTATOR, matching the keyword
           "call-graph"), pass=True in 261 ms against 19 259 ms for the correct row --
           the wrong answer was the fast answer
    "Run the javascript test suite in <dir>."   (the dir contains no JavaScript at all)
        -> python.repository.acceptance.measure.v1 (a PYTHON acceptance measurement), pass=True

The rules that now refuse them are drawn from each row's OWN declaration: a transform row declares
its transform, a mutator declares that it writes, a single-language row names its language.  So the
day a capability that really splits a function, or really runs a JavaScript suite, is bound, the
same declaration admits it and nothing here has to change.

This module pins both halves: the three shapes are refused AND the four things the machine really
can do are still certified.
"""

import hashlib
import pathlib
import shutil
import unittest
from time import perf_counter_ns

from canonical.runtime import live_brain_route_admission_v1 as ra

ROOT = ra.ROOT
SCRATCH = "canonical/astra_runtime/tmp/wrong_kind_of_row"

CALC = ("def add(a, b):\n    total = a + b\n    return total\n\n\n"
        "def mul(a, b):\n    return a * b\n")
TEST = ("import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n"
        "\n    def test_mul(self):\n        self.assertEqual(calc.mul(2, 3), 6)\n")


def _fresh(name, js=False):
    base = "%s/%s" % (SCRATCH, name)
    shutil.rmtree(ROOT / base, ignore_errors=True)
    (ROOT / base / "pkg").mkdir(parents=True)
    (ROOT / base / "pkg" / "calc.py").write_text(CALC, encoding="utf-8")
    (ROOT / base / "pkg" / "test_calc.py").write_text(TEST, encoding="utf-8")
    if js:
        (ROOT / base / "web").mkdir()
        (ROOT / base / "web" / "package.json").write_text('{"name":"w","scripts":{"test":"node --test"}}')
    return base


def _solve(goal):
    return ra.solve({"task_id": "WK%d" % perf_counter_ns(), "goal": goal})


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestAReaderIsNotATransform(unittest.TestCase):

    def test_split_is_not_answered_by_an_inventory(self):
        base = _fresh("split")
        source = ROOT / base / "pkg" / "calc.py"
        before = _digest(source)
        for verb in ("Split", "Decompose"):
            result = _solve("%s the function mul in %s/pkg/calc.py into smaller functions."
                            % (verb, base))
            self.assertFalse(result.get("pass"),
                             "%s was certified by %s" % (verb, result.get("compiled_capability_id")))
            self.assertEqual(_digest(source), before, "a reader edited the source")


class TestAWriterIsNotAnAnswer(unittest.TestCase):

    def test_a_question_is_not_answered_by_a_repair_choreographer(self):
        """The fastest answer must not be a mutator that produces no answer."""
        goal = "Find every caller of the function load_verified_registry in canonical/runtime."
        result = _solve(goal)
        answered_by = str(result.get("compiled_capability_id") or "")
        if result.get("pass") is True:
            self.assertNotIn("repair", answered_by,
                             "a repair row certified a read-only question in %s"
                             % result.get("status"))
        # ... and the unit rule that makes it so, stated on the row that did it.
        entry = dict(ra.load_verified_registry())["software.repair.choreograph.crossfile.v1"]
        errors = ra.stated_answer_errors(goal, entry)
        self.assertTrue(any("READ_ONLY" in e for e in errors),
                        "the gate does not refuse a writer for a question: %s" % errors)


class TestAPythonRowIsNotAJavaScriptSuite(unittest.TestCase):

    def test_a_javascript_suite_that_does_not_exist_is_not_run(self):
        base = _fresh("js", js=True)
        result = _solve("Run the javascript test suite in %s." % base)
        self.assertFalse(result.get("pass"),
                         "a python row certified a javascript suite: %s / %s"
                         % (result.get("status"), result.get("compiled_capability_id")))


class TestWhatTheMachineCanReallyDoIsStillCertified(unittest.TestCase):

    def test_a_real_caller_map_still_passes(self):
        base = _fresh("callers")
        result = _solve("Find every caller of the function add in %s/pkg/calc.py." % base)
        self.assertTrue(result.get("pass"),
                        "a caller map on a small tree was refused: %s" % result.get("status"))

    def test_a_real_extraction_still_passes(self):
        base = _fresh("extract")
        result = _solve("Extract the statement `total = a + b` into a new function named sum2 "
                        "in %s/pkg/calc.py." % base)
        self.assertTrue(result.get("pass"),
                        "a stated extraction was refused: %s" % result.get("status"))
        self.assertIn("def sum2(a, b):", (ROOT / base / "pkg" / "calc.py").read_text())

    def test_a_real_measurement_still_passes(self):
        base = _fresh("coverage")
        result = _solve("Measure the test coverage of %s/pkg/calc.py." % base)
        self.assertTrue(result.get("pass"),
                        "a coverage measurement was refused: %s" % result.get("status"))


if __name__ == "__main__":
    unittest.main()
