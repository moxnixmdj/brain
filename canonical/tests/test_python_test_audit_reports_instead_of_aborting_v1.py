#!/usr/bin/env python3
"""The Python test-corpus audit is a REPORT, so it must report a red corpus.

`python.tests.audit.unittest` exists to answer one question: run this corpus and
tell me the pass rate. For its whole life it did the opposite -- on the first
file that exited nonzero it raised `TEST_FILE_FAILED` and never wrote the
report. So the only corpus it could ever report on was one that was already
green, which means the rate it reported was always 100 percent and carried no
information whatsoever. A pass-rate report that can only ever say "everything
passed" is not a pass-rate report.

These tests pin the behaviour that makes it one:

* a red corpus still produces the report, and EVERY file is in it;
* a file that dies before unittest prints a summary counts as a failure, not as
  a clean file with zero tests -- the one way this report could lie;
* the rate is exact over tests plus crashes;
* `output_verified` stays strict, so "the corpus is clean" is still a separate
  and still-true statement;
* the report carries why each red file is red.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

_ADAPTER = (
    pathlib.Path(__file__).resolve().parents[1]
    / "runtime"
    / "bound_capabilities"
    / "python_test_audit.py"
)

OK_TWO = """
import unittest
class T(unittest.TestCase):
    def test_a(self): self.assertTrue(True)
    def test_b(self): self.assertTrue(True)
if __name__ == "__main__": unittest.main()
"""

OK_ONE = """
import unittest
class T(unittest.TestCase):
    def test_a(self): self.assertTrue(True)
if __name__ == "__main__": unittest.main()
"""

FAILS = """
import unittest
class T(unittest.TestCase):
    def test_a(self): self.assertEqual(1, 2, "deliberate mismatch")
if __name__ == "__main__": unittest.main()
"""

ERRORS = """
import unittest
class T(unittest.TestCase):
    def test_a(self): raise ValueError("deliberate explosion")
