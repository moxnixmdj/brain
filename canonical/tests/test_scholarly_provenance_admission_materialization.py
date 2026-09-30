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
        raise RuntimeError("LOAD_FAILED:"+rel)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

def decomposition(objective):
    return {
        "status":"DECOMPOSED",
        "objective":objective,
        "question_shape":"BOOLEAN_ASSESSMENT",
        "roles":[{"role":"SOURCE_DISCOVERY"}],
    }

class FakeDiscovery:
    def discover(self,objective,limit=12,timeout=15):
        return {
            "status":"CANDIDATES_DISCOVERED",
            "objective":objective,
            "candidates":[
                {
                    "rank":0,"url":"https://weak.example/page","host":"weak.example",
                    "title":"2026 overview","snippet":"2026 overview",
                    "source_class":"OPEN_WEB_SEARCH_CANDIDATE",
                    "discovery_backend":"TEST",
                },
                {
                    "rank":1,"url":"https://doi.org/10.1234/strong","host":"doi.org",
                    "doi":"10.1234/strong","title":"Strong domain measurement study",
                    "source_class":"SCHOLARLY_REGISTRY_CANDIDATE",
                    "discovery_backend":"CROSSREF",
                },
            ],
        }

class FakeVerifier:
    def __init__(self,materialize_ok=True):
        self.materialize_ok=materialize_ok
        self.materialize_calls=[]
    def verify(self,candidate,timeout=15):
        if candidate.get("doi"):
            return {
                "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                "record_title":"Strong domain measurement study",
                "publisher":"Example Society",
                "candidate_url":candidate["url"],
            }
        return {
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "candidate_url":candidate["url"],
            "final_url":candidate["url"],
            "final_host":"weak.example",
        }
    def materialize(self,candidate,timeout=15):
        self.materialize_calls.append(candidate["url"])
        if not self.materialize_ok:
            return {
                "status":"UNVERIFIED",
                "reason":"SELECTED_SOURCE_LIVE_MATERIALIZATION_FAILED",
                "candidate_url":candidate["url"],
            }
        return {
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "verification_method":"SELECTED_CANDIDATE_LIVE_HTTP_MATERIALIZATION",
            "candidate_url":candidate["url"],
            "final_url":"https://publisher.example/strong",
            "final_host":"publisher.example",
            "selected_only_materialization":True,
        }

class FakeRelevance:
    def __init__(self,selected_index):
        self.selected_index=selected_index
        self.seen=None
    def rank(self,objective,candidates):
        self.seen=[dict(x) for x in candidates]
        rows=[]
        for i,c in enumerate(candidates):
            rows.append({
                "original_index":i,
                "candidate":dict(c),
                "lexical_relevance_score":10.0 if i==self.selected_index else 0.1,
                "matched_terms":["measurement"] if i==self.selected_index else ["2026"],
            })
        rows.sort(key=lambda x:-x["lexical_relevance_score"])
        return {
            "status":"LEXICAL_RELEVANCE_RANKED",
            "verification_method":"DETERMINISTIC_BM25",
            "output_verified":True,
            "objective":objective,
            "top_candidate_original_index":self.selected_index,
            "ranked_candidates":rows,
        }

class FakeExtractor:
    def __init__(self):
        self.calls=[]
    def extract(self,objective,candidate,provenance,relevance,timeout=15):
        self.calls.append((dict(candidate),dict(provenance)))
        return {
            "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
            "evidence_extraction_status":"VERIFIED",
            "evidence_unit_count":1,
            "source_url":provenance.get("final_url"),
            "evidence_units":[{"text":"measurement evidence"}],
        }

class FakeBinder:
    def bind(self,objective,extraction,evaluate_relation=True):
        return {
            "status":"UNBOUND",
            "reason":"TEST_STOPS_BEFORE_RELATION",
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        }

class FakeAuthority:
    def bind_candidate(self,candidate,timeout=15):
        return {"status":"AUTHORITY_UNRESOLVED"}

class ScholarlyAdmissionMaterializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load(
            "canonical/runtime/bound_capabilities/open_research_source_frontend.py",
            "scholarly_frontend_under_test",
        )
        cls.prov=load(
            "canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py",
            "scholarly_provenance_under_test",
        )

    def install(self,selected_index=1,materialize_ok=True):
        discovery=FakeDiscovery()
        verifier=FakeVerifier(materialize_ok)
        relevance=FakeRelevance(selected_index)
        extractor=FakeExtractor()
        binder=FakeBinder()
        authority=FakeAuthority()
        mapping={
            "open_web_source_candidate_discovery":discovery,
            "source_candidate_provenance_verify":verifier,
            "objective_relevance_bm25":relevance,
            "objective_evidence_unit_extract":extractor,
            "objective_claim_operand_binding":binder,
            "source_authority_binding_ror":authority,
        }
        self.front._load_sibling=lambda name:mapping[name]
        return verifier,relevance,extractor

    def test_bibliographic_candidate_competes_and_selected_only_materializes(self):
        objective="Assess whether a measured material response exceeds a stated operating threshold."
        verifier,relevance,extractor=self.install(selected_index=1,materialize_ok=True)
        out=self.front.run(objective,decomposition(objective))
        self.assertEqual(out["status"],"SOURCE_FRONTEND_READY")
        self.assertEqual(out["provenance_verified_candidate_count"],2)
        self.assertEqual(out["retrieval_provenance_verified_candidate_count"],1)
        self.assertEqual(out["bibliographic_provenance_verified_candidate_count"],1)
        self.assertEqual(len(relevance.seen),2)
        self.assertEqual(relevance.seen[1]["record_title"],"Strong domain measurement study")
        self.assertEqual(verifier.materialize_calls,["https://doi.org/10.1234/strong"])
        self.assertEqual(len(extractor.calls),1)
        candidate,provenance=extractor.calls[0]
        self.assertEqual(candidate["doi"],"10.1234/strong")
        self.assertEqual(provenance["status"],"RETRIEVAL_PROVENANCE_VERIFIED")
        self.assertEqual(provenance["final_url"],"https://publisher.example/strong")

    def test_selected_bibliographic_materialization_failure_is_fail_closed(self):
        objective="Determine whether a measured coastal quantity exceeds a threshold."
        verifier,relevance,extractor=self.install(selected_index=1,materialize_ok=False)
        out=self.front.run(objective,decomposition(objective))
        self.assertEqual(out["status"],"SELECTED_SOURCE_MATERIALIZATION_BLOCKED")
        self.assertEqual(out["next_required_capability"],"MODEL_INDEPENDENT_SELECTED_SOURCE_LIVE_MATERIALIZATION_V1")
        self.assertEqual(verifier.materialize_calls,["https://doi.org/10.1234/strong"])
        self.assertEqual(extractor.calls,[])

    def test_selected_live_candidate_does_not_materialize_again(self):
        objective="Compare two engineering measurements using documented evidence."
        verifier,relevance,extractor=self.install(selected_index=0,materialize_ok=True)
        out=self.front.run(objective,decomposition(objective))
        self.assertEqual(out["status"],"SOURCE_FRONTEND_READY")
        self.assertEqual(verifier.materialize_calls,[])
        self.assertEqual(len(extractor.calls),1)
        self.assertEqual(extractor.calls[0][0]["url"],"https://weak.example/page")

    def test_materialize_follows_selected_doi_without_authority_upgrade(self):
        seen={}
        def fake_fetch(url,timeout,accept):
            seen.update(url=url,timeout=timeout,accept=accept)
            return (
                b"<html><head><title>Publisher landing</title></head><body>data</body></html>",
                "text/html; charset=utf-8",
                200,
                "https://publisher.example/article",
            )
        out=self.prov.materialize(
            {"url":"https://doi.org/10.1234/example","doi":"10.1234/example"},
            timeout=9,
            fetch=fake_fetch,
        )
        self.assertEqual(out["status"],"RETRIEVAL_PROVENANCE_VERIFIED")
        self.assertEqual(out["verification_method"],"SELECTED_CANDIDATE_LIVE_HTTP_MATERIALIZATION")
        self.assertTrue(out["bibliographic_identity_preserved"])
        self.assertEqual(out["authority_status"],"RETRIEVABILITY_VERIFIED__FACT_AUTHORITY_UNVERIFIED")
        self.assertEqual(out["primary_source_status"],"UNVERIFIED")
        self.assertEqual(out["final_url"],"https://publisher.example/article")
        self.assertEqual(seen["url"],"https://doi.org/10.1234/example")

if __name__=="__main__":
    unittest.main(verbosity=2)
