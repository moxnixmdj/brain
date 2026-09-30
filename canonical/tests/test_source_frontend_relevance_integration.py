#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, sys, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    s=importlib.util.spec_from_file_location("test_"+name,p)
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m)
    return m

class SourceFrontendRelevanceIntegration(unittest.TestCase):
    def test_relevance_advances_frontier_without_primary_gate(self):
        front=load("open_research_source_frontend")
        dec=load("broad_objective_decompose")
        old=front._load_sibling
        class D:
            @staticmethod
            def discover(objective,limit=12,timeout=15):
                return {"status":"CANDIDATES_DISCOVERED","candidates":[
                  {"url":"https://example.org/a","host":"example.org","title":"floating point summation numerical stability cancellation","snippet":"stable summation reduces floating point error","rank":0},
                  {"url":"https://example.org/b","host":"example.org","title":"garden plants","snippet":"watering guide","rank":1},
                ]}
        class P:
            @staticmethod
            def verify(candidate,timeout=15):
                return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":candidate["url"],"final_host":candidate["host"]}
        class A:
            @staticmethod
            def bind_candidate(candidate,timeout=15):
                return {"status":"AUTHORITY_IDENTITY_VERIFIED","organization_name":"Example","matched_domain":candidate["host"]}
        rel=load("objective_relevance_bm25")
        try:
            front._load_sibling=lambda name: {
              "open_web_source_candidate_discovery":D,
              "source_candidate_provenance_verify":P,
              "source_authority_binding_ror":A,
              "objective_relevance_bm25":rel,
            }[name]
            objective="Assess floating point summation numerical stability under severe cancellation"
            out=front.run(objective,dec.decompose(objective),limit=12,timeout=5)
        finally:
            front._load_sibling=old
        self.assertEqual(out["status"],"SOURCE_FRONTEND_READY",out)
        self.assertGreater(out["relevance_verified_candidate_count"],0,out)
        self.assertEqual(out["objective_relevance"]["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertEqual(
          out["next_required_capability"],
          "MODEL_INDEPENDENT_RELEVANCE_SELECTED_SOURCE_EVIDENCE_ACQUISITION_V1",
          out
        )
        self.assertFalse(out["primary_source_gate_required"])
        self.assertEqual(
          out["objective_relevance_claim_scope"],
          "LEXICAL_BM25_OBJECTIVE_RELEVANCE_ONLY"
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
