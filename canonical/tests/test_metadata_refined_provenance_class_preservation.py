#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("refined_provenance_test_"+name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m

def decomposition(objective):
    return {
        "status":"DECOMPOSED",
        "objective":objective,
        "question_shape":"BOOLEAN_ASSESSMENT",
        "roles":[{"role":"SOURCE_DISCOVERY"}],
    }

class Discovery:
    def __init__(self,refined_candidates):
        self.refined_candidates=list(refined_candidates)
        self.calls=[]
    def discover(self,objective,limit=12,timeout=15,query_override=None):
        self.calls.append(query_override)
        if query_override is None:
            return {
                "status":"CANDIDATES_DISCOVERED",
                "objective":objective,
                "candidates":[{
                    "url":"https://doi.org/10.1000/initial",
                    "doi":"10.1000/initial",
                    "title":"Initial candidate concerning a different measurement",
                    "source_class":"SCHOLARLY_REGISTRY_CANDIDATE",
                }],
            }
        return {
            "status":"CANDIDATES_DISCOVERED",
            "objective":objective,
            "query":query_override,
            "query_origin":"METADATA_REFINED_OVERRIDE",
            "candidates":self.refined_candidates,
        }

class Verifier:
    def __init__(self,refined_materialization_ok=True):
        self.materialize_calls=[]
        self.refined_materialization_ok=refined_materialization_ok
    def verify(self,candidate,timeout=15):
        if candidate.get("doi"):
            title=(
                "Refined authoritative thermal-property record"
                if candidate["doi"]=="10.1000/refined"
                else "Initial candidate concerning a different measurement"
            )
            return {
                "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                "candidate_url":candidate["url"],
                "doi":candidate["doi"],
                "record_title":title,
                "publisher":"Reference Laboratory",
                "verification_method":"CROSSREF_DOI_RECORD",
            }
        return {
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "candidate_url":candidate["url"],
            "final_url":candidate["url"],
            "final_host":candidate["url"].split("/")[2],
        }
    def materialize(self,candidate,bibliographic_verification,timeout=15,fetch=None):
        self.materialize_calls.append(candidate["url"])
        if candidate.get("doi")=="10.1000/initial":
            return {
                "status":"UNVERIFIED",
                "reason":"BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION_FAILED",
                "candidate_url":candidate["url"],
            }
        if not self.refined_materialization_ok:
            return {
                "status":"UNVERIFIED",
                "reason":"BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION_FAILED",
                "candidate_url":candidate["url"],
            }
        return {
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "candidate_url":candidate["url"],
            "final_url":"https://reference.example/refined",
            "final_host":"reference.example",
            "verification_method":"SELECTED_BIBLIOGRAPHIC_CANDIDATE_LIVE_HTTP_MATERIALIZATION",
            "bibliographic_provenance_status":"VERIFIED",
            "selected_only_materialization":True,
        }

class Relevance:
    def __init__(self):
        self.calls=[]
    def rank(self,objective,candidates):
        self.calls.append([dict(x) for x in candidates])
        chosen=0
        for i,candidate in enumerate(candidates):
            if candidate.get("doi")=="10.1000/refined":
                chosen=i
                break
            if "refined.example" in str(candidate.get("url") or ""):
                chosen=i
                break
        rows=[]
        for i,candidate in enumerate(candidates):
            matched=["thermal","property","record"] if i==chosen else ["different"]
            rows.append({
                "original_index":i,
                "candidate":dict(candidate),
                "lexical_relevance_score":8.0 if i==chosen else 0.5,
                "matched_terms":matched,
            })
        return {
            "status":"LEXICAL_RELEVANCE_RANKED",
            "verification_method":"DETERMINISTIC_BM25",
            "output_verified":True,
            "objective":objective,
            "query_focus":{"query":"thermal property record"},
            "top_candidate_original_index":chosen,
            "top_candidate_admission":{
                "method":"FOCUSED_QUERY_TOKEN_COVERAGE_V1",
                "verified":True,
                "matched_term_count":3,
                "required_matched_term_count":2,
            },
            "ranked_candidates":rows,
        }

class Extractor:
    def __init__(self):
        self.calls=[]
    def extract(self,objective,candidate,provenance,relevance,timeout=15):
        self.calls.append((dict(candidate),dict(provenance),dict(relevance)))
        return {"status":"EVIDENCE_EXTRACTION_BLOCKED","reason":"TEST_STOPS_AFTER_ROUTING"}

class Binder:
    def bind(self,*args,**kwargs):
        raise AssertionError("BINDER_MUST_NOT_RUN")

class Authority:
    def bind_candidate(self,candidate,timeout=15):
        return {"status":"UNVERIFIED","reason":"TEST_FIXTURE"}

class RefinedProvenanceClassPreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load("open_research_source_frontend")

    def run_front(self,refined_candidates,refined_materialization_ok=True):
        discovery=Discovery(refined_candidates)
        verifier=Verifier(refined_materialization_ok)
        relevance=Relevance()
        extractor=Extractor()
        mapping={
            "open_web_source_candidate_discovery":discovery,
            "source_candidate_provenance_verify":verifier,
            "objective_relevance_bm25":relevance,
            "objective_evidence_unit_extract":extractor,
            "objective_claim_operand_binding":Binder(),
            "source_authority_binding_ror":Authority(),
        }
        original=self.front._load_sibling
        self.front._load_sibling=lambda name:mapping[name]
        objective="Assess whether one engineering material property exceeds another under comparable conditions."
        try:
            out=self.front.run(objective,decomposition(objective),limit=8,timeout=2)
        finally:
            self.front._load_sibling=original
        return out,discovery,verifier,relevance,extractor

    def test_refined_bibliographic_candidate_survives_relevance_and_materializes(self):
        refined=[
            {
                "url":"https://irrelevant.example/live",
                "title":"Generic unrelated page",
                "snippet":"unrelated",
            },
            {
                "url":"https://doi.org/10.1000/refined",
                "doi":"10.1000/refined",
                "title":"Refined authoritative thermal-property record",
                "source_class":"SCHOLARLY_REGISTRY_CANDIDATE",
            },
        ]
        out,discovery,verifier,relevance,extractor=self.run_front(refined)
        self.assertEqual(out["status"],"SOURCE_FRONTEND_READY",out)
        self.assertEqual(len(discovery.calls),2,discovery.calls)
        self.assertIsNone(discovery.calls[0])
        self.assertEqual(
            verifier.materialize_calls,
            ["https://doi.org/10.1000/initial","https://doi.org/10.1000/refined"],
        )
        self.assertEqual(len(relevance.calls),2,relevance.calls)
        refined_seen=relevance.calls[1]
        self.assertEqual(refined_seen[1]["record_title"],"Refined authoritative thermal-property record")
        self.assertEqual(refined_seen[1]["publisher"],"Reference Laboratory")
        self.assertEqual(len(extractor.calls),1,out)
        candidate,provenance,_=extractor.calls[0]
        self.assertEqual(candidate["doi"],"10.1000/refined")
        self.assertEqual(provenance["status"],"RETRIEVAL_PROVENANCE_VERIFIED")
        self.assertEqual(provenance["final_url"],"https://reference.example/refined")
        self.assertEqual(
            out["selected_source_origin"],
            "BIBLIOGRAPHIC_METADATA_REFINED_SELECTED_LIVE_MATERIALIZATION",
            out,
        )
        refinement=out["metadata_anchored_refinement"]
        self.assertTrue(refinement["selected"],refinement)
        self.assertEqual(
            refinement["selected_materialization"]["status"],
            "RETRIEVAL_PROVENANCE_VERIFIED",
            refinement,
        )

    def test_refined_selected_bibliographic_materialization_failure_fails_closed_without_second_retry(self):
        refined=[{
            "url":"https://doi.org/10.1000/refined",
            "doi":"10.1000/refined",
            "title":"Refined authoritative thermal-property record",
            "source_class":"SCHOLARLY_REGISTRY_CANDIDATE",
        }]
        out,discovery,verifier,relevance,extractor=self.run_front(
            refined,refined_materialization_ok=False
        )
        self.assertEqual(out["status"],"SELECTED_SOURCE_MATERIALIZATION_BLOCKED",out)
        self.assertEqual(len(discovery.calls),2,discovery.calls)
        self.assertEqual(
            verifier.materialize_calls,
            ["https://doi.org/10.1000/initial","https://doi.org/10.1000/refined"],
        )
        self.assertEqual(extractor.calls,[])
        self.assertEqual(
            out["next_required_capability"],
            "MODEL_INDEPENDENT_SELECTED_SOURCE_LIVE_MATERIALIZATION_V1",
            out,
        )
        refinement=out["metadata_anchored_refinement"]
        self.assertFalse(refinement["selected"],refinement)
        self.assertEqual(
            refinement["selected_materialization"]["status"],
            "UNVERIFIED",
            refinement,
        )

    def test_refined_live_candidate_path_remains_single_retry_without_rematerialization(self):
        refined=[{
            "url":"https://refined.example/live",
            "title":"Refined thermal property record",
            "snippet":"thermal property record",
        }]
        out,discovery,verifier,relevance,extractor=self.run_front(refined)
        self.assertEqual(out["status"],"SOURCE_FRONTEND_READY",out)
        self.assertEqual(len(discovery.calls),2,discovery.calls)
        self.assertEqual(verifier.materialize_calls,["https://doi.org/10.1000/initial"])
        self.assertEqual(len(extractor.calls),1,out)
        candidate,provenance,_=extractor.calls[0]
        self.assertEqual(candidate["url"],"https://refined.example/live")
        self.assertEqual(provenance["status"],"RETRIEVAL_PROVENANCE_VERIFIED")
        self.assertEqual(
            out["selected_source_origin"],
            "BIBLIOGRAPHIC_METADATA_REFINED_LIVE_RETRIEVAL",
            out,
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
