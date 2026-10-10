from __future__ import annotations
import json
import unittest
from canonical.runtime import current_escape_o_objective_acceptance_v1 as o

class CurrentEscapeOObjectiveAcceptanceTests(unittest.TestCase):
    def test_current_o_rows_are_covered_by_frozen_scope_lift_theorem(self):
        out=o.evaluate_current()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["current_o_count"], 11)
        self.assertEqual(out["current_q_count"], 2)
        self.assertEqual(out["missing_from_frozen_o_theorem"], [])
        self.assertTrue(out["shared_o_acceptance_law_bound"])
        self.assertFalse(out["all_current_o_rows_closed"])
        self.assertEqual(len(out["open_o_rows"]), 11)

    def test_tampered_unknown_o_row_fails_closed(self):
        manifest={
            "rows":[{"obligation_id":"UNKNOWN_O"}]
        }
        oq={"reduction":{"current_frontier_row_count":1,"Q_rows":[],"O_OBJECTIVE_ACCEPTANCE":1,"Q_QUALITATIVE_RELATIVE_ORDER":0,"mixed":0,"unclassified":0}}
        frozen={"current_O_obligations":["KNOWN_O"],"theorem":{"statement":"x"},"proof_schema":{"common_required":["a"]}}
        out=o.evaluate(manifest,oq,frozen)
        self.assertFalse(out["pass"])
        self.assertIn("UNKNOWN_O",out["missing_from_frozen_o_theorem"])

    def test_governance_projects_shared_o_law_without_row_credit(self):
        root=o.ROOT
        activation=json.loads((root/"canonical/governance/ESCAPE_O_OBJECTIVE_ACCEPTANCE_SHARED_LAW_ACTIVATION_20261010_V1.json").read_text())
        current=json.loads((root/"canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json").read_text())
        self.assertTrue(activation["current_frontier"]["all_current_o_rows_in_frozen_theorem_universe"])
        self.assertEqual(activation["current_frontier"]["current_o_row_acceptance_closed_count"],0)
        self.assertTrue(current["objective_acceptance_shared_law"]["shared_law_bound"])
        self.assertEqual(current["objective_acceptance_shared_law"]["current_o_row_acceptance_closed_count"],0)
        self.assertIn("NO_CURRENT_O_ROW_ACCEPTANCE_CLOSURE__SHARED_O_IMPLICATION_ONLY",current["hard_nonclaims"])


    def test_activation_content_addresses_exact_runtime_and_test_bytes(self):
        root=o.ROOT
        activation=json.loads((root/"canonical/governance/ESCAPE_O_OBJECTIVE_ACCEPTANCE_SHARED_LAW_ACTIVATION_20261010_V1.json").read_text())
        runtime_path=root/activation["runtime"]["path"]
        test_path=root/activation["tests"]["path"]
        self.assertEqual(o._git_blob_sha_bytes(runtime_path.read_bytes()),activation["runtime"]["git_blob_sha"])
        self.assertEqual(o._git_blob_sha_bytes(test_path.read_bytes()),activation["tests"]["git_blob_sha"])

if __name__=="__main__":
    unittest.main(verbosity=2)
