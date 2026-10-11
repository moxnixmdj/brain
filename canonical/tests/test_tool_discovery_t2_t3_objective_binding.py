from __future__ import annotations
import hashlib,json,unittest
from pathlib import Path

from canonical.runtime import tool_discovery_information_safe_proof_v2 as proof
from canonical.runtime import tool_discovery_information_safe_candidate as candidate

ROOT=Path(__file__).resolve().parents[2]
BIND=ROOT/"canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"

def git_blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

class ToolDiscoveryObjectiveBindingTests(unittest.TestCase):
    def binding(self):
        return json.loads(BIND.read_text(encoding="utf-8"))

    def test_exact_bound_blobs_match(self):
        b=self.binding()
        for row in b["exact_bound_blobs"].values():
            path=ROOT/row["path"]
            self.assertTrue(path.is_file(),row["path"])
            self.assertEqual(git_blob_sha(path),row["blob_sha"],row["path"])

    def test_route_gates_frozen_except_verification_bit(self):
        g=self.binding()["route_gates"]
        for k in (
            "candidate_package_frozen","executable_evaluator_bound",
            "population_or_source_pool_frozen","information_boundary_frozen",
            "post_freeze_selector_frozen","terminal_parent_binding_frozen"
        ):
            self.assertIs(g[k],True,k)
        self.assertIs(g["independent_verification_pass"],False)

    def test_information_boundary_keeps_hidden_truth_hidden(self):
        b=self.binding()
        hidden=set(b["information_boundary"]["hidden_from_candidate"])
        self.assertIn("ACTUAL_TOOL_CAPABILITY_MATRIX",hidden)
        self.assertIn("LEAST_COST_CAPABLE_ROUTE",hidden)
        self.assertIs(b["information_boundary"]["candidate_receives_hidden_oracle"],False)

    def test_population_covers_every_declared_class(self):
        b=self.binding()
        classes=b["source_pool"]["class_cycle"]
        n=b["source_pool"]["terminal_sample_count"]
        self.assertEqual(n,180)
        seen={proof.generate_case(917,ordinal)["case_class"] for ordinal in range(n)}
        self.assertEqual(seen,set(classes))

    def test_frozen_candidate_passes_180_case_preterminal_population(self):
        out=proof.run_batch(917,180,candidate.next_action)
        self.assertTrue(out["all_pass"],out["failures"][:5])
        self.assertEqual(out["passed"],180)
        self.assertEqual(out["failed"],0)
        self.assertEqual(set(out["by_class"]),set(self.binding()["source_pool"]["class_cycle"]))

    def test_no_terminal_or_promotion_authority(self):
        b=self.binding()
        self.assertIs(b["execution_authority"],False)
        self.assertIs(b["promotion_authority"],False)
        self.assertEqual(b["terminal_results_observed"],0)
        self.assertEqual(b["fresh_terminal_evidence_consumed"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
