import hashlib
import unittest

from canonical.runtime.hle_exact_commit_semantic_certificate_v1 import (
    POPULATION_SIZE,
    TARGET_NUMERATOR,
    TOTAL_SLOTS,
    TRIALS,
    score_exact_commitments,
)


def h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class HLEExactCommitCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.refs = [{"id": f"q{i}", "answer": f"a{i}"} for i in range(POPULATION_SIZE)]

    def full(self):
        return [
            {
                "id": f"q{i}",
                "trial": trial,
                "final_answer": f"a{i}",
                "final_answer_sha256": h(f"a{i}"),
            }
            for trial in range(1, TRIALS + 1)
            for i in range(POPULATION_SIZE)
        ]

    def test_exact_identity_only(self):
        rows = self.full()
        rows[0]["final_answer"] = " a0"
        rows[0]["final_answer_sha256"] = h(" a0")
        r = score_exact_commitments(rows, self.refs)
        self.assertEqual(r["correct_exact_gold_identities"], TOTAL_SLOTS - 1)

    def test_commit_hash_is_mandatory(self):
        rows = self.full()
        rows[0]["final_answer_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "COMMITMENT_HASH_MISMATCH"):
            score_exact_commitments(rows, self.refs)

    def test_requires_complete_five_trial_matrix(self):
        rows = self.full()[:-1]
        with self.assertRaisesRegex(ValueError, "COMMITMENT_COUNT"):
            score_exact_commitments(rows, self.refs)

    def test_threshold_is_8463(self):
        self.assertEqual(TARGET_NUMERATOR, 8463)

    def test_no_grader_equivalence_claim(self):
        r = score_exact_commitments(self.full(), self.refs)
        self.assertFalse(r["grader_equivalence_claimed"])
        self.assertTrue(r["threshold_met"])


if __name__ == "__main__":
    unittest.main()
