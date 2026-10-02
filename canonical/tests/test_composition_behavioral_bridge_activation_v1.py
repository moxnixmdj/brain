from __future__ import annotations
import copy, json, unittest
from pathlib import Path

from canonical.runtime.composition_behavioral_bridge_activation_verifier_v1 import evaluate, git_blob_sha

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
TRANS=ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json"
MAN=ROOT/"canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"
BRIDGE=ROOT/"canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json"
PUB=ROOT/"canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
BASE=ROOT/"canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json"
ACT=ROOT/"canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_V1.json"

def load(p):
    return json.loads(p.read_text())

class ActivationTests(unittest.TestCase):
    def docs(self):
        return (
            load(REG),load(TRANS),load(MAN),load(BRIDGE),load(PUB),load(BASE),load(ACT),
            {"bridge":git_blob_sha(BRIDGE),"public_verify":git_blob_sha(PUB),"baseline":git_blob_sha(BASE)}
        )

    def test_live_exact_two_receipts_reduce_to_ten_open(self):
        out=evaluate(*self.docs())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["activated_receipt_count"],2)
        self.assertEqual(out["activated_components"],["delegation","tool discovery"])
        self.assertEqual(out["open_component_interface_count"],10)
        self.assertFalse(out["parent_predicate_closed"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_invented_third_receipt_fails(self):
        docs=list(self.docs())
        act=copy.deepcopy(docs[6])
        act["receipts"].append({
            "receipt_id":"INVENTED",
            "component_id":"memory",
            "interface_id":"browser/computer action+memory+recovery",
            "proved_properties":["SCOPED_ACCEPTANCE_PROOF"],
            "verified":True,"independent":True,"contamination_clean":True,
            "acceptance_scoped":True,
            "binds_frozen_claim":"MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"
        })
        docs[6]=act
        out=evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn("ACTIVATION_RECEIPTS_NOT_EXACT_TRANSLATION",out["errors"])

    def test_unmerged_public_verification_fails(self):
        docs=list(self.docs())
        pub=copy.deepcopy(docs[4])
        pub["public_runner"]["merge_commit"]=None
        docs[4]=pub
        out=evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn("PUBLIC_RUNNER_NOT_SUCCESSFULLY_MERGED",out["errors"])

    def test_wrong_bridge_blob_fails(self):
        docs=list(self.docs())
        pub=copy.deepcopy(docs[4])
        pub["exact_brain_blobs"]["canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json"]="bad"
        docs[4]=pub
        out=evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn("PUBLIC_VERIFICATION_BRIDGE_BLOB_MISMATCH",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
