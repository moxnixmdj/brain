"""Tests for the governed pipe runner.

The point of this module is that composition does not cost governance: an
argv list can be allowlisted and reasoned about, a shell string cannot. So
the tests assert both halves -- that a chain of any length really runs, and
that a chain which is not well formed runs NOT AT ALL rather than partly.
"""

import os
import pathlib
import shutil
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import pipeline_exec_v1 as P  # noqa: E402
from canonical.runtime.computer_env_v1 import _run_pipeline  # noqa: E402

SCRATCH = "canonical/astra_runtime/tmp/pipex"


class TestAChainOfAnyLengthRuns(unittest.TestCase):

    LINES = "b\na\nc\na\nb\na\n"

    def setUp(self):
        self.root = ROOT / SCRATCH
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "f.txt").write_text(self.LINES, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_three_stages_answer_a_question_no_single_program_can(self):
        # "how many different lines are in this file" -- three programs.
        code, out = P.run_stages(
            [["cat", "f.txt"], ["sort", "-u"], ["wc", "-l"]],
            str(self.root), timeout=10.0)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), b"3")

    def test_four_stages_are_not_a_special_case(self):
        code, out = P.run_stages(
            [["cat", "f.txt"], ["sort"], ["uniq", "-c"], ["sort", "-rn"]],
            str(self.root), timeout=10.0)
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith(b"      3 a"), out)

    def test_one_stage_is_a_plain_command(self):
        code, out = P.run_stages([["cat", "f.txt"]], str(self.root),
                                 timeout=10.0)
        self.assertEqual(code, 0)
        self.assertEqual(out.decode(), self.LINES)

    def test_the_status_is_the_last_stage_s(self):
        # `cat` of a missing file fails, but the chain's status is `wc`'s.
        code, _out = P.run_stages(
            [["cat", "nope.txt"], ["wc", "-l"]], str(self.root), timeout=10.0)
        self.assertEqual(code, 0)

    def test_two_stages_agree_with_the_caller_that_asked_for_two(self):
        # The delegation must not have changed what `_run_pipeline` returns:
        # it is the same code path now, and this pins that.
        a = _run_pipeline(["cat", "f.txt"], ["sort", "-u"], str(self.root),
                          timeout=10.0)
        b = P.run_stages([["cat", "f.txt"], ["sort", "-u"]], str(self.root),
                         timeout=10.0)
        self.assertEqual(a, b)
        self.assertEqual(a[1], b"a\nb\nc\n")


class TestAMalformedChainRunsNotAtAll(unittest.TestCase):
    """Fail closed means refusing, not running the first two of four."""

    def setUp(self):
        self.root = ROOT / SCRATCH
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "touch.txt").write_text("", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_an_empty_chain_is_refused(self):
        self.assertEqual(P.run_stages([], str(self.root)), (None, b""))

    def test_an_empty_stage_is_refused(self):
        self.assertEqual(
            P.run_stages([["cat", "touch.txt"], []], str(self.root)),
            (None, b""))

    def test_an_integer_element_is_accepted_and_becomes_a_string(self):
        # The learner builds these: ["head", "-n", 7, "probe.txt"].  Refusing
        # them is what turned two passing pipeline tests into
        # OPEN__NOTHING_MEASURED_IT.
        (self.root / "n.txt").write_text("a\nb\nc\n", encoding="utf-8")
        code, out = P.run_stages([["head", "-n", 2, "n.txt"]], str(self.root),
                                 timeout=10.0)
        self.assertEqual(code, 0)
        self.assertEqual(out, b"a\nb\n")

    def test_an_element_that_is_neither_string_nor_int_is_refused(self):
        self.assertEqual(
            P.run_stages([["cat", None]], str(self.root)), (None, b""))
        self.assertEqual(
            P.run_stages([["cat", ["x"]]], str(self.root)), (None, b""))

    def test_an_empty_string_argument_is_passed_through_not_refused(self):
        # The learner builds ["sort", "-d", "", "probe.txt"]: a flag given an
        # empty value because the sentence stated no pattern.  Refusing it
        # silently emptied the probe and broke two pipeline tests.  Whether
        # the answer is USEFUL is the learner's call, not this function's.
        (self.root / "s.txt").write_text("b\na\n", encoding="utf-8")
        code, out = P.run_stages([["cat", "s.txt"], ["sort", "-d", ""]],
                                 str(self.root), timeout=10.0)
        self.assertIsNotNone(code, "an empty argument must still run")

    def test_too_many_stages_is_refused(self):
        chain = [["cat", "touch.txt"]] * (P.MAX_STAGES + 1)
        self.assertEqual(P.run_stages(chain, str(self.root)), (None, b""))

    def test_a_program_that_does_not_exist_is_refused_not_raised(self):
        code, out = P.run_stages([["definitely-not-a-program-xyz"]],
                                 str(self.root))
        self.assertIsNone(code)
        self.assertEqual(out, b"")

    def test_a_refused_chain_leaves_no_partial_work_behind(self):
        # If a malformed chain ran its head stage, this file would be gone.
        P.run_stages([["rm", "touch.txt"], []], str(self.root))
        self.assertTrue((self.root / "touch.txt").exists())


class TestAChainIsBounded(unittest.TestCase):

    def setUp(self):
        self.root = ROOT / SCRATCH
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_stage_that_never_stops_talking_is_killed_not_waited_for(self):
        # The failure this prevents is silent: an undrained pipe fills, the
        # process is killed, and a whole run vanishes with no traceback.
        started = time.monotonic()
        code, _out = P.run_stages(
            [["python3", "-c",
              "import sys\nwhile True: sys.stdout.write('x' * 4096)"]],
            str(self.root), timeout=1.0)
        self.assertLess(time.monotonic() - started, 8.0)
        self.assertEqual(code, -9)

    def test_output_is_capped_at_max_bytes(self):
        _code, out = P.run_stages(
            [["python3", "-c", "print('y' * 100000)"]],
            str(self.root), timeout=10.0, max_bytes=256)
        self.assertEqual(len(out), 256)

    def test_the_head_of_a_pipe_does_not_hang_waiting_on_a_terminal(self):
        # `cat` with no operand reads stdin. Fed DEVNULL it returns at once;
        # fed a terminal it would block until the deadline.
        started = time.monotonic()
        code, out = P.run_stages([["cat"]], str(self.root), timeout=5.0)
        self.assertLess(time.monotonic() - started, 5.0)
        self.assertEqual(code, 0)
        self.assertEqual(out, b"")


if __name__ == "__main__":
    unittest.main()
