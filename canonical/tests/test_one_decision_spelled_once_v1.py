#!/usr/bin/env python3
"""One decision, spelled once: a release condition admitted anywhere is admitted everywhere.

WHY THIS EXISTS
---------------
`canonical/runtime/computer_execution_boundary_v1.refuses_execution` is documented as "the single
decision every execution site must use".  On 2026-11-12 a counterfactual
(`canonical/tools/lift_the_refusal_and_see_what_remains_v1.py`) measured that it was not single:
two callers re-derived the same rule from the boundary's smaller predicates instead of asking for
the decision.  The consequence is precise and was measured, not argued:

    with the boundary's own decision lifted, 3 of 21 realistic sentences still came back
    FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT -- emitted by the composer's
    own copy, which no change to the boundary can reach.

A refusal that cannot be released by changing the thing that owns the rule is not a safety
property.  It is a second source of truth, and this repository has already been burned by the same
shape once (a census, not a counterfactual, decided what the blocker was; four rounds).

WHAT THIS PINS
--------------
1. THE CALLERS ASK THE OWNER.  For every id in the registry, both callers move when the boundary's
   decision is substituted.  A caller that re-derives the rule cannot express the change and fails.
2. NO THIRD COPY.  Outside the boundary module itself, no runtime module references the three small
   predicates.  This is a source scan, so a new copy fails here instead of silently changing the
   meaning of "the decision".
3. THE REFUSALS ARE UNCHANGED.  With the real decision in place the two callers refuse exactly what
   they refused before -- identical status, failure class, empty steps and the same failed step.
   This is the anti-regression half: de-duplication may not release anything.
4. THE LIFT NOW PROPAGATES.  With the decision substituted to "no refusal", the callers stop
   refusing.  That is the whole point of a single decision, and it is false for the code this test
   replaced (measured: the composer returned the confinement status anyway).

Written as `unittest` rather than pytest style because this tree's honest baseline runs without
pytest installed on the measurement box; both runners collect it.
"""
from __future__ import annotations

import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_composer_v1 as composer
from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.runtime import composer_route_v1 as composer_route
from canonical.runtime import live_integrated_brain_v1 as integrated

BOUNDARY_MODULE = "canonical/runtime/computer_execution_boundary_v1.py"
SMALL_PREDICATES = (
    "is_unconfined_capability_id",
    "is_unconfined_execution_entry",
    "is_unconfined_repair_entry",
)

# Ids the boundary names by hand, plus the ids the two callers are known to meet.
NAMED_IDS = (
    "shell.command.run",
    "software.analysis.diagnose_and_architect.v1",
    "python.software.repair.apply.verified.v1",
)


def _registry() -> dict:
    return composer.load_registry()


class OneDecisionSpelledOnceTests(unittest.TestCase):
    # --------------------------------------------------------------------- 1. callers ask
    def test_every_caller_agrees_with_the_boundary_decision(self):
        """Substitute the decision; every in-tree caller must move with it."""
        reg = _registry()
        for capability_id in sorted(reg):
            entry = reg[capability_id]
            real = boundary.refuses_execution(capability_id, entry)
            with mock.patch.object(boundary, "refuses_execution", return_value=not real):
                self.assertIs(composer_route._chain_refuses(capability_id, entry), not real,
                              "composer re-derives the rule for " + capability_id)
                self.assertIs(integrated._plan_refuses(capability_id, entry, None, None), not real,
                              "live_integrated_brain re-derives the rule for " + capability_id)

    def test_the_lift_reaches_both_callers_that_used_to_keep_their_own_copy(self):
        """The measured defect, pinned: a lifted decision must actually lift."""
        reg = _registry()
        for capability_id in NAMED_IDS:
            entry = reg.get(capability_id)
            with mock.patch.object(boundary, "refuses_execution", return_value=False):
                self.assertIs(composer_route._chain_refuses(capability_id, entry), False)
                self.assertIs(integrated._plan_refuses(capability_id, entry, None, None), False)

    # --------------------------------------------------------------------- 2. no third copy
    def test_no_runtime_module_re_derives_the_rule_from_the_small_predicates(self):
        offenders: list[str] = []
        for path in sorted((ROOT / "canonical" / "runtime").glob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if rel == BOUNDARY_MODULE:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for name in SMALL_PREDICATES:
                if name + "(" in text:
                    offenders.append(rel + ":" + name)
        self.assertEqual(offenders, [])

    # --------------------------------------------------------------------- 3. refusals stand
    def test_the_real_decision_still_refuses_what_it_refused(self):
        """Every named row still refuses, and the repair row refuses on BOTH of its halves.

        The repair row is the one place where the boundary's `repair` flag is split, so it is
        checked twice: with `repair=False` its own missing-evidence refusal stands, and with
        `repair=True` its executor is closed as well.  An empty plan context is passed for the
        second check because the row is outside the bound registry's single-row path there --
        which is exactly the condition the old hand-written copy tested.
        """
        reg = _registry()
        plan_context = (None, None, frozenset())
        for capability_id in NAMED_IDS:
            entry = reg.get(capability_id)
            self.assertIs(boundary.refuses_execution(capability_id, entry), True, capability_id)
            self.assertIs(composer_route._chain_refuses(capability_id, entry), True, capability_id)
            self.assertIs(integrated._plan_refuses(capability_id, entry, None, plan_context), True,
                          capability_id)
            # ... and again with no context, which is the first-half-only question.
            if capability_id != boundary.REPAIR_CAPABILITY_ID:
                self.assertIs(integrated._plan_refuses(capability_id, entry, None, None), True,
                              capability_id)

    def test_the_repair_row_still_splits_its_two_halves(self):
        """`repair=False` reports the evidence gap; `repair=True` closes execution. Both stand."""
        entry = _registry().get(boundary.REPAIR_CAPABILITY_ID)
        self.assertIs(boundary.refuses_execution(boundary.REPAIR_CAPABILITY_ID, entry,
                                                 repair=False), False,
                      "the repair row's own evidence refusal must be reported first")
        self.assertIs(boundary.refuses_execution(boundary.REPAIR_CAPABILITY_ID, entry,
                                                 repair=True), True,
                      "the repair row must still be closed to execution")

    def test_a_capability_the_boundary_admits_is_still_admitted(self):
        """The de-duplication must not turn "admitted" into "refused" either."""
        reg = _registry()
        admitted = [cid for cid, entry in reg.items()
                    if not boundary.refuses_execution(cid, entry)]
        self.assertTrue(admitted, "the registry has no admitted capability; the fixture is wrong")
        for capability_id in admitted:
            entry = reg[capability_id]
            self.assertIs(composer_route._chain_refuses(capability_id, entry), False,
                          capability_id)

    def test_the_refusal_shape_is_unchanged(self):
        """Same status, same failure class, no executed claim -- the receipt callers already read."""
        entry = _registry().get("shell.command.run")
        self.assertIs(boundary.refuses_execution("shell.command.run", entry), True)
        result = composer_route.execute_chain(["shell.command.run"], "run something")
        self.assertIs(result["pass"], False)
        self.assertEqual(result["status"], boundary.STATUS)
        self.assertEqual(result["failure_class"], boundary.FAILURE_CLASS)
        self.assertIs(result["executed"], False)
        self.assertEqual(result["steps"], [])
        self.assertEqual(result["failed_step"],
                         {"index": 0, "capability_id": "shell.command.run"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
