from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_r10_execution_property_truth_gate_v1 as gate

ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text())

MANIFEST="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json"
SCOPE="canonical/verification/PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_V2_GATE_VERIFY_20261010_V1.json"
CHALLENGE="canonical/verification/PROFESSIONAL_QUALITY_R10_EXECUTION_PROPERTY_CHALLENGE_VERIFY_20261010_V1.json"

class Tests(unittest.TestCase):
    def docs(self): return load(MANIFEST),load(SCOPE),load(CHALLENGE)
    def test_exact_chain_closes_only_r10_execution_leaf(self):
        m,s,c=self.docs(); out=gate.evaluate(leaf_manifest=m,scope_verification=s,challenge_verification=c)
        self.assertTrue(out["pass"],out); self.assertTrue(out["leaf_property_truth_authority"])
        self.assertTrue(out["global_leaf_closed"]); self.assertFalse(out["root_closed"])
        self.assertFalse(out["domain_execution_closure"]); self.assertFalse(out["quality_authority"]); self.assertFalse(out["terminal_authority"])
    def test_scope_not_ready_fails_closed(self):
        m,s,c=self.docs(); s=deepcopy(s); s["consequence"]["property_truth_ready"]=False
        self.assertEqual(gate.evaluate(leaf_manifest=m,scope_verification=s,challenge_verification=c)["reason"],"PROPERTY_TRUTH_READY_REQUIRED")
    def test_same_carrier_twice_fails_independence(self):
        m,s,c=self.docs(); c=deepcopy(c); c["replay"][1]["carrier_id"]=c["replay"][0]["carrier_id"]
        self.assertEqual(gate.evaluate(leaf_manifest=m,scope_verification=s,challenge_verification=c)["reason"],"REPLAY_INDEPENDENCE_REQUIRED")
    def test_missing_adversarial_coverage_fails_closed(self):
        m,s,c=self.docs(); c=deepcopy(c); c["observed_case_coverage"]["all_known_r10_defeaters_blocked"]=False
        self.assertEqual(gate.evaluate(leaf_manifest=m,scope_verification=s,challenge_verification=c)["reason"],"REQUIRED_CASE_COVERAGE_MISSING")
    def test_claim_substitution_fails_closed(self):
        m,s,c=self.docs(); c=deepcopy(c); c["claim_id"]="0"*64
        self.assertEqual(gate.evaluate(leaf_manifest=m,scope_verification=s,challenge_verification=c)["reason"],"CHALLENGE_VERIFICATION_IDENTITY_MISMATCH")
    def test_open_world_nonclaim_is_load_bearing(self):
        m,s,c=self.docs(); c=deepcopy(c); c["hard_nonclaims"]=[x for x in c["hard_nonclaims"] if x!="NO_CLAIM_ALL_CONCEIVABLE_DEFEATERS_ARE_ENUMERATED"]
        self.assertEqual(gate.evaluate(leaf_manifest=m,scope_verification=s,challenge_verification=c)["reason"],"OPEN_WORLD_NONCLAIM_REQUIRED")

if __name__=="__main__": unittest.main(verbosity=2)
