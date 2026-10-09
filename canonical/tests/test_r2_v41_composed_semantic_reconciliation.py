from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHED = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41.json"
PTR = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERM = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"

BLOBS = {
    "canonical/runtime/semantic_relation_control_v1.py":
        "eeafd9b2898a65ee0aafe519b035d1d79fed0fea",
    "canonical/runtime/source_aligned_semantic_entailment_v1.py":
        "855f7d6cff2333bdaf19ca01317a164e81b98534",
    "canonical/runtime/bounded_semantic_relation_proof_v1.py":
        "d2a1dc140535cf6430e3ee79605ddff3cd561db6",
    "canonical/runtime/bounded_authenticated_concept_universe_v1.py":
        "2af90250d6d042646c997cf8c0b49ed7b627ebb7",
    "canonical/runtime/authenticated_context_concept_bridge_v1.py":
        "7fb56a8318d774098812a19b5a0544ee8dea930f",
    "canonical/runtime/oewn_release_sense_universe_v1.py":
        "7c9cd0e81732f05b02348fbd53d364dd567223f7",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class Tests(unittest.TestCase):
    def test_v41_composed_semantic_stack_reconciles_exactly(self):
        sched = load(SCHED)
        ptr = load(PTR)
        term = load(TERM)
        sched_blob = git_blob_sha(SCHED)

        self.assertEqual(
            sched["schema"],
            "PROJECT_BRAIN_ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41",
        )
        self.assertEqual(sched_blob, "1498cfd6776fd063cf65eabd9865940caf6e5780")
        self.assertIn("COMPOSED_DECISION_RELATIVE_SEMANTIC_PROOF_STACK_BOUND", sched["status"])

        self.assertEqual(
            ptr["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41.json",
        )
        self.assertEqual(ptr["scheduler_cut"]["git_blob_sha"], sched_blob)
        self.assertIn("V41", ptr["status"])

        precedence = term["r2_scheduler_precedence"]
        self.assertEqual(
            precedence["current_scheduler_path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41.json",
        )
        self.assertEqual(precedence["current_scheduler_git_blob_sha"], sched_blob)
        self.assertEqual(
            term["live_truth"]["current_r2_scheduler_cut"],
            "ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41",
        )

        for rel, expected in BLOBS.items():
            self.assertEqual(git_blob_sha(ROOT / rel), expected, rel)

        recon = sched["composed_semantic_relation_stack_reconciliation"]
        self.assertEqual(recon["verification"], "64_OF_64_REMOTE_COMPOSED_COMPATIBILITY_PASS")
        self.assertTrue(recon["bounded_directional_entailment_closed"])
        self.assertTrue(recon["bounded_scoped_logical_equivalence_closed"])
        self.assertTrue(recon["release_relative_sense_candidate_enumeration_closed_for_oewn_covered_terms"])
        self.assertFalse(recon["general_natural_language_entailment_closed"])
        self.assertFalse(recon["global_inferred_synonymy_closed"])
        self.assertFalse(recon["general_context_word_sense_closed"])
        self.assertFalse(recon["open_world_ontology_mapping_closed"])

        direct = ptr["direct_adequacy"]
        self.assertEqual(direct["current_route_count"], 28)
        self.assertEqual(direct["bounded_family_count"], 25)
        cell = ptr["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        self.assertEqual(len(cell["verified_positive_subregions"]), 10)

        self.assertIn(
            "NONEXPLICIT_SEMANTIC_RELATIONS_OUTSIDE_EXACT_SOURCE_DECLARATIONS_COMPLETE_BOUNDED_DENOTATION_PROOFS_AND_THE_CHECKED_SOURCE_ALIGNED_ENTAILMENT_FRAGMENT",
            ptr["remaining_problem_class"],
        )
        self.assertFalse(term["live_truth"]["general_inferred_synonymy_closed"])
        self.assertFalse(term["live_truth"]["general_natural_language_entailment_closed"])
        self.assertFalse(term["live_truth"]["general_context_word_sense_closed"])
        self.assertEqual(term["accounting"]["terminal_credit_delta"], 0)
        self.assertEqual(
            term["r2_v41_composed_semantic_relation_reconciliation"]["terminal_credit_delta"],
            0,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