if __name__ == "__main__": unittest.main()
"""

# Dies at import, before unittest ever prints "Ran N tests".
CRASHES = "import module_that_does_not_exist_anywhere\n"


class PythonTestAuditReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(_ADAPTER.is_file(), _ADAPTER)
        spec = importlib.util.spec_from_file_location(
            "project_brain_bound_python_test_audit", _ADAPTER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        self.module = module
        self.run = module.run

        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.tests_dir = self.tmp / "tests"
        self.tests_dir.mkdir()

    def _write(self, name: str, body: str) -> pathlib.Path:
        path = self.tests_dir / name
        path.write_text(body, encoding="utf-8")
        return path

    def _audit(self, **overrides):
        args = {
            "source_root": "tests",
            "pattern": "test_*.py",
            "output_path": "out/report.json",
            "timeout_s": 60,
        }
        args.update(overrides)
        return self.run(args, self.tmp)

    def _report(self, result) -> dict:
        path = self.tmp / result["output_path"]
        self.assertTrue(path.is_file(), "the report must be written to disk")
        return json.loads(path.read_text(encoding="utf-8"))

    # ---------------------------------------------------------------- report

    def test_a_red_corpus_still_produces_the_report_and_records_every_file(self):
        """The whole point: a corpus with failures still yields a report."""
        self._write("test_ok_one.py", OK_ONE)
        self._write("test_ok_two.py", OK_TWO)
        self._write("test_fails.py", FAILS)
        self._write("test_errors.py", ERRORS)

        result = self._audit()
        report = self._report(result)

        self.assertEqual(report["schema"], "PROJECT_BRAIN_PYTHON_TEST_AUDIT_V1")
        totals = report["totals"]
        self.assertEqual(totals["files"], 4, "no file may be dropped")
        self.assertEqual(totals["tests"], 5)
        self.assertEqual(totals["passed"], 3)
        self.assertEqual(totals["failed"], 1)
        self.assertEqual(totals["errors"], 1)
        self.assertEqual(totals["crashed"], 0)
        # 3 passed out of 5 scored units.
        self.assertEqual(totals["pass_rate"], 0.6)
        self.assertEqual(result["pass_rate"], 0.6)
        self.assertEqual(sorted(r["path"] for r in report["records"]),
                         ["tests/test_errors.py", "tests/test_fails.py",
                          "tests/test_ok_one.py", "tests/test_ok_two.py"])

    def test_the_audit_does_not_stop_at_the_first_red_file(self):
        """Three red files up front must not hide the green one behind them."""
        self._write("test_a_fails.py", FAILS)
        self._write("test_b_fails.py", FAILS)
        self._write("test_c_fails.py", FAILS)
        self._write("test_z_ok.py", OK_TWO)

        result = self._audit()
        report = self._report(result)
        self.assertEqual(result["file_count"], 4)
        self.assertEqual(report["totals"]["files"], 4)
        self.assertEqual(report["totals"]["passed"], 2)
        self.assertEqual(report["totals"]["failed"], 3)

    def test_a_green_corpus_is_still_verified_at_rate_one(self):
        """Fixing the report must not weaken the clean-corpus verdict."""
        self._write("test_ok_one.py", OK_ONE)
        self._write("test_ok_two.py", OK_TWO)

        result = self._audit()
        report = self._report(result)
        self.assertIs(result["output_verified"], True)
        self.assertEqual(report["totals"]["pass_rate"], 1.0)
        self.assertEqual(report["totals"]["crashed"], 0)
        self.assertEqual(report["totals"]["failed"], 0)
        self.assertEqual(report["totals"]["errors"], 0)
        for rec in report["records"]:
            self.assertNotIn("failure_tail", rec, "a green file has no cause")

    # ----------------------------------------------------------- truthfulness

    def test_a_file_that_crashes_before_unittest_runs_counts_as_a_failure(self):
        """The one way this report could lie.

        A file that dies at import prints no "Ran N tests" line, so the naive
        count is zero tests and zero failures -- a hard crash recorded as a
        clean file. That inflates the rate and, worse, makes `output_verified`
        true for a corpus that cannot even be imported.
        """
        self._write("test_crashes.py", CRASHES)
        self._write("test_ok.py", OK_TWO)

        result = self._audit()
        report = self._report(result)

        crashed = [r for r in report["records"] if r["crashed"]]
        self.assertEqual(len(crashed), 1, crashed)
        self.assertEqual(crashed[0]["path"], "tests/test_crashes.py")
        self.assertNotEqual(crashed[0]["exit_code"], 0)
        self.assertEqual(report["totals"]["crashed"], 1)
        self.assertEqual(result["crashed_count"], 1)
        # Two passed tests, one crashed file: 2 of 3 scored units, not 2 of 2.
        self.assertEqual(report["totals"]["pass_rate"], round(2 / 3, 6))
        self.assertIs(
            result["output_verified"], False,
            "a corpus that cannot be imported is not a verified corpus",
        )

    def test_output_verified_is_false_whenever_any_file_exited_nonzero(self):
        """The strict verdict must track the raw exit codes, not the parse."""
        self._write("test_ok.py", OK_TWO)
        self._write("test_fails.py", FAILS)
        self._write("test_crashes.py", CRASHES)

        result = self._audit()
        report = self._report(result)
        red = [r for r in report["records"] if r["exit_code"] != 0]
        self.assertEqual(len(red), 2)
        self.assertIs(result["output_verified"], False)
        self.assertTrue(
            report["totals"]["failed"] + report["totals"]["errors"]
            + report["totals"]["crashed"] > 0,
            "a nonzero exit must be accounted for somewhere in the totals",
        )

    # ------------------------------------------------------------------ cause

    def test_the_report_carries_why_each_red_file_is_red(self):
        """Naming a failing file without its cause is not actionable."""
        self._write("test_fails.py", FAILS)
        self._write("test_errors.py", ERRORS)
        self._write("test_crashes.py", CRASHES)

        report = self._report(self._audit())
        by_path = {r["path"]: r for r in report["records"]}
        self.assertIn("deliberate mismatch", by_path["tests/test_fails.py"]["failure_tail"])
        self.assertIn("deliberate explosion", by_path["tests/test_errors.py"]["failure_tail"])
        self.assertIn("module_that_does_not_exist_anywhere",
                      by_path["tests/test_crashes.py"]["failure_tail"])

    def test_each_record_digests_the_bytes_it_actually_ran(self):
        path = self._write("test_ok.py", OK_ONE)
        report = self._report(self._audit())
        self.assertEqual(report["records"][0]["path"], "tests/test_ok.py")
        self.assertEqual(
            report["records"][0]["sha256"],
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )

    # ------------------------------------------------------- guards untouched

    def test_a_source_root_outside_the_repository_is_still_refused(self):
        with self.assertRaisesRegex(RuntimeError, "PATH_OUTSIDE_REPOSITORY"):
            self._audit(source_root="../escape")

    def test_an_output_path_outside_the_repository_is_still_refused(self):
        with self.assertRaisesRegex(RuntimeError, "PATH_OUTSIDE_REPOSITORY"):
            self._audit(output_path="../escape/report.json")

    def test_an_empty_corpus_is_still_refused(self):
        with self.assertRaisesRegex(RuntimeError, "TEST_AUDIT_EMPTY"):
            self._audit()

    def test_a_missing_source_root_is_still_refused(self):
        with self.assertRaisesRegex(RuntimeError, "TEST_AUDIT_ROOT_MISSING"):
            self._audit(source_root="nowhere")


    # ------------------------------------- the consistency check itself

    def _consistent(self, mutate=None):
        """Build a real report, optionally tamper with it, and re-check it."""
        self._write("test_ok.py", OK_TWO)
        self._write("test_fails.py", FAILS)
        self._write("test_crashes.py", CRASHES)
        result = self._audit()
        raw = (self.tmp / result["output_path"]).read_bytes()
        doc = json.loads(raw.decode("utf-8"))
        records, totals = doc["records"], doc["totals"]
        if mutate is not None:
            mutate(records, totals)
            raw = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
        return result, self.module._report_is_consistent(raw, records, totals)

    def test_an_honest_report_verifies_even_when_the_corpus_is_red(self):
        """`report_verified` is about the account, not about the verdict."""
        result, ok = self._consistent()
        self.assertIs(ok, True)
        self.assertIs(result["report_verified"], True)
        self.assertIs(result["output_verified"], False)
        self.assertLess(result["pass_rate"], 1.0)

    def test_the_check_rejects_a_report_that_hides_a_red_file(self):
        """A file that exited nonzero with nothing counted against it is a lie."""
        def hide(records, totals):
            red = next(r for r in records if r["exit_code"] != 0)
            red["failed"] = 0
            red["errors"] = 0
            red["crashed"] = False
            totals["failed"] = 0
            totals["crashed"] = 0
            totals["pass_rate"] = 1.0
        _, ok = self._consistent(hide)
        self.assertIs(ok, False, "under-counting a red file must not verify")

    def test_the_check_rejects_totals_that_do_not_match_the_records(self):
        def inflate(records, totals):
            totals["passed"] = totals["passed"] + 100
            totals["tests"] = totals["tests"] + 100
        _, ok = self._consistent(inflate)
        self.assertIs(ok, False)

    def test_the_check_rejects_an_inflated_pass_rate(self):
        def inflate_rate(records, totals):
            totals["pass_rate"] = 1.0
        _, ok = self._consistent(inflate_rate)
        self.assertIs(ok, False)

    def test_the_check_rejects_a_clean_verdict_on_a_dirty_file(self):
        def fake_clean(records, totals):
            for r in records:
                r["exit_code"] = 0
        _, ok = self._consistent(fake_clean)
        self.assertIs(ok, False)


    # ---------------------------------------------------------- hung files

    def test_a_file_that_hangs_is_recorded_and_does_not_abort_the_audit(self):
        """A per-file timeout is a result about that file, not a reason to stop.

        This is the same defect one layer down: an unhandled TimeoutExpired
        used to propagate out of the loop and kill the audit partway through
        the corpus, so everything after the slow file went unreported.
        """
        self._write("test_a_hangs.py", "import time\ntime.sleep(600)\n")
        self._write("test_z_ok.py", OK_TWO)

        result = self._audit(timeout_s=1)
        report = self._report(result)

        self.assertEqual(report["totals"]["files"], 2, "the run must reach the end")
        hung = [r for r in report["records"] if r["timed_out"]]
        self.assertEqual(len(hung), 1, hung)
        self.assertEqual(hung[0]["path"], "tests/test_a_hangs.py")
        self.assertNotEqual(hung[0]["exit_code"], 0,
                            "a hung file must never look like a clean exit")
        self.assertTrue(hung[0]["crashed"])
        self.assertEqual(hung[0]["passed"], 0)
        self.assertIn("TIMED_OUT_AFTER_1s", hung[0]["failure_tail"])
        self.assertEqual(report["totals"]["timed_out"], 1)
        self.assertEqual(report["totals"]["crashed"], 1)
        self.assertEqual(result["timed_out_count"], 1)
        # The green file that sorts AFTER the hung one is still reported.
        self.assertEqual(report["totals"]["passed"], 2)
        self.assertIs(result["output_verified"], False)
        self.assertIs(result["report_verified"], True)

    def test_a_hung_file_that_printed_before_hanging_is_still_recorded(self):
        """The partial buffers are bytes, and joining them onto a str raises.

        A hung file that printed nothing hides this, because both buffers are
        then None and the join never happens. This is the case that does.
        """
        self._write(
            "test_a_chatty_hang.py",
            "import sys, time\n"
            "sys.stdout.write('marker_before_the_hang\\n')\n"
            "sys.stdout.flush()\n"
            "time.sleep(600)\n",
        )
        self._write("test_z_ok.py", OK_TWO)

        result = self._audit(timeout_s=1)
        report = self._report(result)
        hung = [r for r in report["records"] if r["timed_out"]]
        self.assertEqual(len(hung), 1, hung)
        self.assertIn("marker_before_the_hang", hung[0]["failure_tail"],
                      "the partial output is evidence and must survive")
        self.assertIn("TIMED_OUT_AFTER_1s", hung[0]["failure_tail"])
        self.assertIs(result["report_verified"], True)
        self.assertEqual(report["totals"]["files"], 2)

    # ------------------------------------------- the strict zero verifier

    def _strict_verdict(self, totals, name):
        from canonical.runtime import astra_runtime as runtime

        rel = "canonical/astra_runtime/tmp/PYTHON_TEST_AUDIT_STRICT_" + name + ".json"
        path = runtime.ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "schema": "PROJECT_BRAIN_PYTHON_TEST_AUDIT_V1",
            "records": [],
            "totals": totals,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        out = runtime._goal_action({
            "type": "assert_python_test_audit_zero",
            "args": {"audit_path": rel},
        })
        return out["verified"]

    def test_the_strict_verifier_still_accepts_a_genuinely_clean_corpus(self):
        self.assertIs(self._strict_verdict(
            {"files": 3, "tests": 10, "passed": 10, "failed": 0, "errors": 0,
             "skipped": 0, "crashed": 0, "timed_out": 0}, "CLEAN"), True)

    def test_the_strict_verifier_refuses_a_corpus_with_a_crashed_file(self):
        """Zero failures and zero errors is not the same as nothing broken.

        A file that dies at import contributes no tests and no failures, so
        tests==passed+skipped holds and the old check called the corpus clean.
        """
        self.assertIs(self._strict_verdict(
            {"files": 3, "tests": 10, "passed": 10, "failed": 0, "errors": 0,
             "skipped": 0, "crashed": 1, "timed_out": 0}, "CRASHED"), False)

    def test_the_strict_verifier_refuses_a_corpus_with_a_hung_file(self):
        self.assertIs(self._strict_verdict(
            {"files": 3, "tests": 10, "passed": 10, "failed": 0, "errors": 0,
             "skipped": 0, "crashed": 1, "timed_out": 1}, "HUNG"), False)


if __name__ == "__main__":
    unittest.main()
