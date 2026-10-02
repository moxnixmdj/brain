#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]

def load(rel,name):
    p=ROOT/rel
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m

class ResearchQueryFocusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.focus=load("canonical/runtime/bound_capabilities/research_query_focus.py","focus_test")
        cls.discovery=load("canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py","discovery_focus_test")
        cls.rank=load("canonical/runtime/bound_capabilities/objective_relevance_bm25.py","relevance_focus_test")

    def test_genomics_focus_removes_orchestration_and_preserves_subject(self):
        objective=(
            "Assess whether the complete reference genome sequence length of Escherichia coli K-12 MG1655 "
            "is greater than the human mitochondrial reference genome sequence length. Use authoritative primary "
            "technical evidence and a real executable check. Autonomously discover and verify the relevant primary "
            "records, determine how to extract and interpret the two sequence lengths, choose and run a zero-cost "
            "verification method, identify material reference-version or sequence-scope limitations, independently "
            "verify the consequential result, and produce a decision-quality answer with provenance."
        )
        out=self.focus.focus(objective)
        self.assertEqual(out["status"],"FOCUSED",out)
        q=out["query"].lower()
        for required in ("escherichia","coli","k-12","mg1655","human","mitochondrial","genome","sequence","length"):
            self.assertIn(required,q,out)
        for forbidden in ("assess","authoritative","autonomously","verification","provenance"):
            self.assertNotIn(forbidden,q,out)

    def test_http2_focus_preserves_protocol_subject(self):
        objective=(
            "Assess whether the maximum permitted HTTP/2 initial stream flow-control window is greater than "
            "the protocol's default initial stream flow-control window. Use authoritative primary technical evidence "
            "and a real executable check."
        )
        out=self.focus.focus(objective)
        q=out["query"].lower()
        self.assertIn("http/2",q,out)
        self.assertIn("flow-control",q,out)
        self.assertIn("window",q,out)
        self.assertNotIn("assess",q,out)
        self.assertNotIn("executable",q,out)

    def test_discovery_uses_focused_query_but_preserves_original_objective(self):
        objective=(
            "Evaluate whether battery cycle life improved faster from 2020 to 2025 than from 2015 to 2020. "
            "Use authoritative technical evidence and run a zero-cost verification method."
        )
        seen=[]
        def fake(name):
            def fn(query,limit,timeout):
                seen.append((name,query))
                return ([{
                    "url":"https://example.org/"+name.lower(),
                    "host":"example.org",
                    "title":"battery cycle life 2020 2025",
                    "snippet":"technical record",
                    "source_class":"OPEN_WEB_SEARCH_CANDIDATE",
                    "discovery_backend":name,
                    "authority_status":"UNVERIFIED",
                }],{"backend":name,"candidate_count":1})
            return fn
        self.discovery._bing_rss=fake("BING_RSS")
        self.discovery._ddg=fake("DUCKDUCKGO_HTML")
        self.discovery._crossref=fake("CROSSREF")
        out=self.discovery.discover(objective,limit=10,timeout=3)
        self.assertEqual(out["status"],"CANDIDATES_DISCOVERED",out)
        self.assertEqual(out["objective"],objective,out)
        self.assertEqual(out["query"],out["query_focus"]["query"],out)
        self.assertTrue(seen,out)
        for _,query in seen:
            self.assertEqual(query,out["query"])
            self.assertNotIn("authoritative",query.lower())
            self.assertNotIn("verification",query.lower())

    def test_genomics_spelling_page_loses_to_subject_candidate(self):
        objective=(
            "Assess whether the complete reference genome sequence length of Escherichia coli K-12 MG1655 "
            "is greater than the human mitochondrial reference genome sequence length. Use authoritative primary "
            "technical evidence and a real executable check."
        )
        candidates=[
            {
              "url":"https://irrelevant.example/asess-or-assess",
              "title":"Asess or Assess? Correct spelling and English usage",
              "snippet":"Learn how to spell assess and use assess in a sentence."
            },
            {
              "url":"https://technical.example/ecoli",
              "title":"Escherichia coli K-12 MG1655 complete genome sequence",
              "snippet":"Complete reference genome sequence record and genome length for E. coli K-12 MG1655."
            },
            {
              "url":"https://technical.example/mitochondrial",
              "title":"Human mitochondrial reference genome sequence",
              "snippet":"Human mitochondrial reference sequence record and sequence length."
            },
        ]
        out=self.rank.rank(objective,candidates)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertNotEqual(out["top_candidate_original_index"],0,out)
        self.assertEqual(out["query_focus"]["status"],"FOCUSED",out)
        self.assertNotIn("assess",out["query_tokens"],out)
        self.assertEqual(out["semantic_entailment_status"],"UNVERIFIED",out)
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED",out)

    def test_http2_generic_assessment_page_loses(self):
        objective=(
            "Assess whether the maximum permitted HTTP/2 initial stream flow-control window is greater than "
            "the protocol's default initial stream flow-control window. Use authoritative primary technical evidence."
        )
        candidates=[
            {"url":"https://irrelevant.example/assessment","title":"How to assess technical skills","snippet":"Assessment methods and evaluation."},
            {"url":"https://technical.example/http2","title":"HTTP/2 stream flow-control window","snippet":"Protocol initial stream flow-control window and maximum permitted window."},
        ]
        out=self.rank.rank(objective,candidates)
        self.assertEqual(out["top_candidate_original_index"],1,out)

    def test_abbreviation_does_not_truncate_decision_subject(self):
        objective=(
            "Evaluate whether U.S. GDP growth was higher than U.S. CPI growth from 2021 to 2025. "
            "Use authoritative primary evidence and independently verify the result."
        )
        out=self.focus.focus(objective)
        self.assertEqual(out["status"],"FOCUSED",out)
        q=out["query"].lower()
        self.assertIn("u.s",q,out)
        self.assertIn("gdp",q,out)
        self.assertIn("cpi",q,out)
        self.assertIn("2021",q,out)
        self.assertIn("2025",q,out)
        self.assertNotIn("authoritative",q,out)

    def test_technical_use_and_primary_reference_terms_are_not_misread_as_control(self):
        objective=(
            "Assess whether CPU use is higher for primary reference workloads than for cached workloads. "
            "Use authoritative technical evidence and run a zero-cost verification method."
        )
        out=self.focus.focus(objective)
        self.assertEqual(out["status"],"FOCUSED",out)
        q=out["query"].lower()
        for required in ("cpu","use","primary","reference","workloads","cached"):
            self.assertIn(required,q,out)
        self.assertNotIn("authoritative",q,out)
        self.assertNotIn("verification",q,out)

    def test_single_sentence_control_tail_is_cut_only_at_clause_boundary(self):
        objective=(
            "Determine whether database run length differs by page size, using authoritative evidence "
            "and independently verify the result"
        )
        out=self.focus.focus(objective)
        self.assertEqual(out["status"],"FOCUSED",out)
        q=out["query"].lower()
        self.assertIn("database",q,out)
        self.assertIn("run",q,out)
        self.assertIn("length",q,out)
        self.assertIn("page",q,out)
        self.assertIn("size",q,out)
        self.assertNotIn("authoritative",q,out)

    def test_decision_role_admission_rejects_wrong_property_despite_operand_overlap(self):
        objective=(
            "Assess whether the thermal conductivity of AISI type 304 stainless steel "
            "is higher than the thermal conductivity of 6061 aluminum. "
            "Use authoritative primary technical evidence."
        )
        candidates=[
            {
              "url":"https://wrong.example/ignition",
              "title":"Ignition Temperature of Bulk 6061 Aluminum, 302 Stainless Steel and 1018 Carbon Steel in Oxygen",
              "snippet":"6061 aluminum and stainless steel ignition temperature measurements."
            },
            {
              "url":"https://right.example/304",
              "title":"Thermal conductivity of AISI type 304 stainless steel",
              "snippet":"Measured thermal conductivity for AISI type 304 stainless steel."
            },
            {
              "url":"https://right.example/6061",
              "title":"Thermal conductivity of 6061 aluminum",
              "snippet":"Measured thermal conductivity for 6061 aluminum."
            },
        ]
        out=self.rank.rank(objective,candidates)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        by_index={x["original_index"]:x for x in out["ranked_candidates"]}
        self.assertFalse(by_index[0]["decision_role_admitted"],out)
        self.assertTrue(by_index[1]["decision_role_admitted"],out)
        self.assertTrue(by_index[2]["decision_role_admitted"],out)
        self.assertNotEqual(out["top_candidate_original_index"],0,out)
        self.assertTrue(out["top_candidate_admission"]["decision_role_verified"],out)

    def test_decision_role_admission_rejects_wrong_operand_with_correct_property(self):
        objective=(
            "Determine whether France population growth is higher than Germany population growth."
        )
        candidates=[
            {
              "url":"https://wrong.example/spain",
              "title":"Spain population growth",
              "snippet":"Population growth estimate for Spain."
            },
            {
              "url":"https://right.example/france",
              "title":"France population growth",
              "snippet":"Population growth estimate for France."
            },
        ]
        out=self.rank.rank(objective,candidates)
        by_index={x["original_index"]:x for x in out["ranked_candidates"]}
        self.assertFalse(by_index[0]["decision_role_admitted"],out)
        self.assertTrue(by_index[1]["decision_role_admitted"],out)
        self.assertEqual(out["top_candidate_original_index"],1,out)

    def test_focus_is_deterministic_and_model_free(self):
        objective="Compare sodium battery energy density with lithium battery energy density."
        a=self.focus.focus(objective)
        b=self.focus.focus(objective)
        self.assertEqual(a,b)
        self.assertEqual(a["model_dependency_count"],0)
        self.assertEqual(a["incremental_spend_usd"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
