from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

INTENT = ROOT / "canonical/action_intents/ESCAPE_GAP_A_POLICY_COVER_ADAPTER_ACTION_INTENT_20261010_V2.json"
ACTIVATION = ROOT / "canonical/governance/ESCAPE_GAP_A_POLICY_COVER_ADAPTER_ACTIVATION_20261010_V1.json"
BINDING = ROOT / "canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V6.json"
VERIFY = ROOT / "canonical/verification/ESCAPE_GAP_A_POLICY_COVER_ADAPTER_VERIFY_20261010_V1.json"
OQ = ROOT / "canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class GapAPolicyCoverAdapterActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.intent = load(INTENT)
        cls.activation = load(ACTIVATION)
        cls.binding = load(BINDING)
        cls.verify = load(VERIFY)
        cls.oq = load(OQ)

    def test_exact_runtime_test_and_verification_bindings(self):
        self.assertEqual(
            self.activation["runtime"]["git_blob_sha"],
            blob(ROOT / self.activation["runtime"]["path"]),
        )
        self.assertEqual(
            self.activation["tests"]["git_blob_sha"],
            blob(ROOT / self.activation["tests"]["path"]),
        )
        self.assertEqual(
            self.activation["verification"]["git_blob_sha"],
            blob(ROOT / self.activation["verification"]["path"]),
        )
        self.assertEqual(self.verify["independent_verification"]["total_test_functions_passed"], 52)

    def test_v6_preserves_current_frontier_counts_and_zero_row_credit(self):
        self.assertIn("10_ACQUISITION_3_INTERNAL_PROGRESS", self.binding["status"])
        adapter = self.binding["gap_a_policy_cover_adapter"]
        self.assertEqual(adapter["gap_a_rows"], 10)
        self.assertEqual(adapter["real_gap_a_row_proofs"], 0)
        self.assertEqual(self.activation["current_frontier_effect"]["gap_a_rows"], 10)
        self.assertEqual(self.activation["current_frontier_effect"]["real_row_proofs_after"], 0)
        self.assertEqual(self.binding["accounting"]["terminal_credit_delta"], 0)

    def test_oq_reduction_is_primary_research_compression(self):
        relation = self.binding["relation_to_current_oq_frontier"]
        self.assertEqual(
            relation["current_reduction_path"],
            "canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json",
        )
        self.assertTrue(self.oq["status"].startswith("CURRENT_13_ESCAPE_ACCEPTANCE_FRONTIER_EXECUTABLY_REDUCED_TO_O11_Q2"))
        self.assertEqual(self.oq["reduction"]["O_OBJECTIVE_ACCEPTANCE"], 11)
        self.assertEqual(self.oq["reduction"]["Q_QUALITATIVE_RELATIVE_ORDER"], 2)
        self.assertIn(
            "ATTACK_SHARED_O_AND_Q_ACCEPTANCE_LAWS_FIRST_PER_CURRENT_OQ_FRONTIER_REDUCTION",
            self.binding["execution_order"],
        )
        self.assertIn("NO_O_OR_Q_ACCEPTANCE_LAW_CREDIT_FROM_ADAPTER_EXISTENCE", self.binding["hard_nonclaims"])

    def test_current_generation_lease_revalidated_after_oq_update(self):
        self.assertEqual(
            self.intent["concurrent_frontier_update"]["git_blob_sha"],
            blob(OQ),
        )
        self.assertTrue(
            self.intent["currentness_revalidation"]["all_load_bearing_dependency_blobs_unchanged"]
        )
        self.assertEqual(self.intent["verification"]["git_blob_sha"], blob(VERIFY))
        self.assertEqual(self.intent["verification"]["exact_test_total"], 52)

    def test_adapter_is_realization_bridge_not_acceptance_closure(self):
        self.assertEqual(
            self.intent["recursive_obs"]["adapter_role"],
            "REALIZATION_BRIDGE",
        )
        self.assertFalse(
            self.activation["current_frontier_effect"]["private_acquisition_authorized_by_adapter"]
        )
        self.assertIn("NO_O_OR_Q_CLOSURE", self.intent["hard_nonclaims"])
        self.assertIn("NO_REAL_GAP_A_ROW_PROOF_CREDIT", self.intent["hard_nonclaims"])
        for key in (
            "row_credit_delta",
            "capability_credit_delta",
            "acceptance_credit_delta",
            "ownership_credit_delta",
            "terminal_credit_delta",
        ):
            self.assertEqual(self.intent["accounting"][key], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
