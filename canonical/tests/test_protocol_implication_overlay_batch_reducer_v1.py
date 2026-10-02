import json
from pathlib import Path
import unittest
from canonical.runtime.protocol_implication_overlay_batch_reducer_v1 import reduce_with_overlays

ROOT=Path(__file__).resolve().parents[2]
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    def run_current(self, manifest=None):
        return reduce_with_overlays(
            load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"),
            load("canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"),
            load("canonical/verification/OPUS55_BRAIN_WITNESS_CONTAMINATION_ADMISSIBILITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            manifest or load("canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_MANIFEST_V1.json"),
            root=ROOT)

    def test_current_synthesis_overlay(self):
        out=self.run_current()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertEqual(out["target_count"],11,out)
        self.assertEqual(out["base_pair_count"],99,out)
        self.assertEqual(out["verified_overlay_pair_count"],1,out)
        self.assertEqual(out["total_pair_count"],100,out)
        self.assertEqual(out["improved_target_count"],1,out)
        self.assertEqual(out["closed_target_count"],0,out)
        rows={r["predicate_id"]:r for r in out["target_results"]}
        syn=rows["SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"]
        self.assertEqual(syn["best_current_source_kind"],"VERIFIED_OVERLAY",syn)
        self.assertEqual(syn["best_current_source_id"],"SYNTHESIS_RESIDUAL_V2",syn)
        self.assertTrue(syn["best_current_scope_relation_missing"],syn)
        self.assertEqual(syn["best_current_missing_atoms"],["metric:matched_quality"],syn)
        self.assertEqual(syn["best_current_failed_metrics"],["matched_quality_noninferiority","required_claim_coverage_noninferiority"],syn)
        self.assertEqual(syn["current_best_hole_score"],[1,1,2],syn)
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_blob_mutation_fails_closed(self):
        manifest=load("canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_MANIFEST_V1.json")
        manifest["overlays"][0]["input"]["git_blob_sha"]="0"*40
        out=self.run_current(manifest)
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertTrue(any("OVERLAY_BLOB_MISMATCH" in x for x in out["errors"]),out)

    def test_scope_falsification_cannot_be_erased(self):
        manifest=load("canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_MANIFEST_V1.json")
        manifest["overlays"][0]["expected"]["missing_scope_relation"]=False
        out=self.run_current(manifest)
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertIn("OVERLAY_SCOPE_RESIDUAL_MISMATCH:SYNTHESIS_RESIDUAL_V2",out["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
