#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, sys, unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[2]

def load(rel,name):
    p=ROOT/rel
    s=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m

class ScholarlyAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rank=load("canonical/runtime/bound_capabilities/objective_relevance_bm25.py","scholarly_rank_test")
        cls.discovery=load("canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py","scholarly_discovery_test")
        cls.prov=load("canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py","scholarly_prov_test")
        cls.front=load("canonical/runtime/bound_capabilities/open_research_source_frontend.py","scholarly_front_test")

    def test_low_subject_coverage_positive_bm25_is_not_admitted(self):
        objective="Assess alpha beta gamma delta epsilon zeta eta theta"
        out=self.rank.rank(objective,[{"title":"alpha annual index","snippet":"generic page"}])
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertGreater(out["ranked_candidates"][0]["lexical_relevance_score"],0,out)
        self.assertFalse(out["top_candidate_admission"]["verified"],out)
        self.assertEqual(out["top_candidate_admission"]["matched_term_count"],1,out)
        self.assertEqual(out["top_candidate_admission"]["required_matched_term_count"],2,out)

    def test_high_subject_coverage_is_admitted_without_absolute_score_gate(self):
        objective="Assess alpha beta gamma delta epsilon zeta eta theta"
        out=self.rank.rank(objective,[{"title":"alpha beta gamma delta epsilon","snippet":"technical record"}])
        self.assertTrue(out["top_candidate_admission"]["verified"],out)
        self.assertGreaterEqual(out["top_candidate_admission"]["matched_term_count"],2,out)

    def test_discovery_query_override_preserves_frozen_objective(self):
        seen=[]
        old_bing,old_ddg,old_cross=self.discovery._bing_rss,self.discovery._ddg,self.discovery._crossref
        def fake(query,limit,timeout):
            seen.append(query)
            return ([{"url":"https://example.org/x","host":"example.org","title":"x","source_class":"OPEN_WEB_SEARCH_CANDIDATE","discovery_backend":"BING_RSS","authority_status":"UNVERIFIED"}],{"backend":"fake","candidate_count":1})
        try:
            self.discovery._bing_rss=fake
            self.discovery._ddg=lambda q,l,t:([],{"backend":"fake-ddg","candidate_count":0})
            self.discovery._crossref=lambda q,l,t:([],{"backend":"fake-crossref","candidate_count":0})
            out=self.discovery.discover("Assess alpha beta gamma",query_override="alpha beta scholarly title")
        finally:
            self.discovery._bing_rss, self.discovery._ddg, self.discovery._crossref=old_bing,old_ddg,old_cross
        self.assertEqual(seen,["alpha beta scholarly title"])
        self.assertEqual(out["objective"],"Assess alpha beta gamma")
        self.assertEqual(out["query_origin"],"METADATA_REFINED_OVERRIDE")

    def test_bibliographic_materialization_is_separate_live_receipt(self):
        candidate={"url":"https://doi.org/10.1234/example","doi":"10.1234/example","title":"alpha beta gamma"}
        verification={
          "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
          "candidate_url":candidate["url"],
          "doi":"10.1234/example",
          "record_title":"alpha beta gamma",
          "verification_method":"CROSSREF_DOI_RECORD",
        }
        old=self.prov._fetch
        self.prov._fetch=lambda url,timeout,accept="*/*":(
          b"<html><title>Publisher article</title><body>alpha beta gamma</body></html>",
          "text/html",200,"https://journal.example/article"
        )
        try:
            out=self.prov.materialize_retrieval(candidate,verification)
        finally:
            self.prov._fetch=old
        self.assertEqual(out["status"],"RETRIEVAL_PROVENANCE_VERIFIED",out)
        self.assertEqual(out["verification_method"],"BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION",out)
        self.assertEqual(out["bibliographic_provenance_status"],"VERIFIED",out)
        self.assertEqual(out["final_url"],"https://journal.example/article",out)
        self.assertEqual(out["authority_status"],"RETRIEVABILITY_VERIFIED__FACT_AUTHORITY_UNVERIFIED",out)

    def _decomp(self,objective):
        return {"status":"DECOMPOSED","objective":objective,"question_shape":"OPEN_RESEARCH_ASSESSMENT","roles":[{"role":"SOURCE_DISCOVERY"}]}

    def test_frontend_ranks_bibliographic_candidate_and_materializes_before_extraction(self):
        objective="Assess alpha beta gamma delta epsilon zeta eta theta"
        class Discovery:
            @staticmethod
            def discover(obj,limit=12,timeout=15,query_override=None):
                self.assertIsNone(query_override)
                return {"status":"CANDIDATES_DISCOVERED","candidates":[
                  {"url":"https://example.org/year","title":"alpha annual index"},
                  {"url":"https://doi.org/10.1234/s","doi":"10.1234/s","title":"alpha beta gamma delta epsilon technical study"},
                ]}
        class Provenance:
            @staticmethod
            def verify(candidate,timeout=15):
                if "doi.org" in candidate["url"]:
                    return {"status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED","candidate_url":candidate["url"],"doi":"10.1234/s","record_title":candidate["title"],"verification_method":"CROSSREF_DOI_RECORD"}
                return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","candidate_url":candidate["url"],"final_url":candidate["url"],"final_host":"example.org"}
            @staticmethod
            def materialize_retrieval(candidate,verification,timeout=15):
                return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","candidate_url":candidate["url"],"final_url":"https://journal.example/article","final_host":"journal.example","bibliographic_provenance_status":"VERIFIED"}
        class Extractor:
            @staticmethod
            def extract(obj,candidate,provenance,relevance,timeout=20,max_units=10,fetch=None):
                self.assertIn("doi.org",candidate["url"])
                self.assertEqual(provenance["final_url"],"https://journal.example/article")
                self.assertTrue(relevance["top_candidate_admission"]["verified"])
                return {"status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED","evidence_unit_count":1,"source_url":provenance["final_url"],"evidence_units":[]}
        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=15): return {"status":"UNVERIFIED"}
        class Binder:
            @staticmethod
            def bind(obj,extraction,evaluate_relation=True): return {"status":"UNBOUND","reason":"NOT_PART_OF_SOURCE_ADMISSION_TEST"}
        real=self.front._load_sibling
        def loader(name):
            return {
              "open_web_source_candidate_discovery":Discovery,
              "source_candidate_provenance_verify":Provenance,
              "objective_evidence_unit_extract":Extractor,
              "source_authority_binding_ror":Authority,
              "objective_claim_operand_binding":Binder,
            }.get(name) or real(name)
        with patch.object(self.front,"_load_sibling",side_effect=loader):
            out=self.front.run(objective,self._decomp(objective))
        self.assertEqual(out["selected_source_origin"],"BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION",out)
        self.assertEqual(out["bibliographic_provenance_verified_candidate_count"],1,out)
        self.assertEqual(out["evidence_extracted_candidate_count"],1,out)

    def test_failed_materialization_gets_one_metadata_refined_live_retry(self):
        objective="Assess alpha beta gamma delta epsilon zeta eta theta"
        calls=[]
        class Discovery:
            @staticmethod
            def discover(obj,limit=12,timeout=15,query_override=None):
                calls.append(query_override)
                if query_override is None:
                    return {"status":"CANDIDATES_DISCOVERED","candidates":[
                      {"url":"https://example.org/year","title":"alpha annual index"},
                      {"url":"https://doi.org/10.1234/s","doi":"10.1234/s","title":"alpha beta gamma delta epsilon technical study"},
                    ]}
                return {"status":"CANDIDATES_DISCOVERED","candidates":[
                  {"url":"https://journal.example/live","title":"alpha beta gamma delta epsilon technical result"}
                ]}
        class Provenance:
            @staticmethod
            def verify(candidate,timeout=15):
                if "doi.org" in candidate["url"]:
                    return {"status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED","candidate_url":candidate["url"],"doi":"10.1234/s","record_title":candidate["title"],"verification_method":"CROSSREF_DOI_RECORD"}
                return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","candidate_url":candidate["url"],"final_url":candidate["url"],"final_host":candidate["url"].split("/")[2]}
            @staticmethod
            def materialize_retrieval(candidate,verification,timeout=15):
                return {"status":"UNVERIFIED","reason":"BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION_FAILED"}
        class Extractor:
            @staticmethod
            def extract(obj,candidate,provenance,relevance,timeout=20,max_units=10,fetch=None):
                self.assertEqual(candidate["url"],"https://journal.example/live")
                return {"status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED","evidence_unit_count":1,"source_url":candidate["url"],"evidence_units":[]}
        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=15): return {"status":"UNVERIFIED"}
        class Binder:
            @staticmethod
            def bind(obj,extraction,evaluate_relation=True): return {"status":"UNBOUND","reason":"NOT_PART_OF_SOURCE_ADMISSION_TEST"}
        real=self.front._load_sibling
        def loader(name):
            return {
              "open_web_source_candidate_discovery":Discovery,
              "source_candidate_provenance_verify":Provenance,
              "objective_evidence_unit_extract":Extractor,
              "source_authority_binding_ror":Authority,
              "objective_claim_operand_binding":Binder,
            }.get(name) or real(name)
        with patch.object(self.front,"_load_sibling",side_effect=loader):
            out=self.front.run(objective,self._decomp(objective))
        self.assertEqual(len(calls),2,calls)
        self.assertIsNone(calls[0])
        self.assertIn("alpha beta gamma",calls[1])
        self.assertEqual(out["selected_source_origin"],"BIBLIOGRAPHIC_METADATA_REFINED_LIVE_RETRIEVAL",out)
        self.assertEqual(out["evidence_extracted_candidate_count"],1,out)

if __name__=="__main__": unittest.main(verbosity=2)
