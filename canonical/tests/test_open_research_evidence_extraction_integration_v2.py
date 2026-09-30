#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BC=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    path=BC/(name+".py")
    spec=importlib.util.spec_from_file_location("test_"+name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load("open_research_source_frontend")
        cls.decomp=load("broad_objective_decompose")

    def test_verified_extraction_advances_to_relation_evaluation(self):
        original=self.front._load_sibling
        calls=[]

        class Discovery:
            @staticmethod
            def discover(objective,limit=12,timeout=15):
                return {"status":"CANDIDATES_DISCOVERED","candidates":[
                    {"url":"https://example.org/report","title":"Floating point summation"}
                ]}

        class Provenance:
            @staticmethod
            def verify(candidate,timeout=15):
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "final_url":"https://example.org/report",
                    "final_host":"example.org",
                }

        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=20):
                return {
                    "status":"AUTHORITY_IDENTITY_VERIFIED",
                    "matched_domain":"example.org",
                    "organization_name":"Example Organization",
                }

        class Relevance:
            @staticmethod
            def verify(objective,candidate,provenance,authority_identity,timeout=20):
                return {
                    "status":"FIRST_PARTY_RELEVANT_SOURCE_VERIFIED",
                    "objective_relevance_status":"VERIFIED",
                    "fresh_url":"https://example.org/report",
                    "bound_domain":"example.org",
                    "verification_method":"EXACT_ROR_DOMAIN_PLUS_FRESH_PAGE_OBJECTIVE_TERM_COVERAGE",
                    "model_dependency_count":0,
                    "incremental_spend_usd":0,
                }

        class Extractor:
            @staticmethod
            def extract(objective,candidate,provenance,relevance,timeout=20,max_units=8):
                calls.append((objective,candidate,provenance,relevance))
                return {
                    "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
                    "evidence_extraction_status":"VERIFIED",
                    "evidence_unit_count":1,
                    "evidence_units":[{
                        "text":"Accurate floating point summation reduces cancellation error.",
                        "text_sha256":"a"*64,
                        "matched_objective_tokens":["floating","summation","cancellation"],
                        "visible_text_start":0,
                        "visible_text_end":59,
                    }],
                    "claim_relation_status":"UNVERIFIED",
                    "factual_correctness_status":"UNVERIFIED",
                    "evidence_sufficiency_status":"UNVERIFIED",
                    "model_dependency_count":0,
                    "incremental_spend_usd":0,
                }

        def fake(name):
            return {
                "open_web_source_candidate_discovery":Discovery,
                "source_candidate_provenance_verify":Provenance,
                "source_authority_binding_ror":Authority,
                "first_party_objective_relevance_verify":Relevance,
                "objective_evidence_unit_extract":Extractor,
            }[name]

        try:
            self.front._load_sibling=fake
            goal="Assess floating point summation accuracy under cancellation"
            decomposition=self.decomp.decompose(goal)
            out=self.front.run(goal,decomposition,limit=4,timeout=5)
        finally:
            self.front._load_sibling=original

        self.assertEqual(len(calls),1,calls)
        self.assertEqual(len(calls[0]),4,calls)
        self.assertEqual(out["evidence_extracted_candidate_count"],1,out)
        self.assertEqual(
            out["role_progress"]["EVIDENCE_EXTRACTION"],
            "OBJECTIVE_GROUNDED_VERBATIM_UNITS_VERIFIED",
            out,
        )
        self.assertEqual(out["role_progress"]["RELATION_EVALUATION"],"REQUIRES_GROUNDING",out)
        self.assertEqual(
            out["next_required_capability"],
            "MODEL_INDEPENDENT_EVIDENCE_RELATION_EVALUATION_FROM_VERIFIED_UNITS",
            out,
        )
        self.assertFalse(out["factual_correctness_claims_made"],out)
        self.assertFalse(out["evidence_sufficiency_claims_made"],out)

if __name__=="__main__":
    unittest.main(verbosity=2)
