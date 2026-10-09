from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCHED = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V42.json"
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERM = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class Tests(unittest.TestCase):
    def test_v42_scheduler_is_exactly_bound_everywhere(self):
        sched = load(SCHED)
        r2 = load(R2)
        term = load(TERM)
        sha = git_blob_sha(SCHED)
        self.assertEqual(sha, "203bc3633aa7a402a5e871bcf9151732db8487b9")
        self.assertEqual(r2["scheduler_cut"]["git_blob_sha"], sha)
        self.assertEqual(
            r2["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V42.json",
        )
        self.assertEqual(
            term["r2_scheduler_precedence"]["current_scheduler_git_blob_sha"],
            sha,
        )
        self.assertEqual(
            term["r2_scheduler_precedence"]["current_scheduler_path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V42.json",
        )

    def test_semantic_stack_binds_both_verified_components(self):
        sched = load(SCHED)
        r2 = load(R2)
        term = load(TERM)

        ctx = sched["live_mechanism"]["authenticated_context_concept_bridge"]
        rel = sched["live_mechanism"]["bounded_semantic_relation_proof_kernel"]
        self.assertEqual(ctx["runtime_git_blob_sha"], "7fb56a8318d774098812a19b5a0544ee8dea930f")
        self.assertIn("FOCUSED_7_OF_7", ctx["verification_status"])
        self.assertEqual(rel["runtime_git_blob_sha"], "d2a1dc140535cf6430e3ee79605ddff3cd561db6")
        self.assertIn("25_OF_25", rel["verification_status"])

        self.assertTrue(r2["authenticated_context_concept_frontier"]["authenticated_raw_context_to_bounded_concept_control_closed"])
        self.assertTrue(r2["semantic_relation_frontier"]["complete_bounded_denotation_equivalence_proof"])
        self.assertTrue(r2["semantic_relation_frontier"]["complete_bounded_directional_entailment_proof"])
        self.assertTrue(r2["semantic_relation_frontier"]["exact_counterexample_witnesses"])

        rec = term["r2_v42_semantic_stack_reconciliation"]
        self.assertTrue(rec["authenticated_context_to_bounded_concept_bound"])
        self.assertTrue(rec["complete_bounded_denotation_relation_proof_bound"])

    def test_counts_remain_exactly_28_25_10_with_zero_credit(self):
        sched = load(SCHED)
        r2 = load(R2)
        term = load(TERM)

        self.assertEqual(sched["live_mechanism"]["direct_adequacy_route_count"], 28)
        self.assertEqual(sched["live_mechanism"]["direct_adequacy_bounded_family_count"], 25)
        self.assertEqual(r2["direct_adequacy"]["current_route_count"], 28)
        self.assertEqual(r2["direct_adequacy"]["bounded_family_count"], 25)
        self.assertEqual(
            len(r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]["verified_positive_subregions"]),
            10,
        )
        rec = term["r2_v42_semantic_stack_reconciliation"]
        self.assertEqual(rec["route_count"], 28)
        self.assertEqual(rec["bounded_family_count"], 25)
        self.assertEqual(rec["verified_finance_positive_subregion_count"], 10)
        self.assertEqual(rec["terminal_credit_delta"], 0)
        self.assertEqual(term["accounting"]["terminal_credit_delta"], 0)

    def test_remaining_frontier_is_narrowed_not_erased(self):
        r2 = load(R2)
        term = load(TERM)

        boundary = r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]["remaining_boundary"]
        self.assertIn("NO_COMPLETE_AUTHENTIC_BOUNDED_DENOTATION", boundary)
        self.assertIn("NO_AUTHENTICATED_CONTEXT_TO_BOUNDED_CONCEPT_BINDING", boundary)
        self.assertIn("GENERAL_CROSS_DOCUMENT_BINDING", boundary)
        self.assertIn("STRONGER_EXTERNAL_FACT_AUTHENTICATION", boundary)

        rec = term["r2_v42_semantic_stack_reconciliation"]
        self.assertFalse(rec["general_inferred_synonymy_closed"])
        self.assertFalse(rec["general_word_sense_closed"])
        self.assertFalse(rec["open_world_ontology_mapping_closed"])
        self.assertFalse(rec["source_or_scope_completeness_self_authentication"])

    def test_terminal_remains_false(self):
        term = load(TERM)
        self.assertTrue(term["r2_v42_semantic_stack_reconciliation"]["terminal_remains_false"])
        self.assertEqual(term["r2_v42_semantic_stack_reconciliation"]["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
