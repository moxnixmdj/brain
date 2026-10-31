"""A capability that creates code must write it, wire it, test it -- and say so honestly.

Two sentences were unserved by the 28-task hardcore SWE surface probe on
2026-10-31, and both are ordinary software engineering:

    "Add a parameter qty with a default value to the function line_total in
     app/models.py and update every caller so behaviour is unchanged."
        -> routed to python.refactor.inline_helper.v1, which inlined something
           else; the call line_total(item, 3) still raised TypeError.

    "Add a function total_cents(item) to app/models.py that returns
     price_cents * qty, export it from app/__init__.py, and add a test for it in
     tests/test_total.py"
        -> FAIL_CLOSED__ROUTE_ADMISSION_REJECTED; nothing was written.

The laws these tests pin, in the order the machine applies them:

1. DERIVATION IS EVIDENCE.  An ADDED parameter is a name the sentence states and
   the stated function does NOT already declare; a created function's name is
   read from the sentence's own signature phrase.  A sentence that merely
   mentions "the function line_total" gains neither slot, which is what keeps a
   repair request from being answered by a signature editor.
2. THE DEFAULT IS THE VALUE THE BODY ALREADY USED, so omitting the parameter
   cannot change behaviour and no call site needs an edit.
3. THE FUNCTION IS THE SENTENCE'S, VERBATIM: signature, expression, module,
   export and test path all come from the words, and a free name that is not an
   attribute of the stated module's class is a REFUSAL, not a guess.
4. THE TEST'S EXPECTATION COMES FROM THE SPECIFICATION, not from the code under
   test: the stated expression is evaluated on sample values and the literal is
   asserted.  A red suite rolls every byte back.
5. AN ARTIFACT IS NEVER WRITTEN OVER A FILE THE ADAPTER EDITED.

Every test here fails on the baseline before these capabilities existed (the
first two because the sentences reached the wrong capability, the rest because
the adapters did not exist to be exercised).
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import (  # noqa: E402
    python_refactor_add_parameter as add_param,
    python_source_add_function as add_fn,
)
from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402

MODELS = '''"""Models."""


class Item:
    def __init__(self, name, price_cents, qty=1):
        self.name = name
        self.price_cents = price_cents
        self.qty = qty


def line_total(item):
    return item.price_cents * item.qty
'''

SERVICE = '''"""Logic."""
from app.models import line_total


def cart_total(items):
    return sum(line_total(i) for i in items)
'''

TEST_SERVICE = '''import unittest

from app.models import Item, line_total


class TestService(unittest.TestCase):
    def test_total(self):
        self.assertEqual(line_total(Item("a", 100, 2)), 200)
'''


def _fixture(tmp: pathlib.Path) -> pathlib.Path:
    (tmp / "app").mkdir(parents=True)
    (tmp / "tests").mkdir(parents=True)
    (tmp / "app/__init__.py").write_text("", encoding="utf-8")
    (tmp / "app/models.py").write_text(MODELS, encoding="utf-8")
    (tmp / "app/service.py").write_text(SERVICE, encoding="utf-8")
    (tmp / "tests/__init__.py").write_text("", encoding="utf-8")
    (tmp / "tests/test_service.py").write_text(TEST_SERVICE, encoding="utf-8")
    return tmp


def _run_py(base: pathlib.Path, code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", code], cwd=str(base),
                          capture_output=True, text=True,
                          env={"PYTHONPATH": str(base), "PATH": "/usr/bin:/bin"})


class TestAnAddedParameterDefaultsToWhatTheBodyRead(unittest.TestCase):
    def test_the_default_reproduces_the_old_behaviour_and_the_argument_overrides_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _fixture(pathlib.Path(tmp))
            out = add_param.run({"source_root": ".", "module": "app/models.py",
                                 "symbol": "line_total", "new_param": "qty",
                                 "output_path": "report.json"}, base)
            self.assertEqual(out["gate"], "PASS")
            self.assertTrue(out["verified"] or out["output_verified"])
            probe = _run_py(base, "from app.models import Item, line_total\n"
                                  "i = Item('a', 100, 2)\n"
                                  "print(line_total(i))\nprint(line_total(i, 3))\n")
            self.assertEqual(probe.returncode, 0, probe.stderr)
            self.assertEqual(probe.stdout.split(), ["200", "300"])

    def test_an_existing_parameter_is_a_refusal_not_a_second_declaration(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _fixture(pathlib.Path(tmp))
            with self.assertRaises(SystemExit) as raised:
                add_param.run({"source_root": ".", "module": "app/models.py",
                               "symbol": "line_total", "new_param": "item",
                               "output_path": "report.json"}, base)
            self.assertIn("ALREADY_DECLARED", str(raised.exception))

    def test_a_parameter_name_the_sentence_does_not_state_derives_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _fixture(pathlib.Path(tmp))
            goal = ("Rename the parameter item to thing in the function line_total "
                    "in %s/app/models.py" % base.as_posix())
            entry = {"action_template": {"args": {"capability_id": "x",
                                                  "new_param": "${input.new_param}"}}}
            values = derivation.derive(goal, entry, base)
            self.assertNotEqual(
                (values.get("new_param") or {}).get("rule"),
                "ADDED_PARAM_STATED_AND_NOT_DECLARED",
                "a rename sentence bound the ADDED-parameter rule: %r" % (values,))


class TestAStatedFunctionIsWrittenWiredAndTested(unittest.TestCase):
    def test_the_sentence_is_implemented_exported_and_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _fixture(pathlib.Path(tmp))
            out = add_fn.run({"source_root": "app", "module": "app/models.py",
                              "symbol": "total_cents", "params": ["item"],
                              "body": "price_cents * qty",
                              "export_module": "app/__init__.py",
                              "test_paths": ["tests/test_total.py"],
                              "output_path": "tests/test_total.py"}, base)
            self.assertEqual(out["gate"], "PASS")
            self.assertTrue((base / "tests/test_total.py").is_file())
            self.assertIn("total_cents", (base / "app/__init__.py").read_text())
            # the artifact must not be the test file it just wrote
            self.assertNotEqual(out["output_path"], "tests/test_total.py")
            self.assertTrue((base / out["output_path"]).is_file())
            oracle = _run_py(base, "from app.models import total_cents\n"
                                   "print(total_cents(type('I',(),{'price_cents':3,'qty':4})()))")
            self.assertEqual(oracle.returncode, 0, oracle.stderr)
            self.assertEqual(oracle.stdout.strip(), "12")

    def test_a_free_name_that_is_not_the_class_s_own_attribute_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _fixture(pathlib.Path(tmp))
            with self.assertRaises(SystemExit) as raised:
                add_fn.run({"source_root": "app", "module": "app/models.py",
                            "symbol": "total_cents", "params": ["item"],
                            "body": "price_cents * discount_rate",
                            "export_module": "app/__init__.py",
                            "test_paths": ["tests/test_total.py"],
                            "output_path": "report.json"}, base)
            self.assertIn("UNRESOLVED_FREE_NAME", str(raised.exception))

    def test_a_red_suite_rolls_every_byte_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _fixture(pathlib.Path(tmp))
            before = (base / "app/models.py").read_bytes()
            (base / "tests/test_broken.py").write_text(
                "import unittest\n\nclass T(unittest.TestCase):\n"
                "    def test_always_red(self):\n        self.fail('boom')\n", encoding="utf-8")
            with self.assertRaises(SystemExit) as raised:
                add_fn.run({"source_root": "app", "module": "app/models.py",
                            "symbol": "total_cents", "params": ["item"],
                            "body": "price_cents * qty",
                            "export_module": "app/__init__.py",
                            "test_paths": ["tests/test_total.py"],
                            "output_path": "report.json"}, base)
            self.assertIn("TESTS_RED_AFTER_EDIT", str(raised.exception))
            self.assertEqual((base / "app/models.py").read_bytes(), before)
            self.assertFalse((base / "tests/test_total.py").exists())

    def test_a_function_name_is_only_created_when_the_sentence_asks_for_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _fixture(pathlib.Path(tmp))
            repair = ("Repair %s/app/models.py so line_total(item) handles an empty cart"
                      % base.as_posix())
            entry = {"action_template": {"args": {"capability_id": "x",
                                                  "symbol": "${input.symbol}"}}}
            self.assertNotIn(
                "CREATED_FUNCTION_NAME_STATED",
                [(derivation.derive(repair, entry, base).get("symbol") or {}).get("rule")])
            create = ("Add a function total_cents(item) to %s/app/models.py that returns "
                      "price_cents * qty" % base.as_posix())
            self.assertEqual(derivation.derive(create, entry, base)["symbol"]["value"],
                             "total_cents")


if __name__ == "__main__":
    unittest.main()
