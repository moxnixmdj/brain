# PROJECT_BRAIN
"""Three census rows that were answerable from the tree and answered nowhere.

Census revision 7 scored 5 of 28.  These three are one pass each over artifacts
the repository already builds -- `ast` for definitions, the same `ast` for taint,
and `sys.settrace` (stdlib) for line coverage -- so none of them is a new
primitive.  Measured on the census fixtures, first run:

    python.source.definition_count.v1   -> 5    0.9 ms  (oracle: 5)
    python.source.taint_flow.v1         -> yes  1.8 ms  (oracle: yes)
    python.source.test_adequacy.v1      -> no  44.0 ms  (oracle: no)

Three laws make them reachable by sentence, and every one is a narrowing:

1. ONE VERDICT.  A report is data.  The adequacy artifact used to explain itself
   ("yes means ... no means ..."), and a reader looking for the answer word in
   the file found BOTH; a correct `no` was unreadable.  Measured, the oracle
   wrapper returned ok=False on an artifact whose `answer` was `no`.

2. SIBLING, BOTH WAYS.  Naming the subject finds its sibling `tests`; a sentence
   that names only the tests ("the tests in <d>") must find the code they
   exercise.  Measured, binding the tests dir as the subject died with
   NO_TARGET_FUNCTIONS and no answer was written.

3. DELIVERY AT THE DAG SEAM.  "Write yes or no to <b>/answer.json" is the
   destination of the previous answer, not a second task.  The DAG planner gave
   it to `software.synthesis.grid_induction.v1`, so the run ended
   FAIL_CLOSED__PROMISED_ARTIFACT_MISSING while the capability that HAD the
   answer ran and wrote elsewhere.

Each row declares only `source_root`.  A capability that needs a second path key
before it can be reached by any sentence is unreachable by construction.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as fc  # noqa: E402
from canonical.runtime.bound_capabilities import python_source_definition_count as definitions  # noqa: E402
from canonical.runtime.bound_capabilities import python_source_taint_flow as taint  # noqa: E402
from canonical.runtime.bound_capabilities import python_source_test_adequacy as adequacy  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/pin_three_answers_v1"

COUNT_APP = '''"""Shapes."""


def one():
    return 1


def two():
    return 2


class Thing:
    def method(self):
        return 3


def three():
    def nested():
        return 4
    return nested
'''

HANDLER = '''import json


def parse_request(raw):
    return json.loads(raw)


def run(raw):
    payload = parse_request(raw)
    exec(payload["code"])
'''

HANDLER_SAFE = '''import json


def parse_request(raw):
    return json.loads(raw)


def describe(raw):
    payload = parse_request(raw)
    return payload.get("name", "")
'''

PRICING = '''def apply_discount(subtotal_cents, cut):
    if subtotal_cents < 0:
        return 0
    return subtotal_cents - cut
'''

PRICING_TESTS = '''import unittest
from app.pricing import apply_discount


class T(unittest.TestCase):
    def test_negative(self):
        self.assertEqual(apply_discount(-5, 1), 0)
'''


class Base(unittest.TestCase):
    files: dict[str, str] = {}

    def setUp(self):
        shutil.rmtree(WORK, ignore_errors=True)
        for rel, text in self.files.items():
            path = WORK / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    def run_adapter(self, module, source_root="app", **extra):
        return module.run(dict({"source_root": str(WORK / source_root),
                                "output_path": str(WORK / "answer.json")}, **extra),
                          str(ROOT))

    def artifact(self):
        return (WORK / "answer.json").read_text(encoding="utf-8")


class TestADefinitionCountIsOneNumber(Base):
    files = {"app/__init__.py": "", "app/shapes.py": COUNT_APP}

    def test_every_def_at_every_depth_counts_once(self):
        out = self.run_adapter(definitions)
        # one, two, Thing, Thing.method, three, three.nested
        self.assertEqual(out["answer"], 6)
        self.assertEqual(out["definition_count"], 6)

    def test_the_answer_is_the_single_number_not_two(self):
        # `python.source.audit.ast` reports function_count and class_count
        # separately -- two numbers for a question that asks for one.
        out = self.run_adapter(definitions)
        self.assertIsInstance(out["answer"], int)
        self.assertEqual(out["answer"], out["function_count"] + out["class_count"])
        self.assertEqual(out["class_count"], 1)
        self.assertEqual(out["function_count"], 5)

    def test_the_artifact_is_the_number(self):
        self.run_adapter(definitions)
        self.assertEqual(json.loads(self.artifact())["answer"], 6)


class TestTaintIsBoundAtTheInputBoundary(Base):
    files = {"app/__init__.py": "", "app/handler.py": HANDLER}

    def test_a_parsed_parameter_reaching_exec_is_yes(self):
        out = self.run_adapter(taint)
        self.assertEqual(out["answer"], "yes")
        self.assertEqual(out["source_function"], "parse_request")
        self.assertIn("exec", out["sink"])
        self.assertTrue(out["trace"], "a verdict without its edges is not a proof")

    def test_the_row_needs_no_second_key(self):
        # No source_function, no sink: the input boundary and the sink
        # vocabulary are derived, so a sentence can reach the row.
        out = taint.run({"source_root": str(WORK / "app"),
                         "output_path": str(WORK / "answer.json")}, str(ROOT))
        self.assertEqual(out["answer"], "yes")
        self.assertEqual(
            {k for k in out if k in ("source_function", "sink")}, {"source_function", "sink"})

    def test_a_parsed_parameter_that_reaches_no_sink_is_no(self):
        (WORK / "app/handler.py").write_text(HANDLER_SAFE, encoding="utf-8")
        (WORK / "app/__init__.py").write_text("", encoding="utf-8")
        out = self.run_adapter(taint)
        self.assertEqual(out["answer"], "no")
        self.assertEqual(out["finding_count"], 0)

    def test_the_artifact_carries_one_verdict(self):
        self.run_adapter(taint)
        self.assertEqual(json.loads(self.artifact())["answer"], "yes")


class TestACoverageAnswerIsReadableAndSound(Base):
    files = {"app/__init__.py": "", "app/pricing.py": PRICING,
             "tests/__init__.py": "", "tests/test_pricing.py": PRICING_TESTS}

    def test_the_suite_cannot_catch_a_bug_on_an_unexecuted_line(self):
        out = self.run_adapter(adequacy)
        self.assertEqual(out["answer"], "no")
        self.assertGreater(out["unexecuted_count"], 0)

    def test_the_artifact_holds_exactly_one_verdict(self):
        # Regression: the report used to explain "yes means ... no means ...",
        # so a reader looking for the answer word in the file found both and a
        # correct `no` was unreadable.
        self.run_adapter(adequacy)
        blob = self.artifact().lower()
        self.assertEqual(blob.count('"answer": "no"'), 1, blob)
        self.assertNotIn('"answer": "yes"', blob)
        self.assertIn("NEGATIVE_IS_PROOF", self.artifact())

    def test_naming_only_the_tests_still_finds_the_subject(self):
        # The sibling relation runs both ways.  Measured, binding the tests dir
        # as the subject raised NO_TARGET_FUNCTIONS and wrote nothing.
        out = self.run_adapter(adequacy, source_root="tests")
        self.assertEqual(out["answer"], "no")
        self.assertTrue(out["source_root"].endswith("/pin_three_answers_v1"), out["source_root"])
        self.assertTrue(out["bound_root"].endswith("/tests"), out["bound_root"])

    def test_an_exercised_branch_is_not_a_proof_of_strength(self):
        (WORK / "tests/test_pricing.py").write_text(
            "import unittest\nfrom app.pricing import apply_discount\n\n\n"
            "class T(unittest.TestCase):\n"
            "    def test_odd(self):\n"
            "        self.assertEqual(apply_discount(-5, 1), 0)\n"
            "        self.assertEqual(apply_discount(100, 10), 90)\n",
            encoding="utf-8")
        out = self.run_adapter(adequacy)
        self.assertEqual(out["answer"], "yes")
        self.assertEqual(out["answer_scope"],
                         "NEGATIVE_IS_PROOF__POSITIVE_IS_NECESSARY_NOT_SUFFICIENT")


class TestTheDeliveryClauseNamesOnePlace(unittest.TestCase):
    def _actions(self):
        return [{"type": "invoke_capability",
                 "args": {"capability_id": "python.source.test_adequacy.v1",
                          "output_path": "canonical/astra_runtime/tmp/placeholder.json",
                          "source_root": "canonical/runtime"}}], [
            {"inputs": {"output_path": "canonical/astra_runtime/tmp/placeholder.json"}}]

    def test_yes_or_no_is_delivered(self):
        actions, parts = self._actions()
        self.assertTrue(gc._compile_answer_delivery(
            "Write yes or no to canonical/astra_runtime/tmp/x/answer.json",
            actions, parts, ROOT))
        self.assertEqual(actions[0]["args"]["output_path"],
                         "canonical/astra_runtime/tmp/x/answer.json")

    def test_an_answer_word_without_a_place_is_not_delivered(self):
        actions, parts = self._actions()
        self.assertFalse(gc._compile_answer_delivery(
            "Would the tests catch it? Write yes or no", actions, parts, ROOT))

    def test_the_report_clause_is_still_not_consumed(self):
        actions, parts = self._actions()
        self.assertFalse(gc._compile_answer_delivery(
            "and write the repair report to canonical/astra_runtime/tmp/x/report.json",
            actions, parts, ROOT))


class TestTheDagPlannerDeliversToThePreviousStep(unittest.TestCase):
    def _steps(self):
        entry = {"inputs": {"output_path": {"role": "output"}}}
        return [{"capability_id": "python.source.test_adequacy.v1",
                 "inputs": {"source_root": "canonical/runtime",
                            "output_path": "canonical/astra_runtime/tmp/spool_0.json"},
                 "entry": entry,
                 "outputs": [("output_path", "canonical/astra_runtime/tmp/spool_0.json")]}]

    def test_the_second_clause_is_the_destination_not_a_new_step(self):
        steps = self._steps()
        self.assertTrue(fc._deliver_to_previous(
            "Write yes or no to canonical/astra_runtime/tmp/x/answer.json", steps, ROOT))
        self.assertEqual(steps[0]["inputs"]["output_path"],
                         "canonical/astra_runtime/tmp/x/answer.json")
        self.assertEqual(steps[0]["outputs"],
                         [("output_path", "canonical/astra_runtime/tmp/x/answer.json")])

    def test_nothing_to_deliver_is_refused(self):
        self.assertFalse(fc._deliver_to_previous(
            "Write yes or no to canonical/astra_runtime/tmp/x/answer.json", [], ROOT))


if __name__ == "__main__":
    unittest.main()
