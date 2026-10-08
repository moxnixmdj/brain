from __future__ import annotations
import hashlib,json,unittest
from pathlib import Path
from canonical.runtime import r2_unit_normalized_numeric_comparison_direct_adequacy_v1 as unitcmp

ROOT=Path(__file__).resolve().parents[2]
TMP=ROOT/"canonical/astra_runtime/tmp"
EX=TMP/"R2_UNIT_NORMALIZED_EXTRACTION.json"
OUT=TMP/"R2_UNIT_NORMALIZED_RESULT.json"

def sh(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def fixture(left_text="Vehicle A speed is 36 km/h.",right_text="Vehicle B speed is 10 m/s."):
    texts=[left_text,right_text]
    page=sh("unit-normalized-page")
    visible="\n".join(texts)
    visible_sha=sh(visible)
    rows=[]; cursor=0
    for text in texts:
        start=cursor; end=start+len(text); text_sha=sh(text)
        uid=sh(f"{page}:{start}:{end}:{text_sha}")
        rows.append({
          "evidence_unit_id":uid,"source_url":"https://example.org/units",
          "page_raw_sha256":page,"visible_text_sha256":visible_sha,
          "visible_text_start":start,"visible_text_end":end,
          "text":text,"text_sha256":text_sha
        })
        cursor=end+1
    return {
      "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED","output_verified":True,
      "source_url":"https://example.org/units","page_raw_sha256":page,
      "visible_text_sha256":visible_sha,"evidence_units":rows
    }

def goal(objective):
    return (
      'Using grounded evidence in canonical/astra_runtime/tmp/R2_UNIT_NORMALIZED_EXTRACTION.json, '
      f'verify unit-normalized comparison objective "{objective}" and save the verified comparison result to '
      'canonical/astra_runtime/tmp/R2_UNIT_NORMALIZED_RESULT.json.'
    )

class R2UnitNormalizedNumericComparisonDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True,exist_ok=True)
        EX.write_text(json.dumps(fixture()),encoding="utf-8")
        if OUT.exists(): OUT.unlink()
    def tearDown(self):
        for p in (EX,OUT):
            if p.exists(): p.unlink()

    def test_cross_unit_equal_true(self):
        out=unitcmp.preflight({"task_id":"eq","goal":goal("Vehicle A is equal to Vehicle B")})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["operator"],"EQ")
        self.assertTrue(out["expected_predicate"])
        self.assertEqual(out["dimension"],"speed")
        self.assertEqual(out["left"]["unit"],"km/h")
        self.assertEqual(out["right"]["unit"],"m/s")

    def test_cross_unit_gt_false_is_valid(self):
        out=unitcmp.preflight({"task_id":"gt","goal":goal("Vehicle A is higher than Vehicle B")})
        self.assertEqual(out["status"],"DIRECT_ADEQUACY_ROUTE_MATCHED",out)
        self.assertEqual(out["operator"],"GT")
        self.assertFalse(out["expected_predicate"])

    def test_force_conversion_true(self):
        EX.write_text(json.dumps(fixture("Engine A thrust is 1.2 kN.","Engine B thrust is 1200 N.")),encoding="utf-8")
        out=unitcmp.preflight({"task_id":"force","goal":goal("Engine A is equal to Engine B")})
        self.assertEqual(out["status"],"DIRECT_ADEQUACY_ROUTE_MATCHED",out)
        self.assertTrue(out["expected_predicate"])
        self.assertEqual(out["dimension"],"force")

    def test_absolute_difference_threshold_converts(self):
        EX.write_text(json.dumps(fixture("Vehicle A speed is 36 km/h.","Vehicle B speed is 9.5 m/s.")),encoding="utf-8")
        out=unitcmp.preflight({"task_id":"diff","goal":goal("Vehicle A and Vehicle B differ by at most 1 m/s")})
        self.assertEqual(out["status"],"DIRECT_ADEQUACY_ROUTE_MATCHED",out)
        self.assertEqual(out["operator"],"ABS_DIFF_LTE")
        self.assertTrue(out["expected_predicate"])

    def test_incompatible_dimensions_fail_closed(self):
        EX.write_text(json.dumps(fixture("Engine A thrust is 1 kN.","Engine B power is 1 MW.")),encoding="utf-8")
        out=unitcmp.preflight({"task_id":"dim","goal":goal("Engine A is equal to Engine B")})
        self.assertTrue(out["matched"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("CONVERTIBLE_OPERAND_PAIR_NOT_UNIQUE:0",out["reason"])

    def test_same_units_are_left_to_v23(self):
        EX.write_text(json.dumps(fixture("Engine A thrust is 1200 N.","Engine B thrust is 900 N.")),encoding="utf-8")
        out=unitcmp.preflight({"task_id":"same","goal":goal("Engine A is higher than Engine B")})
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("CONVERTIBLE_OPERAND_PAIR_NOT_UNIQUE:0",out["reason"])

    def test_affine_temperature_rejected(self):
        EX.write_text(json.dumps(fixture("Room A temperature is 20 C.","Room B temperature is 68 F.")),encoding="utf-8")
        out=unitcmp.preflight({"task_id":"temp","goal":goal("Room A is equal to Room B")})
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_multiple_convertible_values_are_ambiguous(self):
        EX.write_text(json.dumps(fixture("Vehicle A speed is 36 km/h and backup speed is 40 km/h.","Vehicle B speed is 10 m/s.")),encoding="utf-8")
        out=unitcmp.preflight({"task_id":"amb","goal":goal("Vehicle A is equal to Vehicle B")})
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("CONVERTIBLE_OPERAND_PAIR_NOT_UNIQUE:2",out["reason"])

    def test_run_writes_dual_verified_result(self):
        out=unitcmp.run({"task_id":"run","goal":goal("Vehicle A is equal to Vehicle B")})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["predicate"])
        self.assertTrue(out["acceptance_receipt"]["producer_independent_arithmetic_recomputation"])
        saved=json.loads(OUT.read_text(encoding="utf-8"))
        self.assertEqual(saved["status"],"UNIT_NORMALIZED_NUMERIC_RELATION_VERIFIED")
        self.assertTrue(saved["predicate"])

if __name__=="__main__":
    unittest.main(verbosity=2)
