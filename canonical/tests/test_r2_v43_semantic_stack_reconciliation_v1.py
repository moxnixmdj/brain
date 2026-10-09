from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCHED = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V43.json"
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERM = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class Tests(unittest.TestCase):
    def test_v43_scheduler_exactly_bound_in_r2_and_terminal(self):
        sched = load(SCHED)
        r2 = load(R2)
        term = load(TERM)
        sha = git_blob_sha(SCHED)
        self.assertEqual(sha, "4fdc6171f14ce3bff684032db734c8c8bace7992")
        self.assertEqual(r2["scheduler_cut"]["git_blob_sha"], sha)
        self.assertEqual(
            r2["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V43.json",
        )
        self.assertEqual(term["r2_scheduler_precedence"]["current_scheduler_git_blob_sha"], sha)
        self.assertEqual(
            term["r2_scheduler_precedence"]["current_scheduler_path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V43.json",
        )

    def test_all_three_semantic_layers_are_bound(self):
        sched = load(SCHED)
        r2 = load(R2)
        term = load(TERM)

        oewn = sched["live_mechanism"]["oewn_release_sense_universe"]
        ctx = sched["live_mechanism"]["authenticated_context_concept_bridge"]
        rel = sched["live_mechanism"]["bounded_semantic_relation_proof_kernel"]

        self.assertEqual(oewn["runtime_git_blob_sha"], "7c9cd0e81732f05b02348fbd53d364dd567223f7")
        self.assertEqual(ctx["runtime_git_blob_sha"], "7fb56a8318d774098812a19b5a0544ee8dea930f")
        self.assertEqual(rel["runtime_git_blob_sha"], "d2a1dc140535cf6430e3ee79605ddff3cd561db6")
        self.assertFalse(oewn["intended_sense_identified"])
        self.assertFalse(oewn["open_world_english_completeness_claimed"])

        self.assertTrue(r2["oewn_release_sense_frontier"]["exact_release_relative_candidate_completeness"])
        self.assertFalse(r2["oewn_release_sense_frontier"]["intended_contextual_sense_identified"])
        self.assertTrue(r2["authenticated_context_concept_frontier"]["authenticated_raw_context_to_bounded_concept_control_closed"])
        self.assertTrue(r2["semantic_relation_frontier"]["complete_bounded_denotation_equivalence_proof"])
        self.assertTrue(r2["semantic_relation_frontier"]["complete_bounded_directional_entailment_proof"])
        self.assertTrue(r2["semantic_relation_frontier"]["exact_counterexample_witnesses"])

        rec = term["r2_v43_semantic_stack_reconciliation"]
        self.assertTrue(rec["oewn_release_relative_candidate_completeness_bound"])
        self.assertFalse(rec["intended_sense_selection_closed"])
        self.assertTrue(rec["authenticated_context_to_bounded_concept_bound"])
        self.assertTrue(rec["complete_bounded_denotation_relation_proof_bound"])

    def test_counts_remain_28_25_10_and_no_credit_is_invented(self):
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
        rec = term["r2_v43_semantic_stack_reconciliation"]
        self.assertEqual(rec["route_count"], 28)
        self.assertEqual(rec["bounded_family_count"], 25)
        self.assertEqual(rec["verified_finance_positive_subregion_count"], 10)
        self.assertEqual(rec["terminal_credit_delta"], 0)
        self.assertEqual(term["accounting"]["terminal_credit_delta"], 0)

    def test_remaining_frontier_is_precisely_narrowed_not_erased(self):
        r2 = load(R2)
        term = load(TERM)
        boundary = r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]["remaining_boundary"]

        self.assertIn("MULTIPLE_OEWN_OR_AUTHENTICATED_REGISTRY_CANDIDATES", boundary)
        self.assertIn("OUTSIDE_PROVED_COMPLETE_LEXICAL_OR_DOMAIN_UNIVERSES", boundary)
        self.assertIn("TASK_SPECIFIC_MAPPING_FROM_LEXICAL_SENSE_OR_DOMAIN_CONCEPT", boundary)
        self.assertIn("OPEN_WORLD_ONTOLOGY_MAPPING", boundary)
        self.assertIn("GENERAL_CROSS_DOCUMENT_BINDING", boundary)
        self.assertIn("STRONGER_EXTERNAL_FACT_AUTHENTICATION", boundary)

        rec = term["r2_v43_semantic_stack_reconciliation"]
        self.assertFalse(rec["general_inferred_synonymy_closed"])
        self.assertFalse(rec["general_word_sense_closed"])
        self.assertFalse(rec["open_world_ontology_mapping_closed"])
        self.assertFalse(rec["source_or_scope_completeness_self_authentication"])

    def test_oewn_boundary_is_release_relative_not_magic_language_truth(self):
        term = load(TERM)
        src = term["authoritative_sources"]["oewn_2025_release_sense_universe"]
        self.assertEqual(
            src["exact_release_archive_sha256"],
            "7d749f6e2c39e6970e4997839dcf6e42fd281f3c2fae0171d2192bae8cfa4b51",
        )
        self.assertIn("RELEASE_RELATIVE", src["note"])
        hard = "\n".join(term["hard_nonclaims"])
        self.assertIn("OPEN_WORLD_ENGLISH_SENSE_COMPLETENESS", hard)
        self.assertIn("INTENDED_CONTEXTUAL_SENSE", hard)
        self.assertIn("SYNSET_IDENTITY_ALONE", hard)

    def test_terminal_stays_false(self):
        term = load(TERM)
        rec = term["r2_v43_semantic_stack_reconciliation"]
        self.assertTrue(rec["terminal_remains_false"])
        self.assertEqual(rec["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
