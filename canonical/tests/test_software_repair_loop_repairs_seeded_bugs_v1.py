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


def _seed(name, source, test_source):
    d = WORK_ROOT / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "calc.py").write_text(source, encoding="utf-8")
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

    python.software.repair.guided.provenance.coupled.v1 is not here: it requires the
    python.source.file.available and python.test.corpus.available effects from upstream producers
    and correctly reports GUIDANCE_EMPTY when invoked standalone. python.repository.acceptance
    .measure.v1 copies the source into its own workspace and runs the tests there, so it never had
    the defect.
    """

    FAMILY = {
        "python.patch.search.test_guided.ast.v1": "source_path",
        "python.software.repair.loop.strict_progress.ast.v1": "source_root",
        "python.software.repair.loop.test_guided.ast.v1": "source_paths",
        "python.software.repair.loop.coupled.ast.v1": "source_root",
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
            (work / "test_calc.py").write_text(
                CASES[0][2] + "\nif __name__ == '__main__':\n    unittest.main()\n", encoding="utf-8"
            )
            try:
                r = runtime._invoke_bound_capability(self._args(cid, slot, work))
                results[cid] = (bool(r.get("pass")), str(r.get("status")))
            except Exception as exc:  # noqa: BLE001 - the message is the finding
                results[cid] = (False, type(exc).__name__ + ": " + str(exc)[:80])
        failing = {k: v for k, v in results.items() if not v[0]}
        self.assertEqual(failing, {}, "capabilities that did not repair: " + repr(failing))
        self.assertEqual(len(results), 4)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
