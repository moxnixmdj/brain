#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,pathlib,unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BC=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BC/(name+".py")
    s=importlib.util.spec_from_file_location("test_"+name,p)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

class SourceAdmissionRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load("open_research_source_frontend")
        cls.decomp=load("broad_objective_decompose")
        cls.rank=load("objective_relevance_bm25")
        cls.refine=load("metadata_anchored_query_refinement")

    def _goal(self):
        return (
            "Determine whether the 2026 Example storm produced an observed coastal flood "
            "depth exceeding 2 meters at a monitored station outside the origin country. "
            "Use authoritative technical evidence and verify the result."
        )

    def _run(self,refined_title):
        goal=self._goal()
        weak={
            "url":"https://example.net/2026",
            "host":"example.net",
            "title":"2026 year overview",
            "snippet":"Events in 2026 outside several countries.",
            "source_class":"OPEN_WEB_SEARCH_CANDIDATE",
            "discovery_backend":"BING_RSS",
            "rank":0,
        }
        meta={
            "url":"https://doi.org/10.1234/example",
            "host":"doi.org",
            "title":"Observed coastal flood depth from the 2026 Example storm tide gauge network",
            "doi":"10.1234/example",
            "publisher":"Example Geoscience Society",
            "source_class":"SCHOLARLY_REGISTRY_CANDIDATE",
            "discovery_backend":"CROSSREF",
            "rank":1,
        }
        refined={
            "url":"https://papers.example.edu/storm",
            "host":"papers.example.edu",
            "title":refined_title,
            "snippet":"Technical observations from monitored instruments.",
            "source_class":"OPEN_WEB_SEARCH_CANDIDATE",
            "discovery_backend":"BING_RSS",
            "rank":0,
        }

        class Discovery:
            @staticmethod
            def discover(objective,limit=12,timeout=15):
                return {
                    "status":"CANDIDATES_DISCOVERED",
                    "query":"2026 example storm observed coastal flood depth exceeding meters monitored station outside origin country",
                    "candidates":[weak,meta],
                }
            @staticmethod
            def discover_query(query,original_objective=None,limit=12,timeout=15,include_crossref=False):
                return {
                    "status":"CANDIDATES_DISCOVERED",
                    "query":query,
                    "query_origin":"METADATA_ANCHORED_REFINEMENT",
                    "candidates":[refined],
                }

        class Provenance:
            @staticmethod
            def verify(candidate,timeout=15):
                if candidate.get("doi"):
                    return {
                        "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                        "candidate_url":candidate["url"],
                        "doi":candidate["doi"],
                        "record_title":candidate["title"],
                        "publisher":candidate["publisher"],
                    }
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "final_url":candidate["url"],
                    "final_host":candidate["host"],
                }
            @staticmethod
            def verify_live_retrieval(candidate,timeout=15):
                if candidate.get("doi"):
                    return {
                        "status":"UNVERIFIED",
                        "reason":"LIVE_RETRIEVAL_FAILED",
                        "candidate_url":candidate["url"],
                    }
                return {
                    "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "final_url":candidate["url"],
                    "final_host":candidate["host"],
                }

        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=20):
                return {"status":"AUTHORITY_UNRESOLVED"}

        class Extractor:
            @staticmethod
            def extract(objective,candidate,provenance,relevance,timeout=20):
                return {
                    "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
                    "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
                    "output_verified":True,
                    "source_url":candidate["url"],
                    "evidence_unit_count":1,
                    "evidence_units":[{
                        "evidence_unit_id":"a"*64,
                        "text":"Observed coastal flood depth at a monitored station was 2.4 meters.",
                    }],
                }

        class Binder:
            @staticmethod
            def bind(objective,extraction,evaluate_relation=True):
                return {"status":"UNBOUND","reason":"OUT_OF_TEST_SCOPE"}

        def fake(name):
            return {
                "open_web_source_candidate_discovery":Discovery,
                "source_candidate_provenance_verify":Provenance,
                "objective_relevance_bm25":self.rank,
                "metadata_anchored_query_refinement":self.refine,
                "objective_evidence_unit_extract":Extractor,
                "objective_claim_operand_binding":Binder,
                "source_authority_binding_ror":Authority,
            }[name]

        original=self.front._load_sibling
        try:
            self.front._load_sibling=fake
            d=self.decomp.decompose(goal)
            self.assertEqual(d["status"],"DECOMPOSED",d)
            return self.front.run(goal,d,limit=8,timeout=5)
        finally:
            self.front._load_sibling=original

    def test_bibliographic_winner_refines_to_continuous_live_source(self):
        x=self._run(
            "Observed coastal flood depth from the 2026 Example storm tide gauge network preprint"
        )
        self.assertEqual(x["provenance_verified_candidate_count"],2,x)
        self.assertEqual(x["retrieval_provenance_verified_candidate_count"],1,x)
        self.assertEqual(x["bibliographic_provenance_verified_candidate_count"],1,x)
        initial=x["initial_objective_relevance"]
        top=initial["top_candidate_original_index"]
        row=next(r for r in initial["ranked_candidates"] if r["original_index"]==top)
        self.assertEqual(row["candidate"]["source_class"],"SCHOLARLY_REGISTRY_CANDIDATE",x)
        self.assertEqual(x["metadata_refinement"]["status"],"REFINEMENT_READY",x)
        self.assertTrue(x["refinement_continuity"]["output_verified"],x)
        self.assertEqual(x["relevance_verified_candidate_count"],1,x)
        self.assertEqual(x["evidence_extracted_candidate_count"],1,x)
        self.assertEqual(
            x["objective_relevance_verifications"][0]["candidate"]["url"],
            "https://papers.example.edu/storm",
        )
        self.assertFalse(x["authority_claims_made"])
        self.assertFalse(x["factual_correctness_claims_made"])
        self.assertFalse(x["evidence_sufficiency_claims_made"])

    def test_refined_candidate_without_metadata_anchor_fails_closed(self):
        x=self._run("Generic 2026 annual news and weather overview")
        self.assertEqual(x["metadata_refinement"]["status"],"REFINEMENT_READY",x)
        self.assertFalse(x["refinement_continuity"]["output_verified"],x)
        self.assertEqual(x["relevance_verified_candidate_count"],0,x)
        self.assertEqual(x["evidence_extracted_candidate_count"],0,x)
        self.assertEqual(
            x["next_required_capability"],
            "MODEL_INDEPENDENT_SELECTED_BIBLIOGRAPHIC_SOURCE_LIVE_MATERIALIZATION_V1",
            x,
        )

    def test_live_only_path_needs_no_refinement(self):
        goal="Determine whether RFC 9110 defines HTTP semantics using technical source evidence."
        live={
            "url":"https://www.rfc-editor.org/rfc/rfc9110",
            "host":"www.rfc-editor.org",
            "title":"RFC 9110 HTTP Semantics",
            "snippet":"HTTP semantics specification",
            "source_class":"OPEN_WEB_SEARCH_CANDIDATE",
            "rank":0,
        }
        class Discovery:
            @staticmethod
            def discover(objective,limit=12,timeout=15):
                return {"status":"CANDIDATES_DISCOVERED","query":"rfc 9110 http semantics","candidates":[live]}
        class Provenance:
            @staticmethod
            def verify(candidate,timeout=15):
                return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","candidate_url":candidate["url"],"final_url":candidate["url"],"final_host":candidate["host"]}
            @staticmethod
            def verify_live_retrieval(candidate,timeout=15):
                raise AssertionError("live-only selected source must not rematerialize")
        class Authority:
            @staticmethod
            def bind_candidate(candidate,timeout=20): return {"status":"AUTHORITY_UNRESOLVED"}
        class Extractor:
            @staticmethod
            def extract(objective,candidate,provenance,relevance,timeout=20):
                return {"schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2","status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED","output_verified":True,"source_url":candidate["url"],"evidence_unit_count":1,"evidence_units":[{"evidence_unit_id":"b"*64,"text":"RFC 9110 defines HTTP semantics."}]}
        class Binder:
            @staticmethod
            def bind(objective,extraction,evaluate_relation=True): return {"status":"UNBOUND","reason":"OUT_OF_TEST_SCOPE"}
        def fake(name):
            return {
                "open_web_source_candidate_discovery":Discovery,
                "source_candidate_provenance_verify":Provenance,
                "objective_relevance_bm25":self.rank,
                "metadata_anchored_query_refinement":self.refine,
                "objective_evidence_unit_extract":Extractor,
                "objective_claim_operand_binding":Binder,
                "source_authority_binding_ror":Authority,
            }[name]
        original=self.front._load_sibling
        try:
            self.front._load_sibling=fake
            d=self.decomp.decompose(goal)
            x=self.front.run(goal,d,limit=4,timeout=5)
        finally:
            self.front._load_sibling=original
        self.assertIsNone(x["metadata_refinement"],x)
        self.assertEqual(x["relevance_verified_candidate_count"],1,x)
        self.assertEqual(x["evidence_extracted_candidate_count"],1,x)

if __name__=="__main__":
    unittest.main(verbosity=2)
