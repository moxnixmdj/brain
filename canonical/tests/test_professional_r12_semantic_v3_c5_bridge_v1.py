from copy import deepcopy
import unittest
from canonical.runtime import professional_r12_semantic_v3_c5_bridge_v1 as v
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3
from canonical.runtime import professional_r12_semantic_c5_claim_bound_verify_v1 as c5

def docs():
    return pack_v3.verify(), c5.verify()

def r12(pack):
    return next(x for x in pack["claims"] if x["leaf_id"]==v.LEAF_ID)

class Tests(unittest.TestCase):
    def test_current_v3_r12_reuses_only_exact_scope_c5(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["c5_coverage_accounting_proved_for_v3_claim"])
        self.assertFalse(out["source_v2_property_authority_transported"])
        self.assertFalse(out["cc_r3_terminal_closure_proved"])
        self.assertFalse(out["semantic_property_truth_authority"])

    def test_v3_claim_id_drift_fails_closed(self):
        p,c=docs(); d=deepcopy(p); r12(d)["frozen_claim"]["claim_id"]="0"*64
        out=v.evaluate(d,c)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"V3_R12_CLAIM_ID_DRIFT")

    def test_scope_claim_id_drift_fails_closed(self):
        p,c=docs(); d=deepcopy(p); r12(d)["whole_leaf_scope_claim_id"]="0"*64
        out=v.evaluate(d,c)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"WHOLE_LEAF_SCOPE_CLAIM_ID_DRIFT")

    def test_scope_digest_drift_fails_closed(self):
        p,c=docs(); d=deepcopy(p); r12(d)["scope_definition_sha256"]="0"*64
        out=v.evaluate(d,c)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"ROW_SCOPE_DIGEST_DRIFT")

    def test_v2_property_authority_transport_is_forbidden(self):
        p,c=docs(); d=deepcopy(p); r12(d)["source_v2_claim_authority_transported"]=True
        out=v.evaluate(d,c)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"V2_PROPERTY_AUTHORITY_TRANSPORT_FORBIDDEN")

    def test_prior_c5_failure_fails_closed(self):
        p,c=docs(); c=deepcopy(c); c["pass"]=False
        out=v.evaluate(p,c)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"PRIOR_C5_VERIFICATION_NOT_PASS")

if __name__=="__main__":
    unittest.main(verbosity=2)
