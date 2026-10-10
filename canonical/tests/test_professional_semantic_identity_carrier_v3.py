from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import coverage_claim_scope_guard_v1 as guard_v1
from canonical.runtime import professional_semantic_identity_carrier_v3 as carrier
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3

ROOT=Path(__file__).resolve().parents[2]


def source_pack():
    out=pack_v3.verify(repo_root=ROOT)
    assert out["pass"] is True,out
    return out


def bindings():
    pointer=json.loads((ROOT/pack_v3.MISSION_POINTER_PATH).read_text(encoding="utf-8"))
    authority=json.loads((ROOT/pack_v3.MISSION_AUTHORITY_PATH).read_text(encoding="utf-8"))
    return pointer,authority


def r12_row(source):
    return next(
        x for x in source["claims"]
        if x["leaf_id"]=="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
    )


class StableIdentityCarrierV3Tests(unittest.TestCase):
    def test_current_stable_v3_claims_factor_12_of_12(self):
        out=carrier.verify(repo_root=ROOT)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_leaf_count"],12)
        self.assertEqual(out["factorization_pass_count"],12)
        self.assertEqual(out["mission_sufficient_carrier_factorization_proved_count"],12)
        self.assertEqual(out["unique_claim_id_count"],12)
        self.assertFalse(out["cross_claim_root_transport_authorized"])
        self.assertFalse(out["leaf_property_truth_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_exact_r12_stable_claim_passes_without_sampling(self):
        src=source_pack(); pointer,authority=bindings(); row=r12_row(src)
        cert=carrier.build_certificate(row)
        out=carrier.evaluate_row(
            row,cert,current_pointer=pointer,mission_authority=authority
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["claim_id"],src["r12_claim_id"])
        self.assertTrue(out["universal_factorization_proved"])
        self.assertFalse(out["semantic_information_loss"])

    def test_cross_claim_certificate_substitution_fails(self):
        src=source_pack(); pointer,authority=bindings()
        rows=sorted(src["claims"],key=lambda x:x["leaf_id"])
        cert=carrier.build_certificate(rows[1])
        out=carrier.evaluate_row(
            rows[0],cert,current_pointer=pointer,mission_authority=authority
        )
        self.assertFalse(out["pass"])
        self.assertTrue(out["reason"].startswith("IDENTITY_CARRIER_BINDING_DRIFT:"))

    def test_lossy_projection_fails_closed(self):
        src=source_pack(); pointer,authority=bindings(); row=r12_row(src)
        cert=carrier.build_certificate(row)
        cert["semantic_information_loss"]=True
        out=carrier.evaluate_row(
            row,cert,current_pointer=pointer,mission_authority=authority
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "IDENTITY_CARRIER_BINDING_DRIFT:semantic_information_loss",
        )

    def test_stale_mission_hash_fails_stable_guard(self):
        src=source_pack(); pointer,authority=bindings(); row=deepcopy(r12_row(src))
        row["frozen_claim"]["mission_blob_sha"]="0"*40
        row["frozen_claim"]["claim_id"]=guard_v1.compute_claim_id(row["frozen_claim"])
        cert=carrier.build_certificate(row)
        out=carrier.evaluate_row(
            row,cert,current_pointer=pointer,mission_authority=authority
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"STABLE_CLAIM_GUARD_REJECTED")
        self.assertIn("MISSION_AUTHORITY_BINDING_STALE",out["claim_guard"]["errors"])

    def test_scope_binding_drift_fails(self):
        src=source_pack(); pointer,authority=bindings(); row=deepcopy(r12_row(src))
        row["scope_definition_sha256"]="f"*64
        cert=carrier.build_certificate(row)
        out=carrier.evaluate_row(
            row,cert,current_pointer=pointer,mission_authority=authority
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"CLAIM_SCOPE_BINDING_DRIFT")

    def test_sampled_factorization_cannot_replace_universal_proof(self):
        src=source_pack(); pointer,authority=bindings(); row=r12_row(src)
        cert=carrier.build_certificate(row)
        cert["factorization"]["universal_not_sampled"]=False
        out=carrier.evaluate_row(
            row,cert,current_pointer=pointer,mission_authority=authority
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "FACTORIZATION_PROOF_DRIFT:universal_not_sampled",
        )

    def test_mutable_pointer_bookkeeping_drift_does_not_break_stable_claim(self):
        src=source_pack(); pointer,authority=bindings()
        pointer=deepcopy(pointer)
        pointer["synthetic_currentness_only"]={"generation":999}
        out=carrier.evaluate_pack(
            src,current_pointer=pointer,mission_authority=authority
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["factorization_pass_count"],12)

    def test_pointer_objective_drift_fails(self):
        src=source_pack(); pointer,authority=bindings()
        pointer=deepcopy(pointer); pointer["real_objective"]="WEAKER_OBJECTIVE"
        out=carrier.evaluate_pack(
            src,current_pointer=pointer,mission_authority=authority
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "STABLE_IDENTITY_CARRIER_BATCH_MEMBER_FAILED",
        )
        self.assertEqual(
            out["verdict"]["reason"],
            "STABLE_CLAIM_GUARD_REJECTED",
        )

    def test_unverified_source_pack_fails_closed(self):
        pointer,authority=bindings()
        out=carrier.evaluate_pack(
            {"pass":False},
            current_pointer=pointer,
            mission_authority=authority,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"STABLE_CLAIM_PACK_REQUIRED")


if __name__=="__main__":
    unittest.main(verbosity=2)
