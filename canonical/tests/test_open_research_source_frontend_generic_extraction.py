#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"

def load():
    s=importlib.util.spec_from_file_location("open_research_source_frontend_generic_test",P)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class FakeDiscovery:
    @staticmethod
    def discover(objective,limit=12,timeout=15):
        return {"status":"CANDIDATES_DISCOVERED","candidates":[
            {"url":"https://example.org/irrelevant","title":"Campus contacts","snippet":"office hours"},
            {"url":"https://docs.example.net/wal","title":"SQLite WAL checkpoint behavior","snippet":"write ahead logging checkpoint database"},
        ]}

class FakeProvenance:
    @staticmethod
    def verify(candidate,timeout=15):
        return {
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "verification_method":"LIVE_HTTP_RETRIEVAL",
            "candidate_url":candidate["url"],
            "final_url":candidate["url"],
            "final_host":candidate["url"].split("/")[2],
        }

class FakeAuthority:
    @staticmethod
    def bind_candidate(candidate,timeout=15):
        return {"status":"UNVERIFIED","reason":"NO_ROR_MATCH"}

class FrontendGenericIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()

    def test_non_ror_source_can_reach_evidence_extraction(self):
        real_load=self.m._load_sibling
        extractor=real_load("objective_evidence_unit_extract")
        def fake_fetch(url,timeout):
            self.assertEqual(url,"https://docs.example.net/wal")
            return (
                b"<html><body><h1>SQLite write ahead logging</h1>"
                b"<p>SQLite WAL checkpoint behavior copies write ahead log frames back into the database during checkpoint processing.</p>"
                b"</body></html>",
                url,"text/html",200
            )
        original_extract=extractor.extract
        extractor.extract=lambda objective,candidate,provenance,relevance,timeout=20,max_units=10,fetch=None: original_extract(
            objective,candidate,provenance,relevance,timeout=timeout,max_units=max_units,fetch=fake_fetch
        )
        def loader(name):
            if name=="open_web_source_candidate_discovery": return FakeDiscovery
            if name=="source_candidate_provenance_verify": return FakeProvenance
            if name=="source_authority_binding_ror": return FakeAuthority
            if name=="objective_evidence_unit_extract": return extractor
            return real_load(name)
        decomposition={
            "status":"DECOMPOSED",
            "objective":"Assess SQLite WAL checkpoint behavior for write ahead logging database frames",
            "question_shape":"TECHNICAL_RESEARCH",
            "roles":[{"role":"SOURCE_DISCOVERY"}],
        }
        with patch.object(self.m,"_load_sibling",side_effect=loader):
            out=self.m.run(decomposition["objective"],decomposition)
        self.assertEqual(out["status"],"SOURCE_FRONTEND_READY",out)
        self.assertEqual(out["authority_identity_verified_candidate_count"],0,out)
        self.assertFalse(out["authority_identity_required_for_admission"],out)
        self.assertEqual(out["evidence_extracted_candidate_count"],1,out)
        self.assertEqual(
            out["next_required_capability"],
            "MODEL_INDEPENDENT_CLAIM_SUPPORT_AND_RELATION_EVALUATION_FROM_EXTRACTED_EVIDENCE_V1",
            out
        )
        self.assertFalse(out["factual_correctness_claims_made"],out)
        self.assertFalse(out["evidence_sufficiency_claims_made"],out)

if __name__=="__main__": unittest.main(verbosity=2)
