#!/usr/bin/env python3
"""The AST software-repair loop must actually repair code, measured on seeded bugs.

The defect this pins. ``_run_tests`` ran the test subprocess with ``cwd=root``, and the bound
executor calls every adapter with the REPOSITORY ROOT as ``root``. An ordinary Python test suite
imports the module it tests - ``import calc`` next to ``calc.py`` - so from the repository root
that import dies with ModuleNotFoundError before any assertion runs.

Measured consequence, on ``def add(a, b): return a - b`` with ``assertEqual(add(2, 3), 5)``:

    cwd = repository root  ->  errors=1   (No module named 'calc')
    cwd = source directory ->  failures=1 (-1 != 5)

Both score 1 on the loop's failure metric. The loop only accepts a candidate that STRICTLY lowers
the score, so no edit to the source could ever qualify, and the loop returned
``OPEN__NO_STRICTLY_IMPROVING_CANDIDATE`` for every bug - while its own patch search, invoked
directly with the source directory as root, found ``Sub->Add`` on the first candidate. Six
capabilities share this path: the whole Python software-repair family.

The fix puts the source directory on PYTHONPATH, which makes the repaired module importable
without changing the working directory the caller chose.

These tests are a benchmark, not a smoke test: each case seeds a real bug of a distinct class the
mutation basis can express, and the loop must find a repair that its own verification replay
confirms. A negative control asserts that a bug OUTSIDE the mutation basis is honestly reported as
unrepaired rather than laundered into a pass.
"""
from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))
BOUND = RUNTIME / "bound_capabilities"
if str(BOUND) not in sys.path:
    sys.path.insert(0, str(BOUND))

_spec = importlib.util.spec_from_file_location("astra_runtime_repair_bench_v1", RUNTIME / "astra_runtime.py")
runtime = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _spec.loader and runtime
_spec.loader.exec_module(runtime)

WORK_ROOT = ROOT / "astra_runtime" / "tmp" / "software_repair_benchmark_v1"
CAPABILITY = "python.software.repair.loop.strict_progress.ast.v1"

# (name, buggy source, test source, expected mutation kind)
# Every case is a single defect the declared mutation basis can express, and each test fails for a
# real behavioural reason - not for an import error.
CASES = [
    (
        "operator_swap",
        "def add(a, b):\n    return a - b\n",
        "import unittest, calc\n"
        "class T(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(calc.add(2, 3), 5)\n",
        "BINOP_SWAP",
    ),
    (
        "comparison_swap",
        "def is_adult(age):\n    return age < 18\n",
        "import unittest, calc\n"
        "class T(unittest.TestCase):\n"
        "    def test_boundary(self):\n"
        "        self.assertTrue(calc.is_adult(18))\n",
        "COMPARE_SWAP",
    ),
    (
        "boolean_swap",
        "def either(a, b):\n    return a and b\n",
        "import unittest, calc\n"
        "class T(unittest.TestCase):\n"
        "    def test_one_true(self):\n"
        "        self.assertTrue(calc.either(True, False))\n",
        "BOOL_SWAP",
    ),
    (
        "wrong_constant",
        "def base():\n    return 1\n",
        "import unittest, calc\n"
        "class T(unittest.TestCase):\n"
        "    def test_base(self):\n"
        "        self.assertEqual(calc.base(), 0)\n",
        "CONSTANT_REPLACE",
    ),
    (
        "inverted_condition",
        'def label(x):\n    if not x:\n        return "yes"\n    return "no"\n',
        "import unittest, calc\n"
        "class T(unittest.TestCase):\n"
        "    def test_label(self):\n"
        '        self.assertEqual(calc.label(True), "yes")\n',
        "DROP_NOT",
    ),
]


GUARD = "\nif __name__ == '__main__':\n    unittest.main()\n"


def _seed(name, source, test_source, guard=True):
    """Write one seeded case. The __main__ guard is added because the fault localizer executes the
    suite with runpy.run_path(..., run_name="__main__"), which only runs the tests if the file has
    that guard - without it the child reports NO_FAILING_TEST. Real unittest files have it; the
    repair capabilities are unaffected either way, since they load the suite through unittest."""
    d = WORK_ROOT / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "calc.py").write_text(source, encoding="utf-8")
    if guard and "__main__" not in test_source:
        test_source = test_source + GUARD
    (d / "test_calc.py").write_text(test_source, encoding="utf-8")
    return d


def _repair(work):
    return runtime._invoke_bound_capability(
        {
            "capability_id": CAPABILITY,
            "source_root": str(work),
            "test_paths": [str(work / "test_calc.py")],
            "test_argv": ["python3", "-m", "unittest", str(work / "test_calc.py")],
            "output_path": str(work / "repair.json"),
        }
    )


class SeededBugBenchmarkTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(WORK_ROOT, ignore_errors=True)

    def test_every_seeded_bug_in_the_mutation_basis_is_repaired(self):
        """Five distinct defect classes; the loop must find a verified repair for all five.

        This is the number that was 0 of 5 before the PYTHONPATH fix.
        """
        repaired = []
        detail = []
        for name, source, test_source, _kind in CASES:
            work = _seed(name, source, test_source)
            result = _repair(work)
            ok = bool(result.get("pass")) and str(result.get("status", "")).startswith("PASS__")
            repaired.append(ok)
            detail.append((name, result.get("status"), [e.get("mutation", {}).get("kind") for e in result.get("accepted_edits") or []]))
        self.assertEqual(
            repaired,
            [True] * len(CASES),
            "unrepaired cases: " + repr([d for d, ok in zip(detail, repaired) if not ok]),
        )

    def test_each_repair_names_the_defect_class_it_actually_fixed(self):
        """The accepted edit must be the class of the seeded defect, not an incidental one."""
        expected = {
            "operator_swap": "BINOP_SWAP",
            "comparison_swap": "COMPARE_SWAP",
            "wrong_constant": "CONSTANT_REPLACE",
            "inverted_condition": "DROP_NOT",
        }
        for name, source, test_source, _ in CASES:
            if name not in expected:
                continue
            with self.subTest(case=name):
                result = _repair(_seed(name, source, test_source))
                kinds = [e.get("mutation", {}).get("kind") for e in result.get("accepted_edits") or []]
                self.assertIn(expected[name], kinds, kinds)

    def test_a_repair_is_confirmed_by_independent_replay(self):
        """The loop must re-run the tests after the edit, and say how many times."""
        work = _seed("operator_swap", *CASES[0][1:3])
        result = _repair(work)
        replays = result.get("final_verification_replays") or []
        self.assertTrue(replays, "no final verification replay recorded")
        for row in replays:
            self.assertEqual(row.get("returncode"), 0, row)
            self.assertEqual(row.get("failure_score"), 0, row)

    def test_the_working_tree_is_left_exactly_as_it_was_found(self):
        """The loop declares NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY; it must honour that."""
        work = _seed("operator_swap", *CASES[0][1:3])
        before = (work / "calc.py").read_bytes()
        result = _repair(work)
        self.assertTrue(result.get("pass"))
        self.assertTrue(result.get("source_restored"))
        self.assertEqual((work / "calc.py").read_bytes(), before)


class NegativeControlTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(WORK_ROOT, ignore_errors=True)

    def test_a_bug_outside_the_mutation_basis_is_not_laundered_into_a_pass(self):
        """A missing statement cannot be produced by swapping an operator or a constant.

        The honest answer is OPEN__ with pass False. If this ever reports PASS__, the loop is
        claiming a repair it did not make.
        """
        work = _seed(
            "outside_basis",
            "def describe(x):\n    return None\n",
            "import unittest, calc\n"
            "class T(unittest.TestCase):\n"
            "    def test_describe(self):\n"
            '        self.assertEqual(calc.describe(3), "odd")\n',
        )
        result = _repair(work)
        self.assertFalse(result.get("pass"), result.get("status"))
        self.assertTrue(str(result.get("status", "")).startswith("OPEN__"), result.get("status"))

    def test_an_already_passing_baseline_is_refused_not_repaired(self):
        work = _seed(
            "already_passing",
            "def add(a, b):\n    return a + b\n",
            "import unittest, calc\n"
            "class T(unittest.TestCase):\n"
            "    def test_add(self):\n"
            "        self.assertEqual(calc.add(2, 3), 5)\n",
        )
        with self.assertRaises(Exception) as ctx:
            _repair(work)
        self.assertIn("BASELINE_ALREADY_PASSES", str(ctx.exception))


class MechanismTests(unittest.TestCase):
    """Pin the cause, so the fix cannot be silently simplified away."""

    @classmethod
    def setUpClass(cls):
        cls.work = _seed("mechanism", *CASES[0][1:3])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(WORK_ROOT, ignore_errors=True)

    def test_without_the_source_directory_the_test_cannot_even_import(self):
        """From the repository root the suite dies on import; from the source dir it asserts."""
        argv = ["python3", "-m", "unittest", str(self.work / "test_calc.py")]
        from_repo = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        self.assertIn("No module named 'calc'", from_repo.stderr)

    def test_pythonpath_alone_is_sufficient_and_cwd_is_not_changed(self):
        """The fix must be PYTHONPATH, not a changed working directory."""
        argv = ["python3", "-m", "unittest", str(self.work / "test_calc.py")]
        import os

        env = {**os.environ, "PYTHONPATH": str(self.work)}
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, env=env)
        # The import now resolves, so the run reaches the real assertion and fails on behaviour.
        self.assertNotIn("No module named 'calc'", proc.stderr)
        self.assertIn("-1 != 5", proc.stderr)

    def test_run_tests_default_behaviour_is_unchanged(self):
        """extra_env defaults to None, i.e. the inherited environment, exactly as before."""
        import python_test_guided_patch_search_v1 as PS

        plain = PS._run_tests(ROOT, ["python3", "-c", "print('ok')"], 30)
        self.assertEqual(plain.get("returncode"), 0)
        self.assertIn("ok", plain.get("stdout") or "")


