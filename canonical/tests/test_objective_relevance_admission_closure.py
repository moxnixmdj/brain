#!/usr/bin/env python3
from __future__ import annotations
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
ASTRA=ROOT/"canonical/runtime/astra_runtime.py"
FRONT=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"

class ObjectiveRelevanceAdmissionClosure(unittest.TestCase):
    def test_frontend_advances_relevance_only_to_extraction(self):
        s=FRONT.read_text(encoding="utf-8")
        self.assertIn("FIRST_PARTY_RELEVANT_SOURCE_VERIFIED",s)
        self.assertIn("MODEL_INDEPENDENT_EVIDENCE_EXTRACTION_FROM_VERIFIED_RELEVANT_SOURCE",s)
        self.assertIn('"factual_correctness_claims_made":False',s)
        self.assertIn('"evidence_sufficiency_claims_made":False',s)
        self.assertIn('"primary_source_claims_made":False',s)

    def test_astra_prefers_relevance_ready_branch_before_identity_blocker(self):
        s=ASTRA.read_text(encoding="utf-8")
        rel=s.index('source_frontend.get("relevance_verified_candidate_count")')
        ready=s.index("OPEN_ENDED_RESEARCH_RELEVANT_SOURCE_READY__",rel)
        identity=s.index("OPEN_ENDED_RESEARCH_SOURCE_IDENTITY_READY__",ready)
        self.assertLess(ready,identity)
        window=s[ready:identity]
        self.assertIn("EVIDENCE_EXTRACTION_REQUIRED",window)

    def test_relevance_receipt_is_exposed_in_blocker_payload(self):
        s=ASTRA.read_text(encoding="utf-8")
        self.assertIn('"relevance_verified_candidate_count":int(',s)
        self.assertIn('"capability_acquisition_attempted":False',s)

if __name__=="__main__":
    unittest.main(verbosity=2)
