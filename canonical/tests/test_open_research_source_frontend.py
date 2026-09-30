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

    def test_standard_objective_reaches_source_frontier(self):
        x=self._run("Determine whether RFC 9110 defines HTTP semantics and identify provenance-bearing source evidence")
        self.assertEqual(x["status"],"SOURCE_FRONTEND_READY",x)
        self.assertGreaterEqual(x["provenance_verified_candidate_count"],1,x)
        self.assertEqual(x["authority_verified_candidate_count"],0)
        self.assertFalse(x["authority_claims_made"])
        self.assertFalse(x["factual_correctness_claims_made"])
        self.assertFalse(x["evidence_sufficiency_claims_made"])
        self.assertEqual(x["model_dependency_count"],0)

    def test_scientific_objective_reaches_current_fail_closed_frontier(self):
        x=self._run("Assess whether lithium ion battery calendar aging is influenced by temperature using published experimental evidence")
        self.assertEqual(x["status"],"SOURCE_FRONTEND_READY",x)
        self.assertGreaterEqual(x["provenance_verified_candidate_count"],1,x)
        self.assertIn(
            x["next_required_capability"],
            {
                "MODEL_INDEPENDENT_EVIDENCE_EXTRACTION_FROM_VERIFIED_PRIMARY_RELEVANT_SOURCE",
                "MODEL_INDEPENDENT_PRIMARY_SOURCE_AND_OBJECTIVE_RELEVANCE_VERIFICATION",
                "MODEL_INDEPENDENT_SOURCE_AUTHORITY_IDENTITY_PRIMARY_SOURCE_AND_RELEVANCE_VERIFICATION",
            },
        )
        self.assertFalse(x["authority_claims_made"])
        self.assertFalse(x["factual_correctness_claims_made"])
        self.assertFalse(x["evidence_sufficiency_claims_made"])

    def test_verified_identity_primary_and_relevance_advance_only_to_extraction(self):
        original=self.front._load_sibling

        class Discovery:
            @staticmethod
            def discover(objective,limit=12,timeout=15):
                return {
                    "status":"CANDIDATES_DISCOVERED",
                    "candidates":[{"url":"https://research.example.org/report","title":"candidate"}],
                }

        class Provenance:
            @staticmethod
            def verify(candidate,timeout=15):
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "final_url":"https://research.example.org/report",
                    "final_host":"research.example.org",
                }

        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=20):
                return {
                    "status":"AUTHORITY_IDENTITY_VERIFIED",
                    "matched_domain":"research.example.org",
                    "organization_name":"Example Research Organization",
                    "authority_claim_scope":"HOST_TO_ROR_ORGANIZATION_DOMAIN_BINDING_ONLY",
                }

        class PrimaryRelevance:
            @staticmethod
            def verify(objective,candidate,provenance,authority_identity,timeout=15):
                return {
                    "status":"PRIMARY_SOURCE_AND_OBJECTIVE_RELEVANCE_VERIFIED",
                    "primary_source_status":"VERIFIED",
                    "relevance_status":"VERIFIED",
                    "factual_correctness_status":"UNVERIFIED",
                    "evidence_sufficiency_status":"UNVERIFIED",
                    "primary_source_claim_scope":"EXACT_ROR_BOUND_ORGANIZATION_HOSTED_DOCUMENT_PUBLICATION_PROVENANCE_ONLY",
                    "relevance_claim_scope":"EXACT_OBJECTIVE_ANCHOR_COVERAGE_ON_LIVE_DOCUMENT_METADATA_ONLY",
                    "model_dependency_count":0,
                    "incremental_spend_usd":0,
                }

        def fake(name):
            return {
                "open_web_source_candidate_discovery":Discovery,
                "source_candidate_provenance_verify":Provenance,
                "source_authority_binding_ror":Authority,
                "source_primary_relevance_verify":PrimaryRelevance,
            }[name]

        try:
            self.front._load_sibling=fake
            goal="Assess whether lithium ion battery calendar aging is influenced by temperature"
            d=self.decomp.decompose(goal)
            x=self.front.run(goal,d,limit=4,timeout=5)
            self.assertEqual(x["primary_relevance_verified_candidate_count"],1,x)
            self.assertEqual(x["primary_source_verified_candidate_count"],1,x)
            self.assertEqual(x["relevance_verified_candidate_count"],1,x)
            self.assertTrue(x["primary_source_claims_made"],x)
            self.assertTrue(x["relevance_claims_made"],x)
            self.assertFalse(x["authority_claims_made"],x)
            self.assertFalse(x["factual_correctness_claims_made"],x)
            self.assertFalse(x["evidence_sufficiency_claims_made"],x)
            self.assertEqual(
                x["next_required_capability"],
                "MODEL_INDEPENDENT_EVIDENCE_EXTRACTION_FROM_VERIFIED_PRIMARY_RELEVANT_SOURCE",
                x,
            )
            self.assertEqual(
                x["role_progress"]["EVIDENCE_ACQUISITION"],
                "PRIMARY_RELEVANT_SOURCE_AVAILABLE__EVIDENCE_EXTRACTION_REQUIRED",
                x,
            )
        finally:
            self.front._load_sibling=original

    def test_mismatch_fails_closed(self):
        d=self.decomp.decompose("Assess whether A is greater than B")
        with self.assertRaises(ValueError):
            self.front.run("Assess whether C is greater than D",d)

if __name__=="__main__":
    unittest.main(verbosity=2)
