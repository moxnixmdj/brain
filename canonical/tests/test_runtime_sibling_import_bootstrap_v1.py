"""A test that cannot be imported asserts nothing at all.

Modules in `canonical/runtime` import their own siblings by bare name, so they
are only importable with that directory on `sys.path`. Nineteen workflows set
PYTHONPATH that way, which is why the habit spread into the tests -- but the
plain `python -m unittest` run and the test-corpus audit invoke each file
directly from the repository root, where `canonical/runtime` is NOT on the path.

Two test files had picked up that habit and paid for it silently:

    from m1b_smooth_surface_compiler import compile_source
    ModuleNotFoundError: No module named 'm1b_smooth_surface_compiler'

The module exists. The import style was wrong. And because the failure happens
at import time, before any TestCase is collected, the file reported one error
and ran zero assertions -- so it looked like a small red test rather than a test
that had never executed a single line. The corpus audit records such a file as
`crashed`, which is how this was found.

The fix is the bootstrap the repository already uses elsewhere, e.g.
`test_capability_composer_v1.py`:

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))

These tests pin the invariant statically, so a new test file cannot reintroduce
the silent-no-op without being named by this suite.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TESTS_DIR = ROOT / "canonical" / "tests"
RUNTIME_DIR = ROOT / "canonical" / "runtime"

# Any sys.path insertion that names the runtime directory, in the several
# spellings this repository actually uses.
_PATH_BOOTSTRAP = re.compile(
    r"sys\.path\.insert\([^)]*[\)\s].{0,80}?[\"']runtime[\"']"
    r"|sys\.path\.insert\([^)]*RUNTIME[A-Z_]*"
    r"|sys\.path\.append\([^)]*[\"']runtime[\"']",
    re.S,
)


def _runtime_sibling_names() -> set[str]:
    return {p.stem for p in RUNTIME_DIR.glob("*.py") if p.stem != "__init__"}


def _is_assert_raises(node: ast.AST) -> bool:
    """True for `with self.assertRaises(...)` / `with pytest.raises(...)`."""
    if not isinstance(node, ast.With):
        return False
    for item in node.items:
        call = item.context_expr
        if isinstance(call, ast.Call):
            name = call.func
            label = name.attr if isinstance(name, ast.Attribute) else getattr(name, "id", "")
            if label in {"assertRaises", "raises"}:
                return True
    return False


def _bare_sibling_imports(source: str) -> list[tuple[int, str]]:
    """(lineno, module) for every bare top-level import of a runtime sibling
    that the file actually DEPENDS on resolving.

    An import sitting inside `assertRaises(ImportError)` is excluded on purpose:
    that is a negative control asserting the import FAILS, which is the opposite
    of depending on it. `test_browser_v1_driver_resolution.py` does exactly that
    to prove the driver loader survives a missing path entry.
    """
    siblings = _runtime_sibling_names()
    out: list[tuple[int, str]] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out

    def walk(nodes, expecting_failure: bool) -> None:
        for node in nodes:
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module in siblings:
                if not expecting_failure:
                    out.append((node.lineno, node.module))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in siblings and not expecting_failure:
                        out.append((node.lineno, alias.name))
            child_expecting = expecting_failure or _is_assert_raises(node)
            for field in ("body", "orelse", "finalbody", "handlers"):
                children = getattr(node, field, None)
                if isinstance(children, list):
                    walk(children, child_expecting)

    walk(tree.body, False)
    return sorted(out)


def _bootstrap_line(source: str) -> int | None:
    """Line number of the first sys.path bootstrap naming the runtime dir."""
    lines = source.split("\n")
    for i, line in enumerate(lines, start=1):
        if "sys.path" in line and re.search(r"[\"']runtime[\"']|RUNTIME", line):
            return i
    return None


class RuntimeSiblingImportBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.files = sorted(TESTS_DIR.glob("test_*.py"))

    def test_the_corpus_is_actually_being_scanned(self):
        """Guard against this suite silently scanning nothing."""
        self.assertGreater(len(self.files), 1000, len(self.files))
        self.assertTrue(RUNTIME_DIR.is_dir())
        self.assertGreater(len(_runtime_sibling_names()), 500)

    def test_no_test_bare_imports_a_runtime_sibling_without_bootstrapping_first(self):
        """The invariant. Every offender is named, not just the first."""
        offenders: list[str] = []
        for path in self.files:
            source = path.read_text(encoding="utf-8")
            imports = _bare_sibling_imports(source)
            if not imports:
                continue
            boot = _bootstrap_line(source)
            first = imports[0][0]
            if boot is None:
                offenders.append(
                    f"{path.name}: bare-imports {imports[0][1]} at line {first} "
                    f"and never puts canonical/runtime on sys.path"
                )
            elif boot > first:
                offenders.append(
                    f"{path.name}: puts canonical/runtime on sys.path at line "
                    f"{boot}, AFTER the bare import of {imports[0][1]} at line {first}"
                )
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_every_runtime_sibling_a_test_names_actually_exists(self):
        """A typo in one of these imports is the same silent no-op."""
        siblings = _runtime_sibling_names()
        missing: list[str] = []
        for path in self.files:
            for _lineno, module in _bare_sibling_imports(path.read_text(encoding="utf-8")):
                if module not in siblings:
                    missing.append(f"{path.name}: {module}")
        self.assertEqual(missing, [], "\n".join(sorted(set(missing))))

    def test_the_bootstrap_is_what_makes_a_bare_sibling_import_resolve(self):
        """Prove the fix is the path, not something incidental.

        `apt_cli_probe` is a runtime module with no external dependencies, so
        this holds on any host. Before the bootstrap it is unimportable; after
        it, it imports -- which is exactly the transition the two repaired test
        files depend on.
        """
        probe = "apt_cli_probe"
        self.assertTrue((RUNTIME_DIR / (probe + ".py")).is_file())
        saved = list(sys.path)
        try:
            sys.path[:] = [p for p in sys.path if not p.endswith("canonical/runtime")]
            sys.modules.pop(probe, None)
            with self.assertRaises(ModuleNotFoundError):
                __import__(probe)
            sys.path.insert(0, str(RUNTIME_DIR))
            sys.modules.pop(probe, None)
            module = __import__(probe)
            self.assertTrue(hasattr(module, "__file__"))
        finally:
            sys.path[:] = saved
            sys.modules.pop(probe, None)

    def test_an_import_inside_assert_raises_is_excluded_but_still_in_the_source(self):
        """The exclusion must be precise, not a licence to see nothing.

        test_browser_v1_driver_resolution.py really does contain a bare sibling
        import -- inside `assertRaises(ImportError)`, as a negative control
        proving the driver loader survives a missing path entry. Both halves are
        pinned: the text is there, and the scan reports no dependency on it. If
        the exclusion ever widened to "ignore every import", the first assertion
        would still hold but the guard would have gone vacuous, so the pair is
        what makes the exclusion falsifiable.
        """
        path = TESTS_DIR / "test_browser_v1_driver_resolution.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn("import osworld_v21_browser_cdp_v1", source)
        self.assertIn("assertRaises(ImportError)", source)
        self.assertEqual(_bare_sibling_imports(source), [])

    def test_the_two_repaired_files_are_the_ones_this_guard_was_written_for(self):
        """Pin that the repair landed, so it cannot be undone quietly."""
        for name in (
            "test_m1b_continuous_geometry_compiler.py",
            "test_m1b_smooth_surface_compiler.py",
        ):
            with self.subTest(file=name):
                source = (TESTS_DIR / name).read_text(encoding="utf-8")
                self.assertTrue(_bare_sibling_imports(source), "expected a bare sibling import")
                boot = _bootstrap_line(source)
                self.assertIsNotNone(boot, "bootstrap missing")
                self.assertLess(boot, _bare_sibling_imports(source)[0][0])


if __name__ == "__main__":
    unittest.main()