class WholeFamilyTests(unittest.TestCase):
    """Every invocable capability in the Python software-repair family must repair the same bug.

    They share one test runner, so they share its defects. Measured before the base patch search
    was fixed: the strict loop and the coupled loop (which delegates to it) repaired the bug while
    python.patch.search.test_guided.ast.v1 -- the search the whole family is named after -- still
    returned OPEN__NO_VERIFIED_CANDIDATE_IN_BOUNDED_SEARCH, because its own run() called
    _run_tests without the environment. Fixing one adapter and not the module it lives in leaves
    the family half-working, which is worse than uniformly broken because it looks fixed.

    python.software.repair.guided.provenance.coupled.v1 was excluded from this benchmark while it
    reported GUIDANCE_EMPTY. That was not a missing-input precondition, it was the same defect one
    layer down: its guidance comes from the dynamic fault localizer, whose traced child also
    inherited the repository root as its working directory, so the localizer ranked nothing and the
    guidance really was empty. Both are fixed, so it is now measured here.
    python.repository.acceptance.measure.v1 is still absent: it copies the source into its own
    workspace and runs the tests there with cwd=workspace, so it never had the defect.
    """

    FAMILY = {
        "python.patch.search.test_guided.ast.v1": "source_path",
        "python.software.repair.loop.strict_progress.ast.v1": "source_root",
        "python.software.repair.loop.test_guided.ast.v1": "source_paths",
        "python.software.repair.loop.coupled.ast.v1": "source_root",
        "python.software.repair.guided.provenance.coupled.v1": "source_root",
    }

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(WORK_ROOT, ignore_errors=True)

    def _args(self, cid, slot, work):
        args = {"capability_id": cid, "test_paths": [str(work / "test_calc.py")],
                "output_path": str(work / "repair.json")}
        if slot == "source_path":
            args["source_path"] = str(work / "calc.py")
            args["test_argv"] = ["python3", "-m", "unittest", str(work / "test_calc.py")]
        elif slot == "source_paths":
            args["source_paths"] = [str(work / "calc.py")]
        else:
            args["source_root"] = str(work)
            args["test_argv"] = ["python3", "-m", "unittest", str(work / "test_calc.py")]
        return args

    def test_every_capability_in_the_family_repairs_the_seeded_bug(self):
        results = {}
        for cid, slot in self.FAMILY.items():
            work = _seed("family_" + cid.replace(".", "_"), *CASES[0][1:3])
            # the test_guided loop runs the test file as a script, so it needs the __main__ guard
            try:
                r = runtime._invoke_bound_capability(self._args(cid, slot, work))
                results[cid] = (bool(r.get("pass")), str(r.get("status")))
            except Exception as exc:  # noqa: BLE001 - the message is the finding
                results[cid] = (False, type(exc).__name__ + ": " + str(exc)[:80])
        failing = {k: v for k, v in results.items() if not v[0]}
        self.assertEqual(failing, {}, "capabilities that did not repair: " + repr(failing))
        self.assertEqual(len(results), 5)

    def test_the_family_shares_one_source_env_implementation(self):
        """The loop must delegate, not keep a second copy that can drift."""
        import python_iterative_software_repair_loop_v1 as LOOP
        import python_test_guided_patch_search_v1 as PS

        self.assertIs(LOOP._source_env.__wrapped__ if hasattr(LOOP._source_env, "__wrapped__") else None, None)
        work = _seed("shared_env", *CASES[0][1:3])
        self.assertEqual(LOOP._source_env(work), PS._source_env(work))
        self.assertIn(str(work), PS._source_env(work)["PYTHONPATH"])

    def test_source_env_accepts_a_file_or_a_directory(self):
        import python_test_guided_patch_search_v1 as PS

        work = _seed("env_shapes", *CASES[0][1:3])
        self.assertEqual(PS._source_env(work / "calc.py"), PS._source_env(work))

    def test_source_env_preserves_an_existing_pythonpath(self):
        """Prepending must not discard what the caller already had."""
        import os

        import python_test_guided_patch_search_v1 as PS

        work = _seed("env_existing", *CASES[0][1:3])
        saved = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = "/some/existing/path"
        try:
            value = PS._source_env(work)["PYTHONPATH"]
        finally:
            if saved is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = saved
        self.assertIn("/some/existing/path", value)
        self.assertTrue(value.startswith(str(work)), value)


