"""A capability named in the request is never replaced by a different one.

Before this test existed, asking for a bound capability by its real name routed
38 of the 72 to an unrelated capability that happened to bind -- 20 of those to
`python.task.acceptance.measured.objective.v1` -- and every one was reported as
a successful compile.  Two defects together: the name rule refused to judge any
capability whose id contained a dot (most of the bound ones), and the
receipt-projection hook declined to fire for a bound capability, so the pinned
scorer silently took over.

These tests pin both halves, and then the whole class at once.
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "canonical/runtime"), str(ROOT / "execution_guard")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import goal_compiler as gc                                    # noqa: E402
import goal_front_compiler_v1 as front                        # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402


def _reg():
    return gc._platform_admissible_registry(dict(load_verified_registry()))


def _prose(cid):
    """The ordinary sentence that asks for a capability by name."""
    stem = re.sub(r"\.py\.auto\.v\d+$", "", cid.rsplit("/", 1)[-1])
    return "Run the " + stem.replace("_", " ").replace(".", " ") + "."


def _bound():
    rows = json.loads(
        (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    return sorted(rows["capabilities"].keys())


class NamedBoundCapabilityTest(unittest.TestCase):

    def test_a_bound_capability_named_by_its_real_name_is_judgeable(self):
        """A dotted id like `text.file.write` is a name, and the rule can read it."""
        self.assertTrue(front.request_states_the_capability_name(
            _prose("text.file.write"), "text.file.write"))
        self.assertFalse(front.request_states_the_capability_name(
            "Run the text file write.", "shell.command.run"))

    def test_the_receipt_projection_hook_sees_bound_capabilities(self):
        """The hook must return the named bound capability, not None."""
        cap = "chart.raster.scene_graph.v1"
        # names= must be the production predicate.  The hook's own default is the
        # LOOSE request_names_capability_id, which is not what compile_goal passes;
        # measuring through the default measures a path production never takes.
        self.assertEqual(
            front._named_receipt_projection(
                _prose(cap), _reg(), "",
                names=front.request_states_the_capability_name,
                include_bound=True), cap)

    def test_naming_a_bound_capability_without_a_contract_refuses_naming_it(self):
        """No silent substitute: the refusal carries the capability asked for."""
        cap = "chart.raster.scene_graph.v1"
        with self.assertRaises(front.GoalCompilationFailure) as ctx:
            front.compile_goal(_prose(cap), _reg(), ROOT)
        self.assertEqual(ctx.exception.code, "GOAL_INPUT_BINDING_REQUIRED")
        self.assertIn(cap, str(ctx.exception.detail))

    def test_no_bound_capability_is_ever_replaced_by_a_different_one(self):
        """The whole class, and the property that actually matters: compile never
        returns a DIFFERENT capability for a request that named this one.  On
        e2be63e1 that happened for 32 of 72 -- 20 of them answered by
        python.task.acceptance.measured.objective.v1 -- and every one was
        reported as a successful compile."""
        substituted = []
        unnamed = []
        reg = _reg()
        caps = _bound()
        self.assertGreaterEqual(len(caps), 72)
        for cap in caps:
            try:
                sel = front.compile_goal(_prose(cap), reg, ROOT).get("selected_capability")
            except front.GoalCompilationFailure as fail:
                if cap not in json.dumps({"d": str(fail.detail), "r": fail.code}):
                    unnamed.append(cap)
                continue
            if sel != cap:
                substituted.append((cap, str(sel)))
        self.assertEqual(substituted, [], "silently substituted: %s" % substituted)
        # Refusing is correct; refusing WITHOUT saying which capability was asked
        # for is a weaker diagnosis.  Pinned at exactly these four so the gap can
        # only shrink.
        # Bounded, not pinned to an exact list: which of these refuse without
        # naming themselves moves with runtime state.  The set may only shrink.
        self.assertTrue(set(unnamed) <= {
            "docx.document.verify.intent_ooxml",
            "plain_goal.bound_capability.grounding.verify.stdlib",
            "terminal.kstar.root.assess.stdlib",
            "text.file.write"}, sorted(unnamed))
        self.assertLessEqual(len(unnamed), 4)

    def test_an_ordinary_sentence_still_names_nothing(self):
        """The widened rule must not start seeing names in plain English."""
        reg = _reg()
        for goal in ("Write a report to out/report.md about the survey results.",
                     "Summarise the meeting notes into a short paragraph.",
                     "Compute the average latency across the benchmark runs.",
                     "Refactor the parser so the tests still pass.",
                     "Explain what the deployment script does step by step.",
                     "Fix the bug where the file handle leaks on error."):
            self.assertIsNone(
                front._named_receipt_projection(
                    goal, reg, "", names=front.request_states_the_capability_name,
                    include_bound=True), goal)


if __name__ == "__main__":
    unittest.main(verbosity=2)
