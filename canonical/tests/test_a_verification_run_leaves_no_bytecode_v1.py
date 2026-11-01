"""A verification run must not leave a second copy of the source behind.

Measured 2026-11-01 on the surface census (``hardcore_swe_surface_probe_20261030.py``):
``fix_then_regression_test`` was nondeterministic.  The door passed 4/4 and the
independent oracle passed 1/4, and the difference was not the repair -- every run
fixed the bug (``fixed_value: '5'``) and left a green suite.  The oracle's third fact
is "the test the machine added FAILS on the buggy code it was given", measured by
reverting ``app/`` to the initial commit and re-running the suite.  That revert was
sometimes answered by a stale bytecode cache::

    return a - b      # buggy, 100 bytes
    return a + b      # fixed, 100 bytes   <- same size

The suite runs that verified the fix imported ``app.calc`` through
``python_test_guided_patch_search_v1._source_env``, which declared ``PYTHONPATH`` and
nothing else, so CPython wrote ``app/__pycache__/calc.cpython-*.pyc`` from the FIXED
source.  ``git checkout`` restored the buggy bytes milliseconds later -- inside the
same wall-clock second -- and the pyc header (source mtime + size) still matched, so
the interpreter executed the fixed bytecode while the oracle believed it was running
the bug.  Reproduced in isolation: stale pyc present -> ``OK``, pyc removed ->
``FAILED (failures=1)``.

So the rule is not "redirect the cache", which keeps its own stale entry, but: a tree
under verification is the only copy of that tree.  The runner is where every suite run
in the family passes, so the rule lives in the runner and in the shared environment
definition, not in a caller's optional ``extra_env``.
"""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as patch  # noqa: E402

BUGGY = '"""Calc."""\n\n\ndef add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n'
FIXED = BUGGY.replace("return a - b", "return a + b")
TEST = (
    "import unittest\n"
    "from app.calc import add\n\n\n"
    "class T(unittest.TestCase):\n"
    "    def test_add(self):\n"
    "        self.assertEqual(add(1, 2), 3)\n"
)


def _tree(root: pathlib.Path, source: str) -> pathlib.Path:
    (root / "app").mkdir(parents=True, exist_ok=True)
    (root / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "app" / "calc.py").write_text(source, encoding="utf-8")
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (root / "tests" / "test_calc.py").write_text(TEST, encoding="utf-8")
    return root


def _run(root: pathlib.Path, *targets: str) -> dict:
    argv = patch.suite_argv(sys.executable, *(root / t for t in targets))
    return patch._run_tests(root, argv, 120, patch._source_env(root / "tests" / "test_calc.py"))


class AVerificationRunLeavesNoBytecode(unittest.TestCase):

    def setUp(self) -> None:
        self.root = _tree(pathlib.Path(tempfile.mkdtemp(prefix="brain-bytecode-")), FIXED)

    def test_the_shared_suite_environment_forbids_bytecode(self) -> None:
        env = patch._source_env(self.root / "tests" / "test_calc.py")
        self.assertEqual(env.get("PYTHONDONTWRITEBYTECODE"), "1")

    def test_a_green_suite_run_leaves_no_cache_in_the_tree(self) -> None:
        result = _run(self.root, "tests/test_calc.py")
        self.assertEqual(result["returncode"], 0, result["stderr"][-600:])
        caches = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("__pycache__"))
        self.assertEqual(caches, [], "a verification run stored a second copy of the source")

    def test_a_runner_run_with_no_extra_environment_also_leaves_no_cache(self) -> None:
        """``extra_env=None`` inherited the ambient environment and wrote the cache."""
        argv = patch.suite_argv(sys.executable, self.root / "tests" / "test_calc.py")
        result = patch._run_tests(self.root, argv, 120)
        self.assertEqual(result["returncode"], 0, result["stderr"][-600:])
        self.assertEqual(sorted(self.root.rglob("__pycache__")), [])

    def test_a_reverted_source_is_not_answered_by_the_fixed_source(self) -> None:
        """The census row, reduced: fix, verify, revert -- the suite must go red at once."""
        self.assertEqual(_run(self.root, "tests/test_calc.py")["returncode"], 0)
        (self.root / "app" / "calc.py").write_text(BUGGY, encoding="utf-8")
        self.assertEqual(len(BUGGY), len(FIXED), "the fixture must keep the edit size-identical")
        after = _run(self.root, "tests/test_calc.py")
        self.assertNotEqual(after["returncode"], 0,
                            "the suite answered with the fixed source's bytecode")
        self.assertIn("failures=1", (after["stderr"] or "") + (after["stdout"] or ""))


if __name__ == "__main__":
    unittest.main()