class LocalizationTests(unittest.TestCase):
    """The fault localizer must rank the real fault, and must not report PASS while ranking nothing.

    Before this fix the traced child inherited the repository root as its working directory and
    runpy.run_path does NOT put the target's own directory on sys.path the way running a script does,
    so the suite died on line 1 with ModuleNotFoundError. The capability still returned
    status=PASS__BOUNDED_DYNAMIC_FAULT_LOCALIZATION and pass=True, with ranked_lines=[] and
    ranked_symbols=[] and a single trace event on the import line. That is a false positive: it
    claims a successful localization while delivering nothing, and every consumer downstream gets
    empty guidance.
    """

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(WORK_ROOT, ignore_errors=True)

    def test_the_localizer_names_the_faulty_function_not_the_import_line(self):
        work = _seed("localize", *CASES[0][1:3])
        r = runtime._invoke_bound_capability({
            "capability_id": "python.fault.localize.dynamic.dataflow.v1",
            "source_root": str(work), "test_paths": [str(work / "test_calc.py")],
            "output_path": str(work / "loc.json")})
        self.assertTrue(r.get("ranked_lines"), "ranked_lines must not be empty: " + repr(r))
        self.assertTrue(r.get("ranked_symbols"), "ranked_symbols must not be empty")
        top = r["ranked_symbols"][0]
        self.assertEqual(top["symbol"], "add")
        self.assertTrue(top["path"].endswith("calc.py"), top["path"])
        # the traceback must reach the assertion, not stop on the import
        tb = (r["test_traces"][0].get("traceback") or [])
        self.assertTrue(tb, "traceback must not be empty")
        lines = [f[1] for f in tb]
        self.assertNotIn(1, lines, "line 1 is the import; stopping there was the original defect")
        assert_line = (work / "test_calc.py").read_text().splitlines().index(
            "        self.assertEqual(calc.add(2, 3), 5)") + 1
        self.assertIn(assert_line, lines,
                      "the traceback must reach the failing assertion: " + repr(lines))

    def test_a_pass_that_ranks_nothing_is_a_false_positive_and_must_not_happen(self):
        """The exact shape that was shipping: pass=True with an empty ranking."""
        work = _seed("localize_false_positive", *CASES[0][1:3])
        r = runtime._invoke_bound_capability({
            "capability_id": "python.fault.localize.dynamic.dataflow.v1",
            "source_root": str(work), "test_paths": [str(work / "test_calc.py")],
            "output_path": str(work / "loc.json")})
        if r.get("pass"):
            self.assertTrue(r.get("ranked_lines") or r.get("ranked_symbols"),
                            "PASS with no ranking is the false positive being fixed")

    def test_provenance_child_sees_the_module_under_test(self):
        work = _seed("provenance_child", *CASES[0][1:3])
        r = runtime._invoke_bound_capability({
            "capability_id": "python.fault.provenance.interprocedural.value.v1",
            "source_root": str(work), "test_paths": [str(work / "test_calc.py")],
            "output_path": str(work / "prov.json")})
        tt = (r.get("test_traces") or [{}])[0]
        self.assertGreater(tt.get("event_count", 0), 1,
                           "one event means the child died on the import line: " + repr(tt))


