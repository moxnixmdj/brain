from __future__ import annotations
import hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import r2_exact_evidence_claim_support_direct_adequacy_v1 as claim

ROOT=Path(__file__).resolve().parents[2]
TMP=ROOT/"canonical/astra_runtime/tmp"
EX=TMP/"R2_EXACT_CLAIM_EXTRACTION.json"
OUT=TMP/"R2_EXACT_CLAIM_RESULT.json"
CLAIM="Project Brain verified capability"
GOAL=(
 'Verify that grounded evidence in canonical/astra_runtime/tmp/R2_EXACT_CLAIM_EXTRACTION.json '
 'contains exactly "Project Brain verified capability" and save the verified claim result to '
 'canonical/astra_runtime/tmp/R2_EXACT_CLAIM_RESULT.json.'
)

def sh(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def fixture():
    page=sh("synthetic-page")
    visible="Project Brain verified capability in one exact evidence block."
    visible_sha=sh(visible)
    text=visible
    text_sha=sh(text)
    start=0
    end=len(text)
    uid=sh(f"{page}:{start}:{end}:{text_sha}")
    return {
      "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "output_verified":True,
      "source_url":"https://example.org/evidence",
      "page_raw_sha256":page,
      "visible_text_sha256":visible_sha,
      "evidence_units":[{
        "evidence_unit_id":uid,
        "source_url":"https://example.org/evidence",
        "page_raw_sha256":page,
        "visible_text_sha256":visible_sha,
        "visible_text_start":start,
        "visible_text_end":end,
        "text":text,
        "text_sha256":text_sha
      }]
    }

class R2ExactEvidenceClaimSupportDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True,exist_ok=True)
        EX.write_text(json.dumps(fixture()),encoding="utf-8")
        if OUT.exists(): OUT.unlink()
    def tearDown(self):
        for p in (EX,OUT):
            if p.exists(): p.unlink()

    def test_preflight_binds_exact_claim(self):
        out=claim.preflight({"task_id":"p","goal":GOAL})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["capability_id"],claim.CAPABILITY_ID)
        self.assertEqual(out["claim_text"],CLAIM)
        self.assertEqual(len(out["expected_match_ids"]),1)
        self.assertFalse(out["preflight_execution_authority"])

    def test_extra_instruction_not_applicable(self):
        out=claim.preflight({"task_id":"x","goal":GOAL+" Then publish it."})
        self.assertFalse(out["matched"])

    def test_absent_claim_fails_closed_before_execution(self):
        goal=GOAL.replace("Project Brain verified capability","different absent claim")
        out=claim.preflight({"task_id":"absent","goal":goal})
        self.assertTrue(out["matched"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("EXACT_CLAIM_NOT_PRESENT",out["reason"])

    @patch.object(claim.generic_evidence_claim_relation,"run")
    def test_independent_match_recomputation_commits(self,producer):
        pf=claim.preflight({"task_id":"ok","goal":GOAL})
        uid=pf["expected_match_ids"][0]
        def fake(*args,**kwargs):
            result={
              "status":"EXACT_TEXT_SUPPORT_VERIFIED",
              "claim_text":pf["claim_text"],
              "matches":[{
                "evidence_unit_id":uid,
                "source_url":"https://example.org/evidence",
                "text_sha256":fixture()["evidence_units"][0]["text_sha256"],
                "claim_text":pf["claim_text"],"match_start":0,"match_end":len(pf["claim_text"])
              }],
              "output_verified":True
            }
            OUT.write_text(json.dumps(result),encoding="utf-8")
            return result
        producer.side_effect=fake
        out=claim.run({"task_id":"ok","goal":GOAL})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["transaction_committed"])

    @patch.object(claim.generic_evidence_claim_relation,"run")
    def test_producer_match_mismatch_rolls_back(self,producer):
        pf=claim.preflight({"task_id":"bad","goal":GOAL})
        OUT.write_bytes(b'{"old":true}')
        def fake(*args,**kwargs):
            result={
              "status":"EXACT_TEXT_SUPPORT_VERIFIED",
              "claim_text":pf["claim_text"],
              "matches":[{"evidence_unit_id":"0"*64}],
              "output_verified":True
            }
            OUT.write_text(json.dumps(result),encoding="utf-8")
            return result
        producer.side_effect=fake
        out=claim.run({"task_id":"bad","goal":GOAL})
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(OUT.read_bytes(),b'{"old":true}')

    def test_tampered_evidence_unit_hash_fails_closed(self):
        obj=fixture()
        obj["evidence_units"][0]["text_sha256"]="0"*64
        EX.write_text(json.dumps(obj),encoding="utf-8")
        out=claim.preflight({"task_id":"tamper","goal":GOAL})
        self.assertTrue(out["matched"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("TEXT_HASH_MISMATCH",out["reason"])

if __name__=="__main__":
    unittest.main(verbosity=2)
