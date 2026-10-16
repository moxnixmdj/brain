#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"

def load():
    s=importlib.util.spec_from_file_location("front",P)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class FakeDiscovery:
    @staticmethod
    def discover(objective,limit=12,timeout=15):
        return {"status":"CANDIDATES_DISCOVERED","objective":objective,"candidates":[
            {"url":"https://research.example.edu/report","title":"Example report"}
        ]}

class FakeVerifier:
    @staticmethod
    def verify(candidate,timeout=15):
        return {
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "final_url":"https://research.example.edu/report",
            "final_host":"research.example.edu",
        }

class FakeAuthority:
    @staticmethod
    def bind_candidate(candidate,timeout=15):
        assert candidate["final_host"]=="research.example.edu"
        return {
            "status":"AUTHORITY_IDENTITY_VERIFIED",
            "authority_status":"VERIFIED",
            "authority_claim_scope":"HOST_TO_ROR_ORGANIZATION_DOMAIN_BINDING_ONLY",
            "primary_source_status":"UNVERIFIED",
            "relevance_status":"UNVERIFIED",
            "evidence_sufficiency_status":"UNVERIFIED",
        }

class CompositionTests(unittest.TestCase):
    def test_identity_advances_only_to_primary_relevance_frontier(self):
        m=load()
        old=m._load_sibling
        try:
            # Current contract: the real objective-relevance ranker and extractor run; only
            # discovery and provenance are faked (no network). Authority identity is bound
            # to the relevance-selected candidate only (optional metadata, not a gate).
            B = pathlib.Path(__file__).resolve().parents[2] / "canonical/runtime/bound_capabilities"
            real = {}
            def _real(name):
                if name not in real:
                    s = importlib.util.spec_from_file_location("ror_real_" + name, B / (name + ".py"))
                    mod = importlib.util.module_from_spec(s); s.loader.exec_module(mod); real[name] = mod
                return real[name]
            fakes = {
                "open_web_source_candidate_discovery": FakeDiscovery,
                "source_candidate_provenance_verify": FakeVerifier,
                "source_authority_binding_ror": FakeAuthority,
            }
            m._load_sibling = lambda name: fakes[name] if name in fakes else _real(name)
            goal="research example evidence"
            d={"status":"DECOMPOSED","objective":goal,"question_shape":"ASSESS","roles":[{"role":"SOURCE_DISCOVERY"}]}
            x=m.run(goal,d,limit=4,timeout=5)
            self.assertEqual(x["status"],"SOURCE_FRONTEND_READY",x)
            self.assertEqual(x["relevance_verified_candidate_count"],1,x)
            self.assertEqual(x["authority_identity_verified_candidate_count"],1,x)
            self.assertTrue(x["authority_identity_claims_made"],x)
            self.assertFalse(x["authority_claims_made"],x)
            self.assertEqual(x["primary_source_verified_candidate_count"],0,x)
            self.assertEqual(x["next_required_capability"],"MODEL_INDEPENDENT_EVIDENCE_EXTRACTION_FROM_VERIFIED_RELEVANT_SOURCE",x)
        finally:
            m._load_sibling=old

if __name__=="__main__": unittest.main(verbosity=2)