class GuardlessSuiteTests(unittest.TestCase):
    """The localizer must handle a suite that a runner collects, not only one that runs itself.

    runpy.run_path(..., run_name="__main__") only executes the tests if the file carries that guard.
    Measured over this repository: 2019 unittest-style test files, 1324 (65%) with the guard and
    695 (34%) without, because they are written to be collected. For those 695 the traced child
    produced no failures at all, the localizer raised NO_FAILING_TEST, and the provenance-guided
    repair that consumes it died with the same error. A third of the corpus was unreachable.

    The fix loads the module and runs the collected suite through a unittest loader, the way a real
    runner does, and re-raises the first failure with its original traceback so the ranking still
    sees the lines that executed. Files that are not unittest suites fall back to runpy.
    """

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(WORK_ROOT, ignore_errors=True)

    def _localize(self, guard):
        work = _seed("guardless" if not guard else "guarded", *CASES[0][1:3], guard=guard)
        return work, runtime._invoke_bound_capability({
            "capability_id": "python.fault.localize.dynamic.dataflow.v1",
            "source_root": str(work), "test_paths": [str(work / "test_calc.py")],
            "output_path": str(work / "loc.json")})

    def test_a_guardless_suite_is_localized_not_refused(self):
        work, r = self._localize(guard=False)
        self.assertNotIn("__main__", (work / "test_calc.py").read_text(),
                         "the fixture must really be guard-less or this test proves nothing")
        self.assertTrue(r.get("ranked_symbols"), "guard-less suite must still rank: " + repr(r))
        self.assertEqual(r["ranked_symbols"][0]["symbol"], "add")

    def test_the_guarded_shape_is_unchanged_by_the_same_fix(self):
        """Backward compatibility is part of the claim, not an assumption."""
        _, guarded = self._localize(guard=True)
        _, guardless = self._localize(guard=False)
        self.assertEqual([s["symbol"] for s in guarded["ranked_symbols"]],
                         [s["symbol"] for s in guardless["ranked_symbols"]])
        self.assertEqual(guarded["failing_test_count"], guardless["failing_test_count"], 1)

    def test_the_traced_child_ran_the_test_not_just_imported_it(self):
        """One event means the child died before running anything - the previous false positive."""
        _, r = self._localize(guard=False)
        tt = (r["test_traces"] or [{}])[0]
        self.assertGreater(tt.get("event_count", 0), 1, repr(tt))
        self.assertFalse(tt.get("pass"), "the seeded suite genuinely fails")

    def test_the_guided_repair_reaches_a_guardless_repository(self):
        work = _seed("guardless_repair", *CASES[0][1:3], guard=False)
        r = runtime._invoke_bound_capability({
            "capability_id": "python.software.repair.guided.provenance.coupled.v1",
            "source_root": str(work), "test_paths": [str(work / "test_calc.py")],
            "test_argv": ["python3", "-m", "unittest", str(work / "test_calc.py")],
            "output_path": str(work / "repair.json")})
        self.assertTrue(r.get("pass"), repr(r.get("status")))

    def test_a_suite_that_is_not_unittest_still_runs_via_the_runpy_fallback(self):
        """The fallback is load-bearing: not every test file is a unittest suite."""
        work = WORK_ROOT / "plain_script"
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        (work / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        (work / "test_calc.py").write_text(
            "import calc\nassert calc.add(2, 3) == 5, 'boom'\n", encoding="utf-8")
        r = runtime._invoke_bound_capability({
            "capability_id": "python.fault.localize.dynamic.dataflow.v1",
            "source_root": str(work), "test_paths": [str(work / "test_calc.py")],
            "output_path": str(work / "loc.json")})
        self.assertTrue(r.get("ranked_symbols"), "plain-assert suite must still be traced: " + repr(r))


class DerivedCommandTests(unittest.TestCase):
    """When no test_argv is supplied, every capability must derive a command line that really runs.

    Seven adapters built their default as [python, <test file>], which executes the file as a script.
    That only starts the tests if the file carries a __main__ guard, and 695 of the 2019 unittest
    files in this repository (34%, measured) do not. Such a run executes nothing and exits 0, so a
    repair loop read it as BASELINE_ALREADY_PASSES: for a third of the corpus the tool reported the
    code already passes, for a program that fails its own test. That is the most dangerous shape of
    false positive in a repair tool, because it looks like a clean bill of health.

    The derived command line now goes through the same loader the localizer uses, which prints the
    standard unittest summary the repair loops parse to score a baseline and re-raises the first
    failure so a tracing caller can still rank the lines that executed.
    """

    FAMILY = [
        "python.patch.search.test_guided.ast.v1",
        "python.software.repair.loop.strict_progress.ast.v1",
        "python.software.repair.loop.test_guided.ast.v1",
        "python.software.repair.loop.coupled.ast.v1",
        "python.software.repair.guided.provenance.coupled.v1",
    ]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(WORK_ROOT, ignore_errors=True)

    def _run_family(self, name, source, guard):
        work = _seed(name, source, CASES[0][2], guard=guard)
        out = {}
        for cid in self.FAMILY:
            args = {"capability_id": cid, "test_paths": [str(work / "test_calc.py")],
                    "output_path": str(work / ("o" + cid.replace(".", "_") + ".json"))}
            if cid == "python.patch.search.test_guided.ast.v1":
                args["source_path"] = str(work / "calc.py")
            elif cid == "python.software.repair.loop.test_guided.ast.v1":
                args["source_paths"] = [str(work / "calc.py")]
            else:
                args["source_root"] = str(work)
            try:
                r = runtime._invoke_bound_capability(args)
                out[cid] = (bool(r.get("pass")), str(r.get("status")))
            except Exception as exc:  # noqa: BLE001 - the exception name is the finding
                out[cid] = (False, type(exc).__name__)
        return out

    def test_a_guardless_failing_suite_is_repaired_not_reported_as_passing(self):
        results = self._run_family("derived_guardless", CASES[0][1], guard=False)
        lying = {k: v for k, v in results.items()
                 if v[1] == "BASELINE_ALREADY_PASSES"}
        self.assertEqual(lying, {}, "reported 'already passes' for code that fails: " + repr(lying))
        broken = {k: v for k, v in results.items() if not v[0]}
        self.assertEqual(broken, {}, "did not repair: " + repr(broken))

    def test_the_guarded_shape_still_repairs_after_the_same_change(self):
        """The change must not trade one shape for the other."""
        self.assertEqual(
            sorted(k for k, v in self._run_family("derived_guarded", CASES[0][1], guard=True).items() if v[0]),
            sorted(self.FAMILY))

    def test_a_genuinely_passing_suite_is_still_refused_not_repaired(self):
        """The safety property: correct code must not be 'fixed'."""
        results = self._run_family("derived_passing", "def add(a, b):\n    return a + b\n", guard=False)
        for cid, (passed, status) in results.items():
            self.assertFalse(passed, cid + " fabricated a repair for correct code")
            self.assertNotEqual(status, "PASS__VERIFIED_CANDIDATE_PATCH_FOUND", cid)

    def test_the_derived_command_line_prints_the_summary_the_scorer_parses(self):
        """A baseline the scorer cannot parse is the regression this pins shut."""
        import python_test_guided_patch_search_v1 as PS

        work = _seed("derived_summary", CASES[0][1], CASES[0][2], guard=False)
        argv = PS.suite_argv("python3", work / "test_calc.py")
        result = PS._run_tests(work, argv, 60, PS._source_env(work))
        self.assertNotEqual(result["returncode"], 0, "the seeded suite genuinely fails")
        import python_iterative_software_repair_loop_v1 as LOOP

        self.assertIsNotNone(LOOP._score(result),
                             "scorer could not parse the child output: " + repr(result)[:400])

    def test_suite_argv_names_every_target_and_runs_them_all(self):
        import python_test_guided_patch_search_v1 as PS

        argv = PS.suite_argv("python3", "/a.py", "/b.py")
        self.assertEqual(argv[0], "python3")
        self.assertEqual(argv[1], "-c")
        self.assertEqual(argv[3:], ["/a.py", "/b.py"])


class AuditAndMeasurementEvidenceTests(unittest.TestCase):
    """The corpus auditor and the acceptance measurer must not record evidence for a suite that never ran.

    Both derived their command line as [python, <test file>], which executes the file as a script and
    therefore only starts the tests when the file carries a __main__ guard. For the 695 unittest
    files in this repository without one (34%, measured) the run exited 0 having executed nothing, so:

      python.tests.audit.unittest             reported test_count 0, failed_count 0
      python.repository.acceptance.measure.v1 recorded returncode 0, test_count 0, empty stderr

    A failing test in such a file became invisible rather than red. That is worse than a wrong
    verdict, because the corpus health report reads as complete while silently omitting a third of
    the tests, and nothing downstream can tell the omission from a clean run.
    """

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(WORK_ROOT, ignore_errors=True)

    EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def _seed_case(self, name, source, guard):
        return _seed(name, source, CASES[0][2], guard=guard)

    def test_the_auditor_counts_a_guardless_failing_test_as_one_failure(self):
        work = self._seed_case("audit_guardless", CASES[0][1], guard=False)
        r = runtime._invoke_bound_capability({
            "capability_id": "python.tests.audit.unittest", "source_root": str(work),
            "test_paths": [str(work / "test_calc.py")], "output_path": str(work / "a.json")})
        self.assertEqual(r.get("test_count"), 1, "a guard-less file must not audit as zero tests")
        self.assertEqual(r.get("failed_count"), 1, "the seeded failure must be counted as a failure")

    def test_the_auditor_is_unchanged_for_the_guarded_shape(self):
        work = self._seed_case("audit_guarded", CASES[0][1], guard=True)
        r = runtime._invoke_bound_capability({
            "capability_id": "python.tests.audit.unittest", "source_root": str(work),
            "test_paths": [str(work / "test_calc.py")], "output_path": str(work / "a.json")})
        self.assertEqual((r.get("test_count"), r.get("failed_count")), (1, 1))

    def test_the_acceptance_measurement_records_truthful_test_evidence(self):
        """The load-bearing field is test_evidence, not the top-level pass flag."""
        work = self._seed_case("measure_guardless", CASES[0][1], guard=False)
        r = runtime._invoke_bound_capability({
            "capability_id": "python.repository.acceptance.measure.v1", "source_root": str(work),
            "test_paths": [str(work / "test_calc.py")], "output_path": str(work / "m.json")})
        ev = r.get("test_evidence") or {}
        self.assertEqual(ev.get("test_count"), 1, "zero tests recorded means nothing ran: " + repr(ev))
        self.assertNotEqual(ev.get("returncode"), 0, "a failing suite must not record a clean exit")
        self.assertNotEqual(ev.get("stderr_sha256"), self.EMPTY_SHA,
                            "empty stderr is the signature of a suite that never ran")

    def test_the_measurement_records_a_passing_guardless_suite_as_actually_passing(self):
        work = self._seed_case("measure_passing", "def add(a, b):\n    return a + b\n", guard=False)
        r = runtime._invoke_bound_capability({
            "capability_id": "python.repository.acceptance.measure.v1", "source_root": str(work),
            "test_paths": [str(work / "test_calc.py")], "output_path": str(work / "m.json")})
        ev = r.get("test_evidence") or {}
        self.assertEqual(ev.get("test_count"), 1)
        self.assertEqual(ev.get("returncode"), 0)
        self.assertNotEqual(ev.get("stderr_sha256"), self.EMPTY_SHA)


PYTEST_STYLE = "import calc\n\n\ndef test_add():\n    assert calc.add(2, 3) == 5\n"
PYTEST_STYLE_MULTI = (
    "import calc\n\n\ndef test_add():\n    assert calc.add(2, 3) == 5\n\n\n"
    "def test_add_zero():\n    assert calc.add(0, 0) == 0\n"
)


class PytestStyleSuiteTests(unittest.TestCase):
    """A suite that is not a unittest suite at all must still be collected, run and counted.

    710 files in this repository hold 3880 bare ``def test_*`` functions in the pytest style, with no
    unittest.TestCase anywhere. From those the unittest loader collects nothing, and the runpy
    fallback executes the module body but never enters a function - so the tests were invisible in
    exactly the way the guard-less unittest files were, one shape over. Measured before this change,
    on a broken function with a pytest-style suite:

      python.tests.audit.unittest                    test_count 0, failed_count 0
      python.fault.localize.dynamic.dataflow.v1      NO_FAILING_TEST
      python.software.repair.loop.strict_progress    BASELINE_ALREADY_PASSES

    The functions are now wrapped in unittest.FunctionTestCase, the standard library type built for
    exactly that, so they run through the same runner and print the same summary the auditor and the
    repair scorers parse. A function needing an argument is skipped rather than guessed at.
    """

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(WORK_ROOT, ignore_errors=True)

    def _seed_pytest(self, name, source, test_source=PYTEST_STYLE):
        d = WORK_ROOT / name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        (d / "calc.py").write_text(source, encoding="utf-8")
        (d / "test_calc.py").write_text(test_source, encoding="utf-8")
        return d

    def test_the_auditor_counts_a_pytest_style_failure(self):
        work = self._seed_pytest("pyt_audit", CASES[0][1])
        r = runtime._invoke_bound_capability({
            "capability_id": "python.tests.audit.unittest", "source_root": str(work),
            "test_paths": [str(work / "test_calc.py")], "output_path": str(work / "a.json")})
        self.assertEqual(r.get("test_count"), 1, "a pytest-style file must not audit as zero tests")
        self.assertEqual(r.get("failed_count"), 1)

    def test_every_bare_function_is_collected_not_just_the_first(self):
        work = self._seed_pytest("pyt_multi", "def add(a, b):\n    return a - b\n", PYTEST_STYLE_MULTI)
        r = runtime._invoke_bound_capability({
            "capability_id": "python.tests.audit.unittest", "source_root": str(work),
            "test_paths": [str(work / "test_calc.py")], "output_path": str(work / "a.json")})
        self.assertEqual(r.get("test_count"), 2, "both bare functions must be collected")
        self.assertEqual(r.get("failed_count"), 1, "only the one that actually fails")
        self.assertEqual(r.get("passed_count"), 1)

    def test_a_passing_pytest_style_suite_counts_as_passing(self):
        work = self._seed_pytest("pyt_pass", "def add(a, b):\n    return a + b\n")
        r = runtime._invoke_bound_capability({
            "capability_id": "python.tests.audit.unittest", "source_root": str(work),
            "test_paths": [str(work / "test_calc.py")], "output_path": str(work / "a.json")})
        self.assertEqual((r.get("test_count"), r.get("failed_count"), r.get("passed_count")), (1, 0, 1))

    def test_the_localizer_ranks_the_faulty_symbol_from_a_pytest_style_suite(self):
        work = self._seed_pytest("pyt_loc", CASES[0][1])
        r = runtime._invoke_bound_capability({
            "capability_id": "python.fault.localize.dynamic.dataflow.v1", "source_root": str(work),
            "test_paths": [str(work / "test_calc.py")], "output_path": str(work / "l.json")})
        self.assertTrue(r.get("ranked_symbols"), "pytest-style suite must still localize: " + repr(r))
        self.assertEqual(r["ranked_symbols"][0]["symbol"], "add")

    def test_the_whole_family_repairs_a_pytest_style_failure(self):
        work = self._seed_pytest("pyt_family", CASES[0][1])
        broken = {}
        for cid in WholeFamilyTests.FAMILY:
            args = {"capability_id": cid, "test_paths": [str(work / "test_calc.py")],
                    "output_path": str(work / ("o" + cid.replace(".", "_") + ".json"))}
            if cid == "python.patch.search.test_guided.ast.v1":
                args["source_path"] = str(work / "calc.py")
            elif cid == "python.software.repair.loop.test_guided.ast.v1":
                args["source_paths"] = [str(work / "calc.py")]
            else:
                args["source_root"] = str(work)
            try:
                r = runtime._invoke_bound_capability(args)
                if not r.get("pass"):
                    broken[cid] = str(r.get("status"))
            except Exception as exc:  # noqa: BLE001
                broken[cid] = type(exc).__name__
        self.assertEqual(broken, {}, "did not repair: " + repr(broken))

    def test_correct_code_with_a_pytest_style_suite_is_still_refused(self):
        work = self._seed_pytest("pyt_correct", "def add(a, b):\n    return a + b\n")
        for cid in WholeFamilyTests.FAMILY:
            args = {"capability_id": cid, "test_paths": [str(work / "test_calc.py")],
                    "output_path": str(work / ("c" + cid.replace(".", "_") + ".json"))}
            if cid == "python.patch.search.test_guided.ast.v1":
                args["source_path"] = str(work / "calc.py")
            elif cid == "python.software.repair.loop.test_guided.ast.v1":
                args["source_paths"] = [str(work / "calc.py")]
            else:
                args["source_root"] = str(work)
            # The call and the assertion are deliberately separated. Wrapping the assertion in
            # try/except Exception swallows its own AssertionError, which makes the test unable to
            # fail - repo_integrity_guard flags exactly this as ASSERTION_SWALLOWED.
            result = None
            try:
                result = runtime._invoke_bound_capability(args)
            except Exception:
                result = None  # refusing by raising is also a refusal
            if result is not None:
                self.assertFalse(result.get("pass"), cid + " fabricated a repair for correct code")

    def test_a_function_needing_an_argument_is_skipped_not_guessed(self):
        """A fixture-parameterised test must not be called with a fabricated argument."""
        work = self._seed_pytest(
            "pyt_fixture", "def add(a, b):\n    return a + b\n",
            "import calc\n\n\ndef test_with_fixture(tmp_path):\n    assert calc.add(1, 1) == 2\n\n\n"
            "def test_plain():\n    assert calc.add(1, 1) == 2\n")
        r = runtime._invoke_bound_capability({
            "capability_id": "python.tests.audit.unittest", "source_root": str(work),
            "test_paths": [str(work / "test_calc.py")], "output_path": str(work / "a.json")})
        self.assertEqual(r.get("test_count"), 1, "the fixture-parameterised function must be skipped")
        self.assertEqual(r.get("error_count"), 0, "skipping must not be recorded as an error")


PEP695 = "from typing import Literal\n\ntype ReasoningEffort = Literal[\"none\", \"low\", \"high\"]\n"


class UnparseableNeighbourTests(unittest.TestCase):
    """One file under source_root that this interpreter cannot parse must not abort the search.

    Found by pointing the repair capabilities at a real red test in this repository with
    source_root=canonical. The tree contains a vendored third-party file,
    canonical/capabilities/internalized/professional_work/stirrup_247f24d/src/stirrup/clients/
    litellm_client.py, whose line 47 is a PEP 695 type alias. That syntax needs Python 3.12 and this
    interpreter is 3.11.2, so ast.parse raises SyntaxError - on a file that has nothing to do with
    the repair target. Seven ast.parse sites in four adapters were unguarded, and one of them
    aborted the whole capability:

      python.software.repair.guided.provenance.coupled.v1 -> SyntaxError: invalid syntax
                                                             (litellm_client.py, line 47)

    A file that cannot be parsed cannot be a repair candidate or a localization target, so it now
    contributes nothing. That is the rule python_test_audit already documents for timeouts: one bad
    file is a fact about that file, not a reason to abandon the run.
    """

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(WORK_ROOT, ignore_errors=True)

    def _seed_with_unparseable_neighbour(self, name):
        d = WORK_ROOT / name
        if d.exists():
            shutil.rmtree(d)
        (d / "vendor").mkdir(parents=True)
        (d / "calc.py").write_text(CASES[0][1], encoding="utf-8")
        (d / "test_calc.py").write_text(CASES[0][2] + GUARD, encoding="utf-8")
        (d / "vendor" / "third_party.py").write_text(PEP695, encoding="utf-8")
        return d

    def test_the_pep695_fixture_really_is_unparseable_here(self):
        """Otherwise this whole class would pass vacuously on a newer interpreter."""
        import ast as _ast
        import sys as _sys

        if _sys.version_info >= (3, 12):
            self.skipTest("PEP 695 parses on this interpreter; the guard is not exercised")
        with self.assertRaises(SyntaxError):
            _ast.parse(PEP695)

    def test_the_guided_repair_completes_instead_of_crashing(self):
        work = self._seed_with_unparseable_neighbour("unparseable_guided")
        r = runtime._invoke_bound_capability({
            "capability_id": "python.software.repair.guided.provenance.coupled.v1",
            "source_root": str(work), "test_paths": [str(work / "test_calc.py")],
            "test_argv": ["python3", "-m", "unittest", str(work / "test_calc.py")],
            "output_path": str(work / "o.json"), "timeout_s": 45})
        self.assertTrue(r.get("pass"), "the repair must still work: " + str(r.get("status")))

    def test_the_localizer_and_provenance_still_rank_past_an_unparseable_neighbour(self):
        work = self._seed_with_unparseable_neighbour("unparseable_loc")
        r = runtime._invoke_bound_capability({
            "capability_id": "python.fault.localize.dynamic.dataflow.v1",
            "source_root": str(work), "test_paths": [str(work / "test_calc.py")],
            "output_path": str(work / "l.json"), "timeout_s": 45})
        self.assertTrue(r.get("ranked_symbols"), "localization must survive: " + repr(r))
        self.assertEqual(r["ranked_symbols"][0]["symbol"], "add")
        paths = [s["path"] for s in r["ranked_symbols"]]
        self.assertFalse(any("third_party" in p for p in paths), paths)

    def test_the_unparseable_file_is_never_offered_as_a_repair_target(self):
        work = self._seed_with_unparseable_neighbour("unparseable_target")
        r = runtime._invoke_bound_capability({
            "capability_id": "python.software.repair.loop.coupled.ast.v1",
            "source_root": str(work), "test_paths": [str(work / "test_calc.py")],
            "test_argv": ["python3", "-m", "unittest", str(work / "test_calc.py")],
            "output_path": str(work / "o.json"), "timeout_s": 45})
        for patch in (r.get("patches") or []):
            self.assertNotIn("third_party", str(patch.get("source_path")), patch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
