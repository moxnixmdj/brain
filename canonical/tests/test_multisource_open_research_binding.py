#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    path=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("multisource_"+name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def sha(value):
    if isinstance(value,str):
        value=value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()

def extraction(source_url,text,page_label):
    page=sha(page_label)
    visible=text
    visible_sha=sha(visible)
    text_sha=sha(text)
    start=0
    end=len(text)
    uid=sha(f"{page}:{start}:{end}:{text_sha}")
    return {
      "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "output_verified":True,
      "source_url":source_url,
      "page_raw_sha256":page,
      "visible_text_sha256":visible_sha,
      "evidence_unit_count":1,
      "evidence_units":[{
        "evidence_unit_id":uid,
        "source_url":source_url,
        "page_raw_sha256":page,
        "visible_text_sha256":visible_sha,
        "text":text,
        "text_sha256":text_sha,
        "visible_text_start":start,
        "visible_text_end":end,
      }],
    }

OBJECTIVE=(
  "Determine whether River Alpha annual discharge is higher than "
  "River Beta annual discharge."
)

class MultiSourceBinderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binder=load("objective_claim_operand_binding")

    def left(self,value="1250",unit="m3/s",suffix="a"):
        return extraction(
          f"https://alpha.example/{suffix}",
          f"River Alpha annual discharge was {value} {unit}.",
          "left-"+suffix,
        )

    def right(self,value="980",unit="m3/s",suffix="b"):
        return extraction(
          f"https://beta.example/{suffix}",
          f"River Beta annual discharge was {value} {unit}.",
          "right-"+suffix,
        )

    def test_unambiguous_cross_source_numeric_relation(self):
        out=self.binder.bind_many(OBJECTIVE,[self.left(),self.right()])
        self.assertEqual(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",out)
        self.assertTrue(out["cross_source"],out)
        self.assertEqual(out["multi_source_bundle_count"],2,out)
        self.assertEqual(out["relation_result"]["status"],"NUMERIC_RELATION_VERIFIED",out)
        self.assertTrue(out["relation_result"]["predicate"],out)
        self.assertTrue(out["relation_result"]["cross_source"],out)
        self.assertEqual(out["relation_result"]["unit"],"m3/s",out)
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED",out)
        self.assertEqual(out["evidence_sufficiency_status"],"UNVERIFIED",out)

    def test_multiple_plausible_cross_source_pairs_fail_closed(self):
        out=self.binder.bind_many(
          OBJECTIVE,
          [self.left("1250",suffix="a1"),self.left("1260",suffix="a2"),self.right()],
          evaluate_relation=False,
        )
        self.assertEqual(out["status"],"UNBOUND",out)
        self.assertEqual(out["reason"],"AMBIGUOUS_MULTI_SOURCE_COMPATIBLE_OPERAND_PAIR",out)
        self.assertEqual(out["compatible_pair_count"],2,out)

    def test_unit_mismatch_fails_closed(self):
        out=self.binder.bind_many(
          OBJECTIVE,[self.left(),self.right(unit="liters/s")],evaluate_relation=False
        )
        self.assertEqual(out["status"],"UNBOUND",out)
        self.assertEqual(
          out["reason"],"NO_EXACT_UNIT_COMPATIBLE_MULTI_SOURCE_OPERAND_PAIR",out
        )

    def test_tampered_page_binding_is_rejected_before_cross_source_use(self):
        bad=self.left()
        bad["evidence_units"][0]["text"]+=" altered"
        with self.assertRaisesRegex(
          ValueError,"TEXT_HASH_MISMATCH|OFFSET_INVALID|ID_BINDING_MISMATCH"
        ):
            self.binder.bind_many(OBJECTIVE,[bad,self.right()])


class RankedCandidateExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extractor=load("objective_evidence_unit_extract")

    def test_second_positive_ranked_candidate_is_admissible(self):
        objective="Assess River Beta annual discharge reference measurement"
        first={
          "url":"https://alpha.example/data",
          "title":"River Alpha discharge",
          "snippet":"annual discharge reference",
        }
        second={
          "url":"https://beta.example/data",
          "title":"River Beta annual discharge",
          "snippet":"reference measurement discharge",
        }
        provenance={
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "candidate_url":second["url"],
          "final_url":second["url"],
          "final_host":"beta.example",
        }
        relevance={
          "schema":"PROJECT_BRAIN_OBJECTIVE_RELEVANCE_BM25_V1",
          "objective":objective,
          "status":"LEXICAL_RELEVANCE_RANKED",
          "verification_method":"DETERMINISTIC_BM25",
          "output_verified":True,
          "top_candidate_original_index":0,
          "ranked_candidates":[
            {
              "original_index":0,"candidate":first,
              "lexical_relevance_score":4.0,
              "matched_terms":["river","discharge"],
            },
            {
              "original_index":1,"candidate":second,
              "lexical_relevance_score":3.0,
              "matched_terms":["river","beta","discharge","reference"],
            },
          ],
        }
        out=self.extractor.extract(
          objective,second,provenance,relevance,
          fetch=lambda url,timeout:(
            b"<html><body><p>River Beta annual discharge reference measurement was 980 m3/s.</p></body></html>",
            second["url"],"text/html",200,
          ),
        )
        self.assertEqual(out["status"],"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",out)

    def test_unranked_candidate_remains_rejected(self):
        objective="Assess River Beta annual discharge reference measurement"
        candidate={"url":"https://unranked.example/data"}
        provenance={
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "candidate_url":candidate["url"],
          "final_url":candidate["url"],
        }
        relevance={
          "objective":objective,
          "status":"LEXICAL_RELEVANCE_RANKED",
          "verification_method":"DETERMINISTIC_BM25",
          "output_verified":True,
          "top_candidate_original_index":0,
          "ranked_candidates":[{
            "original_index":0,
            "candidate":{"url":"https://alpha.example/data"},
            "lexical_relevance_score":1.0,
            "matched_terms":["river"],
          }],
        }
        out=self.extractor.extract(
          objective,candidate,provenance,relevance,
          fetch=lambda *args:(_ for _ in ()).throw(AssertionError("must not fetch")),
        )
        self.assertEqual(out["reason"],"CANDIDATE_NOT_SELECTED_BY_RELEVANCE_RECEIPT",out)


class D:
    @staticmethod
    def discover(objective,limit=12,timeout=15):
        return {
          "status":"CANDIDATES_DISCOVERED",
          "candidates":[
            {"url":"https://alpha.example/data","title":"River Alpha annual discharge","snippet":"River Alpha discharge 1250 m3/s"},
            {"url":"https://beta.example/data","title":"River Beta annual discharge","snippet":"River Beta discharge 980 m3/s"},
          ],
        }

class P:
    @staticmethod
    def verify(candidate,timeout=15):
        return {
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "candidate_url":candidate["url"],
          "final_url":candidate["url"],
          "final_host":candidate["url"].split("/")[2],
        }

class R:
    @staticmethod
    def rank(objective,candidates):
        return {
          "status":"LEXICAL_RELEVANCE_RANKED",
          "verification_method":"DETERMINISTIC_BM25",
          "output_verified":True,
          "objective":objective,
          "top_candidate_original_index":0,
          "ranked_candidates":[
            {"original_index":0,"candidate":candidates[0],"lexical_relevance_score":5.0,"matched_terms":["river","alpha","discharge"]},
            {"original_index":1,"candidate":candidates[1],"lexical_relevance_score":4.0,"matched_terms":["river","beta","discharge"]},
          ],
        }

class E:
    @staticmethod
    def extract(objective,candidate,provenance,relevance,timeout=15):
        if "alpha" in candidate["url"]:
            return extraction(candidate["url"],"River Alpha annual discharge was 1250 m3/s.","frontend-left")
        return extraction(candidate["url"],"River Beta annual discharge was 980 m3/s.","frontend-right")

class A:
    @staticmethod
    def bind_candidate(candidate,timeout=15):
        return {"status":"UNVERIFIED","reason":"OPTIONAL_METADATA_ONLY"}

class FrontendMultiSourceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load("open_research_source_frontend")
        cls.real_binder=load("objective_claim_operand_binding")
        cls.original_loader=cls.front._load_sibling

    def test_frontend_reaches_cross_source_relation_without_claiming_truth(self):
        modules={
          "open_web_source_candidate_discovery":D,
          "source_candidate_provenance_verify":P,
          "objective_relevance_bm25":R,
          "objective_evidence_unit_extract":E,
          "source_authority_binding_ror":A,
          "objective_claim_operand_binding":self.real_binder,
        }
        self.front._load_sibling=lambda name:modules[name]
        try:
            decomposition={
              "status":"DECOMPOSED",
              "objective":OBJECTIVE,
              "question_shape":"COMPARATIVE",
              "roles":[{"role":"SOURCE_DISCOVERY"}],
            }
            out=self.front.run(OBJECTIVE,decomposition,limit=4,timeout=2)
        finally:
            self.front._load_sibling=self.original_loader
        self.assertEqual(out["status"],"SOURCE_FRONTEND_READY",out)
        self.assertEqual(out["relevance_verified_candidate_count"],2,out)
        self.assertEqual(out["evidence_extracted_candidate_count"],2,out)
        self.assertEqual(out["claim_relation_evaluated_count"],1,out)
        multi=[
          x for x in out["claim_relation_evaluations"]
          if x.get("multi_source") is True
        ]
        self.assertEqual(len(multi),1,out)
        binding=multi[0]["binding"]
        self.assertEqual(binding["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",binding)
        self.assertTrue(binding["relation_result"]["predicate"],binding)
        self.assertEqual(
          out["next_required_capability"],
          "MODEL_INDEPENDENT_DECISION_QUALITY_SYNTHESIS_AND_VERIFICATION_FROM_OBJECTIVE_BOUND_RELATION_V1",
          out,
        )
        self.assertFalse(out["factual_correctness_claims_made"],out)
        self.assertFalse(out["evidence_sufficiency_claims_made"],out)

if __name__=="__main__":
    unittest.main(verbosity=2)
