from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from canonical.runtime.brain_witness_normalization_verifier_v1 import evaluate, git_blob_sha

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
NORMALIZED=ROOT/"canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"

class WitnessNormalizationTests(unittest.TestCase):
    def docs(self):
        s=json.loads(SOURCE.read_text())
        n=json.loads(NORMALIZED.read_text())
        return s,n,git_blob_sha(SOURCE)

    def test_live_passes(self):
        s,n,sha=self.docs()
        out=evaluate(s,n,sha)
        self.assertTrue(out["pass"],out)
        expected = sum(1 for x in s["claims"] if x.get("state") == "PROVED")
        self.assertEqual(out["witness_count"], expected)
        self.assertFalse(out["semantic_implication_verified"])

    def test_target_atom_inference_fails(self):
        s,n,sha=self.docs()
        n=copy.deepcopy(n)
        n["witnesses"][0]["normalized_target_atoms"]=["dimension:invented"]
        out=evaluate(s,n,sha)
        self.assertFalse(out["pass"])
        self.assertIn("NORMALIZED_WITNESSES_NOT_EXACT_RECOMPUTATION",out["errors"])

    def test_stale_source_sha_fails(self):
        s,n,sha=self.docs()
        n=copy.deepcopy(n)
        n["authority"]["evidence_bindings"]["git_blob_sha"]="bad"
        out=evaluate(s,n,sha)
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_BLOB_AUTHORITY_MISMATCH",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
