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
    spec=importlib.util.spec_from_file_location("scholarly_admission_test_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def decomposition(objective):
    return {
        "status":"DECOMPOSED",
        "objective":objective,
        "question_shape":"BOOLEAN_ASSESSMENT",
        "roles":[{"role":"SOURCE_DISCOVERY"}],
    }

class ScholarlyProvenanceAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load("open_research_source_frontend")
        cls.rank=load("objective_relevance_bm25")
        cls.prov=load("source_candidate_provenance_verify")

    def _run(self,objective,candidates,verify_map,materialize_impl,extract_impl):
        front=self.front
        original=front._load_sibling
        materialized=[]

        class Discovery:
            @staticmethod
            def discover(obj,limit=12,timeout=15):
                return {
                    "status":"CANDIDATES_DISCOVERED",
                    "objective":obj,
                    "query":"RFC 9110 HTTP Semantics RFC 7230",
                    "candidates":candidates,
                }

        class Verifier:
            @staticmethod
            def verify(candidate,timeout=15):
                return dict(verify_map[candidate["url"]])
            @staticmethod
            def materialize(candidate,timeout=15):
                materialized.append(candidate["url"])
                return materialize_impl(candidate)

        class Extractor:
            @staticmethod
            def extract(obj,candidate,provenance,relevance,timeout=15):
                return extract_impl(obj,candidate,provenance,relevance)

        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=15):
                return {"status":"UNVERIFIED","reason":"TEST_FIXTURE"}

        class Binder:
            @staticmethod
            def bind(*args,**kwargs):
                raise AssertionError("BINDER_MUST_NOT_RUN_WITHOUT_EXTRACTED_EVIDENCE")

        def fake(name):
            return {
                "open_web_source_candidate_discovery":Discovery,
                "source_candidate_provenance_verify":Verifier,
                "objective_relevance_bm25":self.rank,
                "objective_evidence_unit_extract":Extractor,
                "objective_claim_operand_binding":Binder,
                "source_authority_binding_ror":Authority,
            }[name]

        front._load_sibling=fake
        try:
            out=front.run(objective,decomposition(objective),limit=8,timeout=2)
        finally:
            front._load_sibling=original
        return out,materialized

    def test_bibliographic_only_candidate_can_enter_relevance_then_materialize(self):
        objective=(
            "Assess whether RFC 9110 obsoletes RFC 7230. "
            "Use authoritative technical evidence and independently verify the result."
        )
        scholarly={
            "url":"https://doi.org/10.1000/rfc-test",
            "doi":"10.1000/rfc-test",
            "title":"RFC 9110 HTTP Semantics obsoletes RFC 7230",
            "snippet":"",
            "source_class":"SCHOLARLY_REGISTRY_CANDIDATE",
        }
        verify_map={
            scholarly["url"]:{
                "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                "candidate_url":scholarly["url"],
                "doi":scholarly["doi"],
                "record_title":scholarly["title"],
            }
        }
        seen=[]
        def materialize(candidate):
            return {
                "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                "candidate_url":candidate["url"],
                "final_url":"https://publisher.example/rfc9110",
                "final_host":"publisher.example",
            }
        def extract(obj,candidate,provenance,relevance):
            seen.append((candidate,provenance,relevance))
            return {"status":"EVIDENCE_EXTRACTION_BLOCKED","reason":"TEST_STOPS_AFTER_TRANSITION"}

        out,materialized=self._run(objective,[scholarly],verify_map,materialize,extract)
        self.assertEqual(out["relevance_admitted_provenance_candidate_count"],1,out)
        self.assertEqual(out["retrieval_provenance_verified_candidate_count"],0,out)
        self.assertEqual(out["bibliographic_provenance_verified_candidate_count"],1,out)
        self.assertEqual(materialized,[scholarly["url"]],out)
        self.assertTrue(out["selected_source_live_materialized"],out)
        self.assertEqual(out["selected_source_original_provenance"]["status"],"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",out)
        self.assertEqual(len(seen),1,out)
        self.assertEqual(seen[0][1]["status"],"RETRIEVAL_PROVENANCE_VERIFIED",out)
        self.assertEqual(seen[0][1]["final_url"],"https://publisher.example/rfc9110",out)

    def test_stronger_bibliographic_candidate_competes_with_live_web_candidate(self):
        objective=(
            "Assess whether RFC 9110 obsoletes RFC 7230. "
            "Use authoritative technical evidence and independently verify the result."
        )
        weak={
            "url":"https://weak.example/assessment",
            "title":"How to assess technical evidence",
            "snippet":"General assessment and verification methods.",
        }
        scholarly={
            "url":"https://doi.org/10.1000/http-semantics",
            "doi":"10.1000/http-semantics",
            "title":"RFC 9110 HTTP Semantics obsoletes RFC 7230",
            "snippet":"RFC 9110 and RFC 7230 protocol relationship.",
        }
        verify_map={
            weak["url"]:{
                "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                "candidate_url":weak["url"],
                "final_url":weak["url"],
                "final_host":"weak.example",
            },
            scholarly["url"]:{
                "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                "candidate_url":scholarly["url"],
                "doi":scholarly["doi"],
                "record_title":scholarly["title"],
            },
        }
        def materialize(candidate):
            return {
                "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                "candidate_url":candidate["url"],
                "final_url":"https://publisher.example/http-semantics",
                "final_host":"publisher.example",
            }
        def extract(obj,candidate,provenance,relevance):
            return {"status":"EVIDENCE_EXTRACTION_BLOCKED","reason":"TEST_STOPS_AFTER_SELECTION"}

        out,materialized=self._run(objective,[weak,scholarly],verify_map,materialize,extract)
        selected=out["objective_relevance_verifications"][0]["candidate"]
        self.assertEqual(selected["url"],scholarly["url"],out)
        self.assertEqual(materialized,[scholarly["url"]],out)

    def test_live_retrieval_winner_is_not_materialized_again(self):
        objective="Assess whether RFC 9110 defines HTTP semantics. Verify the result."
        live={
            "url":"https://example.org/rfc9110",
            "title":"RFC 9110 HTTP Semantics",
            "snippet":"HTTP semantics RFC 9110.",
        }
        scholarly={
            "url":"https://doi.org/10.1000/unrelated",
            "doi":"10.1000/unrelated",
            "title":"Unrelated battery study",
            "snippet":"battery chemistry",
        }
        verify_map={
            live["url"]:{
                "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                "candidate_url":live["url"],
                "final_url":live["url"],
                "final_host":"example.org",
            },
            scholarly["url"]:{
                "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                "candidate_url":scholarly["url"],
                "doi":scholarly["doi"],
                "record_title":scholarly["title"],
            },
        }
        def materialize(candidate):
            raise AssertionError("LIVE_WINNER_MUST_NOT_BE_MATERIALIZED_AGAIN")
        seen=[]
        def extract(obj,candidate,provenance,relevance):
            seen.append(provenance)
            return {"status":"EVIDENCE_EXTRACTION_BLOCKED","reason":"TEST_STOPS_AFTER_SELECTION"}

        out,materialized=self._run(objective,[live,scholarly],verify_map,materialize,extract)
        self.assertEqual(materialized,[],out)
        self.assertTrue(out["selected_source_live_materialized"],out)
        self.assertEqual(seen[0]["verification_method"] if "verification_method" in seen[0] else "LIVE","LIVE",out)

    def test_selected_bibliographic_materialization_failure_fails_closed(self):
        objective="Assess whether RFC 9110 obsoletes RFC 7230. Verify the result."
        scholarly={
            "url":"https://doi.org/10.1000/fail-closed",
            "doi":"10.1000/fail-closed",
            "title":"RFC 9110 HTTP Semantics obsoletes RFC 7230",
            "snippet":"",
        }
        verify_map={
            scholarly["url"]:{
                "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                "candidate_url":scholarly["url"],
                "doi":scholarly["doi"],
                "record_title":scholarly["title"],
            }
        }
        def materialize(candidate):
            return {
                "status":"UNVERIFIED",
                "reason":"SELECTED_CANDIDATE_LIVE_MATERIALIZATION_FAILED",
                "candidate_url":candidate["url"],
            }
        def extract(*args,**kwargs):
            raise AssertionError("EXTRACTION_MUST_NOT_RUN_AFTER_MATERIALIZATION_FAILURE")

        out,materialized=self._run(objective,[scholarly],verify_map,materialize,extract)
        self.assertEqual(materialized,[scholarly["url"]],out)
        self.assertFalse(out["selected_source_live_materialized"],out)
        self.assertEqual(out["evidence_extractions"],[],out)
        self.assertEqual(
            out["next_required_capability"],
            "MODEL_INDEPENDENT_SELECTED_PROVENANCE_VERIFIED_SOURCE_LIVE_MATERIALIZATION_V1",
            out,
        )

    def test_materialize_preserves_candidate_identity_and_records_final_url(self):
        old=self.prov._fetch
        self.prov._fetch=lambda url,timeout,accept=("*/*"):(
            b"<html><title>Publisher landing</title><body>Evidence</body></html>",
            "text/html",
            200,
            "https://publisher.example/article",
        )
        try:
            out=self.prov.materialize({
                "url":"https://doi.org/10.1000/article",
                "doi":"10.1000/article",
            },timeout=3)
        finally:
            self.prov._fetch=old
        self.assertEqual(out["status"],"RETRIEVAL_PROVENANCE_VERIFIED",out)
        self.assertEqual(out["candidate_url"],"https://doi.org/10.1000/article",out)
        self.assertEqual(out["final_url"],"https://publisher.example/article",out)
        self.assertEqual(out["verification_method"],"SELECTED_CANDIDATE_LIVE_HTTP_MATERIALIZATION",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
