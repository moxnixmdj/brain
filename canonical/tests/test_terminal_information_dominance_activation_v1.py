import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def git_blob_sha(rel):
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class Tests(unittest.TestCase):
    def test_verified_activation_and_parent_pointers(self):
        receipt = load("canonical/verification/TERMINAL_INFORMATION_DOMINANCE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        activation = load("canonical/governance/TERMINAL_CERTIFICATE_CUT_ACTIVATION_V3.json")
        optimizer = load("canonical/governance/EXECUTION_FIRST_SELF_PROVING_OPTIMIZER_V1.json")
        authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")

        self.assertTrue(receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"), receipt)
        for rel, expected in receipt["exact_brain_blobs"].items():
            self.assertEqual(git_blob_sha(rel), expected, rel)

        frontier_rel = activation["frontier"]["path"]
        self.assertEqual(git_blob_sha(frontier_rel), activation["frontier"]["git_blob_sha"])
        self.assertTrue(activation["status"].startswith("ACTIVE_INDEPENDENT_PASS"), activation)
        self.assertEqual(activation["capability_credit_delta"], 0)
        self.assertEqual(activation["family_credit_delta"], 0)
        self.assertFalse(activation["execution_authority"])
        self.assertFalse(activation["promotion_authority"])

        self.assertEqual(
            optimizer["reality_query_admission"]["terminal_certificate_cut_activation"],
            "canonical/governance/TERMINAL_CERTIFICATE_CUT_ACTIVATION_V3.json",
        )
        self.assertEqual(
            optimizer["terminal_certificate_cut"]["frontier"],
            "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V3.json",
        )
        self.assertEqual(
            optimizer["terminal_certificate_cut"]["frontier_git_blob_sha"],
            "106139ff69616670993dbc6af324d8686747e8b1",
        )
        self.assertEqual(
            optimizer["information_dominance"]["verification"],
            "canonical/verification/TERMINAL_INFORMATION_DOMINANCE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
        )

        self.assertEqual(authority["truth"]["opus55_acceptance"], "2/19_PASS__17/19_OPEN")
        self.assertFalse(authority["truth"]["achieved"])
        self.assertTrue(
            authority["sources"]["terminal_information_dominance"]["status"].startswith(
                "INDEPENDENT_PUBLIC_RUNNER_PASS"
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
