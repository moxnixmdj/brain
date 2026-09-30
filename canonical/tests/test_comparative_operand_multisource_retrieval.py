#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[2]
BC=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BC/(name+".py")
    spec=importlib.util.spec_from_file_location("test_"+name,p)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

class Discovery:
    calls=[]
    @classmethod
    def discover(cls,objective,limit=12,timeout=15,query_override=None):
        q=str(query_override or objective)
        cls.calls.append(q)
        if "6061" in q:
            return {
                "status":"CANDIDATES_DISCOVERED",
                "candidates":[{
                    "url":"https://left.example/6061",
                    "title":"Thermal conductivity of annealed 6061 aluminum",
                }],
            }
        if "304" in q:
            return {
                "status":"CANDIDATES_DISCOVERED",
                "candidates":[{
                    "url":"https://right.example/304",
                    "title":"Thermal conductivity of annealed 304 stainless steel",
                }],
            }
        return {"status":"CANDIDATES_DISCOVERED","candidates":[]}

class Provenance:
    @staticmethod
    def verify(candidate,timeout=15):
        return {
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "candidate_url":candidate["url"],
            "final_url":candidate["url"],
            "final_host":candidate["url"].split("/")[2],
        }
    @staticmethod
    def materialize(candidate,bibliographic_verification,timeout=15,fetch=None):
        raise AssertionError("DIRECT_RETRIEVAL_FIXTURE_MUST_NOT_MATERIALIZE")

class Relevance:
    @staticmethod
    def rank(objective,candidates):
        if not candidates:
            return {"status":"RELEVANCE_UNRESOLVED","output_verified":False}
        return {
            "status":"LEXICAL_RELEVANCE_RANKED",
            "output_verified":True,
            "objective":objective,
            "query_focus":{"query":objective},
            "top_candidate_original_index":0,
            "top_candidate_admission":{
                "verified":True,
                "method":"FOCUSED_QUERY_TOKEN_COVERAGE_V1",
            },
            "ranked_candidates":[{"original_index":0,"candidate":dict(candidates[0])}],
        }

class Extractor:
    @staticmethod
    def extract(objective,candidate,provenance,relevance,timeout=15,max_units=10,fetch=None):
        if "6061" in objective:
            row={
                "evidence_unit_id":"a"*64,
                "source_url":candidate["url"],
                "text":"Room-temperature thermal conductivity of annealed 6061 aluminum is 167 W/mK.",
            }
        elif "304" in objective:
            row={
                "evidence_unit_id":"b"*64,
                "source_url":candidate["url"],
                "text":"Room-temperature thermal conductivity of annealed 304 stainless steel is 16.2 W/mK under comparable bulk-material conditions.",
            }
        else:
            raise AssertionError("OPERAND_QUERY_REQUIRED")
        return {
            "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
            "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
            "output_verified":True,
            "evidence_unit_count":1,
            "source_url":candidate["url"],
            "evidence_units":[row],
        }

class Authority:
    @staticmethod
    def bind_candidate(candidate,timeout=15):
        return {"status":"UNVERIFIED","reason":"NOT_REQUIRED"}

class ComparativeOperandMultisourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load("open_research_source_frontend")
        cls.binder=load("objective_claim_operand_binding")

    def setUp(self):
        Discovery.calls=[]

    def _decomposition(self,objective):
        return {
            "status":"DECOMPOSED",
            "objective":objective,
            "question_shape":"BOOLEAN_ASSESSMENT",
            "roles":[{"role":"SOURCE_DISCOVERY"}],
        }

    def _loader(self,name):
        return {
            "open_web_source_candidate_discovery":Discovery,
            "source_candidate_provenance_verify":Provenance,
            "objective_relevance_bm25":Relevance,
            "objective_evidence_unit_extract":Extractor,
            "objective_claim_operand_binding":self.binder,
            "source_authority_binding_ror":Authority,
        }[name]

    def test_explicit_comparison_uses_distinct_operand_sources_and_merges_evidence(self):
        objective=(
            "Determine whether the room-temperature thermal conductivity of annealed 6061 aluminum "
            "is greater than that of annealed 304 stainless steel under comparable bulk-material conditions."
        )
        with patch.object(self.front,"_load_sibling",side_effect=self._loader):
            out=self.front.run(objective,self._decomposition(objective),limit=6,timeout=5)
        self.assertEqual(out["status"],"SOURCE_FRONTEND_READY",out)
        self.assertEqual(out["relevance_verified_candidate_count"],2,out)
        self.assertEqual(out["evidence_extracted_candidate_count"],2,out)
        self.assertEqual(out["claim_relation_evaluated_count"],1,out)
        self.assertEqual(len(out["comparative_operand_queries"]),2,out)
        self.assertTrue(any("6061" in q for q in Discovery.calls),Discovery.calls)
        self.assertTrue(any("304" in q for q in Discovery.calls),Discovery.calls)
        self.assertFalse(any("6061" in q and "304" in q for q in Discovery.calls),Discovery.calls)
        merged=out["merged_evidence_extraction"]
        self.assertEqual(merged["evidence_unit_count"],2,merged)
        self.assertEqual(set(merged["source_urls"]),{
            "https://left.example/6061","https://right.example/304"
        })
        binding=out["claim_relation_evaluations"][0]["binding"]
        self.assertEqual(binding["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",binding)
        self.assertEqual(binding["relation_result"]["status"],"NUMERIC_RELATION_VERIFIED",binding)
        self.assertTrue(binding["relation_result"]["result"],binding)

    def test_missing_operand_source_fails_closed(self):
        objective=(
            "Determine whether the room-temperature thermal conductivity of annealed 6061 aluminum "
            "is greater than that of annealed 304 stainless steel under comparable bulk-material conditions."
        )
        original=Discovery.discover
        @classmethod
        def only_left(cls,objective,limit=12,timeout=15,query_override=None):
            q=str(query_override or objective)
            if "304" in q:
                cls.calls.append(q)
                return {"status":"CANDIDATES_DISCOVERED","candidates":[]}
            return original.__func__(cls,objective,limit,timeout,query_override)
        Discovery.discover=only_left
        try:
            with patch.object(self.front,"_load_sibling",side_effect=self._loader):
                out=self.front.run(objective,self._decomposition(objective),limit=6,timeout=5)
        finally:
            Discovery.discover=original
        self.assertEqual(out["status"],"COMPARATIVE_OPERAND_SOURCE_BLOCKED",out)
        self.assertEqual(out["claim_relation_evaluations"],[],out)
        self.assertEqual(
            out["next_required_capability"],
            "MODEL_INDEPENDENT_COMPARATIVE_OPERAND_AWARE_MULTI_SOURCE_RETRIEVAL_V1",
            out,
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
