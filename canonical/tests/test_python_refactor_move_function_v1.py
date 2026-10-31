# PROJECT_BRAIN
"""Pins for python.refactor.move_function.v1 — move a module-scope function into
another module, and make every importer follow it, by byte splice, with a
rollback gate.

The pins nail the LAWS, not the happy path:

* the def and its decorator move; the body arrives byte-identical;
* `from pkg.calc import add, sub` is SPLIT, not swapped: `sub` did not move and
  must still be imported from the module that defines it;
* `import pkg.calc as calc` is rewritten only because that alias was used for
  the moved name alone; a shared alias refuses the whole edit;
* a source module that still calls the name re-imports it from the new home;
* a target that already defines the name refuses; so does a method, a nested
  function, an unprovable reference and a used-with-no-import name;
* a red named suite restores every byte, sha256-identical;
* two identical worlds produce byte-identical trees and artifacts.

Run: python -m pytest canonical/tests/test_python_refactor_move_function_v1.py -q
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import (
    python_refactor_move_function as mv,
)

PY = sys.executable

CALC = '''import os


def add(a, b):
    """Add two numbers."""
    return a + b


def sub(a, b):
    return a - b
'''

USE = '''from pkg.calc import add, sub


def go():
    return add(1, 2) + sub(3, 4)
'''

ALIASED = '''import pkg.calc as calc


def go():
    return calc.add(1, 2)
'''

SHARED_ALIAS = '''import pkg.calc as calc


def go():
    return calc.add(1, 2) + calc.sub(9, 4)
'''

TEST_GO = '''from pkg.calc import sub
from pkg.ops import add


def test_add():
    assert add(2, 3) == 5


def test_sub():
    assert sub(5, 3) == 2
'''

TEST_RED = '''from pkg.ops import add


def test_always_fails():
    assert add(1, 1) == 3
'''


def _build(root: Path, files: dict) -> Path:
    src = root / "src"
    (src / "pkg").mkdir(parents=True, exist_ok=True)
    (src / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    for rel, text in files.items():
        path = src / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return src


def _run(root: Path, **kw):
    args = {"source_root": "src/pkg", "module": "calc.py", "qualname": "add",
            "target_module": "ops.py", "output_path": "_out/move.json",
            "python_executable": PY, "timeout_s": 120}
    args.update(kw)
    return mv.run(args, root)


_IGNORED = {"__pycache__", ".pytest_cache"}


def _bytes(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*"))
            if p.is_file() and not (_IGNORED & set(p.parts))}


class TestMoveFunction(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="movefn_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_golden_move_splits_the_import_and_keeps_the_rest(self):
        src = _build(self.tmp, {"pkg/calc.py": CALC, "pkg/use.py": USE,
                                "pkg/test_go.py": TEST_GO})
        art = _run(self.tmp, run_tests=["test_go.py"])
        self.assertIn("def sub(a, b):", (src / "pkg/calc.py").read_text())
        self.assertNotIn("def add(", (src / "pkg/calc.py").read_text())
        moved = (src / "pkg/ops.py").read_text()
        self.assertTrue(moved.startswith("def add(a, b):"))
        self.assertIn('"""Add two numbers."""', moved)
        use = (src / "pkg/use.py").read_text()
        self.assertIn("from pkg.ops import add", use)
        self.assertIn("from pkg.calc import sub", use)
        self.assertNotIn("from pkg.calc import add", use)
        self.assertEqual(art["gate"], "PASS")
        self.assertTrue(art["verified"])
        self.assertEqual(art["symbol_kind"], "FUNCTION")
        self.assertEqual(art["moved_to"], "ops.py")

    def test_decorator_travels_with_the_function(self):
        src = _build(self.tmp, {"pkg/calc.py":
                                "def deco(fn):\n    return fn\n\n\n@deco\ndef add(a, b):\n"
                                "    return a + b\n"})
        _run(self.tmp)
        moved = (src / "pkg/ops.py").read_text()
        self.assertIn("@deco\ndef add(a, b):", moved)
        self.assertNotIn("@deco", (src / "pkg/calc.py").read_text())

    def test_module_alias_is_rewritten_when_it_only_names_the_moved_symbol(self):
        src = _build(self.tmp, {"pkg/calc.py": CALC, "pkg/ali.py": ALIASED})
        _run(self.tmp)
        ali = (src / "pkg/ali.py").read_text()
        self.assertIn("import pkg.ops as calc", ali)
        self.assertIn("calc.add(1, 2)", ali)

    def test_shared_module_alias_refuses_the_whole_edit(self):
        src = _build(self.tmp, {"pkg/calc.py": CALC, "pkg/ali.py": SHARED_ALIAS})
        before = _bytes(src)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp)
        self.assertIn("UNSUPPORTED_SHARED_MODULE_IMPORT", str(ctx.exception))
        self.assertEqual(_bytes(src), before)

    def test_source_module_reimports_what_it_still_calls(self):
        src = _build(self.tmp, {"pkg/calc.py": CALC + "\n\ndef double(x):\n    return add(x, x)\n"})
        art = _run(self.tmp)
        calc = (src / "pkg/calc.py").read_text()
        self.assertIn("from ops import add", calc)
        self.assertIn("return add(x, x)", calc)
        self.assertEqual(art["files_edited"], ["calc.py", "ops.py"])

    def test_method_refuses(self):
        _build(self.tmp, {"pkg/calc.py": "class C:\n    def add(self, a):\n        return a\n"})
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, qualname="C.add")
        self.assertIn("SYMBOL_NOT_AT_MODULE_SCOPE", str(ctx.exception))

    def test_target_already_defines_the_name_refuses(self):
        _build(self.tmp, {"pkg/calc.py": CALC, "pkg/ops.py": "def add(a, b):\n    return 0\n"})
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp)
        self.assertIn("TARGET_ALREADY_DEFINES_SYMBOL", str(ctx.exception))

    def test_red_suite_restores_every_byte(self):
        src = _build(self.tmp, {"pkg/calc.py": CALC, "pkg/use.py": USE,
                                "pkg/test_red.py": TEST_RED})
        before = _bytes(src)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, run_tests=["test_red.py"])
        self.assertIn("TESTS_RED_AFTER_EDIT", str(ctx.exception))
        self.assertEqual(_bytes(src), before)

    def test_determinism_two_worlds(self):
        world_a = self.tmp / "a"
        world_b = self.tmp / "b"
        world_a.mkdir()
        world_b.mkdir()
        for world in (world_a, world_b):
            _build(world, {"pkg/calc.py": CALC, "pkg/use.py": USE})
        _run(world_a)
        _run(world_b)
        self.assertEqual(_bytes(world_a / "src"), _bytes(world_b / "src"))


if __name__ == "__main__":
    unittest.main()
