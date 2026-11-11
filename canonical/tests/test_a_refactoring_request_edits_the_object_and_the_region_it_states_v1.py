"""A refactoring request edits the object and the region the sentence states.

Measured 2026-11-11 through the front door (`live_brain_route_admission_v1.solve`) on main 62fa7efa.
The engines were right; the sentence was read wrongly, and the door answered PASS.

1. "rename the variable tmp to product in the function compute in <f>"
     -> python.refactor.rename_symbol.v1 -> PASS, and the FUNCTION was renamed
        (``def product(a, b, verbose=False)``).  The same with the names in quotes, and with
        "the local variable".
   The sentence states two roles.  The existing rule refused a row only when it shared NO role with
   the sentence; this row shared "function", which is where the rename happens, not what it is about.

2. "Extract the function compute from the module <f> lines 13 to 14 into a new function named scale."
     -> start_line=13, end_line=13 -> PASS.  With "lines 13 to 16": the same single line -> PASS.
   No rule on that lane read the numbers, so a search for "the smallest self-contained block" chose
   one, and it happened to begin on the stated line.

The rules pinned here:

* a parameter or a variable the sentence names must be something the serving row can hold;
* a name in quotes or backticks states its role like a bare name;
* a stated line range is bound as written, a range that splits a statement is refused, and without
  a named function the lines say which function they are in.
"""
from __future__ import annotations

import ast
import pathlib
import shutil
import unittest

from canonical.runtime import declared_input_derivation_v1 as derivation
from canonical.runtime import live_brain_route_admission_v1 as door

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = ROOT / "canonical/astra_runtime/tmp/test_refactoring_object_and_region"

SOURCE = '''import math

SECONDS = 3600


def double(x):
    return 2 * x


def compute(a, b, verbose=False):
    tmp = a * b
    scaled = tmp / 3600
    if verbose:
        print("scaled", scaled)
    total = scaled + double(a)
    return total


class Shape:
    def __init__(self, r):
        self.r = r

    def area(self):
        radius = self.r
        return math.pi * radius * radius
'''
# line 10 is ``def compute``; 11 ``tmp = a * b``; 12 ``scaled = ...``; 13-14 the ``if``; 15 ``total = ...``

SYMBOL_ROW = {"action_template": {"args": {"qualname": "${input.qualname}", "new_symbol": "${input.new_symbol}"}}}
PARAMETER_ROW = {"action_template": {"args": {"qualname": "${input.qualname}", "old_param": "${input.old_param}",
                                               "new_param": "${input.new_param}"}}}
NO_ROLE_ROW = {"action_template": {"args": {"input_path": "${input.input_path}"}}}


def _file(tag: str) -> pathlib.Path:
    d = BASE / tag
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    (d / "calc.py").write_text(SOURCE, encoding="utf-8")
    return d / "calc.py"


def _rel(p: pathlib.Path) -> str:
    return p.relative_to(ROOT).as_posix()


def _run(namespace_source: str, call: str):
    scope: dict = {}
    exec(compile(namespace_source, "<refactored>", "exec"), scope)  # noqa: S102 - the module under test
    return eval(call, scope)  # noqa: S307


