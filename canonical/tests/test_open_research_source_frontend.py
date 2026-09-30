#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BC=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BC/(name+".py")
    s=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

class OpenResearchSourceFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load("open_research_source_frontend")
        cls.decomp=load("broad_objective_decompose")

    def _run(self,goal):
        d=self.decomp.decompose(goal)
        self.assertEqual(d["status"],"DECOMPOSED",d)
        return self.front.run(goal,d,limit=8,timeout=20)

    def test_standard_objective_reaches_provenance_frontier(self):
        x=self._run("Determine whether RFC 9110 defines HTTP semantics and identify provenance-bearing source evidence")
        self.assertEqual(x["status"],"SOURCE_FRONTEND_READY",x)
        self.assertGreaterEqual(x["provenance_verified_candidate_count"],1,x)
        self.assertGreaterEqual(x["authority_verified_candidate_count"],0)
        self.assertEqual(x["authority_claims_made"],x["authority_verified_candidate_count"]>0)
        self.assertEqual(x["model_dependency_count"],0)

    def test_scientific_objective_reaches_provenance_frontier(self):
        x=self._run("Assess whether lithium ion battery calendar aging is influenced by temperature using published experimental evidence")
        self.assertEqual(x["status"],"SOURCE_FRONTEND_READY",x)
        self.assertGreaterEqual(x["provenance_verified_candidate_count"],1,x)
        self.assertIn(
            x["next_required_capability"],
            {
                "MODEL_INDEPENDENT_PRIMARY_SOURCE_AND_OBJECTIVE_RELEVANCE_VERIFICATION",
                "MODEL_INDEPENDENT_SOURCE_AUTHORITY_IDENTITY_COVERAGE_OR_PRIMARY_SOURCE_AND_RELEVANCE_VERIFICATION",
            },
        )


    def test_verified_provenance_flows_into_ror_and_stops_before_primary_relevance(self):
        original=self.front._load_sibling
        class Discovery:
            @staticmethod
            def discover(objective,limit=12,timeout=15):
                return {
                    "status":"CANDIDATES_DISCOVERED",
                    "candidates":[
                        {"url":"https://candidate.example/a","title":"good"},
                        {"url":"https://bad.example/b","title":"bad"},
                    ],
                    "model_dependency_count":0,
                    "incremental_spend_usd":0,
                }
        class Provenance:
            @staticmethod
            def verify(candidate,timeout=15):
                if "candidate.example" in candidate["url"]:
                    return {
                        "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                        "final_url":"https://candidate.example/a",
                        "final_host":"candidate.example",
                    }
                return {"status":"UNVERIFIED"}
        class Authority:
            seen=None
            @classmethod
            def bind_discovery(cls,discovery,timeout=20,max_candidates=12):
                cls.seen=discovery
                return {
                    "status":"AUTHORITY_BOUND_CANDIDATES_AVAILABLE",
                    "verified_candidate_count":1,
                    "verified_candidates":[{
                        "matched_domain":"candidate.example",
                        "authority_status":"VERIFIED",
                        "primary_source_status":"UNVERIFIED",
                        "relevance_status":"UNVERIFIED",
                        "evidence_sufficiency_status":"UNVERIFIED",
                    }],
                    "model_dependency_count":0,
                    "incremental_spend_usd":0,
                }
        def fake(name):
            if name=="open_web_source_candidate_discovery": return Discovery
            if name=="source_candidate_provenance_verify": return Provenance
            if name=="source_authority_binding_ror": return Authority
            return original(name)
        try:
            self.front._load_sibling=fake
            goal="Assess whether a documented technical claim is supported by authoritative evidence"
            d=self.decomp.decompose(goal)
            x=self.front.run(goal,d,limit=8,timeout=5)
            self.assertEqual(x["authority_verified_candidate_count"],1,x)
            self.assertTrue(x["authority_claims_made"],x)
            self.assertEqual(
                x["next_required_capability"],
                "MODEL_INDEPENDENT_PRIMARY_SOURCE_AND_OBJECTIVE_RELEVANCE_VERIFICATION",
            )
            self.assertEqual(len(Authority.seen["candidates"]),1)
            self.assertEqual(Authority.seen["candidates"][0]["final_host"],"candidate.example")
            self.assertEqual(x["primary_source_verified_candidate_count"],0)
            self.assertEqual(x["relevance_verified_candidate_count"],0)
        finally:
            self.front._load_sibling=original

    def test_mismatch_fails_closed(self):
        d=self.decomp.decompose("Assess whether A is greater than B")
        with self.assertRaises(ValueError):
            self.front.run("Assess whether C is greater than D",d)

if __name__=="__main__":
    unittest.main(verbosity=2)
