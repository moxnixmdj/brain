"""A capability that cannot be re-inspected can never be accepted -- so inspect it.

The defect, measured on ``e2d7981d``
------------------------------------
``raw_goal_trace_acceptance_v1.INSPECTORS`` held 14 entries.  Three capabilities
that the front door now routes to were not among them, and a capability absent
from that table can never be accepted: the acceptance layer answers
``NO_INDEPENDENT_REINSPECTION_FOR:<cid>``, ``raw_goal_acceptance.pass`` stays
false, and ``live_brain_route_admission_v1`` rolls the artifact back.  The
capability ran, produced a correct answer, and the answer was thrown away.

Measured end to end for "Localize the fault in the python source root D using
the tests and write the report to D/r.json":

    status                = PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED
    raw_goal_acceptance   = NO_INDEPENDENT_REINSPECTION_FOR:python.fault.localize.dynamic.dataflow.v1
    pass                  = false

The same stood for ``python.fault.provenance.interprocedural.value.v1`` and
``python.software.repair.loop.strict_progress.ast.v1``.

What each inspector re-derives, from bytes, without asking the producer
----------------------------------------------------------------------
Localizer: the whole spectrum is rebuilt from the raw per-test trace events the
report itself ships -- ``fail_coverage``, ``pass_coverage``, the Ochiai
coefficient and the score of every ranked row are recomputed and compared.  Each
named line must exist in the file, the ranking must be in its own stated order,
the top row must be a line a failing test actually reached, and every named
symbol must be defined at the span the report claims and own every line it says
it covers.

Provenance: coverage is rebuilt from the raw call observations, and each callee
must really be defined in the named file at the named line.  It deliberately
does NOT reconstruct call sites from the caller's AST -- measured on the report
this capability ships, a class body being created is recorded as a call to the
class from ``<module>``, which is a true edge with no ``ast.Call`` node at that
line, and refusing a true report is as much a defect as passing a false one.

Repair loop: every accepted edit must lower the failure score and continue from
the previous one, the final replays must all pass, and "the source was
restored" is verified by hashing the file on disk against the digest the report
carries -- not by trusting the flag.

These tests must be able to fail.  Each accepting assertion is paired with the
nearest world in which the inspector must refuse.
"""

import ast
import json
import pathlib
import shutil
import sys
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance  # noqa: E402

LOCALIZER = "python.fault.localize.dynamic.dataflow.v1"
PROVENANCE = "python.fault.provenance.interprocedural.value.v1"
REPAIR = "python.software.repair.loop.strict_progress.ast.v1"
MEASURE = "python.repository.acceptance.measure.v1"

_ADAPTERS = {
    LOCALIZER: "python_dynamic_fault_localizer_v1",
    PROVENANCE: "python_interprocedural_value_provenance_v1",
    REPAIR: "python_iterative_software_repair_loop_v1",
    MEASURE: "python_repository_acceptance_measurement_v1",
}


class _Run(unittest.TestCase):
    """One tree and one real report per test, removed by addCleanup.

    The fixture directory must not contain the word "test": path segments are
    BM25 query terms for the routing suites, and a scratch directory named
    test_something would leak into any ranking measured in the same process.
    """

    _NEXT = 0

    def setUp(self):
        import importlib
        import os

        type(self)._NEXT += 1
        self.base = (
            _ROOT
            / "canonical/astra_runtime/tmp"
            / ("reinspect_%d_%d" % (os.getpid(), type(self)._NEXT))
        )
        (self.base / "p" / "tests").mkdir(parents=True)
        (self.base / "p" / "calc.py").write_text("def add(a, b):\n    return a - b\n")
        (self.base / "p" / "tests" / "test_calc.py").write_text(
            "import unittest, calc\n"
            "class T(unittest.TestCase):\n"
            "    def test_a(self):\n"
            "        self.assertEqual(calc.add(1, 2), 3)\n"
        )
        self.addCleanup(shutil.rmtree, self.base, True)
        self.src = self.base / "p"
        self._importlib = importlib

    def produce(self, cid):
        """Run the real adapter and return ``(args, result, report_path)``."""
        module = self._importlib.import_module(
            "canonical.runtime.bound_capabilities." + _ADAPTERS[cid]
        )
        report = self.base / ("%s.json" % _ADAPTERS[cid])
        args = {
            "source_root": str(self.src),
            "test_paths": [],
            "output_path": str(report),
        }
        result = module.run(args, _ROOT)
        self.assertTrue(report.is_file(), "the adapter wrote no report at all")
        return args, result, report

    def inspect(self, cid, args, result):
        inspector = acceptance.INSPECTORS[cid]
        return inspector(args, result, _ROOT)

    def rewrite(self, report, mutate):
        data = json.loads(report.read_text(encoding="utf-8"))
        mutate(data)
        report.write_text(json.dumps(data), encoding="utf-8")


