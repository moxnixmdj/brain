from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from canonical.runtime import p3_conditioned_policy_adequacy_registry_v1 as registry

POLICY = "BRAIN_VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_V1"
ROOT = Path(__file__).resolve().parents[2]
ATOMS = [
    "CODING_VISIBLE_ACCEPTANCE_CONTRACT_FINITE_V1",
    "CODING_VISIBLE_ACCEPTANCE_CHECKERS_TOTAL_V1",
    "CODING_VISIBLE_ACCEPTANCE_CONJUNCTION_SOUND_COMPLETE_V1",
    "CODING_VISIBLE_ACCEPTANCE_SOURCE_AUTHORIZED_V1",
    "CODING_VISIBLE_ACCEPTANCE_BUILDER_INDEPENDENT_V1",
    "CODING_VISIBLE_ACCEPTANCE_CHECK_BUDGET_SUFFICIENT_V1",
    "CODING_VISIBLE_ACCEPTANCE_PRETERMINAL_ADMISSIBLE_V1",
]


def condition():
    return {
        "op": "AND",
        "args": [{"op": "ATOM", "id": atom_id} for atom_id in ATOMS],
    }


class P3VisibleAcceptanceContractRegistryV1Tests(unittest.TestCase):
    def test_catalog_binds_verified_fifth_region(self):
        out = registry.catalog()
        self.assertEqual(out["policy_count"], 6)
        by_id = {row["policy_id"]: row for row in out["policies"]}
        self.assertIn(POLICY, by_id)
        self.assertEqual(by_id[POLICY]["condition"], condition())
        self.assertEqual(
            by_id[POLICY]["binding_path"],
            "canonical/governance/"
            "CODING_VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_POLICY_ADEQUACY_BINDING_20261009_V1.json",
        )
        self.assertEqual(
            by_id[POLICY]["binding_blob_sha"],
            "c8a1fff64da2bff4e8972c71c040b1920271fee6",
        )
        self.assertFalse(out["membership_self_certified"])

    def test_partial_condition_does_not_inject_policy(self):
        out = registry.augment_problem({"decision_basis": ATOMS[:-1]})
        self.assertTrue(out["pass"], out)
        self.assertNotIn(POLICY, out["injected_policy_ids"])
        skipped = {row["policy_id"]: row for row in out["skipped_registered_policies"]}
        self.assertIn(POLICY, skipped)
        self.assertEqual(
            skipped[POLICY]["missing_atoms"],
            ["CODING_VISIBLE_ACCEPTANCE_PRETERMINAL_ADMISSIBLE_V1"],
        )

    def test_all_seven_atoms_inject_exact_verified_binding_only(self):
        out = registry.augment_problem({"decision_basis": ATOMS})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["injected_policy_ids"], [POLICY])
        self.assertEqual(out["basis_eligible_policy_count"], 1)
        self.assertEqual(out["problem"]["policy_conditions"][POLICY], condition())
        binding = out["problem"]["policy_adequacy_bindings"][POLICY]
        self.assertEqual(
            binding,
            {
                "adequacy_certificate_path":
                    "canonical/governance/"
                    "CODING_VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json",
                "adequacy_certificate_blob_sha":
                    "74aaced12d62b61d3266a4705a022350a9c7103f",
                "independent_verification_path":
                    "canonical/verification/"
                    "CODING_VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_INDEPENDENT_VERIFICATION_20261009_V1.json",
                "independent_verification_blob_sha":
                    "18f6f017b3e0daf98dfbbff221e74661c8edb616",
            },
        )
        self.assertFalse(out["membership_self_certified"])
        self.assertNotIn(
            "CODING_VISIBLE_ACCEPTANCE_SOURCE_AUTHORIZED_V1",
            out["proved_condition_atom_ids"],
        )

    def test_registry_presence_never_creates_condition_truth(self):
        out = registry.augment_problem({"decision_basis": ATOMS})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["proved_condition_atom_ids"], [])
        self.assertFalse(out["registry_authority"])
        self.assertFalse(out["membership_self_certified"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_binding_references_exact_certificate_and_verification_blobs(self):
        binding_path = (
            ROOT / "canonical/governance/"
            "CODING_VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_POLICY_ADEQUACY_BINDING_20261009_V1.json"
        )
        binding = json.loads(binding_path.read_text(encoding="utf-8"))

        def blob(path: Path) -> str:
            data = path.read_bytes()
            h = hashlib.sha1()
            h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
            return h.hexdigest()

        cert_path = ROOT / binding["adequacy_certificate_path"]
        verify_path = ROOT / binding["independent_verification_path"]
        self.assertEqual(blob(binding_path), "c8a1fff64da2bff4e8972c71c040b1920271fee6")
        self.assertEqual(
            blob(cert_path),
            binding["adequacy_certificate_blob_sha"],
        )
        self.assertEqual(
            blob(verify_path),
            binding["independent_verification_blob_sha"],
        )
        self.assertEqual(
            binding["adequacy_certificate_blob_sha"],
            "74aaced12d62b61d3266a4705a022350a9c7103f",
        )
        self.assertEqual(
            binding["independent_verification_blob_sha"],
            "18f6f017b3e0daf98dfbbff221e74661c8edb616",
        )

    def test_binding_drift_fails_closed(self):
        mutated = copy.deepcopy(registry._REGISTRY)
        mutated[POLICY]["binding_blob_sha"] = "0" * 40
        original = registry._REGISTRY
        try:
            registry._REGISTRY = mutated
            out = registry.augment_problem({"decision_basis": ATOMS})
        finally:
            registry._REGISTRY = original
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "REGISTERED_POLICY_ADEQUACY_BINDING_INVALID",
        )
        self.assertIn("REGISTERED_BINDING_DRIFT", out["detail"]["binding_error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
