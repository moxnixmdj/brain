#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BC=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BC/(name+".py")
    spec=importlib.util.spec_from_file_location("test_"+name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m

class SourceAdmissionMetadataRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load("open_research_source_frontend")
        cls.rank=load("objective_relevance_bm25")
        cls.discovery=load("open_web_source_candidate_discovery")
        cls.extract=load("objective_evidence_unit_extract")
        cls.focus=load("research_query_focus")

    def test_weak_positive_overlap_is_not_admitted(self):
        objective=(
            "Determine whether cryogenic methane storage pressure exceeded safe "
            "tank pressure during orbital thermal cycling."
        )
        out=self.rank.rank(objective,[{
            "url":"https://example.org/year",
            "title":"Orbital storage report",
            "snippet":"Annual overview and index.",
        }])
        self.assertEqual(out["status"],"RELEVANCE_UNRESOLVED",out)
        self.assertEqual(out["reason"],"INSUFFICIENT_QUERY_TERM_COVERAGE",out)
        row=out["ranked_candidates"][0]
        self.assertGreater(row["lexical_relevance_score"],0,row)
        self.assertEqual(
            row["lexical_admission_status"],
            "REJECTED_INSUFFICIENT_QUERY_TERM_COVERAGE",
            row,
        )
        self.assertGreater(
            row["minimum_matched_terms_for_admission"],
            row["matched_term_count"],
            row,
        )

    def test_strong_subject_candidate_is_admitted(self):
        objective=(
            "Determine whether cryogenic methane storage pressure exceeded safe "
            "tank pressure during orbital thermal cycling."
        )
        out=self.rank.rank(objective,[{
            "url":"https://example.org/experiment",
            "title":"Cryogenic methane storage tank pressure during orbital thermal cycling",
            "snippet":"Measured storage pressure in a cryogenic methane tank.",
        }])
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        row=next(
            x for x in out["ranked_candidates"]
            if x["original_index"]==out["top_candidate_original_index"]
        )
        self.assertEqual(row["lexical_admission_status"],"ADMITTED",row)

    def test_metadata_candidate_can_win_then_refine_to_live_source_once(self):
        objective=(
            "Determine whether cryogenic methane storage pressure exceeded safe "
            "tank pressure during orbital thermal cycling."
        )
        calls=[]
        extracted=[]
        front=self.front
        real_loader=front._load_sibling

        class Discovery:
            @staticmethod
            def discover(goal,limit=12,timeout=15,query_override=None):
                calls.append(query_override)
                if query_override is None:
                    return {
                        "status":"CANDIDATES_DISCOVERED",
                        "candidates":[
                            {
                                "url":"https://weak.example/year",
                                "title":"Orbital storage report",
                                "snippet":"Annual overview.",
                            },
                            {
                                "url":"https://doi.org/10.1234/example.2026.1",
                                "doi":"10.1234/example.2026.1",
                                "title":"Cryogenic methane storage tank pressure during orbital thermal cycling",
                                "source_class":"SCHOLARLY_REGISTRY_CANDIDATE",
                            },
                        ],
                    }
                return {
                    "status":"CANDIDATES_DISCOVERED",
                    "query":query_override,
                    "query_source":"VERIFIED_METADATA_ANCHORED_REFINEMENT",
                    "candidates":[{
                        "url":"https://live.example/experiment",
                        "title":"Cryogenic methane storage tank pressure during orbital thermal cycling experiment",
                        "snippet":"Measured methane storage tank pressure during orbital thermal cycling.",
                    }],
                }

        class Verifier:
            @staticmethod
            def verify(candidate,timeout=15):
                if candidate.get("doi"):
                    return {
                        "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                        "doi":candidate["doi"],
                        "record_title":"Cryogenic methane storage tank pressure during orbital thermal cycling",
                        "record_url":candidate["url"],
                    }
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "final_url":candidate["url"],
                    "final_host":candidate["url"].split("/")[2],
                }

        class Evidence:
            @staticmethod
            def extract(goal,candidate,provenance,relevance,timeout=20):
                extracted.append((candidate,provenance,relevance))
                return {
                    "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
                    "evidence_unit_count":1,
                    "source_url":candidate["url"],
                    "evidence_units":[{"evidence_unit_id":"u1","text":"measured evidence"}],
                }

        class Claims:
            @staticmethod
            def bind(goal,extraction,evaluate_relation=True):
                return {"status":"UNBOUND","reason":"TEST_STOPS_AFTER_SOURCE_REPAIR"}

        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=15):
                return {"status":"UNVERIFIED","reason":"NOT_REQUIRED_FOR_TEST"}

        mapping={
            "open_web_source_candidate_discovery":Discovery,
            "source_candidate_provenance_verify":Verifier,
            "objective_relevance_bm25":self.rank,
            "objective_evidence_unit_extract":Evidence,
            "objective_claim_operand_binding":Claims,
            "source_authority_binding_ror":Authority,
            "research_query_focus":self.focus,
        }
        try:
            front._load_sibling=lambda name:mapping[name]
            decomposition={
                "status":"DECOMPOSED",
                "objective":objective,
                "roles":[{"role":"SOURCE_DISCOVERY"}],
            }
            out=front.run(objective,decomposition,limit=8,timeout=5)
        finally:
            front._load_sibling=real_loader

        self.assertEqual(len(calls),2,calls)
        self.assertIsNone(calls[0],calls)
        self.assertIsNotNone(calls[1],calls)
        self.assertIn("10.1234/example.2026.1",calls[1])
        self.assertIn("cryogenic",calls[1].lower())
        self.assertEqual(
            out["metadata_anchored_retrieval_refinement"]["status"],
            "LIVE_RETRIEVAL_REFINED_AND_SELECTED",
            out,
        )
        self.assertEqual(
            out["metadata_anchored_retrieval_refinement"]["attempt_count"],1,out
        )
        self.assertFalse(
            out["metadata_anchored_retrieval_refinement"][
                "bibliographic_metadata_used_as_evidence"
            ],
            out,
        )
        self.assertEqual(out["bibliographic_provenance_verified_candidate_count"],1,out)
        self.assertEqual(out["relevance_verified_candidate_count"],1,out)
        self.assertEqual(out["evidence_extracted_candidate_count"],1,out)
        self.assertEqual(len(extracted),1,extracted)
        self.assertEqual(extracted[0][0]["url"],"https://live.example/experiment",extracted)
        self.assertEqual(
            extracted[0][1]["status"],"RETRIEVAL_PROVENANCE_VERIFIED",extracted
        )

    def test_irrelevant_bibliographic_metadata_cannot_hijack_strong_live_source(self):
        objective=(
            "Determine whether cryogenic methane storage pressure exceeded safe "
            "tank pressure during orbital thermal cycling."
        )
        calls=[]
        front=self.front
        real_loader=front._load_sibling

        class Discovery:
            @staticmethod
            def discover(goal,limit=12,timeout=15,query_override=None):
                calls.append(query_override)
                return {
                    "status":"CANDIDATES_DISCOVERED",
                    "candidates":[
                        {
                            "url":"https://live.example/experiment",
                            "title":"Cryogenic methane storage tank pressure during orbital thermal cycling",
                            "snippet":"Measured methane tank pressure.",
                        },
                        {
                            "url":"https://doi.org/10.9999/unrelated",
                            "doi":"10.9999/unrelated",
                            "title":"Coastal bird migration census",
                        },
                    ],
                }

        class Verifier:
            @staticmethod
            def verify(candidate,timeout=15):
                if candidate.get("doi"):
                    return {
                        "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                        "doi":candidate["doi"],
                        "record_title":candidate["title"],
                    }
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "final_url":candidate["url"],
                    "final_host":"live.example",
                }

        class Evidence:
            @staticmethod
            def extract(goal,candidate,provenance,relevance,timeout=20):
                return {
                    "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
                    "evidence_unit_count":1,
                    "source_url":candidate["url"],
                    "evidence_units":[{"evidence_unit_id":"u1","text":"measured evidence"}],
                }

        class Claims:
            @staticmethod
            def bind(goal,extraction,evaluate_relation=True):
                return {"status":"UNBOUND","reason":"TEST_STOPS_AFTER_SOURCE_REPAIR"}

        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=15):
                return {"status":"UNVERIFIED"}

        mapping={
            "open_web_source_candidate_discovery":Discovery,
            "source_candidate_provenance_verify":Verifier,
            "objective_relevance_bm25":self.rank,
            "objective_evidence_unit_extract":Evidence,
            "objective_claim_operand_binding":Claims,
            "source_authority_binding_ror":Authority,
            "research_query_focus":self.focus,
        }
        try:
            front._load_sibling=lambda name:mapping[name]
            decomposition={
                "status":"DECOMPOSED",
                "objective":objective,
                "roles":[{"role":"SOURCE_DISCOVERY"}],
            }
            out=front.run(objective,decomposition,limit=8,timeout=5)
        finally:
            front._load_sibling=real_loader

        self.assertEqual(calls,[None],calls)
        self.assertEqual(
            out["metadata_anchored_retrieval_refinement"]["status"],"NOT_REQUIRED",out
        )
        self.assertEqual(out["evidence_extracted_candidate_count"],1,out)
        selected=out["objective_relevance_verifications"][0]["candidate"]
        self.assertEqual(selected["url"],"https://live.example/experiment",out)

    def test_weak_live_only_stops_before_evidence_extraction(self):
        objective=(
            "Determine whether cryogenic methane storage pressure exceeded safe "
            "tank pressure during orbital thermal cycling."
        )
        front=self.front
        real_loader=front._load_sibling
        extraction_calls=[]

        class Discovery:
            @staticmethod
            def discover(goal,limit=12,timeout=15,query_override=None):
                return {
                    "status":"CANDIDATES_DISCOVERED",
                    "candidates":[{
                        "url":"https://weak.example/year",
                        "title":"Orbital storage report",
                        "snippet":"Annual overview.",
                    }],
                }

        class Verifier:
            @staticmethod
            def verify(candidate,timeout=15):
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "final_url":candidate["url"],
                    "final_host":"weak.example",
                }

        class Evidence:
            @staticmethod
            def extract(*args,**kwargs):
                extraction_calls.append(1)
                raise AssertionError("weak source must not reach evidence extraction")

        class Claims:
            @staticmethod
            def bind(*args,**kwargs):
                raise AssertionError("weak source must not reach claim binding")

        class Authority:
            @staticmethod
            def bind_candidate(*args,**kwargs):
                raise AssertionError("weak source must not reach authority lookup")

        mapping={
            "open_web_source_candidate_discovery":Discovery,
            "source_candidate_provenance_verify":Verifier,
            "objective_relevance_bm25":self.rank,
            "objective_evidence_unit_extract":Evidence,
            "objective_claim_operand_binding":Claims,
            "source_authority_binding_ror":Authority,
            "research_query_focus":self.focus,
        }
        try:
            front._load_sibling=lambda name:mapping[name]
            decomposition={
                "status":"DECOMPOSED",
                "objective":objective,
                "roles":[{"role":"SOURCE_DISCOVERY"}],
            }
            out=front.run(objective,decomposition,limit=8,timeout=5)
        finally:
            front._load_sibling=real_loader

        self.assertEqual(extraction_calls,[],out)
        self.assertEqual(out["relevance_verified_candidate_count"],0,out)
        rel=out["objective_relevance_verifications"][0]["relevance"]
        self.assertEqual(rel["reason"],"INSUFFICIENT_QUERY_TERM_COVERAGE",rel)

    def test_discovery_query_override_is_bounded_and_explicit(self):
        seen=[]
        old=(self.discovery._bing_rss,self.discovery._ddg,self.discovery._crossref)
        def backend(name):
            def fn(query,limit,timeout):
                seen.append((name,query))
                return ([{
                    "url":"https://example.org/"+name.lower(),
                    "title":"cryogenic methane storage pressure",
                    "source_class":"OPEN_WEB_SEARCH_CANDIDATE",
                    "discovery_backend":name,
                }],{"backend":name,"candidate_count":1})
            return fn
        try:
            self.discovery._bing_rss=backend("BING_RSS")
            self.discovery._ddg=backend("DUCKDUCKGO_HTML")
            self.discovery._crossref=backend("CROSSREF")
            out=self.discovery.discover(
                "Determine whether cryogenic methane storage pressure changed.",
                limit=6,timeout=3,
                query_override="10.1234/example cryogenic methane storage pressure",
            )
        finally:
            self.discovery._bing_rss,self.discovery._ddg,self.discovery._crossref=old
        self.assertEqual(out["query_source"],"VERIFIED_METADATA_ANCHORED_REFINEMENT",out)
        self.assertEqual(len(seen),3,seen)
        self.assertTrue(all(x[1]==out["query"] for x in seen),seen)

    def test_extractor_rejects_nonadmitted_bm25_receipt(self):
        objective="Determine whether cryogenic methane storage pressure changed."
        candidate={"url":"https://example.org/report"}
        provenance={
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "candidate_url":"https://example.org/report",
            "final_url":"https://example.org/report",
        }
        relevance={
            "status":"LEXICAL_RELEVANCE_RANKED",
            "verification_method":"DETERMINISTIC_BM25_WITH_QUERY_COMPLEXITY_SCALED_TERM_COVERAGE_ADMISSION",
            "output_verified":True,
            "objective":objective,
            "top_candidate_original_index":0,
            "ranked_candidates":[{
                "original_index":0,
                "candidate":candidate,
                "lexical_relevance_score":1.0,
                "matched_terms":["storage"],
                "lexical_admission_status":"REJECTED_INSUFFICIENT_QUERY_TERM_COVERAGE",
            }],
        }
        url,reason=self.extract._qualified_relevance_source(
            objective,candidate,provenance,relevance
        )
        self.assertIsNone(url)
        self.assertEqual(reason,"RELEVANCE_QUERY_TERM_COVERAGE_ADMISSION_REQUIRED")

    def test_repair_contains_no_parent_task_or_source_literals(self):
        paths=[
            BC/"open_research_source_frontend.py",
            BC/"objective_relevance_bm25.py",
            BC/"open_web_source_candidate_discovery.py",
            BC/"objective_evidence_unit_extract.py",
        ]
        joined="\n".join(p.read_text(encoding="utf-8").lower() for p in paths)
        for forbidden in (
            "kamchatka","tsunami","simple.wikipedia","swot satellite","1 meter",
        ):
            self.assertNotIn(forbidden,joined)

if __name__=="__main__":
    unittest.main(verbosity=2)