class TheInspectorsExistTests(unittest.TestCase):
    def test_all_three_capabilities_are_registered(self):
        for cid in (LOCALIZER, PROVENANCE, REPAIR, MEASURE):
            self.assertIn(
                cid, acceptance.INSPECTORS,
                "%s has no re-inspector, so it can never be accepted" % cid,
            )

    def test_the_table_did_not_lose_anything(self):
        self.assertGreaterEqual(len(acceptance.INSPECTORS), 18)


class TheLocalizerIsReinspectedTests(_Run):
    def test_a_genuine_report_is_accepted(self):
        args, result, _ = self.produce(LOCALIZER)
        ok, code, info = self.inspect(LOCALIZER, args, result)
        self.assertTrue(ok, code)
        self.assertGreater(info["ranked_lines_recomputed"], 0)

    def test_coverage_that_the_traces_do_not_support_is_refused(self):
        args, result, report = self.produce(LOCALIZER)

        def bump(data):
            data["ranked_lines"][0]["fail_coverage"] += 1

        self.rewrite(report, bump)
        ok, code, _ = self.inspect(LOCALIZER, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "LOCALIZE_FAIL_COVERAGE_NOT_REPRODUCED_FROM_TRACES")

    def test_a_top_line_no_failing_test_reached_is_refused(self):
        args, result, report = self.produce(LOCALIZER)

        def zero(data):
            row = data["ranked_lines"][0]
            row["fail_coverage"] = 0
            row["pass_coverage"] = 1
            row["ochiai"] = 0.0
            row["score"] = 0.0
            row["reasons"] = ["PASSING_TEST_OVERLAP"]
            data["ranked_lines"].sort(key=lambda r: -float(r["score"]))

        self.rewrite(report, zero)
        ok, code, _ = self.inspect(LOCALIZER, args, result)
        self.assertFalse(ok)
        self.assertIn(
            code,
            {"LOCALIZE_TOP_RANKED_LINE_WAS_REACHED_BY_NO_FAILING_TEST",
             "LOCALIZE_FAIL_COVERAGE_NOT_REPRODUCED_FROM_TRACES",
             "LOCALIZE_PASS_COVERAGE_NOT_REPRODUCED_FROM_TRACES"},
        )

    def test_a_symbol_that_is_not_in_the_file_is_refused(self):
        args, result, report = self.produce(LOCALIZER)

        def rename(data):
            data["ranked_symbols"][0]["symbol"] = "subtract"

        self.rewrite(report, rename)
        ok, code, _ = self.inspect(LOCALIZER, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "LOCALIZE_NAMED_SYMBOL_IS_NOT_DEFINED_IN_THE_FILE")

    def test_a_symbol_span_that_disagrees_with_the_source_is_refused(self):
        args, result, report = self.produce(LOCALIZER)

        def stretch(data):
            data["ranked_symbols"][0]["end_lineno"] += 40

        self.rewrite(report, stretch)
        ok, code, _ = self.inspect(LOCALIZER, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "LOCALIZE_SYMBOL_SPAN_DOES_NOT_MATCH_THE_SOURCE")

    def test_a_line_outside_the_file_is_refused(self):
        args, result, report = self.produce(LOCALIZER)

        def inflate(data):
            data["ranked_lines"][0]["line"] = 9000

        self.rewrite(report, inflate)
        ok, code, _ = self.inspect(LOCALIZER, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "LOCALIZE_RANKED_LINE_OUTSIDE_THE_FILE")

    def test_a_missing_report_is_refused(self):
        args, result, report = self.produce(LOCALIZER)
        report.unlink()
        ok, code, _ = self.inspect(LOCALIZER, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "LOCALIZE_REPORT_ABSENT_FROM_DISK")


