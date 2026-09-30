#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    path=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("bib_live_test_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

class BibliographicLiveRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load("open_research_source_frontend")
        cls.rank=load("objective_relevance_bm25")
        cls.dec=load("broad_objective_decompose")
        cls.prov=load("source_candidate_provenance_verify")

    def _run_frontend(self, objective, discovery_impl, verifier_impl):
        original=self.front._load_sibling
        seen={"extract":[]}

        class Extractor:
            @staticmethod
            def extract(objective,candidate,provenance,relevance,timeout=15):
                seen["extract"].append({
                    "candidate":candidate,
                    "provenance":provenance,
                    "relevance":relevance,
                })
                return {
                    "status":"EVIDENCE_EXTRACTION_BLOCKED",
                    "reason":"QUALIFIER_STOPS_AFTER_LIVE_SOURCE_SELECTION",
                    "source_url":provenance.get("final_url"),
                }

        class Binder:
            @staticmethod
            def bind(*args,**kwargs):
                raise AssertionError("BINDER_MUST_NOT_RUN_WITHOUT_EXTRACTED_EVIDENCE")

        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=15):
                return {"status":"AUTHORITY_UNRESOLVED","reason":"TEST_FIXTURE"}

        def fake(name):
            return {
                "open_web_source_candidate_discovery":discovery_impl,
                "source_candidate_provenance_verify":verifier_impl,
                "objective_relevance_bm25":self.rank,
                "objective_evidence_unit_extract":Extractor,
                "objective_claim_operand_binding":Binder,
                "source_authority_binding_ror":Authority,
            }[name]

        self.front._load_sibling=fake
        try:
            d=self.dec.decompose(objective)
            self.assertEqual(d["status"],"DECOMPOSED",d)
            out=self.front.run(objective,d,limit=8,timeout=2)
        finally:
            self.front._load_sibling=original
        return out,seen

    def test_bibliographic_candidate_enters_relevance_then_direct_live_provenance(self):
        objective=(
            "Evaluate whether RFC 9110 obsoletes RFC 7230. "
            "Use authoritative primary technical evidence and independently verify the result."
        )
        weak={
            "url":"https://generic.example/standards",
            "host":"generic.example",
            "title":"How to evaluate technical standards",
            "snippet":"General standards evaluation guidance.",
            "discovery_backend":"BING_RSS",
        }
        scholarly={
            "url":"https://doi.org/10.1000/rfc-study",
            "host":"doi.org",
            "doi":"10.1000/rfc-study",
            "title":"RFC 9110 and RFC 7230 protocol transition",
            "discovery_backend":"CROSSREF",
        }
        class Discovery:
            @staticmethod
            def discover(q,limit=12,timeout=15):
                return {"status":"CANDIDATES_DISCOVERED","query":"rfc 9110 obsoletes rfc 7230","candidates":[weak,scholarly]}
        class Verifier:
            @staticmethod
            def verify(candidate,timeout=15):
                if candidate.get("doi"):
                    return {
                        "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                        "candidate_url":candidate["url"],
                        "doi":candidate["doi"],
                        "record_title":"RFC 9110 obsoletes RFC 7230 protocol transition",
                        "publisher":"Example Society",
                    }
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "final_url":candidate["url"],
                    "final_host":candidate["host"],
                }
            @staticmethod
            def verify_live(candidate,timeout=15):
                self.assertEqual(candidate["url"],scholarly["url"])
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "final_url":"https://publisher.example/rfc-study",
                    "final_host":"publisher.example",
                }
        out,seen=self._run_frontend(objective,Discovery,Verifier)
        self.assertEqual(out["bibliographic_provenance_verified_candidate_count"],1,out)
        selected=out["objective_relevance_verifications"][0]
        self.assertEqual(selected["candidate"]["url"],scholarly["url"],out)
        self.assertEqual(
            selected["retrieval_refinement"]["status"],
            "BIBLIOGRAPHIC_CANDIDATE_DIRECT_LIVE_RETRIEVAL_VERIFIED",
            out,
        )
        self.assertEqual(len(seen["extract"]),1,out)
        self.assertEqual(
            seen["extract"][0]["provenance"]["status"],
            "RETRIEVAL_PROVENANCE_VERIFIED",
        )
        self.assertEqual(
            seen["extract"][0]["candidate"]["url"],
            scholarly["url"],
        )

    def test_failed_direct_doi_retrieval_uses_metadata_title_to_find_live_source(self):
        objective=(
            "Assess whether lithium ion battery calendar aging increases with storage temperature. "
            "Use authoritative experimental evidence and preserve provenance."
        )
        weak={
            "url":"https://generic.example/aging",
            "host":"generic.example",
            "title":"Aging and temperature words",
            "snippet":"General vocabulary.",
            "discovery_backend":"BING_RSS",
        }
        scholarly={
            "url":"https://doi.org/10.1000/battery-aging",
            "host":"doi.org",
            "doi":"10.1000/battery-aging",
            "title":"Lithium ion battery calendar aging and storage temperature",
            "discovery_backend":"CROSSREF",
        }
        refined={
            "url":"https://lab.example/battery-calendar-aging",
            "host":"lab.example",
            "title":"Lithium ion battery calendar aging storage temperature experiment",
            "snippet":"Measured calendar aging across storage temperatures.",
            "discovery_backend":"BING_RSS",
        }
        class Discovery:
            calls=[]
            @staticmethod
            def discover(q,limit=12,timeout=15):
                Discovery.calls.append(q)
                if q=="Lithium ion battery calendar aging and storage temperature":
                    return {"status":"CANDIDATES_DISCOVERED","query":q,"candidates":[refined]}
                return {"status":"CANDIDATES_DISCOVERED","query":"battery aging temperature","candidates":[weak,scholarly]}
        class Verifier:
            @staticmethod
            def verify(candidate,timeout=15):
                if candidate.get("doi"):
                    return {
                        "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                        "candidate_url":candidate["url"],
                        "record_title":"Lithium ion battery calendar aging and storage temperature",
                        "doi":candidate["doi"],
                    }
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "final_url":candidate["url"],
                    "final_host":candidate["host"],
                }
            @staticmethod
            def verify_live(candidate,timeout=15):
                if candidate.get("doi"):
                    return {"status":"UNVERIFIED","reason":"LIVE_RETRIEVAL_FAILED"}
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "final_url":candidate["url"],
                    "final_host":candidate["host"],
                }
        out,seen=self._run_frontend(objective,Discovery,Verifier)
        ref=out["objective_relevance_verifications"][0]["retrieval_refinement"]
        self.assertEqual(ref["status"],"BIBLIOGRAPHIC_METADATA_ANCHORED_LIVE_RETRIEVAL_SELECTED",out)
        self.assertIn("Lithium ion battery calendar aging and storage temperature",Discovery.calls)
        self.assertEqual(len(seen["extract"]),1,out)
        self.assertEqual(seen["extract"][0]["candidate"]["url"],refined["url"])
        self.assertEqual(
            seen["extract"][0]["relevance"]["objective"],
            objective,
            seen["extract"][0]["relevance"],
        )

    def test_bibliographic_winner_without_live_bridge_fails_closed_before_extraction(self):
        objective=(
            "Determine whether Python 3.13 supports free-threaded execution. "
            "Use authoritative technical evidence and preserve provenance."
        )
        scholarly={
            "url":"https://doi.org/10.1000/python-threading",
            "host":"doi.org",
            "doi":"10.1000/python-threading",
            "title":"Python 3.13 free-threaded execution",
            "discovery_backend":"CROSSREF",
        }
        class Discovery:
            @staticmethod
            def discover(q,limit=12,timeout=15):
                if q=="Python 3.13 free-threaded execution":
                    return {"status":"DISCOVERY_UNAVAILABLE","query":q,"candidates":[]}
                return {"status":"CANDIDATES_DISCOVERED","query":"python 3.13 free threaded execution","candidates":[scholarly]}
        class Verifier:
            @staticmethod
            def verify(candidate,timeout=15):
                return {
                    "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "record_title":"Python 3.13 free-threaded execution",
                    "doi":candidate["doi"],
                }
            @staticmethod
            def verify_live(candidate,timeout=15):
                return {"status":"UNVERIFIED","reason":"LIVE_RETRIEVAL_FAILED"}
        out,seen=self._run_frontend(objective,Discovery,Verifier)
        self.assertEqual(len(seen["extract"]),0,out)
        self.assertEqual(out["evidence_extracted_candidate_count"],0,out)
        self.assertEqual(
            out["next_required_capability"],
            "MODEL_INDEPENDENT_METADATA_ANCHORED_LIVE_RETRIEVAL_FROM_BIBLIOGRAPHIC_CANDIDATE_V1",
            out,
        )

    def test_ordinary_live_candidate_path_is_preserved(self):
        objective=(
            "Evaluate whether RFC 9110 defines HTTP semantics. "
            "Use authoritative technical evidence and preserve provenance."
        )
        live={
            "url":"https://www.rfc-editor.org/rfc/rfc9110",
            "host":"www.rfc-editor.org",
            "title":"RFC 9110 HTTP Semantics",
            "snippet":"HTTP semantics specification.",
            "discovery_backend":"BING_RSS",
        }
        class Discovery:
            @staticmethod
            def discover(q,limit=12,timeout=15):
                return {"status":"CANDIDATES_DISCOVERED","query":"rfc 9110 http semantics","candidates":[live]}
        class Verifier:
            @staticmethod
            def verify(candidate,timeout=15):
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "final_url":candidate["url"],
                    "final_host":candidate["host"],
                }
            @staticmethod
            def verify_live(candidate,timeout=15):
                raise AssertionError("ORDINARY_LIVE_PATH_MUST_NOT_REVERIFY")
        out,seen=self._run_frontend(objective,Discovery,Verifier)
        self.assertEqual(out["retrieval_provenance_verified_candidate_count"],1,out)
        self.assertEqual(out["bibliographic_provenance_verified_candidate_count"],0,out)
        self.assertEqual(len(seen["extract"]),1,out)
        self.assertEqual(seen["extract"][0]["candidate"]["url"],live["url"])

    def test_verify_live_bypasses_doi_bibliographic_short_circuit(self):
        candidate={"url":"https://doi.org/10.1000/test","doi":"10.1000/test"}
        old=self.prov._fetch
        calls=[]
        def fake(url,timeout,accept="*/*"):
            calls.append((url,accept))
            return (
                b"<html><title>Resolved article</title><p>evidence</p></html>",
                "text/html",
                200,
                "https://publisher.example/article",
            )
        self.prov._fetch=fake
        try:
            out=self.prov.verify_live(candidate,timeout=2)
        finally:
            self.prov._fetch=old
        self.assertEqual(out["status"],"RETRIEVAL_PROVENANCE_VERIFIED",out)
        self.assertEqual(out["final_url"],"https://publisher.example/article",out)
        self.assertEqual(calls[0][0],candidate["url"])
        self.assertNotIn("api.crossref.org",calls[0][0])

if __name__=="__main__":
    unittest.main(verbosity=2)
