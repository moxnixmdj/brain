"""A rename must answer the object the sentence names, not a sibling of it.

Measured on main f333567, 3/3, with the filesystem as the oracle:

    "Rename the parameter text to value in the python module <D>/app/models.py."
      -> python.refactor.rename_symbol.v1
      -> PASS, and the FUNCTION was renamed:  def value(text, scale=1)
      the parameter kept its name, `use()` still passed it positionally, and the
      module's public name changed.  Every byte-level gate saw the bytes of the
      named file change, so nothing could tell that the WRONG OBJECT was edited.

    the same sentence plus "and save the report to <D>/r.json"
      -> python.refactor.rename_parameter.v1  ->  def norm(value, scale=1)

Two unrelated clauses decided which object was edited.  The cause was that the
admission rule "the sentence states this row's declared contract completely"
binds a SIBLING row as easily as the intended one: `qualname=norm, new_symbol=value`
binds perfectly -- for a sentence about a parameter.

The law pinned here is read off the sentence's noun and the row's own declared
slots, so nothing is invented:

  * a sentence that says "parameter"/"argument" is about a PARAMETER;
  * a row that declares `old_param`/`new_param` edits a PARAMETER;
  * `qualname`/`new_symbol` edits a SYMBOL;
  * a PASS from a row whose declared object contradicts the stated one is not a PASS.
"""
from __future__ import annotations

import pathlib
import shutil
import unittest

from canonical.runtime import live_brain_route_admission_v1 as door

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = ROOT / "canonical/astra_runtime/tmp/test_rename_answers_the_object"

SOURCE = (
    "def norm(text, scale=1):\n"
    "    return text.strip().lower() * scale\n"
    "\n\n"
    "def use(s):\n"
    "    return norm(s, 2)\n"
)


def _tree(tag: str) -> pathlib.Path:
    d = BASE / tag
    if d.exists():
        shutil.rmtree(d)
    (d / "app").mkdir(parents=True)
    (d / "app/__init__.py").write_text("", encoding="utf-8")
    (d / "app/models.py").write_text(SOURCE, encoding="utf-8")
    return d


def _rel(p: pathlib.Path) -> str:
    return p.relative_to(ROOT).as_posix()


class ObjectRoleTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(BASE, ignore_errors=True)

    def test_the_stated_role_is_read_off_the_noun(self):
        self.assertEqual(door.stated_object_roles(
            "Rename the parameter text to value in the python module a/b/models.py."), {"PARAMETER"})
        self.assertEqual(door.stated_object_roles(
            "Rename the function norm to normalize in a/b/models.py."), {"SYMBOL"})
        self.assertEqual(door.stated_object_roles(
            "Rename the class Item to Product in a/b/models.py."), {"SYMBOL"})
        self.assertEqual(door.stated_object_roles(
            "Rename the local variable item to obj in a/b/models.py."), {"LOCAL"})

    def test_a_path_head_after_a_noun_is_not_a_symbol_named_by_the_sentence(self):
        """'the python module canonical/x/models.py' must not read `canonical` as a name."""
        self.assertEqual(door.stated_object_roles(
            "Rename the parameter text to value in the python module canonical/x/models.py."),
            {"PARAMETER"})

    def test_the_declared_role_is_read_off_the_row_slots(self):
        self.assertEqual(door.declared_object_roles({"action_template": {"args": {
            "old_param": "a", "new_param": "b", "qualname": "c"}}}), {"PARAMETER", "SYMBOL"})
        self.assertEqual(door.declared_object_roles({"action_template": {"args": {
            "qualname": "c", "new_symbol": "d"}}}), {"SYMBOL"})

    def test_a_contradiction_is_an_error_and_nothing_else_is(self):
        symbol_row = {"action_template": {"args": {"qualname": "c", "new_symbol": "d"}}}
        self.assertTrue(door.object_role_errors(
            "Rename the parameter text to value in a/b/models.py.", symbol_row))
        self.assertEqual(door.object_role_errors(
            "Rename the function norm to normalize in a/b/models.py.", symbol_row), [])
        # no stated role, or no declared role: untouched
        self.assertEqual(door.object_role_errors("Rename things.", symbol_row), [])
        self.assertEqual(door.object_role_errors(
            "Rename the parameter text to value.", {"action_template": {"args": {"src": "x"}}}), [])

    def test_the_parameter_rename_edits_the_parameter(self):
        base = _tree("param")
        models = base / "app/models.py"
        result = door.solve({
            "task_id": "ROLE_param",
            "goal": "Rename the parameter text to value in the python module %s." % _rel(models),
        })
        text = models.read_text(encoding="utf-8")
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertIn("def norm(value, scale=1):", text,
                      "the parameter was not the thing renamed")
        self.assertNotIn("def value(text", text,
                         "the FUNCTION was renamed for a sentence about a parameter")

    def test_the_same_sentence_without_a_report_clause_answers_the_same_object(self):
        """The measured pair: the report clause must not decide which object is edited."""
        for tag, goal_template in (
            ("plain", "Rename the parameter text to value in the python module %s."),
            ("report", "Rename the parameter text to value in the python module %s "
                       "and save the report to %s.json."),
        ):
            base = _tree(tag)
            models = base / "app/models.py"
            goal = (goal_template % ((_rel(models),) if tag == "plain"
                                     else (_rel(models), _rel(base / "r"))))
            result = door.solve({"task_id": "ROLE_" + tag, "goal": goal})
            with self.subTest(tag=tag):
                self.assertIs(result.get("pass"), True, result.get("status"))
                self.assertIn("def norm(value, scale=1):", models.read_text(encoding="utf-8"))

    def test_a_function_rename_still_renames_the_function(self):
        base = _tree("func")
        models = base / "app/models.py"
        result = door.solve({
            "task_id": "ROLE_func",
            "goal": "Rename the function norm to normalize in %s." % _rel(models),
        })
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertIn("def normalize(text, scale=1):", models.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
