#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, sys, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/astra_runtime.py"

def load():
    spec=importlib.util.spec_from_file_location("astra_runtime_extraction_transition_test",P)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_extracted_evidence_advances_to_relation_evaluation(self):
        source_frontend={
            "status":"SOURCE_FRONTEND_READY",
            "provenance_verified_candidate_count":2,
            "authority_identity_verified_candidate_count":1,
            "relevance_verified_candidate_count":1,
            "evidence_extracted_candidate_count":1,
            "next_required_capability":"MODEL_INDEPENDENT_EVIDENCE_RELATION_EVALUATION_FROM_VERIFIED_UNITS",
        }
        message=self.m._open_research_frontier_blocker_message(
            source_frontend,
            "canonical/astra_runtime/evidence/X__OPEN_RESEARCH_SOURCE_FRONTEND.json",
        )
        self.assertTrue(
            message.startswith(
                "OPEN_ENDED_RESEARCH_EVIDENCE_UNITS_READY__"
                "RELATION_EVALUATION_REQUIRED:"
            ),
            message,
        )
        self.assertIn('"evidence_extracted_candidate_count": 1',message)
        self.assertIn(
            '"next_required_capability": '
            '"MODEL_INDEPENDENT_EVIDENCE_RELATION_EVALUATION_FROM_VERIFIED_UNITS"',
            message,
        )

    def test_relevance_without_units_still_blocks_on_extraction(self):
        source_frontend={
            "status":"SOURCE_FRONTEND_READY",
            "provenance_verified_candidate_count":1,
            "authority_identity_verified_candidate_count":1,
            "relevance_verified_candidate_count":1,
            "evidence_extracted_candidate_count":0,
            "next_required_capability":"MODEL_INDEPENDENT_EVIDENCE_EXTRACTION_FROM_VERIFIED_RELEVANT_SOURCE",
        }
        message=self.m._open_research_frontier_blocker_message(source_frontend,"x.json")
        self.assertTrue(
            message.startswith(
                "OPEN_ENDED_RESEARCH_RELEVANT_SOURCE_READY__"
                "EVIDENCE_EXTRACTION_REQUIRED:"
            ),
            message,
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
