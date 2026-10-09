from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCHED = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41.json"
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERM = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class Tests(unittest.TestCase):
    def test_v41_scheduler_is_exactly_bound_everywhere(self):
        sched = load(SCHED)
        r2 = load(R2)
        term = load(TERM)
        sha = git_blob_sha(SCHED)

        self.assertEqual(sha, "f3eb629ac2b7d732b28aa72bda4732bed4000f98")
        self.assertEqual(
            r2["scheduler_cut"],
            {
                "path": "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41.json",
                "git_blob_sha": sha,
            },
        )
        self.assertEqual(
            term["r2_scheduler_precedence"]["current_scheduler_path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41.json",
        )
        self.assertEqual(
            term["r2_scheduler_precedence"]["current_scheduler_git_blob_sha"],
            sha,
        )

    def test_counts_do_not_receive_fake_capability_credit(self):
        sched = load(SCHED)
        r2 = load(R2)
        term = load(TERM)

        self.assertEqual(r2["direct_adequacy"]["current_route_count"], 28)
        self.assertEqual(r2["direct_adequacy"]["bounded_family_count"], 25)
        self.assertEqual(sched["live_mechanism"]["direct_adequacy_route_count"], 28)
        self.assertEqual(sched["live_mechanism"]["direct_adequacy_bounded_family_count"], 25)
        self.assertEqual(
            len(r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]["verified_positive_subregions"]),
            10,
        )
        self.assertEqual(term["r2_v41_semantic_relation_proof_reconciliation"]["route_count"], 28)
        self.assertEqual(term["r2_v41_semantic_relation_proof_reconciliation"]["bounded_family_count"], 25)
        self.assertEqual(term["accounting"]["terminal_credit_delta"], 0)
        self.assertEqual(sched["accounting"]["terminal_credit_delta"], 0)

    def test_new_proof_kernel_is_bound_with_exact_verified_bytes(self):
        sched = load(SCHED)
        r2 = load(R2)
        term = load(TERM)

        row = sched["live_mechanism"]["bounded_semantic_relation_proof_kernel"]
        self.assertEqual(
            row["runtime_git_blob_sha"],
            "d2a1dc140535cf6430e3ee79605ddff3cd561db6",
        )
        self.assertIn("25_OF_25", row["verification_status"])

        frontier = r2["semantic_relation_frontier"]
        self.assertTrue(frontier["complete_bounded_denotation_equivalence_proof"])
        self.assertTrue(frontier["complete_bounded_directional_entailment_proof"])
        self.assertTrue(frontier["exact_counterexample_witnesses"])
        self.assertFalse(frontier["global_inferred_synonymy_closed"])

        rec = term["r2_v41_semantic_relation_proof_reconciliation"]
        self.assertTrue(rec["complete_bounded_denotation_relation_proof_bound"])
        self.assertFalse(rec["general_inferred_synonymy_closed"])
        self.assertFalse(rec["source_or_scope_completeness_self_authentication"])

    def test_remaining_frontier_is_narrowed_not_erased(self):
        sched = load(SCHED)
        r2 = load(R2)

        boundary = r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]["remaining_boundary"]
        self.assertIn("NO_COMPLETE_AUTHENTIC_BOUNDED_DENOTATION", boundary)
        self.assertIn("CONTEXT_DEPENDENT_WORD_SENSE", boundary)
        self.assertIn("GENERAL_CROSS_DOCUMENT_BINDING", boundary)
        self.assertIn("STRONGER_EXTERNAL_FACT_AUTHENTICATION", boundary)

        hard = "\n".join(sched["hard_nonclaims"])
        self.assertIn("OPEN_WORLD_SYNONYMY", hard)
        self.assertIn("DENOTATION_PACKAGES_AUTHENTICATE_THEIR_OWN_SOURCE", hard)
        self.assertIn("UNRESTRICTED_SUBSTITUTABILITY", hard)

    def test_terminal_stays_false(self):
        term = load(TERM)
        self.assertTrue(
            term["r2_v41_semantic_relation_proof_reconciliation"]["terminal_remains_false"]
        )
        self.assertEqual(
            term["r2_v41_semantic_relation_proof_reconciliation"]["terminal_credit_delta"],
            0,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
