#!/usr/bin/env python3
"""A question has a VALUE. An artifact has a FILE. They must not share a status.

discover() refuses question-shaped goals with
OPEN__A_QUESTION_IS_NOT_CLOSED_BY_A_FILE_APPEARING and that refusal is correct and
pinned elsewhere -- returning `closed=True` from a question would let a number travel
on the artifact path as DISCOVERED_BY_ACTING_AND_EFFECT_VERIFIED.

What was missing is the HANDOFF. Its refusal message says "this route cannot answer
questions -- answer_query does", and nothing called answer_query from any decision
path. These tests pin the handoff and, just as importantly, pin that the handoff
does NOT pretend to have closed an artifact.
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load(name: str, rel: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


qh = _load("canonical.runtime.question_handoff_v1",
           "canonical/runtime/question_handoff_v1.py")
cenv = _load("canonical.runtime.computer_env_v1",
             "canonical/runtime/computer_env_v1.py")


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self._tmp.name)
        self.src = self.d / "notes.txt"
        self.src.write_text("banana\napple\n\ncherry\napple\ndate\nelderberry\n")

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_countable_question_is_answered_with_a_value(self):
        r = qh.route("count the lines in notes.txt", self.src)
        self.assertTrue(r["answered"], r)
        self.assertEqual(r["status"], "ANSWERED__VALUE_MEASURED")

    def test_the_answer_agrees_with_the_program_that_owns_it(self):
        # Independent of this module: ask wc directly.
        r = qh.route("count the lines in notes.txt", self.src)
        real = subprocess.run(["wc", "-l", str(self.src)],
                              capture_output=True, text=True).stdout.split()[0]
        self.assertEqual(str(r["value"]), real)

    def test_an_answered_question_NEVER_REPORTS_CLOSED(self):
        # The whole point of a separate result shape: a value is not an artifact.
        for goal in ("count the lines in notes.txt",
                     "count the words in notes.txt",
                     "the different lines of notes.txt"):
            r = qh.route(goal, self.src)
            if r["answered"]:
                self.assertFalse(r["closed"], goal)
                self.assertNotIn("PASS__", str(r["status"]), goal)

    def test_a_missing_file_is_refused_not_guessed(self):
        r = qh.route("count the lines in notes.txt", self.d / "absent.txt")
        self.assertFalse(r["answered"])
        self.assertEqual(r["status"], "OPEN__NO_EXISTING_INPUT_FILE_IN_GOAL")

    def test_an_artifact_goal_is_not_a_question(self):
        for goal in ("compress notes.txt into out.gz",
                     "write a summary of notes.txt into s.md"):
            r = qh.route(goal, self.src)
            self.assertFalse(r["answered"], goal)
            self.assertEqual(r["status"], "NOT_A_QUESTION", goal)

    def test_discover_still_refuses_the_same_goal(self):
        # The handoff does NOT change discover(). The pinned refusal must stand.
        d = cenv.discover("the different lines of the file a.txt")
        self.assertFalse(d.get("closed"))
        self.assertEqual("OPEN__A_QUESTION_IS_NOT_CLOSED_BY_A_FILE_APPEARING",
                         d.get("status"))
        self.assertNotIn("VERIFIED", str(d.get("status")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
