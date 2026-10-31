"""A count is not a collection, and a PASS over a count is a wrong answer with a certificate.

Measured 2026-10-31 on `main` f3d2e21, 62 human software-engineering sentences through
``live_brain_route_admission_v1.solve``: 12 PASSes, 7 of them wrong, and five of those seven
one skeleton -- an inspector that COUNTS was chosen for a request that asked to EXTRACT.

    "Find every caller of build_plan in .../swe_typed_plan_v1.py"
      result   {"caller_index_size": 8, "call_edge_count": 236739, "symbol_count": 92726}
      artifact {"callers_of": {"build_plan": ["plan_report"], ...}}   (42 keys)
    "List the functions in .../swe_typed_plan_v1.py"
      result   {"function_count": 10}
      artifact {"files": [{"functions": ["_effect_consistent", ..., "stated_family_token"]}]}
    "Show the imports of .../swe_typed_plan_v1.py"
      result   {"distinct_imported_module_count": 5}
      artifact {"distinct_imported_modules": ["__future__", "canonical", "pathlib", "re", "typing"]}

The bytes were written, hashed and verified, then discarded in favour of a number that happens
to be true.  ``answer_shape_v1`` copies the matching field verbatim onto ``answer`` and refuses
when no field can answer the sentence; the door applies it at ``_close_observations``, the one
exit every route passes through.

Four assertions, each an independent oracle:

  * projection delivers the measured artifact bytes, narrowed to the key the sentence names;
  * a row that only has a count refuses with a reason that NAMES the capability and the noun;
  * an artifact over the cap is refused without being parsed (the 108 MB ``code.index`` shape);
  * the door turns such a PASS into ``FAIL_CLOSED__ANSWER_SHAPE_UNSERVED`` -- and leaves a
    sentence that states no collection shape completely alone, including the correct answers
    "Which commit broke the tests" and "How many functions ...".
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import answer_shape_v1 as shape  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402


class AskedShape(unittest.TestCase):
    """The sentence decides; a sentence that states no collection shape is untouched."""

    ASKS = {
        "Find every caller of build_plan in pkg/x.py": "caller",
        "List the functions in pkg/x.py": "function",
        "Show the imports of pkg/x.py": "import",
        "Show the definition of _family_terms in pkg/x.py": "definition",
        "Which commits touched pkg/x.py": "commit",
        "List the branches": "branch",
        "Find duplicated code in canonical/runtime": "duplicate",
        "Find the dead code in pkg/x.py": "dead",
        "List every reference to build_plan in pkg/x.py": "reference",
    }
    SILENT = (
        "Show the status of the working tree",
        "What changed in the last 5 commits",
        "How many functions are in pkg/x.py",      # the count IS the answer
        "Who wrote line 3 of pkg/x.py",
        "Type-check pkg/x.py",
        "Show me the diff",
        "Which commit broke the tests",            # a lookup, already answered correctly
        "Find the fault in pkg/x.py",
        "Find the slow function in pkg/x.py",
    )

    def test_the_noun_the_sentence_names_is_the_noun_that_is_asked(self) -> None:
        for goal, noun in self.ASKS.items():
            got = shape.asked(goal)
            self.assertIsNotNone(got, goal)
            self.assertEqual(got["noun"], noun, goal)

    def test_a_lookup_and_a_count_are_not_enumerations(self) -> None:
        for goal in self.SILENT:
            self.assertIsNone(shape.asked(goal), goal)


class DeliveredAnswer(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _artifact(self, name: str, payload: dict) -> str:
        path = self.root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    def _result(self, inner: dict, cid: str = "python.source.symbols.index.ast") -> dict:
        return {"pass": True, "status": "PASS__MEASURED", "execution": [
            {"capability_id": cid, "pass": True, "result": inner}]}

    def test_the_callers_the_sentence_asked_for_are_delivered_not_their_count(self) -> None:
        callers = {name: ["plan_report"] for name in
                   ("_family_terms", "build_plan", "_effect_consistent", "is_swe_request")}
        artifact = self._artifact("callers.json", {"callers_of": callers})
        result = self._result({"caller_index_size": 8, "call_edge_count": 236739,
                               "symbol_count": 92726, "output_path": artifact,
                               "output_verified": True})
        self.assertEqual(shape.deliver("Find every caller of build_plan in pkg/x.py",
                                       result, self.root), [])
        answer = result["answer"]
        self.assertEqual(answer["field"], "callers_of")
        self.assertEqual(answer["noun"], "caller")
        # The sentence names ONE key of the map; the other three are not its answer.
        self.assertEqual(answer["value"], {"build_plan": ["plan_report"]})

    def test_a_count_of_definitions_cannot_answer_a_request_for_a_definition(self) -> None:
        result = self._result({"schema": "PROJECT_BRAIN_PYTHON_SOURCE_DEFINITION_COUNT_V1",
                               "answer": 10, "definition_count": 10},
                              cid="python.source.definition_count.v1")
        reasons = shape.deliver("Show the definition of _family_terms in pkg/x.py",
                                result, self.root)
        self.assertEqual(len(reasons), 1)
        self.assertTrue(reasons[0].startswith(
            "ANSWER_SHAPE_UNSERVED:python.source.definition_count.v1:definition:"), reasons[0])
        self.assertNotIn("answer", result)

    def test_an_artifact_past_the_cap_is_refused_without_being_read(self) -> None:
        path = self.root / "huge.json"
        with open(path, "wb") as handle:
            handle.write(b"{" + b" " * (shape.MAX_ARTIFACT_BYTES + 1) + b"}")
        result = self._result({"output_path": str(path), "duplicate_group_count": 3},
                              cid="code.index.tree_sitter.incremental.v1")
        reasons = shape.deliver("Find duplicated code in canonical/runtime", result, self.root)
        self.assertTrue(any("ARTIFACT_TOO_LARGE" in reason for reason in reasons), reasons)

    def test_an_artifact_outside_the_repository_is_not_read(self) -> None:
        artifact = self._artifact("outside.json", {"functions": ["real"]})
        result = self._result({"output_path": artifact, "function_count": 1},
                              cid="python.source.audit.ast")
        reasons = shape.deliver("List the functions in pkg/x.py", result,
                                self.root / "somewhere-else")
        self.assertTrue(any("ARTIFACT_OUTSIDE_REPOSITORY" in reason for reason in reasons),
                        reasons)


class TheDoorRefusesToCertifyIt(unittest.TestCase):
    """``_close_observations`` is the one exit every route passes through."""

    def test_a_pass_over_a_count_becomes_a_named_refusal(self) -> None:
        result = {"pass": True,
                  "status": "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED",
                  "execution": [{"capability_id": "python.source.audit.ast",
                                 "pass": True, "result": {"function_count": 10}}]}
        closed = door._close_observations(result, "List the functions in pkg/x.py", None)
        self.assertFalse(closed["pass"])
        self.assertEqual(closed["status"], "FAIL_CLOSED__ANSWER_SHAPE_UNSERVED")
        self.assertEqual(closed["failure_class"], "ANSWER_SHAPE_UNSERVED")
        self.assertTrue(str(closed["answer_shape_errors"][0]).startswith(
            "ANSWER_SHAPE_UNSERVED:python.source.audit.ast:function:"))

    def test_a_pass_with_no_collection_asked_is_left_exactly_as_it_was(self) -> None:
        for goal in ("Which commit broke the tests", "How many functions are in pkg/x.py",
                     "Show the status of the working tree"):
            result = {"pass": True, "status": "PASS__MEASURED",
                      "answer": {"culprit_commit": "abc"}, "execution": [
                          {"capability_id": "c", "pass": True, "result": {"rows": []}}]}
            closed = door._close_observations(result, goal, None)
            self.assertTrue(closed["pass"], goal)
            self.assertEqual(closed["status"], "PASS__MEASURED", goal)
            self.assertEqual(closed["answer"], {"culprit_commit": "abc"}, goal)


if __name__ == "__main__":
    unittest.main()
