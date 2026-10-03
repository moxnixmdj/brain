from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from canonical.runtime import universal_learning_contract_v1 as contract

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "canonical/governance/UNIVERSAL_LEARNING_CONTRACT_V1.json"


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class UniversalLearningContractBindingV1Tests(unittest.TestCase):
    def test_every_bound_component_matches_exact_blob(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        for rel, expected in gov["exact_bound_components"].items():
            with self.subTest(path=rel):
                self.assertEqual(blob_sha(ROOT / rel), expected)

    def test_governance_nonclaims_preserve_empirical_residual(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        dec = gov["target_acceptance_decomposition"]
        self.assertEqual(dec["target_predicate"], "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        self.assertEqual(dec["current_state"], "OPEN")
        self.assertEqual(
            dec["remaining_irreducible_question"],
            "MATCHED_EMPIRICAL_LEARNING_EFFECTIVENESS_NONINFERIORITY",
        )
        self.assertEqual(dec["acceptance_credit_before_empirical_and_separate_reducer"], 0)
        self.assertIn(
            "NO_FINITE_SAMPLE_TO_OPEN_WORLD_SUCCESS_INFERENCE",
            gov["hard_nonclaims"],
        )

    def test_runtime_theorem_matches_governance_boundary(self):
        out = contract.prove_control_invariants()
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["semantic_success_rate_proved"])
        self.assertFalse(out["tool_learning_noninferiority_proved"])
        self.assertEqual(out["acceptance_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
