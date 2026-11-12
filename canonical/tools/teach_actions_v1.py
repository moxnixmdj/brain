#!/usr/bin/env python3
"""Teach the front door the actions in ``canonical/swe_kernel/taught_actions``.

    PYTHONPATH=. python3 canonical/tools/teach_actions_v1.py           # teach, write the bundle
    PYTHONPATH=. python3 canonical/tools/teach_actions_v1.py --check   # teach again, compare with the bundle

A lesson is: a program that does the action once (its ``REQUEST`` line holds the values of the first
example), the sentences the action may be asked with, the line the program prints when it is done,
and a second example with different values.

For every lesson this tool

1. checks that each taught value occurs once in the program, inside a string literal -- the compiler
   generalizes by replacing those values textually, so a second occurrence would be rewritten too
   and a value outside a string literal would let a request put code into the program;
2. runs the program on the first example and compares every file with what the lesson expects;
3. hands the program and each sentence to ``causal_trace_to_skill_compiler_v1`` with the second
   example, which runs the generalized program there and stores it only if that run qualifies;
4. compares every file of the second example with what the lesson expects (the compiler's own
   postcondition only reads the program's last line).

What qualifies is exported to ``canonical/astra_runtime/skills/COMPILED_WORKFLOWS_BUNDLE_V1.json``.
The front door seeds its skill database from that file.

The programs run inside the namespace sandbox.  Where no sandbox can be started nothing is taught.
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import pathlib
import sys
import tempfile
import tokenize

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler  # noqa: E402

PROGRAMS = ROOT / "canonical" / "swe_kernel" / "taught_actions"
BUNDLE = compiler.default_workflow_bundle_path()

LESSONS: list[dict] = [
    {
        "action": "rename_local_variable_v1",
        "parameters": ("path", "function", "old", "new"),
        "said_as": [
            "rename the variable '{old}' to '{new}' in the function '{function}' in {path}",
            "rename the local variable '{old}' to '{new}' in the function '{function}' in {path}",
        ],
        "answers": "renamed the variable '{old}' to '{new}' in the function '{function}' in {path}",
        "first_example": {
            "before": {"lessons_q7/ledger_q7.py": (
                "def settle_q7(entries, fee):\n"
                "    subtotal_q7 = 0\n"
                "    for entry in entries:\n"
                "        subtotal_q7 += entry  # running sum\n"
                "    return subtotal_q7 - fee\n")},
            "after": {"lessons_q7/ledger_q7.py": (
                "def settle_q7(entries, fee):\n"
                "    running_q7 = 0\n"
                "    for entry in entries:\n"
                "        running_q7 += entry  # running sum\n"
                "    return running_q7 - fee\n")},
        },
        "second_example": {
            "request": {"path": "shapes/geometry.py", "function": "Disc.area", "old": "r", "new": "radius"},
            "before": {"shapes/geometry.py": (
                "import math\n\n\n"
                "class Disc:\n"
                "    def __init__(self, r):\n"
                "        self.r = r\n\n"
                "    def area(self):\n"
                "        r = self.r\n"
                "        return math.pi * r * r\n")},
            "after": {"shapes/geometry.py": (
                "import math\n\n\n"
                "class Disc:\n"
                "    def __init__(self, r):\n"
                "        self.r = r\n\n"
                "    def area(self):\n"
                "        radius = self.r\n"
                "        return math.pi * radius * radius\n")},
        },
    },
    {
        "action": "inline_variable_v1",
        "parameters": ("path", "function", "name"),
        "said_as": [
            "inline the variable '{name}' in the function '{function}' in {path}",
            "inline the local variable '{name}' in the function '{function}' in {path}",
        ],
        "answers": "inlined the variable '{name}' in the function '{function}' in {path}",
        "first_example": {
            "before": {"lessons_q7/pricing_q7.py": (
                "def quote_q7(price, rate):\n"
                "    markup_q7 = price * rate\n"
                "    return round(price + markup_q7, 2)\n")},
            "after": {"lessons_q7/pricing_q7.py": (
                "def quote_q7(price, rate):\n"
                "    return round(price + (price * rate), 2)\n")},
        },
        "second_example": {
            "request": {"path": "report/lines.py", "function": "longest", "name": "ordered"},
            "before": {"report/lines.py": (
                "def longest(lines):\n"
                "    if not lines:\n"
                "        return ''\n"
                "    ordered = sorted(lines, key=len)\n"
                "    return ordered[-1]\n")},
            "after": {"report/lines.py": (
                "def longest(lines):\n"
                "    if not lines:\n"
                "        return ''\n"
                "    return sorted(lines, key=len)[-1]\n")},
        },
    },
    {
        "action": "edit_by_example_v1",
        "parameters": ("target", "before", "after"),
        "said_as": [
            "edit {target} the way {before} was changed into {after}",
            "make the same change in {target} that turned {before} into {after}",
        ],
        "answers": "edited {target} the way {before} was changed into {after}",
        "first_example": {
            "before": {
                "lessons_q7/shown_q7/earlier.py": (
                    "import unittest\n"
                    "\n"
                    "\n"
                    "class LedgerTest(unittest.TestCase):\n"
                    "    def test_total(self):\n"
                    "        self.assertEquals(total([1, 2]), 3)\n"
                    "        self.assertTrue(total([]) == 0)\n"
                    "\n"
                    "    def test_names(self):\n"
                    "        self.assertEquals(names(), ['a', 'b'], 'names differ')\n"),
                "lessons_q7/shown_q7/later.py": (
                    "import unittest\n"
                    "\n"
                    "\n"
                    "class LedgerTest(unittest.TestCase):\n"
                    "    def test_total(self):\n"
                    "        self.assertEqual(total([1, 2]), 3)\n"
                    "        self.assertTrue(total([]) == 0)\n"
                    "\n"
                    "    def test_names(self):\n"
                    "        self.assertEqual(names(), ['a', 'b'], 'names differ')\n"),
                "lessons_q7/suite_q7.py": (
                    "import unittest\n"
                    "\n"
                    "\n"
                    "class RatesTest(unittest.TestCase):\n"
                    "    def test_rate(self):\n"
                    "        self.assertEquals(rate(2), 0.5)  # half\n"
                    "        outcome = self.assertEquals(rate(4), 0.25, msg='quarter')\n"
                    "        other.assertEquals(outcome, None)\n"),
            },
            "after": {"lessons_q7/suite_q7.py": (
                "import unittest\n"
                "\n"
                "\n"
                "class RatesTest(unittest.TestCase):\n"
                "    def test_rate(self):\n"
                "        self.assertEqual(rate(2), 0.5)  # half\n"
                "        outcome = self.assertEqual(rate(4), 0.25, msg='quarter')\n"
                "        other.assertEquals(outcome, None)\n")},
        },
        "second_example": {
            "request": {"target": "checks/orders.py", "before": "checks/shown/as_it_was.py",
                        "after": "checks/shown/as_it_is.py"},
            "before": {
                "checks/shown/as_it_was.py": (
                    "def settle(total, rate):\n"
                    "    if total == None:\n"
                    "        return 0\n"
                    "    missing = rate.value == None\n"
                    "    return total == 0 or missing\n"),
                "checks/shown/as_it_is.py": (
                    "def settle(total, rate):\n"
                    "    if total is None:\n"
                    "        return 0\n"
                    "    missing = rate.value is None\n"
                    "    return total == 0 or missing\n"),
                "checks/orders.py": (
                    "def last(order, fallback):\n"
                    "    while order.parent == None:  # top of the chain\n"
                    "        order = order.following\n"
                    "    unset = (order.note or fallback) == None\n"
                    "    return unset == False\n"),
            },
            "after": {"checks/orders.py": (
                "def last(order, fallback):\n"
                "    while order.parent is None:  # top of the chain\n"
                "        order = order.following\n"
                "    unset = (order.note or fallback) is None\n"
                "    return unset == False\n")},
        },
    },
]


class LessonError(Exception):
    """A lesson that must not be taught as written."""


def program_and_request(lesson: dict) -> tuple[str, dict[str, str]]:
    """The program text and the values of its first example, read from its ``REQUEST`` line."""
    text = (PROGRAMS / (lesson["action"] + ".py")).read_text(encoding="utf-8")
    values = None
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and [getattr(t, "id", None) for t in node.targets] == ["REQUEST"]:
            try:
                values = ast.literal_eval(node.value)
            except ValueError:
                values = None
    if (not isinstance(values, tuple) or len(values) != len(lesson["parameters"])
            or not all(isinstance(value, str) and value for value in values)):
        raise LessonError("%s: REQUEST must be a tuple of %d string literals"
                          % (lesson["action"], len(lesson["parameters"])))
    request = dict(zip(lesson["parameters"], values))
    literals = [t.string for t in tokenize.generate_tokens(io.StringIO(text).readline) if t.type == tokenize.STRING]
    for key, value in request.items():
        if text.count(value) != 1:
            raise LessonError("%s: the taught %s %r occurs %d times in the program; it must occur once"
                              % (lesson["action"], key, value, text.count(value)))
        if not any(value in literal for literal in literals):
            raise LessonError("%s: the taught %s %r is not inside a string literal" % (lesson["action"], key, value))
        if any(value != other and value in other for other in request.values()):
            raise LessonError("%s: the taught %s %r is part of another taught value" % (lesson["action"], key, value))
    return text, request


def _world(directory: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    for name, content in files.items():
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8"))
    return directory


def _differences(directory: pathlib.Path, expected: dict[str, str]) -> list[str]:
    return [name for name, content in expected.items()
            if not (directory / name).is_file() or (directory / name).read_bytes() != content.encode("utf-8")]


def teach(bundle_path: pathlib.Path) -> dict:
    """Teach every lesson into a fresh database and export it.  Raises ``LessonError`` on any failure."""
    if compiler._sandbox_for_taught_programs() is None:
        raise LessonError("this machine cannot start the namespace sandbox, so nothing can be taught")
    taught: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="teach_actions_") as scratch_name:
        scratch = pathlib.Path(scratch_name)
        database = scratch / "skills.sqlite"
        for number, lesson in enumerate(LESSONS):
            program, request = program_and_request(lesson)
            trace = [{"layer": "confined_python_exec", "code": program}]
            postcondition = {"kind": "stdout_equals", "expected": lesson["answers"].format(**request)}

            first = _world(scratch / ("first_%d" % number), lesson["first_example"]["before"])
            ran = compiler.execute_compiled_steps(trace, cwd=first)
            done, why = compiler.verify_postcondition(postcondition, cwd=first, execution_result=ran) if ran.get("ok") else (False, ran.get("reason"))
            if not done or _differences(first, lesson["first_example"]["after"]):
                raise LessonError("%s: the first example did not come out as the lesson says (%s)" % (lesson["action"], why))

            second = lesson["second_example"]
            for variant, sentence in enumerate(lesson["said_as"]):
                world = _world(scratch / ("second_%d_%d" % (number, variant)), second["before"])
                verdict = compiler.compile_and_qualify_skill(
                    goal=sentence.format(**request), trace=trace, postcondition=postcondition,
                    heldout_goal=sentence.format(**second["request"]), heldout_cwd=world,
                    source_channel="taught_action_program", db_path=database)
                if verdict.get("pass") is not True:
                    raise LessonError("%s: %r did not qualify: %s" % (lesson["action"], sentence, verdict.get("status")))
                wrong = _differences(world, second["after"])
                if wrong:
                    raise LessonError("%s: the second example passed its postcondition but %s is not what the lesson expects"
                                      % (lesson["action"], ", ".join(wrong)))
                taught.append({"action": lesson["action"], "skill_id": verdict.get("skill_id"),
                               "sentence": verdict.get("goal_skeleton")})
        exported = compiler.export_workflow_bundle(bundle_path, db_path=database)
    return {"taught": taught, "skill_count": exported.get("skill_count"), "bundle_sha256": exported.get("bundle_sha256")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="teach again and compare with the tracked bundle")
    args = parser.parse_args(argv)
    try:
        if args.check:
            with tempfile.TemporaryDirectory(prefix="teach_check_") as scratch:
                fresh = pathlib.Path(scratch) / "bundle.json"
                report = teach(fresh)
                same = BUNDLE.is_file() and fresh.read_bytes() == BUNDLE.read_bytes()
            print(json.dumps({**report, "same_as_tracked_bundle": same}, indent=1))
            return 0 if same else 1
        print(json.dumps(teach(BUNDLE), indent=1))
        return 0
    except LessonError as problem:
        print("NOT TAUGHT: %s" % problem)
        return 2


if __name__ == "__main__":
    sys.exit(main())
