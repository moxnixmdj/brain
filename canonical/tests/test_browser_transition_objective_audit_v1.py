from __future__ import annotations
import unittest
from canonical.runtime.browser_transition_objective_audit_v1 import audit_trace

def good():
    return {
        "declared_writable_keys": ["ui.panel", "ui.query"],
        "allowed_system_keys": ["ui.focus"],
        "no_progress_repeat_limit": 1,
        "terminal_success": True,
        "steps": [
            {"action_signature": "click:settings", "state_hash_before": "S0", "state_hash_after": "S1", "observed_diff_keys": ["ui.panel", "ui.focus"], "receipt_bound": True},
            {"action_signature": "type:search", "state_hash_before": "S1", "state_hash_after": "S2", "observed_diff_keys": ["ui.query"], "receipt_bound": True},
        ],
    }

class BrowserTransitionObjectiveAuditTests(unittest.TestCase):
    def test_pass(self):
        self.assertTrue(audit_trace(good())["pass"])

    def test_undeclared_side_effect_fails(self):
        p=good()
        p["steps"][0]["observed_diff_keys"].append("account.deleted")
        out=audit_trace(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"UNDECLARED_SIDE_EFFECT")

    def test_no_progress_loop_fails(self):
        p=good()
        p["steps"]=[
            {"action_signature":"click:x","state_hash_before":"S","state_hash_after":"S","observed_diff_keys":[],"receipt_bound":True},
            {"action_signature":"click:x","state_hash_before":"S","state_hash_after":"S","observed_diff_keys":[],"receipt_bound":True},
        ]
        out=audit_trace(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"NO_PROGRESS_LOOP")

    def test_unbound_receipt_fails(self):
        p=good()
        p["steps"][0]["receipt_bound"]=False
        self.assertEqual(audit_trace(p)["reason"],"UNBOUND_ACTION_RECEIPT")

    def test_parent_failure_fails(self):
        p=good()
        p["terminal_success"]=False
        self.assertEqual(audit_trace(p)["reason"],"PARENT_TERMINAL_ACCEPTANCE_FAILED")

if __name__=="__main__":
    unittest.main()
