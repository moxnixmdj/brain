from __future__ import annotations
import unittest
from canonical.runtime.authority_epoch_guard_v1 import AuthorityEpochError, compute_epoch, select_latest_active_activation

class AuthorityEpochGuardTests(unittest.TestCase):
    def test_epoch_is_order_independent(self):
        self.assertEqual(compute_epoch({"b":"2"*40,"a":"1"*40}), compute_epoch({"a":"1"*40,"b":"2"*40}))
    def test_any_blob_delta_changes_epoch(self):
        a={"a":"1"*40,"b":"2"*40}; b=dict(a); b["b"]="3"*40
        self.assertNotEqual(compute_epoch(a),compute_epoch(b))
    def test_invalid_component_fails_closed(self):
        with self.assertRaises(AuthorityEpochError): compute_epoch({"a":"not-a-sha"})
    def test_empty_epoch_fails_closed(self):
        with self.assertRaises(AuthorityEpochError): compute_epoch({})
    def test_highest_version_active_activation_wins(self):
        rows=[(12,"v12",{"scheduling_authority":True}),(13,"v13",{"scheduling_authority":True})]
        self.assertEqual(select_latest_active_activation(rows)[:2],(13,"v13"))
    def test_inactive_newer_candidate_does_not_preempt_active(self):
        rows=[(13,"v13",{"scheduling_authority":True}),(14,"v14",{"scheduling_authority":False})]
        self.assertEqual(select_latest_active_activation(rows)[:2],(13,"v13"))
    def test_no_active_activation_fails_closed(self):
        with self.assertRaises(AuthorityEpochError):
            select_latest_active_activation([(13,"v13",{"scheduling_authority":False})])

if __name__=="__main__": unittest.main(verbosity=2)
