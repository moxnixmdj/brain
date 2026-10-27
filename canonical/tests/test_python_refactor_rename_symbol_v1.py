# PROJECT_BRAIN
"""Pins for python.refactor.rename_symbol.v1 — scope-aware rename of ANY
def-sited symbol (function, class, module binding, method, nested function)
with provable-binding cross-file propagation and fail-closed rollback.

Run: python -m pytest canonical/tests/test_python_refactor_rename_symbol_v1.py -q
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import (
    python_refactor_rename_symbol as rs,
)

PY = sys.executable

CORE = '''THRESHOLD = 0.5


def top(values, verbose=False):
    total = sum(values)
    return total / len(values) if total > THRESHOLD else 0


class Meter:
    step = 1

    def bands(self, base):
        return self.step + top([base])
'''

CALLER_T = '''from pkg.core import top, THRESHOLD
import pkg.core as core_mod


def run_twice(size):
    return top([size]) + core_mod.top([2.0]) + THRESHOLD
'''

CALLER_ALIAS = '''from pkg.core import top as apex


def duck(k):
    return apex([k])
'''

SHADOWED = '''def top(values):
    total = values
    def inner(top):
        return top
    return inner(total)
'''

LOOSE_STRING = '''def top(values):
    return values[0]


def topper(values):
    return "top of " + str(values)


print(topper([1]))
'''

USE_META = '''class Runner:
    def report(self):
        return self.report
'''


def _build(root: Path, core: str = CORE, packages: dict | None = None):
    src = root / "src"
    (src / "pkg").mkdir(parents=True, exist_ok=True)
    (src / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (src / "pkg" / "core.py").write_text(core, encoding="utf-8")
    (src / "use").mkdir(parents=True, exist_ok=True)
    for rel, body in (packages if packages is not None else {"use/caller.py": ""}).items():
        f = src / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    return src


def _build_wide(root: Path):
    """Cross-file consumer worlds."""
    src = root / "src"
    (src / "pkg").mkdir(parents=True, exist_ok=True)
    (src / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (src / "pkg" / "core.py").write_text(CORE, encoding="utf-8")
    (src / "use").mkdir(parents=True, exist_ok=True)
    (src / "use" / "caller.py").write_text(CALLER_T, encoding="utf-8")
    (src / "use" / "aliaser.py").write_text(CALLER_ALIAS, encoding="utf-8")
    (src / "tests").mkdir(parents=True, exist_ok=True)
    (src / "tests" / "test_apex.py").write_text(TECT, encoding="utf-8")
    return src


TECT = '''import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1].parent / "src"))
from use.caller import run_twice


def test_answer():
    assert run_twice(3) == 3 + 2 + 0.5
'''


def _run(root: Path, **kw):
    args = {"source_root": "src", "module": "pkg/core.py",
            "output_path": "_out/refactor.json",
            "python_executable": PY, "timeout_s": 120}
    args.update(kw)
    rs.run(args, root)
    return json.loads((root / "_out/refactor.json").read_text())


def _bytes(root: Path):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


class TestRenameSymbol(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="renamesym_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_golden_function_cross_file(self):
        src = _build_wide(self.tmp)
        art = _run(self.tmp, qualname="top", new_symbol="apex",
                   run_tests=["tests/test_apex.py"])
        core = (src / "pkg/core.py").read_text()
        caller = (src / "use/caller.py").read_text()
        alias = (src / "use/aliaser.py").read_text()
        self.assertIn("def apex(values, verbose=False):", core)
        self.assertIn("return self.step + apex([base])", core)   # class-body use renamed
        self.assertIn("from pkg.core import apex, THRESHOLD", caller)
        self.assertIn("apex([size]) + core_mod.apex([2.0])", caller)
        self.assertIn("from pkg.core import apex as apex", alias)  # alias preserved, name token renamed
        self.assertIn("return apex([k])", alias)
        self.assertNotIn("d import top", caller)
        self.assertTrue(art["complete"] is True or art["unknown_sites"] == [])
        self.assertEqual(art["symbol_kind"], "FUNCTION")
        self.assertTrue(art["verified"])

    def test_class_rename_propagates_imports_and_construction(self):
        src = _build_wide(self.tmp)
        art = _run(self.tmp, qualname="Meter", new_symbol="Gauge")
        core = (src / "pkg/core.py").read_text()
        self.assertIn("class Gauge:", core)
        self.assertNotIn("class Meter", core)

    def test_module_level_constant_renamed_cross_file(self):
        src = _build_wide(self.tmp)
        art = _run(self.tmp, qualname="THRESHOLD", new_symbol="FLOOR")
        core = (src / "pkg/core.py").read_text()
        caller = (src / "use/caller.py").read_text()
        self.assertIn("FLOOR = 0.5", core)
        self.assertIn("total > FLOOR", core)
        self.assertIn("from pkg.core import top, FLOOR", caller)
        self.assertIn("+ FLOOR", caller)
        self.assertEqual(art["symbol_kind"], "MODULE_BINDING")

    def test_method_rename_self_and_class_refs_only(self):
        src = _build(self.tmp, core='''class Meter:
    step = 1

    def bands(self, base):
        return self.step + base

    def chain(self):
        return self.bands(2) + Meter.bands(self, 3)
''')
        art = _run(self.tmp, qualname="Meter.bands", new_symbol="segments")
        core = (src / "pkg/core.py").read_text()
        self.assertIn("def segments(self, base):", core)
        self.assertIn("return self.segments(2) + Meter.segments(self, 3)", core)
        self.assertTrue(art["complete"])
        self.assertEqual(art["symbol_kind"], "METHOD")

    def test_inherited_override_refused(self):
        _build(self.tmp, core='''class Meter:
    def bands(self, base):
        return base


class Sub(Meter):
    def bands(self, base):
        return super().bands(base)
''')
        with self.assertRaises(SystemExit) as cm:
            _run(self.tmp, qualname="Meter.bands", new_symbol="segments")
        self.assertIn("REFUSE_INHERITED_OVERRIDE:Sub.bands",
                      str(cm.exception.code))

    def test_inherited_use_refused(self):
        _build(self.tmp, core='''class Meter:
    def bands(self, base):
        return base


class Sub(Meter):
    def run(self):
        return self.bands(4)
''')
        with self.assertRaises(SystemExit) as cm:
            _run(self.tmp, qualname="Meter.bands", new_symbol="segments")
        self.assertIn("REFUSE_INHERITED_USE", str(cm.exception.code))

    def test_shadowed_nested_scope_keeps_old_name(self):
        src = _build(self.tmp, core=SHADOWED, packages={"use/caller.py": ""})
        art = _run(self.tmp, qualname="top", new_symbol="apex")
        core = (src / "pkg/core.py").read_text()
        self.assertIn("def apex(values):", core)
        self.assertIn("return inner(total)", core)
        self.assertIn("def inner(top):", core)     # inner param named top: shadowed keep
        self.assertIn("return top", core)
        self.assertTrue(any(s["scope"] == "inner" for s in art["shadowed_keeps"]))

    def test_never_edits_strings_or_substrings(self):
        src = _build(self.tmp, core=LOOSE_STRING,
                     packages={"use/caller.py": ""})
        art = _run(self.tmp, qualname="top", new_symbol="apex", module="pkg/core.py")
        core = (src / "pkg/core.py").read_text()
        self.assertIn("def topper(values):", core)   # substring carrier untouched
        self.assertIn('"top of "', core)             # string literal untouched
        self.assertIn("topper([1])", core)

    def test_new_name_collision_with_existing_def_refuses(self):
        colliding = CORE + "\ndef Gauged():\n    pass\n"
        _build(self.tmp, core=colliding)
        with self.assertRaises(SystemExit) as cm:
            _run(self.tmp, qualname="Meter", new_symbol="Gauged")
        self.assertIn("NEW_NAME_COLLIDES", str(cm.exception.code))

    def test_new_name_collision_with_nested_binding_refuses(self):
        _build(self.tmp, core=SHADOWED, packages={"use/caller.py": ""})
        with self.assertRaises(SystemExit) as cm:
            _run(self.tmp, qualname="top", new_symbol="inner")
        self.assertIn("NEW_NAME_COLLIDES", str(cm.exception.code))

    def test_nonlocal_declaration_refuses(self):
        global_body = '''probe = 1


def top():
    global probe
    return probe
'''
        _build(self.tmp, core=global_body, packages={"use/caller.py": ""})
        with self.assertRaises(SystemExit) as cm2:
            _run(self.tmp, qualname="probe", new_symbol="signal")
        self.assertIn("REFUSE_NONLOCAL_OR_GLOBAL", str(cm2.exception.code))

    def test_nonlocal_on_unrelated_name_does_not_refuse(self):
        body = '''def top():
    acc = 0
    def collect(x):
        nonlocal acc
        acc += x
    return collect(1)


def probe():
    return top()
'''
        _build(self.tmp, core=body, packages={"use/caller.py": ""})
        art = _run(self.tmp, qualname="top", new_symbol="apex")
        core = (self.tmp / "src/pkg/core.py").read_text()
        self.assertIn("def apex():", core)
        self.assertIn("return apex()", core)

    def test_invalid_identifier_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as cm:
            _run(self.tmp, qualname="top", new_symbol="9lives")
        self.assertIn("INVALID_IDENTIFIER", str(cm.exception.code))

    def test_symbol_not_found_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as cm:
            _run(self.tmp, qualname="does_not_exist", new_symbol="x")
        self.assertIn("SYMBOL_NOT_FOUND", str(cm.exception.code))

    def test_red_named_suite_rolls_back_every_byte(self):
        src = _build_wide(self.tmp)
        bad = "def test_always_fails():\n    assert False\n"
        (src / "tests" / "test_bad.py").write_text(bad, encoding="utf-8")
        before = _bytes(self.tmp / "src")
        with self.assertRaises(SystemExit) as cm:
            _run(self.tmp, qualname="top", new_symbol="apex",
                 run_tests=["tests/test_bad.py"])
        self.assertIn("TESTS_RED_AFTER_EDIT", str(cm.exception.code))
        after = _bytes(self.tmp / "src")
        self.assertEqual(before, after)  # byte-for-byte rollback
        for k, v in before.items():
            self.assertEqual(hashlib.sha256(after[k]).hexdigest(),
                             hashlib.sha256(v).hexdigest())

    def test_no_named_tests_is_loudly_unverified(self):
        src = _build_wide(self.tmp)
        art = _run(self.tmp, qualname="top", new_symbol="apex")
        self.assertFalse(art["verified"])
        self.assertEqual(art["gate"], "PASS_BLIND")
        self.assertIn("def apex(values, verbose=False):",
                      (src / "pkg/core.py").read_text())

    def test_determinism_two_worlds(self):
        world_a = self.tmp / "a"; world_b = self.tmp / "b"
        world_a.mkdir(); world_b.mkdir()
        _build_wide(world_a); _build_wide(world_b)
        ra = _run(world_a, qualname="top", new_symbol="apex",
                  output_path="_out/refactor.json")
        rb = _run(world_b, qualname="top", new_symbol="apex",
                  output_path="_out/refactor.json")
        ba = _bytes(world_a / "src"); bb = _bytes(world_b / "src")
        self.assertEqual(ba, bb)
        self.assertEqual(ra["edit_count"], rb["edit_count"])

    def test_annassign_module_binding(self):
        _build(self.tmp, core="RATIO: float = 2.0\n\n\ndef top(v):\n    return v * RATIO\n",
               packages={"use/caller.py": ""})
        art = _run(self.tmp, qualname="RATIO", new_symbol="FACTOR")
        core = (self.tmp / "src/pkg/core.py").read_text()
        self.assertIn("FACTOR: float = 2.0", core)
        self.assertIn("v * FACTOR", core)
        self.assertEqual(art["symbol_kind"], "MODULE_BINDING")


if __name__ == "__main__":
    unittest.main()
