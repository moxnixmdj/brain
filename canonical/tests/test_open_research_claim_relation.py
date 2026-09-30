#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    s=importlib.util.spec_from_file_location("test_"+name,p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def sha(x):
    if isinstance(x,str): x=x.encode()
    return hashlib.sha256(x).hexdigest()

def extraction(left="Alpha latency was 9 ms.",right="Beta latency was 4 ms."):
    page=sha(b"page"); texts=[left,right]; visible=sha("\n".join(texts))
    rows=[]; offset=0
    for text in texts:
        tsha=sha(text); start=offset; end=start+len(text)
        uid=sha(f"{page}:{start}:{end}:{tsha}")
        rows.append({
          "evidence_unit_id":uid,"source_url":"https://example.org/measurements",
          "page_raw_sha256":page,"visible_text_sha256":visible,
          "text":text,"text_sha256":tsha,
          "visible_text_start":start,"visible_text_end":end,
        })
        offset=end+1
    return {
      "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "output_verified":True,"source_url":"https://example.org/measurements",
      "page_raw_sha256":page,"visible_text_sha256":visible,
      "evidence_unit_count":2,"evidence_units":rows,
    }

def frontend(objective,data=None):
    return {
      "schema":"PROJECT_BRAIN_OPEN_RESEARCH_SOURCE_FRONTEND_V1",
      "status":"SOURCE_FRONTEND_READY","objective":objective,
      "decomposition":{"status":"DECOMPOSED","objective":objective,"roles":[{"role":"SOURCE_DISCOVERY"}]},
      "evidence_extractions":[{
        "candidate":{"url":"https://example.org/measurements","title":"Measurements"},
        "provenance":{"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":"https://example.org/measurements","final_host":"example.org"},
        "relevance":{"status":"LEXICAL_RELEVANCE_RANKED","output_verified":True},
        "authority_identity_metadata":{"status":"UNVERIFIED"},
        "extraction":data or extraction(),
      }],
      "evidence_extracted_candidate_count":1,
      "model_dependency_count":0,"incremental_spend_usd":0,
    }

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline=load("open_research_claim_relation")
        cls.verifier=load("objective_claim_relation_verify")

    def test_numeric_relation_closes_with_independent_verification(self):
        objective="Assess whether Alpha latency is greater than Beta latency."
        out=self.pipeline.evaluate(objective,frontend(objective))
        self.assertEqual(out["status"],"OPEN_RESEARCH_CLAIM_RELATION_VERIFIED",out)
        self.assertTrue(out["decision"]["predicate"],out)
        self.assertTrue(out["independent_verification"]["verified"],out)
        self.assertEqual(out["model_dependency_count"],0,out)
        self.assertTrue(out["output_verified"],out)

    def test_false_relation_is_still_a_verified_decision(self):
        objective="Assess whether Beta latency is greater than Alpha latency."
        data=extraction("Beta latency was 4 ms.","Alpha latency was 9 ms.")
        out=self.pipeline.evaluate(objective,frontend(objective,data))
        self.assertEqual(out["status"],"OPEN_RESEARCH_CLAIM_RELATION_VERIFIED",out)
        self.assertFalse(out["decision"]["predicate"],out)
        self.assertTrue(out["independent_verification"]["verified"],out)

    def test_ambiguous_objective_fails_closed(self):
        objective="Compare Alpha latency and Beta latency."
        out=self.pipeline.evaluate(objective,frontend(objective))
        self.assertEqual(out["status"],"BLOCKED",out)
        self.assertEqual(out["reason"],"NO_INDEPENDENTLY_VERIFIED_CLAIM_RELATION",out)

    def test_tampered_extraction_cannot_pass(self):
        objective="Assess whether Alpha latency is greater than Beta latency."
        data=extraction(); data["evidence_units"][0]["text"]+=" altered"
        out=self.pipeline.evaluate(objective,frontend(objective,data))
        self.assertEqual(out["status"],"BLOCKED",out)
        self.assertFalse(out["output_verified"],out)

    def test_independent_verifier_rejects_predicate_tamper(self):
        objective="Assess whether Alpha latency is greater than Beta latency."
        data=extraction()
        binder=load("objective_claim_operand_binding")
        binding=binder.bind(objective,data,evaluate_relation=True)
        binding["relation_result"]["predicate"]=False
        check=self.verifier.verify(objective,data,binding)
        self.assertFalse(check["verified"],check)
        self.assertEqual(check["reason"],"PREDICATE_MISMATCH",check)

if __name__=="__main__":
    unittest.main(verbosity=2)