class TheProvenanceIsReinspectedTests(_Run):
    def test_a_genuine_report_is_accepted(self):
        args, result, _ = self.produce(PROVENANCE)
        ok, code, info = self.inspect(PROVENANCE, args, result)
        self.assertTrue(ok, code)
        self.assertGreater(info["edges_recomputed"], 0)

    def test_a_callee_that_is_not_where_the_report_says_is_refused(self):
        args, result, report = self.produce(PROVENANCE)

        def move(data):
            data["ranked_call_edges"][0]["callee"]["firstlineno"] += 50

        self.rewrite(report, move)
        ok, code, _ = self.inspect(PROVENANCE, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "PROVENANCE_CALLEE_IS_NOT_DEFINED_WHERE_THE_REPORT_SAYS")

    def test_coverage_the_call_observations_do_not_support_is_refused(self):
        args, result, report = self.produce(PROVENANCE)

        def bump(data):
            data["ranked_call_edges"][0]["fail_coverage"] += 1

        self.rewrite(report, bump)
        ok, code, _ = self.inspect(PROVENANCE, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "PROVENANCE_FAIL_COVERAGE_NOT_REPRODUCED_FROM_TRACES")

    def test_an_edge_no_failing_test_crossed_is_refused(self):
        args, result, report = self.produce(PROVENANCE)

        def zero(data):
            row = data["ranked_call_edges"][0]
            row["fail_coverage"] = 0
            row["pass_coverage"] = 1
            row["ochiai"] = 0.0

        self.rewrite(report, zero)
        ok, code, _ = self.inspect(PROVENANCE, args, result)
        self.assertFalse(ok)
        self.assertIn(
            code,
            {"PROVENANCE_FAIL_COVERAGE_NOT_REPRODUCED_FROM_TRACES",
             "PROVENANCE_EDGE_WAS_CROSSED_BY_NO_FAILING_TEST"},
        )

    def test_a_missing_report_is_refused(self):
        args, result, report = self.produce(PROVENANCE)
        report.unlink()
        ok, code, _ = self.inspect(PROVENANCE, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "PROVENANCE_REPORT_ABSENT_FROM_DISK")


class TheRepairLoopIsReinspectedTests(_Run):
    def test_a_genuine_report_is_accepted(self):
        args, result, _ = self.produce(REPAIR)
        ok, code, info = self.inspect(REPAIR, args, result)
        self.assertTrue(ok, code)
        self.assertGreater(info["sources_hashed"], 0)

    def test_an_edit_that_made_no_progress_is_refused(self):
        args, result, report = self.produce(REPAIR)

        def stall(data):
            data["accepted_edits"][0]["score_after"] = data["accepted_edits"][0]["score_before"]

        self.rewrite(report, stall)
        ok, code, _ = self.inspect(REPAIR, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "REPAIR_EDIT_MADE_NO_STRICT_PROGRESS")

    def test_a_loop_that_never_reached_a_passing_suite_is_refused(self):
        args, result, report = self.produce(REPAIR)

        def stall(data):
            data["accepted_edits"][0]["score_after"] = 1
            data["accepted_edits"][0]["score_before"] = 2
            data["baseline_failure_score"] = 2

        self.rewrite(report, stall)
        ok, code, _ = self.inspect(REPAIR, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "REPAIR_LOOP_DID_NOT_REACH_A_PASSING_SUITE")

    def test_a_source_left_modified_while_claiming_restored_is_refused(self):
        """The promise is checked against the bytes, not against the flag."""
        args, result, _ = self.produce(REPAIR)
        (self.src / "calc.py").write_text("def add(a, b):\n    return a + b\n")
        ok, code, detail = self.inspect(REPAIR, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "REPAIR_LEFT_THE_SOURCE_MODIFIED_WHILE_CLAIMING_RESTORED")
        self.assertNotEqual(detail["on_disk"], detail["claimed"])

    def test_a_failing_final_replay_is_refused(self):
        args, result, report = self.produce(REPAIR)

        def fail(data):
            data["final_verification_replays"][0]["returncode"] = 1

        self.rewrite(report, fail)
        ok, code, _ = self.inspect(REPAIR, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "REPAIR_FINAL_REPLAY_DOES_NOT_PASS")

    def test_a_missing_report_is_refused(self):
        args, result, report = self.produce(REPAIR)
        report.unlink()
        ok, code, _ = self.inspect(REPAIR, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "REPAIR_REPORT_ABSENT_FROM_DISK")


class TheHelpersAreHonestTests(_Run):
    def test_the_ochiai_coefficient_is_the_producers_own_formula(self):
        """f / sqrt(F * (f + q)) -- a line no failing test reached scores zero."""
        self.assertAlmostEqual(acceptance._ochiai(1, 0, 1), 1.0)
        self.assertEqual(acceptance._ochiai(0, 5, 3), 0.0)
        self.assertAlmostEqual(acceptance._ochiai(2, 2, 4), 2 / (16 ** 0.5))

    def test_line_coverage_refuses_a_trace_naming_a_file_that_is_not_there(self):
        traces = [{"pass": False, "events": [["no/such/file.py", 1, "f", 1]]}]
        self.assertIsNone(acceptance._trace_line_coverage(traces, _ROOT))

    def test_call_coverage_refuses_a_trace_naming_a_file_that_is_not_there(self):
        traces = [{
            "pass": False,
            "events": [{"event": "call", "callee": {"path": "no/such/file.py",
                                                    "function": "f"}}],
        }]
        self.assertIsNone(acceptance._trace_call_coverage(traces, _ROOT))

    def test_the_module_still_parses(self):
        ast.parse((_ROOT / "canonical/runtime/raw_goal_trace_acceptance_v1.py").read_bytes())


