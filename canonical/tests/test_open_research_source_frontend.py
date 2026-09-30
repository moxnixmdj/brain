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

    def test_standard_objective_preserves_narrow_claim_boundaries(self):
        x=self._run("Determine whether RFC 9110 defines HTTP semantics and identify provenance-bearing source evidence")
        self.assertEqual(x["status"],"SOURCE_FRONTEND_READY",x)
        self.assertGreaterEqual(x["provenance_verified_candidate_count"],1,x)
        self.assertFalse(x["authority_claims_made"],x)
        self.assertFalse(x["primary_source_claims_made"],x)
        self.assertFalse(x["claim_support_claims_made"],x)
        self.assertFalse(x["evidence_relation_claims_made"],x)
        self.assertFalse(x["factual_correctness_claims_made"],x)
        self.assertFalse(x["evidence_sufficiency_claims_made"],x)
        self.assertEqual(x["model_dependency_count"],0,x)

    def test_primary_and_authority_identity_are_not_universal_gates(self):
        x=self._run("Assess whether a technical claim is supported by authoritative evidence")
        self.assertFalse(x["authority_identity_gate_required"],x)
        self.assertFalse(x["primary_source_gate_required"],x)
        self.assertEqual(
            x["primary_source_status_role"],
            "OPTIONAL_METADATA_NOT_UNIVERSAL_RESEARCH_ADMISSION_GATE",
        )

    def test_relevant_but_unextractable_source_stops_at_extraction(self):
        original=self.front._load_sibling
        class Discovery:
            @staticmethod
            def discover(objective,limit=12,timeout=15):
                return {"status":"CANDIDATES_DISCOVERED","candidates":[{"url":"https://example.org/report"}]}
        class Provenance:
            @staticmethod
            def verify(candidate,timeout=15):
                return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":"https://example.org/report","final_host":"example.org"}
        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=20):
                return {"status":"UNVERIFIED","reason":"NO_ROR_MATCH"}
        class Extractor:
            @staticmethod
            def extract(objective,candidate,provenance,timeout=20):
                return {
                    "schema":"PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1",
                    "status":"EXTRACTION_BLOCKED",
                    "reason":"NO_OBJECTIVE_ANCHORED_PASSAGES_AFTER_VERIFIED_RELEVANCE",
                    "relevance_verification":{
                        "status":"PROVENANCE_RELEVANT_SOURCE_VERIFIED",
                        "objective_relevance_status":"VERIFIED",
                    },
                    "evidence_records":[],
                }
        def fake(name):
            return {
                "open_web_source_candidate_discovery":Discovery,
                "source_candidate_provenance_verify":Provenance,
                "source_authority_binding_ror":Authority,
                "relevant_source_evidence_extract":Extractor,
            }[name]
        try:
            self.front._load_sibling=fake
            goal="Assess floating point summation accuracy under cancellation"
            d=self.decomp.decompose(goal)
            x=self.front.run(goal,d,limit=4,timeout=5)
            self.assertEqual(x["authority_identity_verified_candidate_count"],0,x)
            self.assertEqual(x["relevance_verified_candidate_count"],1,x)
            self.assertEqual(x["evidence_extracted_candidate_count"],0,x)
            self.assertTrue(x["relevance_claims_made"],x)
            self.assertFalse(x["evidence_extraction_claims_made"],x)
            self.assertEqual(
                x["next_required_capability"],
                "MODEL_INDEPENDENT_EVIDENCE_EXTRACTION_FROM_VERIFIED_RELEVANT_SOURCE",
                x,
            )
        finally:
            self.front._load_sibling=original

    def test_extraction_succeeds_with_no_authority_identity_and_advances_to_relation(self):
        original=self.front._load_sibling
        class Discovery:
            @staticmethod
            def discover(objective,limit=12,timeout=15):
                return {"status":"CANDIDATES_DISCOVERED","candidates":[{"url":"https://example.org/report"}]}
        class Provenance:
            @staticmethod
            def verify(candidate,timeout=15):
                return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":"https://example.org/report","final_host":"example.org"}
        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=20):
                return {"status":"UNVERIFIED","reason":"NO_ROR_MATCH"}
        class Extractor:
            @staticmethod
            def extract(objective,candidate,provenance,timeout=20):
                return {
                    "schema":"PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1",
                    "status":"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",
                    "output_verified":True,
                    "relevance_verification":{
                        "status":"PROVENANCE_RELEVANT_SOURCE_VERIFIED",
                        "objective_relevance_status":"VERIFIED",
                    },
                    "evidence_record_count":1,
                    "evidence_records":[{
                        "record_type":"OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATE",
                        "ordinal":0,
                        "text":"Floating point summation accuracy degrades under cancellation.",
                        "text_sha256":"a"*64,
                        "matched_objective_tokens":["floating","summation"],
                        "numeric_literals":[],
                        "source_url":"https://example.org/report",
                    }],
                    "claim_support_status":"UNVERIFIED",
                    "factual_correctness_status":"UNVERIFIED",
                    "evidence_sufficiency_status":"UNVERIFIED",
                }
        def fake(name):
            return {
                "open_web_source_candidate_discovery":Discovery,
                "source_candidate_provenance_verify":Provenance,
                "source_authority_binding_ror":Authority,
                "relevant_source_evidence_extract":Extractor,
            }[name]
        try:
            self.front._load_sibling=fake
            goal="Assess floating point summation accuracy under cancellation"
            d=self.decomp.decompose(goal)
            x=self.front.run(goal,d,limit=4,timeout=5)
            self.assertEqual(x["authority_identity_verified_candidate_count"],0,x)
            self.assertFalse(x["authority_identity_gate_required"],x)
            self.assertEqual(x["evidence_extracted_candidate_count"],1,x)
            self.assertTrue(x["evidence_extraction_claims_made"],x)
            self.assertFalse(x["claim_support_claims_made"],x)
            self.assertFalse(x["evidence_relation_claims_made"],x)
            self.assertFalse(x["factual_correctness_claims_made"],x)
            self.assertFalse(x["evidence_sufficiency_claims_made"],x)
            self.assertEqual(
                x["next_required_capability"],
                "MODEL_INDEPENDENT_CLAIM_SUPPORT_AND_RELATION_EVALUATION_FROM_EXTRACTED_EVIDENCE_V1",
                x,
            )
            self.assertEqual(
                x["role_progress"]["RELATION_EVALUATION"],
                "REQUIRED_FROM_EXTRACTED_EVIDENCE",
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
