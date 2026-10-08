from __future__ import annotations
import hashlib,json,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from canonical.runtime import r2_knowledge_consistency_direct_adequacy_v1 as kc

ROOT=Path(__file__).resolve().parents[2]
TMP=ROOT/"canonical/astra_runtime/tmp"
MAN=TMP/"R2_KC_MANIFEST.json"
OUT=TMP/"R2_KC_ASSESSMENT.json"
E1=TMP/"R2_KC_E1.json"
E2=TMP/"R2_KC_E2.json"

def now(delta=0):
    return (datetime.now(timezone.utc)+timedelta(seconds=delta)).isoformat()

def ev(url,value,ts=None,path=None):
    return {
      "schema":"PROJECT_BRAIN_KNOWLEDGE_EVIDENCE_V1",
      "source_url":url,
      "final_url":url,
      "http_status":200,
      "retrieved_at_utc":ts or now(),
      "body_sha256":hashlib.sha256((url+json.dumps(value,sort_keys=True)).encode()).hexdigest(),
      "json_path":path or ["value"],
      "value":value,
      "source_type":"external_json"
    }

def manifest(max_age=None):
    obj={"schema":"PROJECT_BRAIN_KNOWLEDGE_CONSISTENCY_REQUEST_V1",
         "evidence_paths":[
           "canonical/astra_runtime/tmp/R2_KC_E1.json",
           "canonical/astra_runtime/tmp/R2_KC_E2.json"]}
    if max_age is not None: obj["max_age_s"]=max_age
    return obj

GOAL=("Assess knowledge consistency using manifest "
      "canonical/astra_runtime/tmp/R2_KC_MANIFEST.json and save the verified assessment to "
      "canonical/astra_runtime/tmp/R2_KC_ASSESSMENT.json.")

class R2KnowledgeConsistencyDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True,exist_ok=True)
        E1.write_text(json.dumps(ev("https://a.example/data",{"x":1})),encoding="utf-8")
        E2.write_text(json.dumps(ev("https://b.example/data",{"x":1})),encoding="utf-8")
        MAN.write_text(json.dumps(manifest()),encoding="utf-8")
        if OUT.exists(): OUT.unlink()
    def tearDown(self):
        for p in (MAN,OUT,E1,E2):
            if p.exists(): p.unlink()

    def test_supported_distinct_sources(self):
        out=kc.run({"task_id":"supported","goal":GOAL})
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["assessment_status"],"SUPPORTED")
        self.assertEqual(out["distinct_fresh_values"],1)
        self.assertEqual(out["distinct_fresh_source_identities"],2)

    def test_conflicted_values_are_verified_outcome(self):
        E2.write_text(json.dumps(ev("https://b.example/data",{"x":2})),encoding="utf-8")
        out=kc.run({"task_id":"conflict","goal":GOAL})
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["assessment_status"],"CONFLICTED")
        self.assertEqual(out["distinct_fresh_values"],2)

    def test_stale_is_verified_outcome(self):
        old=now(-3600)
        E1.write_text(json.dumps(ev("https://a.example/data",1,old)),encoding="utf-8")
        E2.write_text(json.dumps(ev("https://b.example/data",1,old)),encoding="utf-8")
        MAN.write_text(json.dumps(manifest(60)),encoding="utf-8")
        out=kc.run({"task_id":"stale","goal":GOAL})
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["assessment_status"],"STALE")
        self.assertEqual(out["fresh_evidence_count"],0)

    def test_same_source_identity_is_insufficient(self):
        E2.write_text(json.dumps(ev("https://a.example/data",{"x":1})),encoding="utf-8")
        out=kc.run({"task_id":"insufficient","goal":GOAL})
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["assessment_status"],"INSUFFICIENT")
        self.assertEqual(out["distinct_fresh_source_identities"],1)

    def test_different_json_paths_are_distinct_bounded_identities(self):
        E2.write_text(json.dumps(ev("https://a.example/data",{"x":1},path=["other"])),encoding="utf-8")
        out=kc.run({"task_id":"path-identity","goal":GOAL})
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["assessment_status"],"SUPPORTED")
        self.assertEqual(out["distinct_fresh_source_identities"],2)

    def test_malformed_evidence_fails_closed(self):
        bad=ev("https://b.example/data",{"x":1})
        bad["body_sha256"]="bad"
        E2.write_text(json.dumps(bad),encoding="utf-8")
        out=kc.preflight({"task_id":"bad","goal":GOAL})
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("EVIDENCE_CONTRACT_INVALID",out["reason"])

    def test_extra_instruction_not_applicable(self):
        out=kc.preflight({"task_id":"x","goal":GOAL+" Then publish it."})
        self.assertFalse(out["matched"])

if __name__=="__main__":
    unittest.main(verbosity=2)
