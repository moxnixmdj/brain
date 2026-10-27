# PROJECT_BRAIN
"""Pins for python.refactor.rename_parameter.v1 — scope-aware parameter rename
with cross-file kwarg propagation.  The pins exist to nail the scoping LAWS:
shadowed bindings keep the old name, dynamic receivers list-and-lower-complete,
named tests gate the bytes, and a red suite rolls the whole edit back.

Run: python -m pytest canonical/tests/test_python_refactor_rename_parameter_v1.py -q
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
    python_refactor_rename_parameter as rp,
)

PY = sys.executable

CORE = '''def fib(n: int, depth: int = 0) -> int:
    if n < 2:
        return n
    inner_lambda = lambda m: n + m
    return fib(n - 1) + fib(n - 2) + inner_lambda(depth)
'''

CALLER = '''from pkg.core import fib


def run_twice(size: int) -> int:
    return fib(n=size) + fib(n=10, depth=0)


def run_positional(k: int) -> int:
    return fib(k)
'''

ALIAS_CALLER = '''import pkg.core as core_mod


def via_alias(amount: int) -> int:
    return core_mod.fib(n=amount)
'''

SHADOWED = '''def fib(n: int, depth: int = 0) -> int:
    total = n
    def helper(n):
        return n * 100
    return helper(n) + fib(n - 1) if n > 1 else total
'''

BROKEN_CALLER_TESTRIG = '''from pkg.core import fib
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
'''


def _build(root: Path, core: str = CORE, caller: str = CALLER, extra: dict | None = None):
    src = root / "src"
    (src / "pkg").mkdir(parents=True, exist_ok=True)
    (src / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (src / "pkg" / "core.py").write_text(core, encoding="utf-8")
    (src / "use").mkdir(parents=True, exist_ok=True)
    (src / "use" / "caller.py").write_text(caller, encoding="utf-8")
    for rel, body in (extra or {}).items():
        f = src / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    return src


def _run(root: Path, **kw):
    args = {"source_root": "src", "module": "pkg/core.py", "qualname": "fib",
            "old_param": "n", "new_param": "size",
            "output_path": "_out/refactor.json",
            "python_executable": PY, "timeout_s": 120}
    args.update(kw)
    return rp.run(args, root), json.loads((root / "_out/refactor.json").read_text())


class TestRenameParameter(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="renameparam_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_definition_body_and_cross_file_kwargs_renamed(self):
        _build(self.tmp)
        res, art = _run(self.tmp)
        core = (self.tmp / "src/pkg/core.py").read_text()
        caller = (self.tmp / "src/use/caller.py").read_text()
        self.assertIn("def fib(size: int, depth: int = 0) -> int:", core)
        self.assertIn("return fib(size - 1)", core)
        self.assertIn("lambda m: size + m", core)  # closure captures renamed param
        self.assertIn("fib(size=size)", caller)     # from-import kwarg site
        self.assertIn("fib(size=10, depth=0)", caller)
        self.assertIn("fib(k)", caller)             # positional UNTOUCHED
        self.assertNotIn("(n=", caller)
        self.assertNotIn("def fib(n", core)
        self.assertTrue(art["complete"])

    def test_alias_module_form_propagates(self):
        _build(self.tmp, extra={"use/alias.py": ALIAS_CALLER})
        res, art = _run(self.tmp)
        alias = (self.tmp / "src/use/alias.py").read_text()
        self.assertIn("core_mod.fib(size=amount)", alias)

    def test_shadowing_law_inner_binding_keeps_old_name(self):
        _build(self.tmp, core=SHADOWED)
        res, art = _run(self.tmp)
        core = (self.tmp / "src/pkg/core.py").read_text()
        self.assertIn("def fib(size: int, depth: int = 0) -> int:", core)
        self.assertIn("total = size", core)
        self.assertIn("def helper(n):", core)       # helper's OWN n survives
        self.assertIn("return n * 100", core)       # and its body untouched
        self.assertIn("helper(size) + fib(size - 1)", core)
        self.assertTrue(any(s["scope"] == "helper" for s in art["shadowed_keeps"]))

    def test_dynamic_receiver_lowers_complete_but_never_edits(self):
        dynamic = '''obj = __import__("pkg.core", fromlist=["fib"])


def duck(amount: int) -> int:
    return obj.fib(n=amount)
'''
        _build(self.tmp, extra={"use/dyn.py": dynamic})
        res, art = _run(self.tmp)
        self.assertFalse(art["complete"])
        self.assertTrue(any("dynamic receiver" in s.get("rule", "") for s in art["unknown_sites"]))
        self.assertIn("obj.fib(n=amount)", (self.tmp / "src/use/dyn.py").read_text())

    def test_star_kwargs_passthrough_listed(self):
        star = '''from pkg.core import fib


def relay(kw):
    return fib(**kw)
'''
        _build(self.tmp, extra={"use/star.py": star})
        res, art = _run(self.tmp)
        self.assertFalse(art["complete"])
        self.assertTrue(any("star-star" in s.get("rule", "") for s in art["unknown_sites"]))

    def test_getattr_dynamic_dispatch_listed_never_edited(self):
        dyn = '''import pkg.core as core_mod


def via_getattr(k: int) -> int:
    return getattr(core_mod, "fib")(n=k)
'''
        _build(self.tmp, extra={"use/dyn.py": dyn})
        res, art = _run(self.tmp)
        self.assertFalse(art["complete"])
        self.assertTrue(any("getattr" in s.get("rule", "") for s in art["unknown_sites"]))
        # dynamic dispatch site must survive byte-identical except resolvable files
        after = (self.tmp / "src/use/dyn.py").read_text()
        self.assertEqual(after, dyn)

    def test_named_tests_gate_the_bytes(self):
        test = ('import sys, pathlib\nsys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n'
                "from pkg.core import fib\n\n\ndef test_fib():\n    assert fib(5) + fib(n=5, depth=0) == 52\n")
        _build(self.tmp, extra={"tests/test_fib.py": test})
        res, art = _run(self.tmp, run_tests=["tests/test_fib.py"])
        self.assertEqual(res["gate"], "PASS")
        self.assertTrue(res["verified"])

    def test_red_tests_roll_back_everything(self):
        # red suite world: the assertion is simply wrong (fib(5)==26 not 25);
        # the pin measures the LAW: red => every edited byte restored
        test = ('import sys, pathlib\nsys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n'
                "from pkg.core import fib\n\n\ndef test_static_kw():\n    assert fib(5) == 25\n")
        _build(self.tmp, extra={"tests/test_fib.py": test})
        snapshots = {p: p.read_bytes() for p in (self.tmp / "src").rglob("*.py")}
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, run_tests=["tests/test_fib.py"])
        self.assertIn("TESTS_RED_AFTER_EDIT", str(ctx.exception))
        after = {p: p.read_bytes() for p in (self.tmp / "src").rglob("*.py")}
        self.assertEqual(snapshots, after)  # nothing edits if nothing proves

    def test_nonlocal_refuses(self):
        bad = "outer = 1\n\ndef fib(n, depth=0):\n    global outer\n    return n\n"
        _build(self.tmp, core=bad)
        core2 = 'def fib(n, depth=0):\n    global depth\n    return n\n'
        _build(self.tmp, core='def fib(n):\n    global n\n    return n')
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp)
        self.assertIn("REFUSE_NONLOCAL_OR_GLOBAL", str(ctx.exception))

    def test_param_not_found_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, old_param="nosuch")
        self.assertIn("PARAM_NOT_FOUND", str(ctx.exception))

    def test_new_name_collision_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, new_param="depth")
        self.assertIn("NEW_PARAM_ALREADY_PRESENT", str(ctx.exception))

    def test_invalid_identifier_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, new_param="1bad")
        self.assertIn("INVALID_IDENTIFIER", str(ctx.exception))

    def test_symbol_not_found_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, qualname="ghost")
        self.assertIn("SYMBOL_NOT_FOUND", str(ctx.exception))

    def test_byte_determinism_of_edit_application(self):
        _build(self.tmp)
        _run(self.tmp)
        r1 = {p: p.read_bytes() for p in (self.tmp / "src").rglob("*.py")}
        a1 = (self.tmp / "_out/refactor.json").read_bytes()
        # second world, identical inputs
        w2 = Path(tempfile.mkdtemp(prefix="renameparam2_"))
        self.addCleanup(shutil.rmtree, w2, True)
        _build(w2)
        _run(w2, output_path="_out/refactor.json")
        r2 = {str(p.relative_to(w2 / "src")): p.read_bytes() for p in (w2 / "src").rglob("*.py")}
        a2 = (w2 / "_out/refactor.json").read_bytes()
        self.assertEqual({str(k.relative_to(self.tmp / "src")): v for k, v in r1.items()}, r2)
        self.assertEqual(a1, a2)

    def test_path_escape_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, module="../outside.py")
        self.assertIn("PATH_ESCAPE", str(ctx.exception))

    def test_artifact_schema_and_counts(self):
        _build(self.tmp)
        res, art = _run(self.tmp)
        for key in ("schema", "module", "qualname", "old_param", "new_param",
                    "edit_count", "files_edited", "edits", "unknown_sites",
                    "shadowed_keeps", "positional_callsites_untouched",
                    "verification", "gate", "law", "complete"):
            self.assertIn(key, art)
        # def(1) + body uses (n in `if n<2`, `return n`, first fib call) + 2 caller kw sites
        self.assertGreaterEqual(art["edit_count"], 5)
        self.assertEqual(art["positional_callsites_untouched"], 3)  # 2 recursive + caller fib(k)


if __name__ == "__main__":
    unittest.main()
