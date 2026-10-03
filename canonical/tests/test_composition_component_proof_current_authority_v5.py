from __future__ import annotations
import json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

class CompositionCurrentAuthorityV5Tests(unittest.TestCase):
    def test_current_component_authority_is_exact_three_of_twelve(self):
        a=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V5.json")
        t=a["truth"]
        self.assertEqual(t["frozen_interface_count"],12)
        self.assertEqual(t["current_admissible_scoped_proved"],3)
        self.assertEqual(t["current_open"],9)
        self.assertEqual(t["current_scoped_proved_components"],["memory","recovery","delegation"])
        self.assertFalse(t["parent_composition_predicate_closed"])
        self.assertEqual(t["strict_opus55_acceptance_delta"],0)

    def test_authority_binds_independent_v5_slice(self):
        a=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V5.json")
        s=load("canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_PUBLIC_RUNNER_VERIFICATION_20261003_V5.json")
        self.assertTrue(s["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"))
        self.assertEqual(s["verified"]["scoped_proved_count"],3)
        self.assertEqual(s["verified"]["open_count"],9)
        self.assertEqual(s["verified"]["scoped_proved_components"],["memory","recovery","delegation"])
        self.assertEqual(a["current_slice"]["verification_git_blob_sha"],"4115b5ee386a0258dfcbfe14d68129d836c1f2a5")

    def test_terminal_authority_projects_three_of_twelve_without_acceptance_credit(self):
        t=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        self.assertEqual(t["truth"]["opus55_acceptance"],"4/19_PASS__15/19_OPEN")
        self.assertFalse(t["truth"]["achieved"])
        self.assertEqual(t["integrator_reconciliation_20261002_current"]["composition"],
            "3_OF_12_CURRENTLY_ADMISSIBLE__MEMORY_RECOVERY_AND_DELEGATION_SCOPED_PROVED__9_OPEN__PARENT_OPEN")
        self.assertIn("FROZEN_COMPOSITION_COMPONENT_INTERFACES__3_OF_12_CURRENTLY_ADMISSIBLE__MEMORY_RECOVERY_AND_DELEGATION_CURRENT_SOURCE_SCOPED_PROVED__9_OPEN__PARENT_OPEN__ZERO_CREDIT",t["residual"])
        self.assertIn("COMPOSITION_CURRENT_SLICE_V5_RECEIPT_DERIVED__MEMORY_RECOVERY_AND_DELEGATION_SCOPED_PROVED__9_COMPONENT_INTERFACES_OPEN__HISTORICAL_QUARANTINED_RECEIPTS_NOT_REUSED__PARENT_OPEN",t["residual"])
        self.assertNotIn("FROZEN_COMPOSITION_COMPONENT_INTERFACES__2_OF_12_CURRENTLY_ADMISSIBLE__MEMORY_AND_DELEGATION_CURRENT_SOURCE_SCOPED_PROVED__10_OPEN__PARENT_OPEN__ZERO_CREDIT",t["residual"])

    def test_no_parent_or_execution_authority(self):
        a=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V5.json")
        self.assertFalse(a["execution_authority"])
        self.assertFalse(a["promotion_authority"])
        self.assertEqual(a["capability_credit_delta"],0)
        self.assertEqual(a["family_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
