#!/usr/bin/env python3
from __future__ import annotations
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
ASTRA=ROOT/"canonical/runtime/astra_runtime.py"
FRONT=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"

class EvidenceExtractionFrontierClosure(unittest.TestCase):
    def test_frontend_advances_extraction_only_to_relation_evaluation(self):
        s=FRONT.read_text(encoding="utf-8")
        self.assertIn("OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",s)
        self.assertIn("MODEL_INDEPENDENT_EVIDENCE_RELATION_EVALUATION",s)
        self.assertIn('"evidence_relation_claims_made":False',s)
        self.assertIn('"factual_correctness_claims_made":False',s)
        self.assertIn('"evidence_sufficiency_claims_made":False',s)
        self.assertIn('"primary_source_claims_made":False',s)

    def test_astra_prefers_extraction_ready_branch_before_relevance_blocker(self):
        s=ASTRA.read_text(encoding="utf-8")
        count=s.index('source_frontend.get("evidence_extracted_candidate_count")')
        ready=s.index("OPEN_ENDED_RESEARCH_GROUNDED_EVIDENCE_READY__",count)
        relation=s.index("EVIDENCE_RELATION_EVALUATION_REQUIRED",ready)
        relevant=s.index("OPEN_ENDED_RESEARCH_RELEVANT_SOURCE_READY__",relation)
        self.assertLess(ready,relevant)

    def test_extraction_receipt_is_exposed_in_blocker_payload(self):
        s=ASTRA.read_text(encoding="utf-8")
        self.assertIn('"evidence_extracted_candidate_count":int(',s)
        self.assertIn('"capability_acquisition_attempted":False',s)

if __name__=="__main__":
    unittest.main(verbosity=2)
