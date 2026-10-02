import inspect
import json
import unittest
from pathlib import Path

import canonical.runtime.delegation_dynamic_reassignment_proof as proof

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/"canonical/governance/TASK_TO_DELEGATION_WHOLE_SCOPE_AUDIT_V1.json"
REGISTRY=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"

class DelegationWholeScopeAuditTests(unittest.TestCase):
    def setUp(self):
        self.audit=json.loads(AUDIT.read_text(encoding="utf-8"))
        self.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.contract=next(x for x in self.registry["active_contracted_residuals"] if x["behavior_id"]=="TASK_TO_DELEGATION_GRAPH_001")

    def test_contract_requires_dimensions_audit_marks_missing(self):
        text=" ".join([
            self.contract["inputs"], self.contract["required_output_or_action"],
            self.contract["success_condition"], self.contract["failure_condition"],
            self.contract["verification_route"]
        ]).lower()
        for phrase in ("evidence ownership","conflicting writes","fanin","single-worker","naive fanout","resource constraints"):
            self.assertIn(phrase,text)
        states={x["id"]:x["current_route"] for x in self.audit["required_dimensions"]}
        self.assertEqual(states["EVIDENCE_OWNERSHIP_AND_FANIN_INTEGRITY"],"MISSING")
        self.assertEqual(states["CONFLICTING_WRITES_AND_OWNERSHIP_EXCLUSION"],"MISSING")
        self.assertEqual(states["CONTROLLED_BASELINE_ADVANTAGE"],"MISSING")
        self.assertEqual(states["RESOURCE_CONSTRAINTS"],"PARTIAL")

    def test_current_generator_is_fixed_topology(self):
        src=inspect.getsource(proof.generate_case)
        for token in ("PARSE_","REASON_","RETRIEVE_","INTEGRATE_","REVIEW_"):
            self.assertIn(token,src)
        self.assertIn('("WORKER_UNAVAILABLE", "STEP_UNAVAILABLE", "WORKER_CAPABILITY_REMOVED")',src)

    def test_current_route_has_no_evidence_ownership_or_write_conflict_model(self):
        src=inspect.getsource(proof)
        self.assertNotIn("evidence_owner",src)
        self.assertNotIn("write_conflict",src)
        self.assertNotIn("naive_fanout",src)
        self.assertNotIn("single_worker_baseline",src)

    def test_audit_does_not_revoke_bounded_preflight(self):
        self.assertIn("INDEPENDENT_INFORMATION_SAFE_DYNAMIC_REASSIGNMENT_PREFLIGHT_REMAINS_VALID_FOR_ITS_BOUNDED_SCOPE",self.audit["preserved_credit"])
        self.assertEqual(self.audit["terminal_results_observed"],0)
        self.assertEqual(self.audit["capability_credit_delta"],0)
        self.assertTrue(self.audit["status"].startswith("FAIL_CLOSED"))

if __name__=="__main__":
    unittest.main(verbosity=2)
