import hashlib
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def git_blob_sha(rel):
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

class TestR2DomainMappingAuthorityReconciliationV1(unittest.TestCase):
    def test_exact_domain_mapping_bytes_match_reconciliation(self):
        rec = load("canonical/governance/R2_PROOF_CARRYING_DOMAIN_MAPPING_RECONCILIATION_20261009_V1.json")
        for key in ("producer", "truth_certificate", "semantic_truth_dispatch", "p3_consumer"):
            row = rec["exact_verified_route"][key]
            self.assertEqual(git_blob_sha(row["path"]), row["git_blob_sha"])
        ver = rec["exact_verified_route"]["independent_verification"]
        self.assertEqual(git_blob_sha(ver["path"]), ver["git_blob_sha"])
        self.assertEqual(ver["focused_checks"], "62_OF_62_PASS")

    def test_v46_preserves_fail_closed_open_world_boundary(self):
        sched = load("canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V46.json")
        self.assertEqual(sched["live_mechanism"]["direct_adequacy_route_count"], 31)
        self.assertEqual(sched["live_mechanism"]["direct_adequacy_bounded_family_count"], 28)
        mapping = sched["live_mechanism"]["proof_carrying_domain_mapping"]
        self.assertFalse(mapping["open_world_ontology_completeness_claimed"])
        self.assertEqual(mapping["verified_focused_checks"], "62_OF_62_PASS")
        fin = sched["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        ids = {row["id"] for row in fin["verified_positive_subregions"]}
        self.assertIn("SCOPED_PROOF_CARRYING_DOMAIN_MAPPING_WITH_INDEPENDENT_DECISION_RELEVANT_SEMANTIC_COMPLETENESS", ids)
        self.assertIn("OPEN_WORLD_ONTOLOGY", fin["remaining_boundary"])
        self.assertFalse(fin["proof_carrying_domain_mapping"]["open_world_ontology_closed"])
        self.assertEqual(sched["accounting"]["terminal_credit_delta"], 0)

    def test_current_r2_projects_v46_exactly(self):
        cur = load("canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json")
        sched_path = cur["scheduler_cut"]["path"]
        self.assertEqual(sched_path, "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V46.json")
        self.assertEqual(git_blob_sha(sched_path), cur["scheduler_cut"]["git_blob_sha"])
        self.assertIn("V46", cur["status"])
        self.assertFalse(cur["proof_carrying_domain_mapping_frontier"]["open_world_ontology_mapping_closed"])
        self.assertEqual(cur["scheduler_result"]["primary_cell"], "FINANCE_SEMANTIC_ADEQUACY_TAIL")

    def test_terminal_projection_preserves_terminal_false(self):
        term = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY.json")
        self.assertEqual(term["live_truth"]["current_r2_scheduler_cut"], "ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V46")
        self.assertTrue(term["live_truth"]["r2_proof_carrying_domain_mapping_bound"])
        self.assertFalse(term["live_truth"]["r2_proof_carrying_domain_mapping_open_world_ontology_closed"])
        self.assertEqual(term["live_truth"]["r2_primary_internal_unsolved_count"], 1)
        self.assertEqual(term["live_truth"]["r2_primary_internal_unsolved_cell"], "FINANCE_SEMANTIC_ADEQUACY_TAIL")
        self.assertFalse(term["live_truth"]["terminal"])

    def test_one_shot_projection_matches_current_r2(self):
        one = load("canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json")
        cur = load("canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json")
        t = one["terminal_truth_frontier_reconciliation"]
        self.assertEqual(t["current_r2_version"], "V46")
        self.assertEqual(t["current_r2_pointer_git_blob_sha"], git_blob_sha("canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"))
        self.assertEqual(t["current_r2_scheduler_git_blob_sha"], cur["scheduler_cut"]["git_blob_sha"])
        self.assertEqual(t["current_r2_direct_route_count"], 31)
        self.assertEqual(t["current_r2_bounded_family_count"], 28)
        self.assertTrue(t["current_r2_proof_carrying_domain_mapping_bound"])
        self.assertEqual(t["current_r2_remaining_problem_class"], cur["remaining_problem_class"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
