from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/reasoning/2026-10-10_PROFESSIONAL_QUALITY_RESEARCH_CORPUS_POINTER_V1.json"
PARTS = [ROOT / f"canonical/reasoning/2026-10-10_PROFESSIONAL_QUALITY_RESEARCH_CORPUS_PART{i}_V1.json" for i in range(1, 5)]

EXPECTED_ROOTS = {
    "R1_TARGET_SPECIFICATION",
    "R2_CANDIDATE_SEARCH",
    "R3_REALIZATION_OBSERVATION",
    "R4_MEASUREMENT_CONSTRUCT",
    "R5_EVALUATOR_REFERENCE",
    "R6_EVIDENCE_GROUNDING_DEPENDENCE",
    "R7_CAUSAL_PRESCRIPTIVE",
    "R8_POPULATION_CONTEXT_OPERATOR",
    "R9_TEMPORAL_DEPLOYMENT",
    "R10_ANALYSIS_DECISION",
    "R11_ADAPTIVE_INTEGRITY_SECURITY",
    "R12_META_COMPOSITION_CLOSURE",
}

class TestProfessionalQualityResearchCorpusV1(unittest.TestCase):
    def test_full_97_layer_corpus_is_preserved_and_root_mapped(self):
        pointer = json.loads(POINTER.read_text())
        self.assertEqual(pointer["source_layer_count"], 97)
        self.assertEqual(pointer["status"], "RESEARCH_PROVENANCE_ONLY__ZERO_CREDIT")

        rows = []
        for part_path in PARTS:
            part = json.loads(part_path.read_text())
            self.assertEqual(part["status"], "RESEARCH_PROVENANCE_ONLY__ZERO_CREDIT")
            rows.extend(part["layers"])

        self.assertEqual(len(rows), 97)
        self.assertEqual([row["id"] for row in rows], list(range(1, 98)))

        for row in rows:
            self.assertTrue(row["title"])
            self.assertTrue(row["summary"])
            roots = set(row["root_ids"])
            self.assertTrue(roots)
            self.assertTrue(roots.issubset(EXPECTED_ROOTS), row)

    def test_process_transition_remains_fail_closed(self):
        part4 = json.loads(PARTS[-1].read_text())
        transition = part4["process_transition"]
        self.assertEqual(transition["from"], "SERIAL_NAMED_LAYER_DISCOVERY")
        self.assertIn("NEW_ROOT_ONLY_IF", transition["new_root_rule"])
        self.assertIn("NO_PROFESSIONAL_QUALITY_COMPLETENESS_PROOF", part4["hard_nonclaims"])
        self.assertIn("NO_TERMINAL_OR_CAPABILITY_CREDIT_FROM_RESEARCH_PERSISTENCE", part4["hard_nonclaims"])

if __name__ == "__main__":
    unittest.main()
