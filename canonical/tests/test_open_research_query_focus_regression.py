#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    path=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("query_focus_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class QueryFocusRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.discovery=load("open_web_source_candidate_discovery")
        cls.front=load("open_research_source_frontend")
        cls.decomp=load("broad_objective_decompose")
        cls.relevance=load("objective_relevance_bm25")

    def test_genomics_like_parent_query_excludes_control_prose(self):
        goal=(
            "Assess whether the complete reference genome sequence length of "
            "Escherichia coli K-12 MG1655 is greater than the human mitochondrial "
            "reference genome sequence length. Use authoritative primary technical "
            "evidence and a real executable check. Autonomously discover and verify "
            "the relevant primary records, determine how to extract and interpret the "
            "two sequence lengths, choose and run a zero-cost verification method, "
            "identify material reference-version or sequence-scope limitations, "
            "independently verify the consequential result, and produce a "
            "decision-quality answer with provenance."
        )
        q=self.discovery._query(goal)
        self.assertEqual(
            q,
            "the complete reference genome sequence length of Escherichia coli K-12 "
            "MG1655 is greater than the human mitochondrial reference genome sequence length",
        )
        low=q.lower()
        for control in ("assess","authoritative","executable","autonomously","verification method","decision-quality"):
            self.assertNotIn(control,low)

    def test_frontend_ranks_against_focused_query_not_imperative_noise(self):
        goal=(
            "Assess whether the complete reference genome sequence length of "
            "Escherichia coli K-12 MG1655 is greater than the human mitochondrial "
            "reference genome sequence length. Use authoritative primary technical "
            "evidence and a real executable check. Autonomously discover and verify "
            "the relevant primary records, determine how to extract and interpret the "
            "two sequence lengths, choose and run a zero-cost verification method, "
            "identify material reference-version or sequence-scope limitations, "
            "independently verify the consequential result, and produce a "
            "decision-quality answer with provenance."
        )
        focused=self.discovery._query(goal)
        candidates=[
            {
                "url":"https://noise.example/assess",
                "host":"noise.example",
                "title":"Asess or Assess - Which is Correct?",
                "snippet":"Assess means evaluate quality. Two examples explain assess.",
            },
            {
                "url":"https://science.example/reference-records",
                "host":"science.example",
                "title":"Escherichia coli K-12 MG1655 complete reference genome sequence",
                "snippet":"Human mitochondrial reference genome sequence length and MG1655 sequence length records.",
            },
        ]
        original=self.front._load_sibling

        class Discovery:
            @staticmethod
            def discover(objective,limit=12,timeout=15):
                return {
                    "status":"CANDIDATES_DISCOVERED",
                    "objective":objective,
                    "query":focused,
                    "query_strategy":"DECISION_CLAUSE_FOCUSED__ORCHESTRATION_PROSE_EXCLUDED",
                    "candidates":candidates,
                }

        class Provenance:
            @staticmethod
            def verify(candidate,timeout=15):
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "final_url":candidate["url"],
                    "final_host":candidate["host"],
                }

        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=15):
                return {"status":"AUTHORITY_UNRESOLVED","reason":"TEST_FIXTURE"}

        class Extractor:
            @staticmethod
            def extract(objective,candidate,provenance,relevance,timeout=15):
                return {
                    "status":"EVIDENCE_EXTRACTION_BLOCKED",
                    "reason":"TEST_STOPS_AFTER_SOURCE_SELECTION",
                    "source_url":candidate["url"],
                }

        class Binder:
            @staticmethod
            def bind(*args,**kwargs):
                raise AssertionError("BINDER_MUST_NOT_RUN_WITHOUT_EXTRACTED_EVIDENCE")

        def fake(name):
            return {
                "open_web_source_candidate_discovery":Discovery,
                "source_candidate_provenance_verify":Provenance,
                "objective_relevance_bm25":self.relevance,
                "objective_evidence_unit_extract":Extractor,
                "objective_claim_operand_binding":Binder,
                "source_authority_binding_ror":Authority,
            }[name]

        self.front._load_sibling=fake
        try:
            d=self.decomp.decompose(goal)
            self.assertEqual(d["status"],"DECOMPOSED",d)
            out=self.front.run(goal,d,limit=4,timeout=2)
        finally:
            self.front._load_sibling=original

        self.assertEqual(out["relevance_query"],focused,out)
        selected=out["objective_relevance_verifications"][0]["candidate"]
        self.assertEqual(selected["url"],"https://science.example/reference-records",out)
        ranked=out["objective_relevance_verifications"][0]["relevance"]
        self.assertEqual(ranked["objective"],focused,ranked)
        self.assertNotIn("assess",ranked["query_tokens"],ranked)
        self.assertIn("mg1655",ranked["query_tokens"],ranked)
        self.assertEqual(out["evidence_extracted_candidate_count"],0,out)
        self.assertEqual(out["claim_relation_evaluated_count"],0,out)

if __name__=="__main__":
    unittest.main(verbosity=2)
