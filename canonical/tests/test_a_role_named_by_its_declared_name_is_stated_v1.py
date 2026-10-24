"""A role named by its own declared name is a role the sentence states.

`_role_phrases` answers "what words may introduce this role immediately before a
path".  For `output_path` it returned only natural-language aliases from
_KEY_ALIASES -- "save to", "write to", "store to", "report to" -- so the literal
token `output_path` matched nothing.

That is not a cosmetic gap.  `_named_output_destinations` uses those phrases to
work out which named path the sentence offers as a DESTINATION, so it can be
kept out of input binding.  When the destination cannot be recognised, and it
already exists on disk (a re-run of the same request, or an artifact an earlier
step left behind), the input binder counts it as a second type-compatible
existing file and fails closed on ambiguity:

    input_path:2_type_compatible_existing_files_named

That is exactly the phantom-second-candidate case `_named_output_destinations`
was written to remove -- unreachable only because the sentence used the machine
name instead of prose.

Measured on 5402138, over the eleven capabilities that carry a real
re-inspector in raw_goal_trace_acceptance_v1.INSPECTORS, driven with their exact
declared roles and real fixtures on disk: 6 of 11 passed and 5 reached exact
semantic acceptance.  Two of the five failures were this defect --
decision.synthesis.typed.stdlib and source.objective_relevance.rank.bm25, both
of which take an `input_path`.  After the change 9 of 11 pass and 8 reach exact
acceptance.

Over the 51 capabilities that declare an output artifact, with every role
stated: exact acceptance 3 -> 5, pass 9 -> 9.
Over all 367 admissible capabilities driven from prose: pass 223 / fail 144 and
failure kinds CONTRACT_REFUSAL 138 / ENVIRONMENT_BLOCKER 3 / UNKNOWN 3, all
unchanged, so nothing that bound before binds differently now.

A second, smaller defect is fixed in the same function: the generic-word filter
emptied the stem of `input_path` ("input" is in _GENERIC_ROLE_WORDS) and of
`path`, leaving those two roles with no phrase at all.  Measured over all 367
capabilities and their 57 distinct declared roles, exactly those two were in
that state, covering 15 capabilities between them.

Tests 1-2 are deterministic unit pins.  Tests 3-4 drive the real binder.  Test 5
drives both capabilities end to end through solve() and requires exact semantic
acceptance; it fails on 5402138, where both are refused before any binder runs.
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest
from time import perf_counter_ns

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "canonical" / "runtime") not in sys.path:
    sys.path.insert(0, str(ROOT / "canonical" / "runtime"))

from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime.live_brain_route_admission_v1 import solve  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import (  # noqa: E402
    load_verified_registry,
)

# Two capabilities that carry a real re-inspector and take an `input_path`.
# Chosen by measurement, not by guess: these are the two whose refusal
# disappeared when the role's declared name became a phrase.
_TARGETS = (
    "decision.synthesis.typed.stdlib",
    "source.objective_relevance.rank.bm25",
)


class TestARoleNamedByItsDeclaredNameIsStatedV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = dict(load_verified_registry())
        cls.dir = ROOT / "canonical" / "astra_runtime" / "tmp" / "role_named_v1"
        cls.dir.mkdir(parents=True, exist_ok=True)
        (cls.dir / "decision.json").write_text(json.dumps(
            {"question": "pick",
             "options": [{"id": "a", "score": 1}, {"id": "b", "score": 9}],
             "decision": "b"}), encoding="utf-8")
        (cls.dir / "docs").mkdir(exist_ok=True)
        (cls.dir / "docs" / "note.md").write_text(
            "# Note\nobjective relevance ranking sample text about capability\n",
            encoding="utf-8")

    def _goal(self, cid: str, tag: str) -> str:
        rel = "canonical/astra_runtime/tmp/role_named_v1"
        source = ("decision.json" if cid.endswith("typed.stdlib")
                  else "docs/note.md")
        prose = cid.replace(".", " ").replace("_", " ")
        return ("Run the %s with input_path %s/%s and output_path %s/out_%s.json."
                % (prose, rel, source, rel, tag))

    def test_the_declared_name_is_a_role_phrase(self) -> None:
        for key in ("output_path", "input_path", "json_path", "manifest_path"):
            self.assertIn(key, front._role_phrases(key),
                          "%s cannot be stated by its own name" % key)

    def test_a_stem_made_only_of_generic_words_keeps_its_name(self) -> None:
        # `input_path` -> stem "input", which is in _GENERIC_ROLE_WORDS; `path`
        # -> stem "path", likewise.  Both used to end up with no phrase at all.
        self.assertIn("input", front._role_phrases("input_path"))
        self.assertIn("path", front._role_phrases("path"))

    def test_the_binder_takes_the_stated_file_not_the_destination(self) -> None:
        for cid in _TARGETS:
            goal = self._goal(cid, "bind")
            # The destination already exists, which is what made it a phantom
            # second candidate for the input binder.
            (self.dir / "out_bind.json").write_text("{}", encoding="utf-8")
            bound = front.bind_all_inputs(goal, self.registry[cid], ROOT,
                                          cycle=0, spool=set())
            self.assertEqual(
                bound.get("input_path"),
                "canonical/astra_runtime/tmp/role_named_v1/"
                + ("decision.json" if cid.endswith("typed.stdlib")
                   else "docs/note.md"),
                "%s bound the destination as its input" % cid)
            self.assertEqual(front._inputs_not_stated_by(goal, bound), [],
                             "%s still reports an unstated input" % cid)

    def test_the_named_destination_is_recognised_as_a_destination(self) -> None:
        goal = self._goal("decision.synthesis.typed.stdlib", "dest")
        (self.dir / "out_dest.json").write_text("{}", encoding="utf-8")
        named = front._named_output_destinations(
            goal, self.registry["decision.synthesis.typed.stdlib"],
            ["input_path", "output_path"], ROOT)
        self.assertIn("canonical/astra_runtime/tmp/role_named_v1/out_dest.json",
                      set(named))

    def test_both_capabilities_reach_exact_semantic_acceptance(self) -> None:
        """End to end.  Both are refused before any binder runs on 5402138.

        The tag is unique per invocation on purpose.  The controller keeps a
        checkpoint keyed on the plan hash of the goal, so re-running the same
        sentence twice -- which is what a test suite does, across files and
        across runs -- returns FAIL__LIVE_CONTROLLER_EXECUTION on the second
        one.  That was measured, not guessed: this test passed standalone and
        failed the moment it ran a second time in the same tree.
        """
        tag = "e2e%x" % perf_counter_ns()
        for index, cid in enumerate(_TARGETS):
            goal = self._goal(cid, "%s_%d" % (tag, index))
            (self.dir / ("out_%s_%d.json" % (tag, index))).write_text(
                "{}", encoding="utf-8")
            result = solve({"task_id": "ROLENAMED_%s_%d" % (tag, index),
                            "goal": goal})
            self.assertIs(
                result.get("status"),
                "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED",
                "%s -> %s / %s" % (cid, result.get("status"),
                                   result.get("tool_truth_errors")
                                   or result.get("compiler_detail")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
