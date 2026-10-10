from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import coverage_cc_r1_professional_r12_semantic_reality_containment_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]
def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))

class R12SemanticCCR1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=load(v.MANIFEST_PATH);cls.frozen=load(v.CLAIM_PATH);cls.cert=load(v.CERT_PATH)
        cls.dv=load(v.DOMAIN_VERIFY_PATH);cls.sv=load(v.SCOPE_BATCH_VERIFY_PATH)
        cls.ia=load(v.IDENTITY_ACTIVATION_PATH);cls.iv=load(v.IDENTITY_VERIFY_PATH)
    def run_eval(self,**overrides):
        args={"manifest":deepcopy(self.manifest),"frozen":deepcopy(self.frozen),"certificate":deepcopy(self.cert),
              "domain_verification":deepcopy(self.dv),"scope_batch_verification":deepcopy(self.sv),
              "identity_activation":deepcopy(self.ia),"identity_verification":deepcopy(self.iv)}
        args.update(overrides);return v.evaluate_documents(**args)
    def test_real_current_claim_passes_cc_r1_only(self):
        out=v.verify();self.assertTrue(out["pass"],out);self.assertTrue(out["cc_r1_reality_containment_proved"])
        self.assertTrue(out["b_real_subseteq_b_plus"]);self.assertFalse(out["r12_semantic_property_truth_authority"]);self.assertFalse(out["terminal_authority"])
    def test_scope_narrowing_fails_closed(self):
        frozen=deepcopy(self.frozen);frozen["claim_scope"]["scope_definition"]["domain_definition"]["filters"]=["CONVENIENT_SUBSET"]
        self.assertFalse(self.run_eval(frozen=frozen)["pass"])
    def test_foreign_claim_id_fails_closed(self):
        cert=deepcopy(self.cert);cert["claim_id"]="0"*64;out=self.run_eval(certificate=cert)
        self.assertFalse(out["pass"]);self.assertIn("CERTIFICATE_CLAIM_MISMATCH",out["errors"])
    def test_identity_replay_must_be_current(self):
        iv=deepcopy(self.iv);iv["independent_replay"]["tests_passed"]=7;out=self.run_eval(identity_verification=iv)
        self.assertFalse(out["pass"]);self.assertIn("IDENTITY_INDEPENDENT_VERIFY_INVALID",out["errors"])
    def test_lossy_carrier_overclaim_fails_closed(self):
        cert=deepcopy(self.cert);cert["theorem"]["semantic_information_loss"]=True;out=self.run_eval(certificate=cert)
        self.assertFalse(out["pass"]);self.assertIn("THEOREM_BOUNDARY_DRIFT:semantic_information_loss",out["errors"])
    def test_property_truth_self_authority_fails_closed(self):
        cert=deepcopy(self.cert);cert["r12_semantic_property_truth_authority"]=True;out=self.run_eval(certificate=cert)
        self.assertFalse(out["pass"]);self.assertIn("CERTIFICATE_SELF_AUTHORITY_FORBIDDEN:r12_semantic_property_truth_authority",out["errors"])
    def test_catalog_completeness_cannot_be_required_as_proof(self):
        cert=deepcopy(self.cert);cert["theorem"]["catalog_completeness_required"]=True;out=self.run_eval(certificate=cert)
        self.assertFalse(out["pass"]);self.assertIn("THEOREM_BOUNDARY_DRIFT:catalog_completeness_required",out["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
