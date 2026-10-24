"""A ``goal`` input receives the goal, not the sentence that invoked the capability.

``_bind_inputs`` gave a ``goal`` key the entire raw request verbatim.  That is right
when the request *is* the goal, and wrong when the request is an INVOCATION that
names a capability and then hands the goal over as an argument.

Measured on 0351c257, over the 13 verified capabilities that take a ``goal`` input:

    clean goal (what was asked for)   0 of 13
    goal containing "Run the ..."     4 of 13

    "Run the docx document create python docx with goal Write a report on
     quarterly sales."
    -> goal = "Run the docx document create python docx with goal Write a report on
               quarterly sales."

so the document would have been about the invocation sentence.  That is the worst
kind of failure: it passes and it is wrong.  ``_extract_text_argument`` already did
the extraction for ``text``; this gives ``goal`` the same treatment.  Nothing is
invented -- a request that states no goal still receives the whole request, exactly
as before.
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "canonical/runtime")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import goal_compiler as gc                                    # noqa: E402
import goal_front_compiler_v1 as front                        # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

STATED = "Write a report on quarterly sales"


def _registry():
    return json.loads(
        (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
    )["capabilities"]


def _reg():
    return gc._platform_admissible_registry(dict(load_verified_registry()))


def _goal_caps():
    tmpl = re.compile(r"\$\{input\.([A-Za-z0-9_]+)\}")
    return [c for c, e in sorted(_registry().items())
            if "goal" in set(tmpl.findall(json.dumps(e.get("action_template") or {})))]


class GoalInputGetsTheGoalTest(unittest.TestCase):

    def test_a_stated_goal_is_not_the_invocation_sentence(self):
        got = gc._extract_goal_argument(
            "Run the docx document create python docx with goal %s." % STATED)
        self.assertEqual(got, STATED)

    def test_a_plain_request_still_gets_the_whole_request(self):
        """No regression for the overwhelmingly common shape.  A request that states
        no separate goal IS the goal."""
        raw = "%s and save it as report.docx" % STATED
        self.assertEqual(gc._extract_goal_argument(raw), raw)

    def test_a_quoted_goal_wins(self):
        got = gc._extract_goal_argument(
            'Create a document about "the annual safety review" using docx document create python docx.')
        self.assertEqual(got, "the annual safety review")

    def test_for_the_goal_is_also_recognised(self):
        got = gc._extract_goal_argument(
            "Run the docx document create from json record for the goal Summarise the incident log.")
        self.assertEqual(got, "Summarise the incident log")

    def test_no_capability_receives_its_own_invocation_as_the_goal(self):
        """Whole class.  Measured 4 of 13 on 0351c257; must be zero."""
        reg = _reg()
        caps = _goal_caps()
        self.assertGreaterEqual(len(caps), 13)
        wrapped = []
        bound = 0
        for cap in caps:
            entry = reg.get(cap)
            if not entry:
                continue
            stem = re.sub(r"\.py\.auto\.v\d+$", "", cap.rsplit("/", 1)[-1])
            goal = "Run the %s with goal %s." % (
                stem.replace("_", " ").replace(".", " "), STATED)
            try:
                bound_inputs = front.bind_all_inputs(goal, entry, ROOT, cycle=0, spool=set())
            except front.GoalCompilationFailure:
                continue
            value = bound_inputs.get("goal")
            if not isinstance(value, str):
                continue
            bound += 1
            if value.lower().startswith("run the "):
                wrapped.append((cap, value[:60]))
        self.assertGreaterEqual(bound, 4, "only %d bound; probe changed shape" % bound)
        self.assertEqual(wrapped, [], "still handed the wrapper: %s" % (wrapped,))

    def test_the_stated_goal_counts_as_stated_for_the_contract_check(self):
        """PR #6101 refuses a named capability whose input the sentence does not
        state.  A goal lifted out of the sentence must survive that check -- if it
        did not, this change would turn a working route into a refusal."""
        entry = _reg()["docx.document.create.python_docx"]
        goal = "Run the docx document create python docx with goal %s." % STATED
        bound = front.bind_all_inputs(goal, entry, ROOT, cycle=0, spool=set())
        self.assertEqual(bound.get("goal"), STATED)
        self.assertNotIn("goal", front._inputs_not_stated_by(goal, bound))

    def test_the_binder_routes_goal_through_the_extractor(self):
        """Pins the wiring: _bind_inputs must call _extract_goal_argument, so a
        future refactor that puts str(goal) back fails here."""
        entry = {"action_template": {"args": {"goal": "${input.goal}"}}}
        got = gc._bind_inputs(
            "Run the docx document create python docx with goal %s." % STATED,
            ROOT, entry)
        self.assertEqual(got.get("goal"), STATED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
