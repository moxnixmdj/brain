from __future__ import annotations
import copy, hashlib, json, unittest
from pathlib import Path

from canonical.runtime.witness_target_binding_totalizer_v2 import evaluate

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def git_blob_sha(rel):
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

TARGETS="canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V2.json"
VERIFY="canonical/verification/OPUS55_MATCHED_TARGET_NORMALIZATION_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json"
WITNESSES="canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"

class WitnessTargetBindingTotalizerV2Tests(unittest.TestCase):
    def docs(self):
        return load(TARGETS),load(VERIFY),load(WITNESSES),git_blob_sha(TARGETS)

    def test_current_13_by_9_surface_totalizes_to_117_holes(self):
        out=evaluate(*self.docs())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["target_count"],13)
        self.assertEqual(out["witness_count"],9)
        self.assertEqual(out["pair_count"],117)
        self.assertEqual(out["target_atom_occurrence_count"],62)
        self.assertEqual(out["target_metric_occurrence_count"],13)
        self.assertEqual(out["direct_atom_binding_count"],0)
        self.assertEqual(out["direct_metric_binding_count"],0)
        self.assertFalse(out["semantic_implication_verified"])
        target_ids={p["target_predicate_id"] for p in out["pairs"]}
        self.assertIn("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",target_ids)
        self.assertIn("DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",target_ids)
        self.assertTrue(all(not p["bound_atoms"] and not p["bound_metrics"] for p in out["pairs"]))
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_target_provenance_must_match_independent_receipt(self):
        targets,verify,witnesses,sha=self.docs()
        verify=copy.deepcopy(verify)
        verify["exact_brain_blobs"][TARGETS]="bad"
        out=evaluate(targets,verify,witnesses,sha)
        self.assertFalse(out["pass"])
        self.assertIn("TARGET_PROVENANCE_BLOB_NOT_INDEPENDENTLY_VERIFIED",out["errors"])

    def test_target_verification_counts_must_match_v2_frontier(self):
        targets,verify,witnesses,sha=self.docs()
        verify=copy.deepcopy(verify)
        verify["projection"]["verified_target_count"]=12
        out=evaluate(targets,verify,witnesses,sha)
        self.assertFalse(out["pass"])
        self.assertIn("TARGET_VERIFICATION_COUNT_MISMATCH",out["errors"])

    def test_witness_catalog_must_remain_zero_semantic(self):
        targets,verify,witnesses,sha=self.docs()
        witnesses=copy.deepcopy(witnesses)
        witnesses["witnesses"][0]["normalized_target_atoms"]=["metric:terminal_success"]
        out=evaluate(targets,verify,witnesses,sha)
        self.assertFalse(out["pass"])
        self.assertTrue(any("POSITIVE_SEMANTIC_BINDING_FORBIDDEN_IN_V1" in e for e in out["errors"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
