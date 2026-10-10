from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_semantic_totality_claim_pack_v2 as pack

ROOT = Path(__file__).resolve().parents[2]


def current_documents():
    manifest=json.loads((ROOT/pack.PINS["manifest"][0]).read_text(encoding="utf-8"))
    ledger=json.loads((ROOT/pack.PINS["residual_ledger"][0]).read_text(encoding="utf-8"))
    from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as batch
    batch_out=batch.verify(repo_root=ROOT)
    mission_blob=pack._blob(ROOT/pack.MISSION_PATH)
    return manifest,ledger,batch_out,mission_blob


class ProfessionalSemanticTotalityClaimPackV2Tests(unittest.TestCase):
    def test_current_twelve_semantic_claims_freeze_separately_with_zero_authority(self):
        out=pack.verify(repo_root=ROOT)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_claim_count"],12)
        self.assertEqual(out["unique_claim_id_count"],12)
        self.assertEqual(len(out["claims"]),12)
        self.assertEqual(len({x["frozen_claim"]["claim_id"] for x in out["claims"]}),12)
        self.assertTrue(out["single_active_claim_policy_preserved"])
        self.assertFalse(out["cross_claim_root_transport_authorized"])
        self.assertEqual(out["root_proved_claim_count"],0)
        self.assertEqual(out["property_truth_claim_count"],0)
        for row in out["claims"]:
            self.assertTrue(row["claim_guard_pass"])
            self.assertFalse(row["mission_sufficient_carrier_factorization_proved"])
            self.assertFalse(row["cc_r1_reality_containment_proved"])
            self.assertFalse(row["cc_r2_mission_soundness_proved"])
            self.assertFalse(row["cc_r3_terminal_closure_proved"])
            self.assertFalse(row["r4_proof_closure"])
            self.assertFalse(row["semantic_property_truth_authority"])
            self.assertFalse(row["activation_authorized"])

    def test_missing_semantic_leaf_fails_closed(self):
        manifest,ledger,batch_out,mission_blob=current_documents()
        ledger["leaves"]=[
            x for x in ledger["leaves"]
            if x.get("leaf_id")!="PQ::R9_TEMPORAL_DEPLOYMENT::SEMANTIC"
        ]
        out=pack.project_documents(
            manifest,ledger,batch_out,current_mission_blob_sha=mission_blob
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"LEDGER_MANIFEST_SEMANTIC_LEAF_SET_MISMATCH")

    def test_bounded_witness_cannot_self_promote_to_global_leaf(self):
        manifest,ledger,batch_out,mission_blob=current_documents()
        row=next(
            x for x in ledger["leaves"]
            if x.get("leaf_id")=="PQ::R1_TARGET_SPECIFICATION::SEMANTIC"
        )
        row["bounded_witnesses"][0]["global_leaf_closure"]=True
        out=pack.project_documents(
            manifest,ledger,batch_out,current_mission_blob_sha=mission_blob
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SEMANTIC_WITNESS_GLOBAL_PROMOTION_FORBIDDEN")

    def test_scope_incompleteness_blocks_claim_pack(self):
        manifest,ledger,batch_out,mission_blob=current_documents()
        row=next(
            x for x in batch_out["rows"]
            if x.get("leaf_id")=="PQ::R3_REALIZATION_OBSERVATION::SEMANTIC"
        )
        row["whole_leaf_scope_complete"]=False
        out=pack.project_documents(
            manifest,ledger,batch_out,current_mission_blob_sha=mission_blob
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SEMANTIC_SCOPE_ROW_NOT_PROPERTY_READY")

    def test_claim_ids_bind_mission_and_do_not_survive_mission_change(self):
        manifest,ledger,batch_out,mission_blob=current_documents()
        first=pack.project_documents(
            manifest,ledger,batch_out,current_mission_blob_sha=mission_blob
        )
        changed=pack.project_documents(
            manifest,ledger,deepcopy(batch_out),current_mission_blob_sha="0"*40
        )
        self.assertTrue(first["pass"],first)
        self.assertTrue(changed["pass"],changed)
        ids1=[x["frozen_claim"]["claim_id"] for x in first["claims"]]
        ids2=[x["frozen_claim"]["claim_id"] for x in changed["claims"]]
        self.assertNotEqual(ids1,ids2)
        self.assertNotEqual(first["claim_id_set_sha256"],changed["claim_id_set_sha256"])

    def test_bounded_witness_change_changes_only_affected_claim_identity(self):
        manifest,ledger,batch_out,mission_blob=current_documents()
        first=pack.project_documents(
            manifest,ledger,batch_out,current_mission_blob_sha=mission_blob
        )
        changed_ledger=deepcopy(ledger)
        target=next(
            x for x in changed_ledger["leaves"]
            if x.get("leaf_id")=="PQ::R4_MEASUREMENT_CONSTRUCT::SEMANTIC"
        )
        target["bounded_witnesses"][0]["claim_kind"] += "__MUTATED"
        second=pack.project_documents(
            manifest,changed_ledger,deepcopy(batch_out),current_mission_blob_sha=mission_blob
        )
        self.assertTrue(first["pass"],first)
        self.assertTrue(second["pass"],second)
        a={x["leaf_id"]:x["frozen_claim"]["claim_id"] for x in first["claims"]}
        b={x["leaf_id"]:x["frozen_claim"]["claim_id"] for x in second["claims"]}
        changed=[leaf for leaf in a if a[leaf]!=b[leaf]]
        self.assertEqual(changed,["PQ::R4_MEASUREMENT_CONSTRUCT::SEMANTIC"])


if __name__=="__main__":
    unittest.main(verbosity=2)
