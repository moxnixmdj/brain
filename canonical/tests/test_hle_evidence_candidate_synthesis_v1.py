from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.hle_evidence_candidate_synthesis_v1 import synthesize

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "governance" / "HLE_EVIDENCE_CANDIDATE_PREEXPOSURE_20261011_V1.json"


class HLEEvidenceCandidateSynthesisV1Tests(unittest.TestCase):
    def test_all_frozen_synthetic_cases(self):
        doc = json.loads(PRE.read_text(encoding="utf-8"))
        self.assertEqual(len(doc["cases"]), 10)
        for case in doc["cases"]:
            out = synthesize(
                contract=case["contract"],
                focus_terms=case["focus"],
                evidence=case["evidence"],
            )
            got = [x["answer"] for x in out.get("candidates", [])]
            self.assertEqual(got, case["expected_candidates"], (case["id"], out))
            self.assertFalse(out["candidate_answer_authority"])
            self.assertFalse(out["semantic_truth_authority"])
            self.assertFalse(out["gold_accessed"])
            self.assertEqual(out["external_model_calls"], 0)
            self.assertEqual(out["model_dependency_count"], 0)
            self.assertFalse(out["terminal_authority"])
            self.assertEqual(out["terminal_credit_delta"], 0)

    def test_candidate_occurrence_without_relation_is_not_support(self):
        out = synthesize(
            contract={"kind":"PERSON","polarity":"POSITIVE"},
            focus_terms=["zephyr","particle"],
            evidence="Dr. Mira Sol attended a lecture about the synthetic Zephyr particle.",
        )
        self.assertEqual(out["candidates"], [])

    def test_two_relation_bound_people_is_ambiguous(self):
        out = synthesize(
            contract={"kind":"PERSON","polarity":"POSITIVE"},
            focus_terms=["zephyr","particle"],
            evidence=(
                "The synthetic Zephyr particle was discovered by Dr. Mira Sol. "
                "A second source in the same passage says the synthetic Zephyr particle was discovered by Dr. Kian Vey."
            ),
        )
        self.assertEqual(out["candidates"], [])
        self.assertEqual(out["status"], "NO_CANDIDATE__RELATION_ABSENT_OR_AMBIGUOUS")

    def test_negative_contract_never_gets_positive_support_authority(self):
        out = synthesize(
            contract={"kind":"ENTITY_OR_TERM","polarity":"NEGATIVE"},
            focus_terms=["tau","transformation"],
            evidence="The fictional Tau transformation is called the Tau inversion.",
        )
        self.assertEqual(len(out["candidates"]), 1)
        row = out["candidates"][0]
        self.assertEqual(row["relation"], "REQUIRES_NEGATED_TARGET_REASONING")
        self.assertFalse(row["support_authority"])

    def test_insufficient_anchor_coverage_fails_closed(self):
        out = synthesize(
            contract={"kind":"YEAR","polarity":"POSITIVE"},
            focus_terms=["meridian","protocol","published"],
            evidence="An unrelated chronology lists 2042.",
        )
        self.assertEqual(out["candidates"], [])
        self.assertEqual(out["status"], "NO_CANDIDATE__INSUFFICIENT_OBJECTIVE_ANCHOR_COVERAGE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
