"""Focused fail-closed controls for the RAW_GOAL repair routing junction."""
from unittest import TestCase, mock

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime import swe_typed_plan_v1 as typed

AUDIT = "python.tests.audit.unittest"
REPAIR = "python.software.repair.apply.verified.v1"
AUDIT_ENTRY = {"provides": ["python.tests.audit"], "keywords": ["audit the tests"]}
REPAIR_ENTRY = {"provides": ["python.source.write.verified_repair_applied"],
                "keywords": ["apply the repair"]}
GOAL = "Fix the failing tests in the python source root example and write the report to report.json"


class RepairRouteGuardTests(TestCase):
    def _run(self, goal, proposal, admission=True):
        registry = {AUDIT: AUDIT_ENTRY, REPAIR: REPAIR_ENTRY}
        compiled = {"selected_capability": AUDIT, "inputs": {}}
        with mock.patch.object(live, "compile_against_live_registry", return_value=(registry, registry, compiled)), \
             mock.patch.object(typed, "build_plan", return_value=proposal) as build, \
             mock.patch.object(door, "route_admission", return_value={"admitted": admission}), \
             mock.patch.object(live, "drive_controller") as execute:
            result = live._run_raw_goal_impl({"task_id": "repair-route-guard", "goal": goal})
        execute.assert_not_called()
        return result, build

    def test_no_decisive_plan_does_not_run_the_auditor(self):
        result, build = self._run(GOAL, None)
        build.assert_called_once()
        self.assertEqual(result["status"], "FAIL_CLOSED__STATED_REPAIR_ROUTE_UNAVAILABLE")
        self.assertEqual(result["refused_capability"], AUDIT)
        self.assertFalse(result["pass"])

    def test_refused_proposal_does_not_run(self):
        registry = {AUDIT: AUDIT_ENTRY, REPAIR: REPAIR_ENTRY}
        proposal = (registry, registry, {"selected_capability": REPAIR, "inputs": {}})
        result, build = self._run(GOAL, proposal, admission=False)
        build.assert_called_once()
        self.assertEqual(result["status"], "FAIL_CLOSED__STATED_REPAIR_ROUTE_UNAVAILABLE")
        self.assertFalse(result["pass"])

    def test_a_proposal_outside_the_original_admissible_registry_is_refused(self):
        outsider = "python.other.repair.apply.v1"
        proposed = {outsider: REPAIR_ENTRY}
        result, _ = self._run(GOAL, (proposed, proposed, {"selected_capability": outsider}))
        self.assertEqual(result["status"], "FAIL_CLOSED__STATED_REPAIR_ROUTE_UNAVAILABLE")
        self.assertFalse(result["pass"])

    def test_a_non_editing_proposal_is_refused(self):
        registry = {AUDIT: AUDIT_ENTRY, REPAIR: REPAIR_ENTRY}
        result, _ = self._run(GOAL, (registry, registry, {"selected_capability": AUDIT}))
        self.assertEqual(result["status"], "FAIL_CLOSED__STATED_REPAIR_ROUTE_UNAVAILABLE")
        self.assertFalse(result["pass"])

    def test_explicitly_named_auditor_is_not_silently_substituted(self):
        result, build = self._run(GOAL + " using " + AUDIT, None)
        build.assert_not_called()
        self.assertEqual(result["status"], "FAIL_CLOSED__STATED_REPAIR_ROUTE_UNAVAILABLE")
        self.assertEqual(result["refused_capability"], AUDIT)
        self.assertFalse(result["pass"])
