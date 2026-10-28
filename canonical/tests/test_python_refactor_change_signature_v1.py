# PROJECT_BRAIN
"""Pins for python.refactor.change_signature.v1 — change a def's signature and
every call site that must follow it, by byte splice, with a rollback gate.

The pins nail the LAWS, not the happy path:

* a rename moves the def, the body by lexical scope, and every keyword call
  site -- and leaves a POSITIONAL call site's bytes alone;
* a scope that rebinds the name is not this function: its calls are untouched;
* a required parameter is only added when the spec supplies the call value, and
  a function that ESCAPES as a value refuses the edit instead of leaving a
  broken arity somewhere this verb cannot see;
* removal is refused unless it is the trailing parameter with a default that
  nothing reads and nothing passes;
* a red named suite restores every byte, sha256-identical.

Run: python -m pytest canonical/tests/test_python_refactor_change_signature_v1.py -q
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
    python_refactor_change_signature as cs,
)

PY = sys.executable

CORE = '''def add(a, b):
    return a + b


def outer():
    def add(a, b):
        return a - b
    return add(a=1, b=2)
'''

CALLER = '''from pkg.core import add


def total():
    return add(1, 2) + add(a=3, b=4)
'''

ALIAS_CALLER = '''import pkg.core as core_mod


def via_alias():
    return core_mod.add(a=5, b=6)
'''

TESTS = '''from pkg.core import add


def test_add():
    assert add(1, 2) == 3
    assert add(a=3, b=4) == 7
'''

RED_TESTS = '''from pkg.core import add


def test_arity():
    assert add(1) == 1
'''

ESCAPES = '''from pkg.core import add

CALLBACK = add
'''


def _build(root: Path, core: str = CORE, caller: str = CALLER,
           extra: dict | None = None) -> Path:
    src = root / "src"
    (src / "pkg").mkdir(parents=True, exist_ok=True)
    (src / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (src / "pkg" / "core.py").write_text(core, encoding="utf-8")
    (src / "use").mkdir(parents=True, exist_ok=True)
    (src / "use" / "caller.py").write_text(caller, encoding="utf-8")
    (src / "pkg" / "test_ok.py").write_text(TESTS, encoding="utf-8")
    for rel, body in (extra or {}).items():
        f = src / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    return src


def _run(root: Path, **kw):
    args = {"source_root": "src", "module": "pkg/core.py", "qualname": "add",
            "output_path": "_out/sig.json", "python_executable": PY,
            "timeout_s": 120}
    args.update(kw)
    return cs.run(args, root), json.loads((root / "_out/sig.json").read_text())


def _snapshot(src: Path) -> dict:
    return {p.relative_to(src).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(src.rglob("*.py"))}


class TestChangeSignature(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="changesig_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_rename_reaches_def_body_and_keyword_call_sites_only(self):
        src = _build(self.tmp)
        res, art = _run(self.tmp, renames={"a": "x"}, run_tests=["pkg/test_ok.py"])
        core = (src / "pkg/core.py").read_text()
        caller = (src / "use/caller.py").read_text()
        self.assertIn("def add(x, b):", core)
        self.assertIn("return x + b", core)
        self.assertIn("add(x=3, b=4)", caller)
        self.assertIn("add(1, 2)", caller)          # positional bytes untouched
        self.assertEqual(art["gate"], "PASS")
        self.assertTrue(art["verified"])
        self.assertEqual(art["old_signature"], "(a, b)")
        self.assertEqual(art["new_signature"], "(x, b)")

    def test_a_scope_that_rebinds_the_name_is_not_this_function(self):
        src = _build(self.tmp)
        _run(self.tmp, renames={"a": "x"})
        core = (src / "pkg/core.py").read_text()
        # outer()'s own add is a different function; its keyword call keeps `a=`
        self.assertIn("def add(a, b):\n        return a - b", core)
        self.assertIn("return add(a=1, b=2)", core)

    def test_module_alias_call_site_follows_the_rename(self):
        src = _build(self.tmp, extra={"use/alias.py": ALIAS_CALLER})
        _run(self.tmp, renames={"a": "x"})
        alias = (src / "use/alias.py").read_text()
        self.assertIn("core_mod.add(x=5, b=6)", alias)

    def test_added_parameter_with_default_leaves_callers_alone(self):
        src = _build(self.tmp)
        res, art = _run(self.tmp, add=[{"name": "scale", "default": "1"}],
                        run_tests=["pkg/test_ok.py"])
        core = (src / "pkg/core.py").read_text()
        self.assertIn("def add(a, b, scale=1):", core)
        # caller.total has two calls and the pin suite has two more; outer()'s local
        # add is a different function and is not counted
        self.assertEqual(art["call_sites_edited"], 4)
        self.assertEqual(art["gate"], "PASS")

    def test_required_parameter_is_passed_at_every_resolved_call(self):
        src = _build(self.tmp)
        res, art = _run(self.tmp, add=[{"name": "scale"}], call_default="1",
                        run_tests=["pkg/test_ok.py"])
        caller = (src / "use/caller.py").read_text()
        self.assertIn("add(1, 2, scale=1)", caller)
        self.assertIn("add(a=3, b=4, scale=1)", caller)
        self.assertEqual(art["gate"], "PASS")

    def test_required_parameter_without_call_value_refuses(self):
        src = _build(self.tmp)
        before = _snapshot(src)
        with self.assertRaises(SystemExit) as raised:
            _run(self.tmp, add=[{"name": "scale"}])
        self.assertIn("REQUIRED_PARAM_NEEDS_CALL_VALUE", str(raised.exception))
        self.assertEqual(before, _snapshot(src))

    def test_escaping_function_object_refuses_a_non_backward_compatible_change(self):
        src = _build(self.tmp, extra={"use/esc.py": ESCAPES})
        before = _snapshot(src)
        with self.assertRaises(SystemExit) as raised:
            _run(self.tmp, add=[{"name": "scale"}], call_default="1")
        self.assertIn("FUNCTION_OBJECT_ESCAPES", str(raised.exception))
        self.assertEqual(before, _snapshot(src))

    def test_removal_of_a_parameter_callers_pass_refuses(self):
        src = _build(self.tmp, core="def add(a, b=0):\n    return a + b\n")
        before = _snapshot(src)
        with self.assertRaises(SystemExit) as raised:
            _run(self.tmp, remove=["b"])
        self.assertIn("PARAM_IN_USE", str(raised.exception))
        self.assertEqual(before, _snapshot(src))

    def test_trailing_defaulted_parameter_nothing_reads_is_removable(self):
        src = _build(self.tmp, core="def add(a, b=0):\n    return a\n",
                     caller="from pkg.core import add\n\n\ndef total():\n    return add(1)\n",
                     extra={"pkg/test_ok.py": "from pkg.core import add\n\n\ndef test_add():\n    assert add(1) == 1\n"})
        res, art = _run(self.tmp, remove=["b"], run_tests=["pkg/test_ok.py"])
        self.assertIn("def add(a):", (src / "pkg/core.py").read_text())
        self.assertEqual(art["gate"], "PASS")

    def test_red_suite_restores_every_byte(self):
        src = _build(self.tmp, extra={"pkg/test_red.py": RED_TESTS})
        before = _snapshot(src)
        with self.assertRaises(SystemExit) as raised:
            _run(self.tmp, renames={"a": "x"}, run_tests=["pkg/test_red.py"])
        self.assertIn("TESTS_RED_AFTER_EDIT", str(raised.exception))
        self.assertEqual(before, _snapshot(src))

    def test_no_tests_named_is_pass_blind_and_says_so(self):
        _build(self.tmp)
        res, art = _run(self.tmp, renames={"a": "x"})
        self.assertEqual(art["gate"], "PASS_BLIND")
        self.assertFalse(art["verified"])

    def test_structured_edit_spec_is_a_file(self):
        src = _build(self.tmp)
        (self.tmp / "sig.json").write_text(
            json.dumps({"renames": {"a": "left"},
                        "add": [{"name": "scale", "default": "1"}]}), encoding="utf-8")
        res, art = _run(self.tmp, edits_path="sig.json", run_tests=["pkg/test_ok.py"])
        self.assertEqual(art["new_signature"], "(left, b, scale=1)")
        self.assertEqual(art["edits_path"], "sig.json")
        self.assertEqual(art["gate"], "PASS")

    def test_nothing_stated_refuses_and_changes_nothing(self):
        src = _build(self.tmp)
        before = _snapshot(src)
        with self.assertRaises(SystemExit) as raised:
            _run(self.tmp)
        self.assertIn("SIGNATURE_NOT_STATED", str(raised.exception))
        self.assertEqual(before, _snapshot(src))

    def test_determinism_two_pristine_worlds_are_byte_identical(self):
        first = Path(tempfile.mkdtemp(prefix="changesig_a_"))
        second = Path(tempfile.mkdtemp(prefix="changesig_b_"))
        self.addCleanup(shutil.rmtree, first, True)
        self.addCleanup(shutil.rmtree, second, True)
        _build(first)
        _build(second)
        _, art_a = _run(first, renames={"a": "x"}, add=[{"name": "scale", "default": "1"}])
        _, art_b = _run(second, renames={"a": "x"}, add=[{"name": "scale", "default": "1"}])
        self.assertEqual(_snapshot(first / "src"), _snapshot(second / "src"))
        self.assertEqual(art_a["new_signature"], art_b["new_signature"])
        self.assertEqual(art_a["edit_count"], art_b["edit_count"])


if __name__ == "__main__":
    unittest.main()
