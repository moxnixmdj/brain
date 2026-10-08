from __future__ import annotations
import json, unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import r2_http_json_observation_direct_adequacy_v1 as obs

ROOT=Path(__file__).resolve().parents[2]
TMP=ROOT/"canonical/astra_runtime/tmp"
STATE=TMP/"R2_HTTP_JSON_STATE.json"
OUT=TMP/"R2_HTTP_JSON_OUT.json"
GOAL=("Fetch JSON from URL key metadata_url in "
      "canonical/astra_runtime/tmp/R2_HTTP_JSON_STATE.json and save the verified result to "
      "canonical/astra_runtime/tmp/R2_HTTP_JSON_OUT.json.")

class R2HttpJsonObservationDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True,exist_ok=True)
        STATE.write_text(json.dumps({"metadata_url":"https://example.com/data.json"}),encoding="utf-8")
        if OUT.exists(): OUT.unlink()
    def tearDown(self):
        for p in (STATE,OUT):
            if p.exists(): p.unlink()

    def test_preflight_binds_exact_state_key(self):
        out=obs.preflight({"task_id":"p","goal":GOAL})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["capability_id"],obs.CAPABILITY_ID)
        self.assertEqual(out["url_key"],"metadata_url")
        self.assertFalse(out["preflight_execution_authority"])

    def test_extra_instruction_not_applicable(self):
        out=obs.preflight({"task_id":"x","goal":GOAL+" Then post it elsewhere."})
        self.assertFalse(out["matched"])

    @patch.object(obs.http_json_fetch,"run")
    def test_independent_semantic_equality_commits(self,execute):
        pf=obs.preflight({"task_id":"ok","goal":GOAL})
        def fake(*args,**kwargs):
            OUT.write_text(json.dumps({"x":1,"items":[1,2]}),encoding="utf-8")
            return {"output_verified":True,"output_path":pf["output_path"],
                    "requested_url":pf["requested_url"],"final_url":pf["requested_url"]}
        execute.side_effect=fake
        out=obs.run({"task_id":"ok","goal":GOAL},
                    independent_fetch_provider=lambda url:{
                        "producer_independent":True,"parsed_json":{"x":1,"items":[1,2]},
                        "final_url":url,"body_sha256":"a"*64})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["transaction_committed"])

    @patch.object(obs.http_json_fetch,"run")
    def test_independent_mismatch_rolls_back(self,execute):
        pf=obs.preflight({"task_id":"bad","goal":GOAL})
        OUT.write_bytes(b'{"old":true}')
        def fake(*args,**kwargs):
            OUT.write_text(json.dumps({"x":1}),encoding="utf-8")
            return {"pass":True,"capability_id":obs.CAPABILITY_ID,
                    "result":{"output_verified":True,"output_path":pf["output_path"],
                              "requested_url":pf["requested_url"],"final_url":pf["requested_url"]}}
        execute.side_effect=fake
        out=obs.run({"task_id":"bad","goal":GOAL},
                    independent_fetch_provider=lambda url:{
                        "producer_independent":True,"parsed_json":{"x":2},"final_url":url})
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(OUT.read_bytes(),b'{"old":true}')

if __name__=="__main__":
    unittest.main(verbosity=2)
