"""A question never writes over the file it asks about.

Measured 2026-10-29 on `1f5f86d`, fresh tree, the filesystem as the oracle::

    "Explain the bug in <T>/pkg/calc.py"
      composed [code.multilanguage.parse.tree_sitter.v1, python.patch.search...]
      bound  output_path = <T>/pkg/calc.py     (its only other slot was the DIRECTORY
                                               source_root, so an output-equals-input
                                               rule saw no collision)
      result calc.py = 32 bytes -> 545 bytes, a JSON report; the source was GONE
      verdict FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN

    "Count the functions in <T>/pkg/calc.py"  -> the same destruction, and no refusal.

The front compiler has always refused to let an action's output be one of its own inputs
(`repair_output_collisions`, F10) and has always had the remedy for a sentence that names
no output at all (F13: a deterministic spool artifact).  Neither rule reached a sentence
whose only other slot is a directory, and the composer bound its own arguments with no
equivalent rule at all.  So the fix is one rule in the one place that owns it, called from
both sites -- and a second one for the mirror case the destruction was hiding: a question
must be answered by something that explains.
"""
from __future__ import annotations

import hashlib
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_question_never_writes"
BROKEN = "def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n"
TEST_SOURCE = ("import calc, unittest\n\n\n"
               "class T(unittest.TestCase):\n"
               "    def test_add(self):\n"
               "        self.assertEqual(calc.add(2, 3), 5)\n")
SPOOL = front.SPOOL_DIR + "/"


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/calc.py").write_text(BROKEN, encoding="utf-8")
    (base / "pkg/test_calc.py").write_text(TEST_SOURCE, encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AQuestionNamesAnInputNotAnOutput(unittest.TestCase):
    def test_the_sentence_itself_decides(self):
        self.assertTrue(front._sentence_asks_for_a_change("Reformat x.py in place"))
        self.assertFalse(front._sentence_asks_for_a_change("Explain the bug in x.py"))

    def test_the_output_slot_is_spooled_instead_of_the_named_file(self):
        """The rule, on the shapes that produced the destruction."""
        base = _fresh("rule")
        src = _rel(base / "pkg/calc.py")
        inputs = {"output_path": src, "source_root": _rel(base / "pkg")}
        front.repair_output_collisions(
            "Count the functions in %s" % src, inputs, ROOT,
            cycle=0, spool={src})
        self.assertTrue(str(inputs["output_path"]).startswith(SPOOL),
                        "the result goes to a spool artifact, not over the source")
        self.assertNotEqual(inputs["output_path"], src)

    def test_a_stated_change_keeps_the_binding_it_had(self):
        """A capability that DECLARES it edits the file may still write that file.

        The judgement is the capability's own declaration, not the phrasing of the
        sentence: a report capability and a formatter are told apart by what they say
        they do, so `Reformat X in place` keeps its binding and `Explain X` does not.
        """
        base = _fresh("in_place")
        src = _rel(base / "pkg/calc.py")
        formatter = {"capability_id": "python.source.format.v1",
                     "provides": ["python.source.format.reformatted"],
                     "keywords": ["format", "reformat"]}
        inputs = {"output_path": src, "source_root": _rel(base / "pkg")}
        front.repair_output_collisions(
            "Reformat %s in place" % src, inputs, ROOT, entry=formatter,
            cycle=0, spool={src})
        self.assertEqual(inputs["output_path"], src)


class TheDoorKeepsTheFile(unittest.TestCase):
    def test_explaining_a_bug_leaves_the_source_byte_identical(self):
        base = _fresh("explain")
        before = _digest(base / "pkg/calc.py")
        door.solve({"task_id": "Q_EXPLAIN", "goal":
                    "Explain the bug in %s" % _rel(base / "pkg/calc.py")})
        self.assertEqual(_digest(base / "pkg/calc.py"), before,
                         "a question must never rewrite the file it asks about")

    def test_counting_the_functions_answers_without_touching_the_file(self):
        base = _fresh("count")
        before = _digest(base / "pkg/calc.py")
        result = door.solve({"task_id": "Q_COUNT", "goal":
                             "Count the functions in %s" % _rel(base / "pkg/calc.py")})
        self.assertEqual(_digest(base / "pkg/calc.py"), before)
        self.assertIs(result.get("pass"), True, result.get("status"))
        row = (result.get("execution") or [{}])[0].get("result") or {}
        self.assertEqual(row.get("function_count"), 2,
                         "the answer, not just a verdict")
        self.assertTrue(str(row.get("output_path", "")).startswith(SPOOL),
                        "and the report is a spool artifact")

    def test_a_question_the_capability_cannot_answer_is_refused(self):
        base = _fresh("unanswerable")
        before = _digest(base / "pkg/calc.py")
        result = door.solve({"task_id": "Q_WHY", "goal":
                             "Explain why the test in %s fails."
                             % _rel(base / "pkg/test_calc.py")})
        self.assertIs(result.get("pass"), False, result.get("status"))
        self.assertEqual(_digest(base / "pkg/calc.py"), before)

    def test_a_stated_write_still_writes(self):
        base = _fresh("write")
        out = base / "out.txt"
        result = door.solve({"task_id": "Q_WRITE", "goal":
                             "Write the text 'hello' to the file %s" % _rel(out)})
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertEqual(out.read_text(encoding="utf-8").strip(), "hello")


if __name__ == "__main__":
    unittest.main()