class ACommandlineThatNamesNoTestIsNotARunnerTests(_Run):
    """The second gate in the same lane: a bound argv with no target runs nothing.

    Measured on ``e2d7981d``, "Run the iterative repair loop on the python source
    root D using the tests" reached the right capability, which then raised
    ``RepairLoopError:BASELINE_ALREADY_PASSES`` against a suite that really was
    failing.  The bound ``test_argv`` was ``[python3, "-c", script]`` -- the
    generated runner reads its targets from ``sys.argv[1:]`` and there were none,
    so it executed zero suites and exited 0.

    Six adapters shared the shape ``args.get("test_argv") or suite_argv(...)``,
    which derives only when the value is MISSING.  A value that is present but
    empty of targets is worse than a missing one, because it looks bound.  All
    six now call ``argv_or_derived``.
    """

    def test_a_command_line_with_no_target_names_nothing(self):
        from canonical.runtime.bound_capabilities import (
            python_test_guided_patch_search_v1 as ptg,
        )

        self.assertFalse(ptg.argv_names_a_target([]))
        self.assertFalse(ptg.argv_names_a_target(None))
        self.assertFalse(ptg.argv_names_a_target(["/usr/bin/python3", "-c", "print(1)"]))

    def test_a_command_line_with_a_target_names_something(self):
        from canonical.runtime.bound_capabilities import (
            python_test_guided_patch_search_v1 as ptg,
        )

        self.assertTrue(
            ptg.argv_names_a_target(["/usr/bin/python3", "-c", "print(1)", "t.py"])
        )
        self.assertTrue(ptg.argv_names_a_target(["/usr/bin/python3", "-m", "pytest", "t.py"]))

    def test_an_empty_of_targets_command_line_derives_instead(self):
        from canonical.runtime.bound_capabilities import (
            python_test_guided_patch_search_v1 as ptg,
        )

        target = self.src / "tests" / "test_calc.py"
        derived = ptg.argv_or_derived(
            ["/usr/bin/python3", "-c", "print(1)"], "/usr/bin/python3", target
        )
        self.assertIn(str(target), derived)

    def test_a_command_line_that_names_a_target_is_kept_verbatim(self):
        from canonical.runtime.bound_capabilities import (
            python_test_guided_patch_search_v1 as ptg,
        )

        supplied = ["/usr/bin/python3", "-c", "print(1)", "my_suite.py"]
        self.assertEqual(
            ptg.argv_or_derived(supplied, "/usr/bin/python3", "other.py"), supplied
        )

    def test_every_site_that_consumed_test_argv_verbatim_now_derives(self):
        """Eleven named and three wired is a defect; this pins all six."""
        import re

        base = _ROOT / "canonical/runtime/bound_capabilities"
        offenders = []
        for path in sorted(base.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if re.search(r'args\.get\(["\']test_argv["\']\)\s*or\s', line):
                    offenders.append("%s: %s" % (path.name, line.strip()[:90]))
        self.assertEqual(
            offenders, [],
            "these sites still use a supplied test_argv verbatim, so an argv "
            "with no target still runs zero suites and exits 0: %s" % offenders,
        )

    def test_the_repair_loop_sees_a_failing_baseline_through_a_bound_argv(self):
        """The end-to-end negative control for the whole class."""
        from canonical.runtime.bound_capabilities import (
            python_iterative_software_repair_loop_v1 as loop,
        )

        args = {
            "source_root": str(self.src),
            "test_paths": [],
            # A command line that is present, looks bound, and names no suite.
            "test_argv": ["/usr/bin/python3", "-c", "import sys"],
            "output_path": str(self.base / "loop.json"),
        }
        result = loop.run(args, _ROOT)
        self.assertTrue(result["pass"], result.get("status"))
        self.assertEqual(result["accepted_edit_count"], 1)
        self.assertIs(result["source_restored"], True)


class TheMeasurementIsReinspectedTests(_Run):
    """The capability that answers "run the tests" -- the most ordinary sentence.

    Measured on ``a5a0230``, "Run the tests for the python source root D" and
    "Write the tests for the python source root D" both reached
    ``python.repository.acceptance.measure.v1``, ran, wrote a correct 4618-byte
    report, and had it rolled back with
    ``NO_INDEPENDENT_REINSPECTION_FOR:python.repository.acceptance.measure.v1``.

    The inspector re-hashes every file in the report's own subject manifest,
    recomputes the Python file count and the parse verdict, and RUNS THE SUITE
    AGAIN to confirm the exit status and the test count reproduce.  It does not
    compare the captured stderr's digest: the producer runs the suite in a copied
    workspace, so its stderr embeds that path and a re-run legitimately differs.
    """

    def test_a_genuine_report_is_accepted(self):
        args, result, _ = self.produce(MEASURE)
        ok, code, info = self.inspect(MEASURE, args, result)
        self.assertTrue(ok, code)
        self.assertGreater(info["subject_files_rehashed"], 0)
        self.assertGreater(info["python_files_reparsed"], 0)

    def test_a_passing_verdict_the_return_code_does_not_support_is_refused(self):
        args, result, report = self.produce(MEASURE)

        def lie(data):
            data["measurements"]["tests_pass"] = True

        self.rewrite(report, lie)
        ok, code, _ = self.inspect(MEASURE, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "MEASURE_PASS_VERDICT_DOES_NOT_FOLLOW_FROM_THE_RETURN_CODE")

    def test_a_return_code_the_evidence_does_not_support_is_refused(self):
        args, result, report = self.produce(MEASURE)

        def lie(data):
            data["test_evidence"]["returncode"] = 0

        self.rewrite(report, lie)
        ok, code, _ = self.inspect(MEASURE, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "MEASURE_RETURN_CODE_DISAGREES_WITH_ITS_EVIDENCE")

    def test_a_file_count_that_is_not_in_the_tree_is_refused(self):
        args, result, report = self.produce(MEASURE)

        def lie(data):
            data["measurements"]["python_file_count"] = 7

        self.rewrite(report, lie)
        ok, code, _ = self.inspect(MEASURE, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "MEASURE_PYTHON_FILE_COUNT_NOT_REPRODUCED")

    def test_a_manifest_digest_that_is_not_the_file_on_disk_is_refused(self):
        args, result, report = self.produce(MEASURE)

        def lie(data):
            data["subject"]["manifest"][0]["bytes"] = 999

        self.rewrite(report, lie)
        ok, code, _ = self.inspect(MEASURE, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "MEASURE_SUBJECT_FILE_CHANGED_SINCE_THE_MEASUREMENT")

    def test_a_tree_that_gained_a_file_since_the_measurement_is_refused(self):
        args, result, _ = self.produce(MEASURE)
        (self.src / "extra.py").write_text("x = 1\n")
        ok, code, detail = self.inspect(MEASURE, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "MEASURE_SUBJECT_IS_NOT_THE_TREE_ON_DISK")
        self.assertIn("extra.py", detail["not_in_report"])

    def test_a_test_count_the_suite_does_not_reproduce_is_refused(self):
        args, result, report = self.produce(MEASURE)

        def lie(data):
            data["test_evidence"]["test_count"] = 42
            data["measurements"]["test_count"] = 42

        self.rewrite(report, lie)
        ok, code, _ = self.inspect(MEASURE, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "MEASURE_TEST_COUNT_NOT_REPRODUCED_BY_THE_RE_RUN")

    def test_a_command_line_that_names_no_suite_is_refused(self):
        """The empty-runner defect cannot hide inside a measurement report."""
        args, result, report = self.produce(MEASURE)

        def empty(data):
            argv = data["measurement_spec"]["test_argv"]
            del argv[3:]

        self.rewrite(report, empty)
        ok, code, _ = self.inspect(MEASURE, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "MEASURE_TEST_ARGV_NAMES_NO_SUITE")

    def test_a_missing_report_is_refused(self):
        args, result, report = self.produce(MEASURE)
        report.unlink()
        ok, code, _ = self.inspect(MEASURE, args, result)
        self.assertFalse(ok)
        self.assertEqual(code, "MEASURE_REPORT_ABSENT_FROM_DISK")

    def test_the_canonical_digest_matches_the_producers_own_form(self):
        """ensure_ascii=False: a re-derivation that differs refuses a true report."""
        from canonical.runtime.bound_capabilities import (
            python_repository_acceptance_measurement_v1 as producer,
        )

        rows = [{"path": "a.py", "bytes": 1, "sha256": "x"}, {"path": "é.py", "bytes": 2,
                                                          "sha256": "y"}]
        self.assertEqual(
            acceptance._measure_canon_sha256(rows), producer._sha_obj(rows)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
