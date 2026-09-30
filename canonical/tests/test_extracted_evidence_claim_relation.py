#!/usr/bin/env python3
import importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/extracted_evidence_claim_relation.py"
spec=importlib.util.spec_from_file_location("claim_relation_under_test",P)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def extraction():
    return {
      "schema":"PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1",
      "status":"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",
      "output_verified":True,
      "fresh_url":"https://example.org/report",
      "evidence_records":[
        {
          "record_type":"OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATE",
          "ordinal":2,
          "text":"The measured concentration was 421.7 ppm during the period.",
          "text_sha256":"a"*64,
          "numeric_literals":["421.7 ppm"],
          "source_url":"https://example.org/report"
        },
        {
          "record_type":"OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATE",
          "ordinal":5,
          "text":"A prior reference value was 419.2 ppm and the threshold was 3 ppm.",
          "text_sha256":"b"*64,
          "numeric_literals":["419.2 ppm","3 ppm"],
          "source_url":"https://example.org/report"
        }
      ]
    }

class ClaimRelationTests(unittest.TestCase):
    def test_exact_verbatim_support(self):
        out=mod.evaluate(extraction(),{"mode":"VERBATIM_TEXT","claim_text":"measured concentration was 421.7 ppm"})
        self.assertEqual(out["status"],"SUPPORT_VERIFIED")
        self.assertTrue(out["matches"])
        self.assertEqual(out["semantic_entailment_status"],"UNVERIFIED")

    def test_paraphrase_not_promoted(self):
        out=mod.evaluate(extraction(),{"mode":"VERBATIM_TEXT","claim_text":"concentration increased to roughly 422 ppm"})
        self.assertEqual(out["status"],"SUPPORT_NOT_VERIFIED")
        self.assertEqual(out["matches"],[])

    def test_numeric_greater_than(self):
        out=mod.evaluate(extraction(),{
          "mode":"NUMERIC_RELATION","operator":"GT",
          "left":{"record_ordinal":2,"numeric_literal_index":0},
          "right":{"record_ordinal":5,"numeric_literal_index":0}
        })
        self.assertTrue(out["predicate"])
        self.assertEqual(out["status"],"RELATION_VERIFIED")

    def test_abs_diff_lte_with_unit_threshold(self):
        out=mod.evaluate(extraction(),{
          "mode":"NUMERIC_RELATION","operator":"ABS_DIFF_LTE",
          "left":{"record_ordinal":2,"numeric_literal_index":0},
          "right":{"record_ordinal":5,"numeric_literal_index":0},
          "threshold":{"record_ordinal":5,"numeric_literal_index":1}
        })
        self.assertTrue(out["predicate"])

    def test_unit_mismatch_fails_closed(self):
        data=extraction(); data["evidence_records"][1]["numeric_literals"][0]="419.2 percent"
        with self.assertRaisesRegex(ValueError,"UNIT_MISMATCH"):
            mod.evaluate(data,{
              "mode":"NUMERIC_RELATION","operator":"GT",
              "left":{"record_ordinal":2,"numeric_literal_index":0},
              "right":{"record_ordinal":5,"numeric_literal_index":0}
            })

    def test_unverified_extraction_rejected(self):
        data=extraction(); data["output_verified"]=False
        with self.assertRaisesRegex(ValueError,"VERIFIED_EXTRACTION_REQUIRED"):
            mod.evaluate(data,{"mode":"VERBATIM_TEXT","claim_text":"421.7 ppm"})

    def test_bad_reference_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"NUMERIC_LITERAL_INDEX_INVALID"):
            mod.evaluate(extraction(),{
              "mode":"NUMERIC_RELATION","operator":"EQ",
              "left":{"record_ordinal":2,"numeric_literal_index":99},
              "right":{"record_ordinal":5,"numeric_literal_index":0}
            })

if __name__=="__main__":
    unittest.main(verbosity=2)
