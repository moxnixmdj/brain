#!/usr/bin/env python3
"""Teach the front door the actions in ``canonical/swe_kernel/taught_actions``.

    PYTHONPATH=. python3 canonical/tools/teach_actions_v1.py           # teach, write the bundle
    PYTHONPATH=. python3 canonical/tools/teach_actions_v1.py --check   # teach again, compare with the bundle

A lesson is: a program that does the action once (its ``REQUEST`` line holds the values of the first
example), the sentences the action may be asked with, the line the program prints when it is done,
and a second example with different values.

One program may serve several actions.  Such a lesson names the program, says which of its actions it
is (``does``) and gives the values of its first example itself; the program's ``REQUEST`` line is then
written from the lesson before anything is run or taught.

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
        "does": "edit",
        "first_request": {"target": "lessons_q7/suite_q7.py", "before": "lessons_q7/shown_q7/earlier.py",
                          "after": "lessons_q7/shown_q7/later.py"},
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
                    "        self.assertEquals(names(), ['a', 'b'], msg='names differ')\n"),
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
                    "        self.assertEqual(names(), ['a', 'b'], msg='names differ')\n"),
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


# ----------------------------------------------------------------------------- a change kept in a lesson file

LESSON_NOTE = ("A change worked out from examples, kept to be repeated on other files. "
               "'teaches' is checked against 'examples' every time the lesson is used.")


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def _kept(teaches: list[dict], *examples: tuple) -> dict:
    """A lesson file as the action writes it: what it teaches, and the examples (shown by, before, after,
    and -- for an example a try made -- the places of its first file a check left unsettled)."""
    return {"format": "CHANGE_LEARNED_FROM_EXAMPLES_V1", "what this is": LESSON_NOTE, "teaches": teaches,
            "examples": [dict([("shown by", example[0]), ("before", _lines(example[1])), ("after", _lines(example[2]))]
                              + ([("not settled", example[3])] if example[3:] else []))
                         for example in examples]}


def _as_file(lesson: dict) -> str:
    return json.dumps(lesson, indent=1, ensure_ascii=False) + "\n"


SUITE_WAS = ("import unittest\n"
             "\n"
             "\n"
             "class LedgerTest(unittest.TestCase):\n"
             "    def test_total(self):\n"
             "        self.assertEquals(total([1, 2]), 3)\n"
             "        self.assertTrue(total([]) == 0)\n")
SUITE_IS = SUITE_WAS.replace("assertEquals", "assertEqual")
NAMED_WAS = ("import unittest\n"
             "\n"
             "\n"
             "class NamesTest(unittest.TestCase):\n"
             "    def test_names(self):\n"
             "        self.assertEquals(names(), ['a', 'b'], msg='names differ')\n")
NAMED_IS = NAMED_WAS.replace("assertEquals", "assertEqual")
EQUALS_ONE = {"change": "self.assertEquals -> self.assertEqual", "shown": ["called with 2 arguments"]}
EQUALS_TWO = {"change": "self.assertEquals -> self.assertEqual",
              "shown": ["called with 2 arguments", "called with 2 arguments and the keyword msg"]}

UNSET_WAS = ("def settle(total, rate):\n"
             "    if total == None:\n"
             "        return 0\n"
             "    missing = rate.value == None\n"
             "    return total == 0 or missing\n")
UNSET_IS = UNSET_WAS.replace("== None", "is None")
GIVEN_WAS = ("def pick(first, second):\n"
             "    if first != None:\n"
             "        return first\n"
             "    return second if second.value != None else 0\n")
GIVEN_IS = GIVEN_WAS.replace("!= None", "is not None")
UNSET = {"change": "?1 == None -> ?1 is None"}
GIVEN = {"change": "?1 != None -> ?1 is not None"}

LESSONS += [
    {
        "action": "remember_a_change_v1",
        "program": "edit_by_example_v1",
        "does": "remember",
        "parameters": ("lesson", "before", "after"),
        "first_request": {"lesson": "lessons_q7/kept_q7/equal_q7.lesson", "before": "lessons_q7/shown_q7/was_q7.py",
                          "after": "lessons_q7/shown_q7/became_q7.py"},
        "said_as": [
            "remember in {lesson} the way {before} was changed into {after}",
            "remember in {lesson} also the way {before} was changed into {after}",
        ],
        "answers": "remembered in {lesson} the way {before} was changed into {after}",
        "first_example": {                      # the lesson file is not there yet: it is made
            "before": {"lessons_q7/shown_q7/was_q7.py": SUITE_WAS, "lessons_q7/shown_q7/became_q7.py": SUITE_IS},
            "after_json": {"lessons_q7/kept_q7/equal_q7.lesson": _kept(
                [EQUALS_ONE], ("lessons_q7/shown_q7/was_q7.py -> lessons_q7/shown_q7/became_q7.py", SUITE_WAS, SUITE_IS))},
        },
        "second_example": {                     # the lesson file holds one example: a second is added to it
            "request": {"lesson": "notes/unset.lesson", "before": "checks/given/as_it_was.py",
                        "after": "checks/given/as_it_is.py"},
            "before": {
                "notes/unset.lesson": _as_file(_kept([UNSET], ("earlier/was.py -> earlier/is.py", UNSET_WAS, UNSET_IS))),
                "checks/given/as_it_was.py": GIVEN_WAS,
                "checks/given/as_it_is.py": GIVEN_IS,
            },
            "after_json": {"notes/unset.lesson": _kept(
                [UNSET, GIVEN], ("earlier/was.py -> earlier/is.py", UNSET_WAS, UNSET_IS),
                ("checks/given/as_it_was.py -> checks/given/as_it_is.py", GIVEN_WAS, GIVEN_IS))},
        },
    },
    {
        "action": "repeat_a_remembered_change_v1",
        "program": "edit_by_example_v1",
        "does": "repeat",
        "parameters": ("target", "lesson"),
        "first_request": {"target": "lessons_q7/rates_q7.py", "lesson": "lessons_q7/kept_q7/equal_q7.lesson"},
        "said_as": ["edit {target} the way {lesson} remembers"],
        "answers": "edited {target} the way {lesson} remembers",
        "first_example": {                      # a lesson of two examples; the second showed the keyword
            "before": {
                "lessons_q7/kept_q7/equal_q7.lesson": _as_file(_kept(
                    [EQUALS_TWO], ("one/was.py -> one/is.py", SUITE_WAS, SUITE_IS),
                    ("two/was.py -> two/is.py", NAMED_WAS, NAMED_IS))),
                "lessons_q7/rates_q7.py": (
                    "import unittest\n"
                    "\n"
                    "\n"
                    "class RatesTest(unittest.TestCase):\n"
                    "    def test_rate(self):\n"
                    "        self.assertEquals(rate(2), 0.5)  # half\n"
                    "        outcome = self.assertEquals(rate(4), 0.25, msg='quarter')\n"
                    "        other.assertEquals(outcome, None)\n"),
            },
            "after": {"lessons_q7/rates_q7.py": (
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
            "request": {"target": "checks/orders.py", "lesson": "notes/unset.lesson"},
            "before": {
                "notes/unset.lesson": _as_file(_kept(
                    [UNSET, GIVEN], ("earlier/was.py -> earlier/is.py", UNSET_WAS, UNSET_IS),
                    ("later/was.py -> later/is.py", GIVEN_WAS, GIVEN_IS))),
                "checks/orders.py": (
                    "def last(order, fallback):\n"
                    "    while order.parent == None:  # top of the chain\n"
                    "        order = order.following\n"
                    "    unset = (order.note or fallback) != None\n"
                    "    return unset == False\n"),
            },
            "after": {"checks/orders.py": (
                "def last(order, fallback):\n"
                "    while order.parent is None:  # top of the chain\n"
                "        order = order.following\n"
                "    unset = (order.note or fallback) is not None\n"
                "    return unset == False\n")},
        },
    },
    {
        "action": "repeat_what_a_lesson_showed_v1",
        "program": "edit_by_example_v1",
        "does": "repeat_shown",
        "parameters": ("target", "lesson"),
        "first_request": {"target": "lessons_q7/sizes_q7.py", "lesson": "lessons_q7/kept_q7/plain_q7.lesson"},
        "said_as": ["edit {target} the way {lesson} remembers and leave the rest alone"],
        "answers": "edited {target} the way {lesson} remembers and left the rest alone",
        "first_example": {                      # the lesson showed two arguments; the call with a keyword is left
            "before": {
                "lessons_q7/kept_q7/plain_q7.lesson": _as_file(_kept(
                    [EQUALS_ONE], ("one/was.py -> one/is.py", SUITE_WAS, SUITE_IS))),
                "lessons_q7/sizes_q7.py": (
                    "import unittest\n"
                    "\n"
                    "\n"
                    "class SizesTest(unittest.TestCase):\n"
                    "    def test_size(self):\n"
                    "        self.assertEquals(size(2), 4)\n"
                    "        self.assertEquals(size(3), 9, msg='nine')  # a use the lesson never showed\n"),
            },
            "after": {"lessons_q7/sizes_q7.py": (
                "import unittest\n"
                "\n"
                "\n"
                "class SizesTest(unittest.TestCase):\n"
                "    def test_size(self):\n"
                "        self.assertEqual(size(2), 4)\n"
                "        self.assertEquals(size(3), 9, msg='nine')  # a use the lesson never showed\n")},
        },
        "second_example": {
            "request": {"target": "tools/load.py", "lesson": "notes/safe.lesson"},
            "before": {
                "notes/safe.lesson": _as_file(_kept(
                    [{"change": "yaml.load -> yaml.safe_load", "shown": ["called with 1 argument"],
                      "imports": {"yaml": ["import yaml"]}}],
                    ("earlier/was.py -> earlier/is.py",
                     "import yaml\n\n\ndef read(stream):\n    return yaml.load(stream)\n",
                     "import yaml\n\n\ndef read(stream):\n    return yaml.safe_load(stream)\n"))),
                "tools/load.py": (
                    "import yaml\n"
                    "\n"
                    "\n"
                    "def settings(handle, trusted):\n"
                    "    if trusted:\n"
                    "        return yaml.load(handle, Loader=yaml.FullLoader)\n"
                    "    return yaml.load(handle)\n"),
            },
            "after": {"tools/load.py": (
                "import yaml\n"
                "\n"
                "\n"
                "def settings(handle, trusted):\n"
                "    if trusted:\n"
                "        return yaml.load(handle, Loader=yaml.FullLoader)\n"
                "    return yaml.safe_load(handle)\n")},
        },
    },
]

WATCH_WAS = ("import threading\n"
             "\n"
             "\n"
             "class Watch_q7:\n"
             "    def __init__(self):\n"
             "        self.thread_q7 = threading.Thread(target=print)\n"
             "\n"
             "    def busy_q7(self):\n"
             "        return self.thread_q7.isAlive()\n")
WATCH_IS = WATCH_WAS.replace("isAlive", "is_alive")
POOL_WAS = "def running_q7(threads):\n    return [t for t in threads if t.isAlive()]\n"
POOL_CHECK = ("import threading\n"
              "import unittest\n"
              "\n"
              "import pool_q7\n"
              "\n"
              "\n"
              "class PoolTest_q7(unittest.TestCase):\n"
              "    def test_running_q7(self):\n"
              "        finished = threading.Thread(target=print)\n"
              "        finished.start()\n"
              "        finished.join()\n"
              "        self.assertEqual(pool_q7.running_q7([finished]), [])\n")
AGENT_WAS = ("import threading\n"
             "\n"
             "\n"
             "class Agent:\n"
             "    def __init__(self):\n"
             "        self.worker = threading.Thread(target=print)\n"
             "\n"
             "    def busy(self):\n"
             "        return self.worker.isAlive()\n")
AGENT_IS = AGENT_WAS.replace("isAlive", "is_alive")
LEVEL_WAS = ("def active(jobs):\n"
             "    return [job for job in jobs if job.isAlive()]\n"
             "\n"
             "\n"
             "def forgotten(job):\n"
             "    return job.isAlive()\n")
LEVEL_CHECK = ("import threading\n"
               "import unittest\n"
               "\n"
               "import level\n"
               "\n"
               "\n"
               "class LevelTest(unittest.TestCase):\n"
               "    def test_active(self):\n"
               "        ended = threading.Thread(target=print)\n"
               "        ended.start()\n"
               "        ended.join()\n"
               "        self.assertEqual(level.active([ended]), [])\n")
WATCHED = {"change": "self.thread_q7.isAlive -> self.thread_q7.is_alive", "shown": ["called with 0 arguments"]}
AGENTS = {"change": "self.worker.isAlive -> self.worker.is_alive", "shown": ["called with 0 arguments"]}
ANY_ALIVE = {"change": "?1.isAlive -> ?1.is_alive", "shown": ["called with 0 arguments"]}

LESSONS += [
    {
        "action": "try_what_a_lesson_did_not_show_v1",
        "program": "edit_by_example_v1",
        "does": "repeat_tried",
        "parameters": ("target", "lesson", "check"),
        "first_request": {"target": "lessons_q7/pool_q7.py", "lesson": "lessons_q7/kept_q7/alive_q7.lesson",
                          "check": "lessons_q7/check_q7.py"},
        "said_as": ["edit {target} the way {lesson} remembers and try the rest with {check}"],
        "answers": "edited {target} the way {lesson} remembers and tried the rest with {check}",
        "first_example": {                      # `t.isAlive()` fits only the wider reading; the check settles it
            "before": {
                "lessons_q7/kept_q7/alive_q7.lesson": _as_file(_kept(
                    [WATCHED], ("shown_q7/watch_was.py -> shown_q7/watch_is.py", WATCH_WAS, WATCH_IS))),
                "lessons_q7/pool_q7.py": POOL_WAS,
                "lessons_q7/check_q7.py": POOL_CHECK,
            },
            "after": {"lessons_q7/pool_q7.py": POOL_WAS.replace("isAlive", "is_alive")},
            "after_json": {"lessons_q7/kept_q7/alive_q7.lesson": _kept(
                [ANY_ALIVE], ("shown_q7/watch_was.py -> shown_q7/watch_is.py", WATCH_WAS, WATCH_IS),
                ("a try on lessons_q7/pool_q7.py that lessons_q7/check_q7.py settled; kept line 2: a test "
                 "that passes with it fails when that code fails",
                 POOL_WAS, POOL_WAS.replace("isAlive", "is_alive")))},
        },
        "second_example": {                     # a use the check never runs stays as it was, named "not settled"
            "request": {"target": "floor/level.py", "lesson": "notes/alive.lesson", "check": "floor/check_level.py"},
            "before": {
                "notes/alive.lesson": _as_file(_kept(
                    [AGENTS], ("earlier/was.py -> earlier/is.py", AGENT_WAS, AGENT_IS))),
                "floor/level.py": LEVEL_WAS,
                "floor/check_level.py": LEVEL_CHECK,
            },
            "after": {"floor/level.py": LEVEL_WAS.replace("if job.isAlive()", "if job.is_alive()")},
            "after_json": {"notes/alive.lesson": _kept(
                [ANY_ALIVE], ("earlier/was.py -> earlier/is.py", AGENT_WAS, AGENT_IS),
                ("a try on floor/level.py that floor/check_level.py settled; kept line 2: a test that passes "
                 "with it fails when that code fails; not settled, line 6",
                 LEVEL_WAS, LEVEL_WAS.replace("if job.isAlive()", "if job.is_alive()"), [[6, 11, 6, 22]]))},
        },
    },
]


class LessonError(Exception):
    """A lesson that must not be taught as written."""


def program_and_request(lesson: dict) -> tuple[str, dict[str, str]]:
    """The program text and the values of its first example, read from its ``REQUEST`` line."""
    text = (PROGRAMS / (lesson.get("program", lesson["action"]) + ".py")).read_text(encoding="utf-8")
    if "does" in lesson:
        lines = text.splitlines(keepends=True)
        at = [number for number, line in enumerate(lines) if line.startswith("REQUEST = ")]
        if len(at) != 1 or tuple(lesson["first_request"]) != tuple(lesson["parameters"]):
            raise LessonError("%s: the program needs one REQUEST line, and the lesson one first value for each "
                              "parameter, in order" % lesson["action"])
        lines[at[0]] = "REQUEST = (%s, (%s,))\n" % (json.dumps(lesson["does"]), ", ".join(
            json.dumps(lesson["first_request"][name]) for name in lesson["parameters"]))
        text = "".join(lines)
    values = None
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and [getattr(t, "id", None) for t in node.targets] == ["REQUEST"]:
            try:
                values = ast.literal_eval(node.value)
            except ValueError:
                values = None
            if "does" in lesson:        # the line written above: (action, values)
                values = values[1] if isinstance(values, tuple) and len(values) == 2 else None
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


def _differences(directory: pathlib.Path, example: dict) -> list[str]:
    """Files of an example that are not what the lesson expects: by bytes (``after``) or as JSON (``after_json``)."""
    wrong = [name for name, content in example.get("after", {}).items()
             if not (directory / name).is_file() or (directory / name).read_bytes() != content.encode("utf-8")]
    for name, content in example.get("after_json", {}).items():
        try:
            same = json.loads((directory / name).read_bytes().decode("utf-8")) == content
        except (OSError, ValueError):
            same = False
        if not same:
            wrong.append(name)
    return wrong


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
            if not done or _differences(first, lesson["first_example"]):
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
                wrong = _differences(world, second)
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
