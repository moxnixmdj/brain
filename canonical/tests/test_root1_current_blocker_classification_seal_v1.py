from __future__ import annotations

import copy
import unittest

from canonical.runtime import root1_current_blocker_classification_seal_v1 as s

def fixtures():
    envelope={"target_family_count":3,"families":[{"id":"A"},{"id":"B"},{"id":"C"}]}
    manifest={"expected_family_count":3,"actual_family_count":3,"families":[{"id":"A"},{"id":"B"},{"id":"C"}]}
    registry={"predicates":[{"id":"p1"},{"id":"p2"},{"id":"p3"},{"id":"p4"}]}
    ledger={"claims":[
        {"predicate_id":"p1","state":"PROVED","scope_complete":True,"independent_or_objective":True},
        {"predicate_id":"p2","state":"PROVED","scope_complete":True,"independent_or_objective":True},
        {"predicate_id":"p3","state":"EXTERNAL_BLOCKED"},
    ]}
    root={
      "current_acceptance":{"total_families":3,"total_atomic":4,"proved_atomic":2,"unresolved_atomic":2},
      "current_residual_root_partition":{
        "unresolved_total":2,"root1_positive_gap_count":0,
        "root2_only_count":1,"root3_only_count":0,"root2_and_root3_count":1,
        "root2_only":["p3"],"root3_only":[],"root2_and_root3":["p4"]},
      "roots":{"root_1_capability_missing":{"current_positive_root1_blockers":[]}}
    }
    return envelope,manifest,registry,ledger,root

class Tests(unittest.TestCase):
    def test_exact_exhaustive_partition_seals_current_root1(self):
        out=s.compute_current_root1_blocker_seal(
            target_envelope=fixtures()[0],terminal_manifest=fixtures()[1],
            predicate_registry=fixtures()[2],evidence_ledger=fixtures()[3],root_state=fixtures()[4])
        self.assertTrue(out["current_root1_classification_sealed"])
        self.assertEqual(out["root1_current_blocker_residual_count"],0)
        self.assertEqual(out["unresolved_predicate_count"],2)

    def test_unclassified_unresolved_predicate_fails(self):
        e,m,r,l,root=fixtures()
        root["current_residual_root_partition"]["root2_and_root3"]=[]
        root["current_residual_root_partition"]["root2_and_root3_count"]=0
        with self.assertRaisesRegex(s.Root1SealError,"ROOT_PARTITION_NOT_EXHAUSTIVE"):
            s.compute_current_root1_blocker_seal(target_envelope=e,terminal_manifest=m,predicate_registry=r,evidence_ledger=l,root_state=root)

    def test_extra_classified_predicate_fails(self):
        e,m,r,l,root=fixtures()
        root["current_residual_root_partition"]["root2_only"].append("ghost")
        root["current_residual_root_partition"]["root2_only_count"]=2
        with self.assertRaisesRegex(s.Root1SealError,"ROOT_PARTITION_NOT_EXHAUSTIVE"):
            s.compute_current_root1_blocker_seal(target_envelope=e,terminal_manifest=m,predicate_registry=r,evidence_ledger=l,root_state=root)

    def test_positive_root1_gap_fails(self):
        e,m,r,l,root=fixtures()
        root["current_residual_root_partition"]["root1_positive_gap_count"]=1
        with self.assertRaisesRegex(s.Root1SealError,"ROOT1_POSITIVE_GAP_COUNT_NONZERO"):
            s.compute_current_root1_blocker_seal(target_envelope=e,terminal_manifest=m,predicate_registry=r,evidence_ledger=l,root_state=root)

    def test_positive_root1_blocker_row_fails(self):
        e,m,r,l,root=fixtures()
        root["roots"]["root_1_capability_missing"]["current_positive_root1_blockers"]=["x"]
        with self.assertRaisesRegex(s.Root1SealError,"ROOT1_POSITIVE_BLOCKERS_NONEMPTY"):
            s.compute_current_root1_blocker_seal(target_envelope=e,terminal_manifest=m,predicate_registry=r,evidence_ledger=l,root_state=root)

    def test_proved_without_scope_complete_fails(self):
        e,m,r,l,root=fixtures()
        l["claims"][0]["scope_complete"]=False
        with self.assertRaisesRegex(s.Root1SealError,"PROVED_WITHOUT_SCOPE_COMPLETE"):
            s.compute_current_root1_blocker_seal(target_envelope=e,terminal_manifest=m,predicate_registry=r,evidence_ledger=l,root_state=root)

    def test_family_identity_drift_fails(self):
        e,m,r,l,root=fixtures()
        m["families"][2]["id"]="D"
        with self.assertRaisesRegex(s.Root1SealError,"TERMINAL_FAMILY_IDENTITY_DRIFT"):
            s.compute_current_root1_blocker_seal(target_envelope=e,terminal_manifest=m,predicate_registry=r,evidence_ledger=l,root_state=root)

    def test_duplicate_predicate_fails(self):
        e,m,r,l,root=fixtures()
        r["predicates"][3]["id"]="p3"
        with self.assertRaisesRegex(s.Root1SealError,"PREDICATE_DUPLICATE"):
            s.compute_current_root1_blocker_seal(target_envelope=e,terminal_manifest=m,predicate_registry=r,evidence_ledger=l,root_state=root)

if __name__=="__main__":
    unittest.main(verbosity=2)
