from __future__ import annotations
import hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import r2_explicit_numeric_comparison_direct_adequacy_v1 as cmp

ROOT=Path(__file__).resolve().parents[2]
TMP=ROOT/"canonical/astra_runtime/tmp"
EX=TMP/"R2_NUMERIC_COMPARISON_EXTRACTION.json"
OUT=TMP/"R2_NUMERIC_COMPARISON_RESULT.json"

TRUE_OBJECTIVE="Engine A is higher than Engine B"
FALSE_OBJECTIVE="Engine A is lower than Engine B"

def goal(objective):
    return (
      'Using grounded evidence in canonical/astra_runtime/tmp/R2_NUMERIC_COMPARISON_EXTRACTION.json, '
      f'verify comparison objective "{objective}" and save the verified comparison result to '
      'canonical/astra_runtime/tmp/R2_NUMERIC_COMPARISON_RESULT.json.'
    )

def sh(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def fixture(unit_b="kN", duplicate_a=False):
    texts=["Engine A thrust is 120 kN.",f"Engine B thrust is 90 {unit_b}."]
    if duplicate_a:
        texts.append("Engine A backup reading is 121 kN.")
    page=sh("numeric-comparison-page")
    visible="\n".join(texts)
    visible_sha=sh(visible)
    rows=[]
    cursor=0
    for text in texts:
        start=cursor
        end=start+len(text)
        text_sha=sh(text)
        uid=sh(f"{page}:{start}:{end}:{text_sha}")
        rows.append({
          "evidence_unit_id":uid,
          "source_url":"https://example.org/numeric-evidence",
          "page_raw_sha256":page,
          "visible_text_sha256":visible_sha,
          "visible_text_start":start,
          "visible_text_end":end,
          "text":text,
          "text_sha256":text_sha
        })
        cursor=end+1
    return {
      "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "output_verified":True,
      "source_url":"https://example.org/numeric-evidence",
      "page_raw_sha256":page,
      "visible_text_sha256":visible_sha,
      "evidence_units":rows
    }

class R2ExplicitNumericComparisonDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True,exist_ok=True)
        EX.write_text(json.dumps(fixture()),encoding="utf-8")
        if OUT.exists(): OUT.unlink()
    def tearDown(self):
        for p in (EX,OUT):
            if p.exists(): p.unlink()

    def test_preflight_binds_true_gt(self):
        out=cmp.preflight({"task_id":"gt","goal":goal(TRUE_OBJECTIVE)})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["operator"],"GT")
        self.assertTrue(out["expected_predicate"])
        self.assertEqual(out["expected_left"]["value"],"120")
        self.assertEqual(out["expected_right"]["value"],"90")
        self.assertEqual(out["expected_left"]["unit"],"kn")
        self.assertFalse(out["preflight_execution_authority"])

    def test_preflight_preserves_false_predicate(self):
        out=cmp.preflight({"task_id":"lt","goal":goal(FALSE_OBJECTIVE)})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["operator"],"LT")
        self.assertFalse(out["expected_predicate"])

    def test_unit_mismatch_fails_closed(self):
        EX.write_text(json.dumps(fixture(unit_b="MW")),encoding="utf-8")
        out=cmp.preflight({"task_id":"unit","goal":goal(TRUE_OBJECTIVE)})
        self.assertTrue(out["matched"])
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_ambiguous_entity_binding_fails_closed(self):
        EX.write_text(json.dumps(fixture(duplicate_a=True)),encoding="utf-8")
        out=cmp.preflight({"task_id":"ambiguous","goal":goal(TRUE_OBJECTIVE)})
        self.assertTrue(out["matched"])
        self.assertEqual(out["status"],"FAIL_CLOSED")

    @patch.object(cmp.objective_claim_operand_binding,"run")
    def test_independent_relation_recomputation_commits(self,producer):
        pf=cmp.preflight({"task_id":"ok","goal":goal(TRUE_OBJECTIVE)})
        self.assertEqual(pf["status"],"DIRECT_ADEQUACY_ROUTE_MATCHED",pf)
        def fake(*args,**kwargs):
            result=cmp.objective_claim_operand_binding.bind(
                TRUE_OBJECTIVE,
                json.loads(EX.read_text(encoding="utf-8")),
                evaluate_relation=True
            )
            OUT.write_text(json.dumps(result),encoding="utf-8")
            return result
        producer.side_effect=fake
        out=cmp.run({"task_id":"ok","goal":goal(TRUE_OBJECTIVE)})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["predicate"])
        self.assertTrue(out["transaction_committed"])

    @patch.object(cmp.objective_claim_operand_binding,"run")
    def test_wrong_predicate_rolls_back(self,producer):
        pf=cmp.preflight({"task_id":"bad","goal":goal(TRUE_OBJECTIVE)})
        OUT.write_bytes(b'{"old":true}')
        def fake(*args,**kwargs):
            result=cmp.objective_claim_operand_binding.bind(
                TRUE_OBJECTIVE,
                json.loads(EX.read_text(encoding="utf-8")),
                evaluate_relation=True
            )
            result["relation_result"]["predicate"]=False
            OUT.write_text(json.dumps(result),encoding="utf-8")
            return result
        producer.side_effect=fake
        out=cmp.run({"task_id":"bad","goal":goal(TRUE_OBJECTIVE)})
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(OUT.read_bytes(),b'{"old":true}')

if __name__=="__main__":
    unittest.main(verbosity=2)
