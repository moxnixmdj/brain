# PROJECT_BRAIN
"""Pins for python.refactor.inline_function.v1.

Inlining is the only refactor here whose failure mode is *silently wrong code*: the module still
parses, the call is gone, and the answer is different.  So what is pinned is not the happy path --
it is the five laws that keep the answer the same:

* a parameter that is already live at the site is RENAMED, and the returned expression is renamed
  with it, because the expression was written in the callee's scope;
* the definition is deleted only when the module was its only user -- a sibling or a test file
  that imports the name keeps it, and the suite stays green;
* a body whose return is inside a branch is refused, named, rather than spliced with an invented
  flag;
* a call site nested in an expression is refused, named by line;
* a red post-edit suite restores every byte, and no named suite means PASS_BLIND with
  verified=false, stated loudly.

Run: python -m pytest canonical/tests/test_python_refactor_inline_function_v1.py -q
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import python_refactor_inline_function as I

CAP = "python.refactor.inline_function.v1"

CALC = '''def add(a, b):
    return a + b


def sub(a, b):
    diff = a - b
    return diff


def scale(n):
    return n * 2


def use(x):
    y = 2
    return sub(x, y)


def other():
    return sub(1, add(2, 3))
'''

TESTS = '''from pkg.calc import add, sub, scale, use, other


def test_use():
    assert use(5) == 3


def test_other():
    assert other() == -4


def test_scale():
    assert scale(4) == 8


def test_add_sub():
    assert add(1, 2) == 3
    assert sub(5, 2) == 3
'''


class _Repo(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="inline_pin_"))
        self.root = self.tmp / "repo"
        (self.root / "pkg").mkdir(parents=True)
        (self.root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        self.write("pkg/calc.py", CALC)
        self.write("pkg/test_calc.py", TESTS)

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def read(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def inline(self, qualname: str = "sub", **extra):
        args = {"source_root": str(self.root), "module": "pkg/calc.py",
                "qualname": qualname, "output_path": str(self.root / ".out" / "inline.json"),
                "run_tests": ["pkg/test_calc.py"]}
        args.update(extra)
        return I.run(args, self.root)

    def refuse(self, qualname: str = "sub", **extra) -> str:
        with self.assertRaises(I.InlineError) as ctx:
            self.inline(qualname=qualname, **extra)
        return str(ctx.exception)


class InlineLawTests(_Repo):

    def test_every_call_site_is_inlined_and_the_suite_stays_green(self):
        result = self.inline()
        self.assertEqual(result["gate"], "PASS")
        self.assertEqual(result["inlined_sites"], [16, 20])
        self.assertTrue(result["verified"])
        text = self.read("pkg/calc.py")
        self.assertNotIn("sub(x, y)", text)
        self.assertNotIn("sub(1, add(2, 3))", text)
        # the body is carried over byte-faithfully, at the site's indentation
        self.assertIn("    a = x\n    b = y\n    diff = a - b\n    return diff\n", text)

    def test_the_definition_is_kept_when_tests_import_it(self):
        result = self.inline()
        self.assertFalse(result["function_removed"])
        self.assertEqual(result["external_references"], ["pkg/test_calc.py"])
        self.assertIn("def sub(a, b):", self.read("pkg/calc.py"))

    def test_the_definition_is_deleted_once_nothing_names_it(self):
        self.write("pkg/calc.py", "def scale(n):\n    return n * 2\n\n\n"
                                  "def call():\n    t = 0\n    for n in range(3):\n"
                                  "        t += scale(n)\n    return t\n")
        self.write("pkg/test_calc.py", "def test_nothing():\n    assert True\n")
        result = self.inline(qualname="scale", run_tests=[])
        self.assertTrue(result["function_removed"])
        self.assertNotIn("def scale", self.read("pkg/calc.py"))
        self.assertIn("t += _inl_n * 2", self.read("pkg/calc.py"))

    def test_a_live_parameter_is_renamed_and_the_answer_is_unchanged(self):
        self.write("pkg/calc.py", "def scale(n):\n    return n * 2\n\n\n"
                                  "def call():\n    t = 0\n    for n in range(3):\n"
                                  "        t += scale(n)\n    return t\n")
        result = self.inline(qualname="scale", run_tests=[])
        self.assertEqual(result["renames"], {"n": "_inl_n"})
        self.assertIn("_inl_n = n", self.read("pkg/calc.py"))
        # the value expression came from the callee's scope, so it is renamed with the binding
        self.assertIn("t += _inl_n * 2", self.read("pkg/calc.py"))

    def test_call_lines_restricts_the_edit_to_one_site(self):
        result = self.inline(call_lines=[16])
        self.assertEqual(result["inlined_sites"], [16])
        self.assertIn("sub(1, add(2, 3))", self.read("pkg/calc.py"))


class InlineRefusalTests(_Repo):

    def test_a_branching_return_is_refused_not_spliced(self):
        self.write("pkg/calc.py", "def clamp(v, hi):\n    if v > hi:\n        return hi\n"
                                  "    return v\n\n\ndef use(v):\n    return clamp(v, 3)\n")
        self.assertIn("INLINE_MULTIPLE_RETURNS", self.refuse(qualname="clamp"))

    def test_a_call_inside_an_expression_is_refused_by_line(self):
        self.write("pkg/calc.py", "def scale(n):\n    return n * 2\n\n\n"
                                  "def call(k):\n    return scale(k) + 1\n")
        reason = self.refuse(qualname="scale")
        self.assertIn("INLINE_NO_CALL_SITES", reason)
        self.assertIn("CALL_SITE_INSIDE_EXPRESSION:6", reason)

    def test_a_function_with_no_caller_is_refused_by_name(self):
        self.write("pkg/calc.py", "def lonely(n):\n    return n\n")
        self.assertIn("INLINE_NO_CALL_SITES:lonely", self.refuse(qualname="lonely"))

    def test_a_recursive_function_is_refused(self):
        self.write("pkg/calc.py", "def fact(n):\n    return n * fact(n - 1)\n\n\n"
                                  "def call():\n    return fact(3)\n")
        self.assertIn("RECURSIVE_FUNCTION_UNSUPPORTED", self.refuse(qualname="fact"))


class InlineRefereeTests(_Repo):

    def test_a_red_suite_restores_every_byte(self):
        before = self.read("pkg/calc.py")
        self.write("pkg/test_calc.py", TESTS.replace("assert use(5) == 3", "assert use(5) == 99"))
        self.assertIn("TESTS_RED_AFTER_EDIT", self.refuse())
        self.assertEqual(self.read("pkg/calc.py"), before)

    def test_no_named_suite_is_blind_not_verified(self):
        result = self.inline(run_tests=[])
        self.assertEqual(result["gate"], "PASS_BLIND")
        self.assertFalse(result["verified"])
        payload = json.loads((self.root / ".out" / "inline.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["qualname"], "sub")
        self.assertTrue(result["output_verified"])


if __name__ == "__main__":
    unittest.main()
