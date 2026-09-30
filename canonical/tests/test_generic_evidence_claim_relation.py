#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py"

def load():
    spec=importlib.util.spec_from_file_location("generic_evidence_claim_relation_test",P)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def sha(x):
    if isinstance(x,str): x=x.encode()
    return hashlib.sha256(x).hexdigest()

def fixture():
    page=sha(b"page")
    visible=sha("The observed value was 421.7 ppm.\nA prior value was 419.2 ppm and tolerance 3 ppm.")
    rows=[]
    offset=0
    for text in [
        "The observed value was 421.7 ppm.",
        "A prior value was 419.2 ppm and tolerance 3 ppm.",
    ]:
        start=offset; end=start+len(text); tsha=sha(text)
        uid=sha(f"{page}:{start}:{end}:{tsha}")
        rows.append({
          "evidence_unit_id":uid,"source_url":"https://example.org/data",
          "page_raw_sha256":page,"visible_text_sha256":visible,
          "text":text,"text_sha256":tsha,
          "visible_text_start":start,"visible_text_end":end,
        })
        offset=end+1
    return {
      "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "output_verified":True,
      "source_url":"https://example.org/data",
      "page_raw_sha256":page,"visible_text_sha256":visible,
      "evidence_units":rows,
    }

class GenericEvidenceClaimRelationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_exact_verbatim_support_only(self):
        data=fixture()
        out=self.m.evaluate(data,{"mode":"VERBATIM_SUPPORT","claim_text":"observed value was 421.7 ppm"})
        self.assertEqual(out["status"],"EXACT_TEXT_SUPPORT_VERIFIED",out)
        self.assertTrue(out["matches"])
        self.assertEqual(out["semantic_entailment_status"],"UNVERIFIED")
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED")

    def test_paraphrase_is_not_promoted(self):
        out=self.m.evaluate(fixture(),{"mode":"VERBATIM_SUPPORT","claim_text":"the measurement was about 422 ppm"})
        self.assertEqual(out["status"],"EXACT_TEXT_SUPPORT_NOT_VERIFIED",out)
        self.assertEqual(out["matches"],[])

    def test_numeric_gt(self):
        data=fixture(); a,b=[x["evidence_unit_id"] for x in data["evidence_units"]]
        out=self.m.evaluate(data,{
          "mode":"NUMERIC_RELATION","operator":"GT",
          "left":{"evidence_unit_id":a,"numeric_literal_index":0},
          "right":{"evidence_unit_id":b,"numeric_literal_index":0},
        })
        self.assertEqual(out["status"],"NUMERIC_RELATION_VERIFIED",out)
        self.assertTrue(out["predicate"],out)
        self.assertEqual(out["numeric_literal_semantic_role_status"],"UNVERIFIED")

    def test_abs_diff_lte_threshold_literal(self):
        data=fixture(); a,b=[x["evidence_unit_id"] for x in data["evidence_units"]]
        out=self.m.evaluate(data,{
          "mode":"NUMERIC_RELATION","operator":"ABS_DIFF_LTE",
          "left":{"evidence_unit_id":a,"numeric_literal_index":0},
          "right":{"evidence_unit_id":b,"numeric_literal_index":0},
          "threshold":"3 ppm",
        })
        self.assertTrue(out["predicate"],out)

    def test_abs_diff_lte_threshold_from_evidence(self):
        data=fixture(); a,b=[x["evidence_unit_id"] for x in data["evidence_units"]]
        out=self.m.evaluate(data,{
          "mode":"NUMERIC_RELATION","operator":"ABS_DIFF_LTE",
          "left":{"evidence_unit_id":a,"numeric_literal_index":0},
          "right":{"evidence_unit_id":b,"numeric_literal_index":0},
          "threshold":{"evidence_unit_id":b,"numeric_literal_index":1},
        })
        self.assertTrue(out["predicate"],out)
        self.assertIsNotNone(out["threshold"]["provenance"])

    def test_unit_mismatch_fails_closed(self):
        data=fixture(); a,b=[x["evidence_unit_id"] for x in data["evidence_units"]]
        data["evidence_units"][1]["text"]="A prior value was 419.2 percent and tolerance 3 percent."
        row=data["evidence_units"][1]; row["text_sha256"]=sha(row["text"]); row["visible_text_end"]=row["visible_text_start"]+len(row["text"])
        row["evidence_unit_id"]=sha(f"{data['page_raw_sha256']}:{row['visible_text_start']}:{row['visible_text_end']}:{row['text_sha256']}")
        b=row["evidence_unit_id"]
        with self.assertRaisesRegex(ValueError,"UNIT_MISMATCH"):
            self.m.evaluate(data,{
              "mode":"NUMERIC_RELATION","operator":"GT",
              "left":{"evidence_unit_id":a,"numeric_literal_index":0},
              "right":{"evidence_unit_id":b,"numeric_literal_index":0},
            })

    def test_tampered_text_hash_fails_closed(self):
        data=fixture(); data["evidence_units"][0]["text"]+=" altered"
        with self.assertRaisesRegex(ValueError,"TEXT_HASH_MISMATCH"):
            self.m.evaluate(data,{"mode":"VERBATIM_SUPPORT","claim_text":"421.7 ppm"})

    def test_tampered_unit_id_fails_closed(self):
        data=fixture(); data["evidence_units"][0]["evidence_unit_id"]="0"*64
        with self.assertRaisesRegex(ValueError,"ID_BINDING_MISMATCH"):
            self.m.evaluate(data,{"mode":"VERBATIM_SUPPORT","claim_text":"421.7 ppm"})

    def test_unverified_extraction_rejected(self):
        data=fixture(); data["output_verified"]=False
        with self.assertRaisesRegex(ValueError,"VERIFIED_GENERIC_EXTRACTION_REQUIRED"):
            self.m.evaluate(data,{"mode":"VERBATIM_SUPPORT","claim_text":"421.7 ppm"})

    def test_bad_numeric_reference_rejected(self):
        data=fixture(); uid=data["evidence_units"][0]["evidence_unit_id"]
        with self.assertRaisesRegex(ValueError,"NUMERIC_LITERAL_INDEX_INVALID"):
            self.m.evaluate(data,{
              "mode":"NUMERIC_RELATION","operator":"EQ",
              "left":{"evidence_unit_id":uid,"numeric_literal_index":99},
              "right":{"evidence_unit_id":uid,"numeric_literal_index":0},
            })

if __name__=="__main__":
    unittest.main(verbosity=2)