class TheObjectTheSentenceNames(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(BASE, ignore_errors=True)

    # ---- the rule ------------------------------------------------------------------------------

    def test_a_quoted_name_states_its_role_like_a_bare_one(self):
        for sentence, expected in (
            ("rename the variable 'tmp' to 'product' in a/b/calc.py", {"LOCAL"}),
            ('rename the variable "tmp" to "product" in a/b/calc.py', {"LOCAL"}),
            ("rename the variable `tmp` to `product` in a/b/calc.py", {"LOCAL"}),
            ("rename the parameter 'a' to 'left' in a/b/calc.py", {"PARAMETER"}),
            ("rename the function 'double' to 'twice' in a/b/calc.py", {"SYMBOL"}),
            ("rename the variable 'tmp' to 'product' in the function 'compute' in a/b/calc.py", {"LOCAL", "SYMBOL"}),
        ):
            self.assertEqual(door.stated_object_roles(sentence), expected, sentence)

    def test_a_quoted_path_head_is_still_not_a_symbol(self):
        self.assertEqual(door.stated_object_roles(
            "Rename the parameter text to value in the python module canonical/x/models.py."), {"PARAMETER"})

    def test_a_row_must_be_able_to_hold_the_variable_or_parameter_the_sentence_names(self):
        cannot = door.object_roles_a_row_cannot_answer
        # the original rule: no shared role
        self.assertEqual(cannot({"PARAMETER"}, {"SYMBOL"}), {"PARAMETER"})
        # the new case: one role shared, the operand left over
        self.assertEqual(cannot({"LOCAL", "SYMBOL"}, {"SYMBOL"}), {"LOCAL"})
        self.assertEqual(cannot({"PARAMETER", "SYMBOL"}, {"SYMBOL"}), {"PARAMETER"})
        # everything that was fine stays fine
        self.assertEqual(cannot({"SYMBOL"}, {"SYMBOL"}), set())
        self.assertEqual(cannot({"PARAMETER", "SYMBOL"}, {"PARAMETER", "SYMBOL"}), set())
        self.assertEqual(cannot({"SYMBOL"}, {"PARAMETER", "SYMBOL"}), set())
        self.assertEqual(cannot(set(), {"SYMBOL"}), set())
        self.assertEqual(cannot({"LOCAL"}, set()), set())

    def test_the_exit_check_reads_the_same_rule(self):
        sentence = "rename the variable tmp to product in the function compute in a/b/calc.py"
        self.assertEqual(door.object_role_errors(sentence, SYMBOL_ROW), ["OBJECT_ROLE_MISMATCH:LOCAL+SYMBOL!=SYMBOL"])
        self.assertEqual(door.object_role_errors(sentence, NO_ROLE_ROW), [])
        self.assertEqual(door.object_role_errors(
            "rename the parameter a to left in the function compute in a/b/calc.py", PARAMETER_ROW), [])
        self.assertEqual(door.object_role_errors(
            "rename the function double to twice in a/b/calc.py", SYMBOL_ROW), [])

    # ---- through the front door ------------------------------------------------------------------

    def test_a_request_to_rename_a_variable_does_not_rename_the_function(self):
        for tag, template in (
            ("bare", "rename the variable tmp to product in the function compute in %s"),
            ("quoted", "rename the variable 'tmp' to 'product' in the function 'compute' in %s"),
            ("local", "Rename the local variable tmp to product in the function compute in %s."),
        ):
            with self.subTest(tag):
                path = _file("variable_" + tag)
                result = door.solve({"task_id": "REFACTOR_variable_" + tag, "goal": template % _rel(path)})
                self.assertIsNot(result.get("pass"), True, result.get("status"))
                self.assertIsNot(result.get("executed"), True, "a row ran for a sentence it cannot answer")
                self.assertEqual(path.read_text(encoding="utf-8"), SOURCE, "the file was edited")

    def test_the_renames_that_were_right_are_still_done(self):
        path = _file("function")
        result = door.solve({"task_id": "REFACTOR_function",
                             "goal": "rename the function 'double' to 'twice' in %s" % _rel(path)})
        self.assertIs(result.get("pass"), True, result.get("status"))
        text = path.read_text(encoding="utf-8")
        self.assertIn("def twice(x):", text)
        self.assertIn("total = scaled + twice(a)", text)
        self.assertEqual(_run(text, "compute(3, 4)"), _run(SOURCE, "compute(3, 4)"))

        path = _file("parameter")
        result = door.solve({"task_id": "REFACTOR_parameter",
                             "goal": "rename the parameter 'a' to 'left' in the function 'compute' in %s" % _rel(path)})
        self.assertIs(result.get("pass"), True, result.get("status"))
        text = path.read_text(encoding="utf-8")
        self.assertIn("def compute(left, b, verbose=False):", text)
        self.assertIn("tmp = left * b", text)
        self.assertEqual(result.get("compiled_capability_id"), "python.refactor.rename_parameter.v1")


class TheRegionTheSentenceStates(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(BASE, ignore_errors=True)

    def _extract(self, tag: str, template: str):
        path = _file(tag)
        result = door.solve({"task_id": "REFACTOR_" + tag, "goal": template % _rel(path)})
        return result, path.read_text(encoding="utf-8")

    def _helper(self, text: str, name: str) -> ast.FunctionDef:
        for node in ast.parse(text).body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        self.fail("no function %s in the result" % name)

    def test_two_stated_lines_are_two_extracted_lines(self):
        result, text = self._extract(
            "two", "Extract the function compute from the module %s lines 11 to 12 into a new function named scale.")
        self.assertIs(result.get("pass"), True, result.get("status"))
        helper = self._helper(text, "scale")
        self.assertEqual([ast.unparse(s) for s in helper.body],
                         ["tmp = a * b", "scaled = tmp / 3600", "return scaled"])
        self.assertIn("    scaled = scale(a, b)\n    if verbose:", text)
        for call in ("compute(3, 4)", "compute(0, 9)", "compute(-2.5, 8)"):
            self.assertEqual(_run(text, call), _run(SOURCE, call), call)

    def test_a_longer_stated_region_is_extracted_whole(self):
        result, text = self._extract(
            "four", "Extract the function compute from the module %s lines 11 to 14 into a new function named scale.")
        self.assertIs(result.get("pass"), True, result.get("status"))
        helper = self._helper(text, "scale")
        self.assertEqual([type(s).__name__ for s in helper.body], ["Assign", "Assign", "If", "Return"])
        self.assertEqual([a.arg for a in helper.args.args], ["a", "b", "verbose"])
        self.assertEqual(_run(text, "compute(3, 4)"), _run(SOURCE, "compute(3, 4)"))

    def test_one_stated_line_is_a_region_of_one_line(self):
        result, text = self._extract(
            "one", "Extract the function compute from the module %s line 12 into a new function named scale.")
        self.assertIs(result.get("pass"), True, result.get("status"))
        helper = self._helper(text, "scale")
        self.assertEqual([ast.unparse(s) for s in helper.body], ["scaled = tmp / 3600", "return scaled"])

    def test_a_region_that_splits_a_statement_is_refused_not_replaced(self):
        result, text = self._extract(
            "split", "Extract the function compute from the module %s lines 12 to 13 into a new function named scale.")
        self.assertIsNot(result.get("pass"), True, result.get("status"))
        self.assertIn("REGION_NOT_STATEMENT_ALIGNED", str(result.get("status")) + str(result.get("reason")))
        self.assertEqual(text, SOURCE, "another region was extracted instead of the stated one")

    def test_without_a_named_function_the_lines_say_which_one(self):
        for tag, template in (
            ("bare", "extract lines 11 to 12 of %s into a function named scale"),
            ("quoted", "extract lines 11 to 12 of %s into a function named 'scale'"),
        ):
            with self.subTest(tag):
                result, text = self._extract("nohost_" + tag, template)
                self.assertIs(result.get("pass"), True, result.get("status"))
                self.assertEqual(result.get("compiled_capability_id"), "python.refactor.extract_function.v1")
                helper = self._helper(text, "scale")
                self.assertEqual([ast.unparse(s) for s in helper.body],
                                 ["tmp = a * b", "scaled = tmp / 3600", "return scaled"])
                self.assertEqual(_run(text, "compute(3, 4)"), _run(SOURCE, "compute(3, 4)"))

    def test_the_function_that_holds_the_lines(self):
        tree = ast.parse(SOURCE)
        spanning = derivation._innermost_function_spanning
        self.assertEqual(spanning(tree, 11, 12), "compute")
        self.assertEqual(spanning(tree, 15, 15), "compute")
        self.assertEqual(spanning(tree, 24, 25), "Shape.area")
        self.assertEqual(spanning(tree, 10, 12), "", "a region may not begin on the def line")
        self.assertEqual(spanning(tree, 7, 11), "", "no one function holds lines of two")
        self.assertEqual(spanning(tree, 3, 3), "", "module level is not a function")
        nested = ast.parse("def outer():\n    def inner():\n        x = 1\n        return x\n    return inner\n")
        self.assertEqual(spanning(nested, 3, 4), "outer.inner")
        self.assertEqual(spanning(nested, 5, 5), "outer")

    def test_the_stated_lines_are_read_in_the_usual_spellings(self):
        for sentence, expected in (
            ("extract lines 11 to 12 of f.py", ("11", "12")),
            ("extract lines 11-12 of f.py", ("11", "12")),
            ("extract lines 11 through 12 of f.py", ("11", "12")),
            ("extract lines 11..12 of f.py", ("11", "12")),
            ("extract line 7 of f.py", ("7", None)),
            ("extract the first lines of f.py", None),
            ("extract the 3 longest lines of f.py", None),
        ):
            found = derivation._STATED_LINES.search(sentence)
            self.assertEqual(found.groups() if found else None, expected, sentence)


if __name__ == "__main__":
    unittest.main()
