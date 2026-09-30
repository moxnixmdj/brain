#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, pathlib, sys, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BOUND=ROOT/"canonical/runtime/bound_capabilities"
RUNTIME=ROOT/"canonical/runtime/astra_runtime.py"

def load(name):
    path=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("integration_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def sha(v):
    if isinstance(v,str):
        v=v.encode("utf-8")
    return hashlib.sha256(v).hexdigest()

def extraction(left="River Alpha annual discharge was 1250 m3/s.",
               right="River Beta annual discharge was 980 m3/s."):
    page=sha(b"parent-integration-fixture")
    texts=[left,right]
    visible="\n".join(texts)
    visible_sha=sha(visible)
    units=[]
    offset=0
    for text in texts:
        text_sha=sha(text)
        start=offset
        end=start+len(text)
        uid=sha(f"{page}:{start}:{end}:{text_sha}")
        units.append({
          "evidence_unit_id":uid,
          "source_url":"https://example.org/evidence",
          "page_raw_sha256":page,
          "visible_text_sha256":visible_sha,
          "text":text,
          "text_sha256":text_sha,
          "visible_text_start":start,
          "visible_text_end":end,
        })
        offset=end+1
    return {
      "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "output_verified":True,
      "source_url":"https://example.org/evidence",
      "page_raw_sha256":page,
      "visible_text_sha256":visible_sha,
      "evidence_unit_count":len(units),
      "evidence_units":units,
      "factual_correctness_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "source_independence_status":"UNVERIFIED",
    }

class D:
    @staticmethod
    def discover(objective,limit=12,timeout=15):
        return {
          "status":"CANDIDATES_DISCOVERED",
          "candidates":[{
            "url":"https://example.org/evidence",
            "host":"example.org",
            "title":"River discharge comparison",
            "snippet":"River Alpha River Beta annual discharge",
          }],
        }

class P:
    @staticmethod
    def verify(candidate,timeout=15):
        return {
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "candidate_url":candidate["url"],
          "final_url":candidate["url"],
          "final_host":"example.org",
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
          "ranked_candidates":[{
            "original_index":0,
            "lexical_relevance_score":4.0,
            "matched_terms":["river","discharge"],
            "candidate":candidates[0],
          }],
        }

class E:
    @staticmethod
    def extract(objective,candidate,provenance,relevance,timeout=15):
        return extraction()

class A:
    @staticmethod
    def bind_candidate(candidate,timeout=15):
        return {"status":"UNVERIFIED","reason":"OPTIONAL_METADATA_ONLY"}

class FrontendClaimRelationIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load("open_research_source_frontend")
        cls.real_binder=cls.front._load_sibling("objective_claim_operand_binding")
        cls.original_loader=cls.front._load_sibling

    def run_front(self,objective):
        modules={
          "open_web_source_candidate_discovery":D,
          "source_candidate_provenance_verify":P,
          "objective_relevance_bm25":R,
          "objective_evidence_unit_extract":E,
          "source_authority_binding_ror":A,
          "objective_claim_operand_binding":self.real_binder,
        }
        self.front._load_sibling=lambda name: modules[name]
        try:
            decomposition={
              "status":"DECOMPOSED",
              "objective":objective,
              "question_shape":"COMPARATIVE",
              "roles":[
                {"role":"SOURCE_DISCOVERY"},
                {"role":"EVIDENCE_ACQUISITION"},
                {"role":"EVIDENCE_EXTRACTION"},
                {"role":"RELATION_EVALUATION"},
                {"role":"DECISION_SYNTHESIS_AND_VERIFICATION"},
              ],
            }
            return self.front.run(objective,decomposition,limit=4,timeout=2)
        finally:
            self.front._load_sibling=self.original_loader

    def test_explicit_comparison_reaches_verified_relation(self):
        objective=(
          "Determine whether River Alpha annual discharge is higher than "
          "River Beta annual discharge."
        )
        out=self.run_front(objective)
        self.assertEqual(out["status"],"SOURCE_FRONTEND_READY",out)
        self.assertEqual(out["evidence_extracted_candidate_count"],1,out)
        self.assertEqual(out["claim_relation_evaluated_count"],1,out)
        binding=out["claim_relation_evaluations"][0]["binding"]
        self.assertEqual(binding["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",binding)
        self.assertEqual(binding["relation_spec"]["operator"],"GT",binding)
        self.assertEqual(binding["relation_result"]["status"],"NUMERIC_RELATION_VERIFIED",binding)
        self.assertTrue(binding["relation_result"]["predicate"],binding)
        self.assertEqual(
          out["role_progress"]["RELATION_EVALUATION"],
          "OBJECTIVE_BOUND_EXPLICIT_RELATION_EVALUATED__FACTUAL_CORRECTNESS_UNVERIFIED",
        )
        self.assertEqual(
          out["next_required_capability"],
          "MODEL_INDEPENDENT_DECISION_QUALITY_SYNTHESIS_AND_VERIFICATION_FROM_OBJECTIVE_BOUND_RELATION_V1",
        )
        self.assertFalse(out["factual_correctness_claims_made"])
        self.assertFalse(out["evidence_sufficiency_claims_made"])
        self.assertEqual(binding["factual_correctness_status"],"UNVERIFIED")
        self.assertEqual(binding["evidence_sufficiency_status"],"UNVERIFIED")

    def test_unsupported_objective_stops_at_claim_spec_gap(self):
        out=self.run_front("Compare River Alpha and River Beta annual discharge.")
        self.assertEqual(out["evidence_extracted_candidate_count"],1,out)
        self.assertEqual(out["claim_relation_evaluated_count"],0,out)
        binding=out["claim_relation_evaluations"][0]["binding"]
        self.assertEqual(binding["status"],"UNBOUND",binding)
        self.assertEqual(
          binding["reason"],
          "OBJECTIVE_RELATION_AMBIGUOUS_OR_UNSUPPORTED",
          binding,
        )
        self.assertEqual(
          out["next_required_capability"],
          "MODEL_INDEPENDENT_CLAIM_SPEC_AND_OPERAND_BINDING_FROM_OBJECTIVE_AND_GENERIC_EVIDENCE_V1",
        )
        self.assertFalse(out["factual_correctness_claims_made"])
        self.assertFalse(out["evidence_sufficiency_claims_made"])

    def test_runtime_has_relation_evaluated_stop_marker(self):
        text=RUNTIME.read_text(encoding="utf-8")
        self.assertIn("OPEN_ENDED_RESEARCH_RELATION_EVALUATED__",text)
        self.assertIn("DECISION_SYNTHESIS_AND_VERIFICATION_REQUIRED",text)
        self.assertIn("claim_relation_evaluated_count",text)

if __name__=="__main__":
    unittest.main(verbosity=2)
