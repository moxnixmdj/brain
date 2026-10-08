from __future__ import annotations
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import r2_typed_json_transform_direct_adequacy_v1 as transform

ROOT=Path(__file__).resolve().parents[2]
TMP=ROOT/"canonical/astra_runtime/tmp"
SPEC=TMP/"R2_TYPED_JSON_TRANSFORM_SPEC.json"
SOURCE=TMP/"R2_TYPED_JSON_TRANSFORM_SOURCE.json"
OUTPUT=TMP/"R2_TYPED_JSON_TRANSFORM_OUTPUT.json"
GOAL=("Using the typed JSON transform spec at canonical/astra_runtime/tmp/"
"R2_TYPED_JSON_TRANSFORM_SPEC.json, transform canonical/astra_runtime/tmp/"
"R2_TYPED_JSON_TRANSFORM_SOURCE.json and save the verified JSON result to "
"canonical/astra_runtime/tmp/R2_TYPED_JSON_TRANSFORM_OUTPUT.json.")

class R2TypedJsonTransformDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True,exist_ok=True)
        SOURCE.write_text(json.dumps([
            {"id":"b","status":"KEEP","score":2},
            {"id":"a","status":"KEEP","score":1},
            {"id":"c","status":"DROP","score":3}
        ]),encoding="utf-8")
        SPEC.write_text(json.dumps({
            "schema":transform.SPEC_SCHEMA,
            "operations":[
                {"op":"select_eq","path":["status"],"value":"KEEP"},
                {"op":"sort_by","path":["score"]},
                {"op":"project","fields":["id","score"]},
                {"op":"take","count":1}
            ]
        }),encoding="utf-8")
        if OUTPUT.exists(): OUTPUT.unlink()

    def tearDown(self):
        for p in (SPEC,SOURCE,OUTPUT):
            if p.exists(): p.unlink()

    def test_preflight_binds_verified_jq(self):
        out=transform.preflight({"task_id":"preflight","goal":GOAL})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["capability_id"],"json.query.jq")
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(transform.bound_exec,"execute")
    def test_exact_semantics_commit(self,execute):
        pf=transform.preflight({"task_id":"pass","goal":GOAL})
        def fake(*args,**kwargs):
            OUTPUT.write_text(json.dumps([{"id":"a","score":1}]),encoding="utf-8")
            return {"pass":True,"capability_id":transform.CAPABILITY_ID,
                    "result":{"output_verified":True,"output_path":pf["output_path"]}}
        execute.side_effect=fake
        out=transform.run({"task_id":"pass","goal":GOAL})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["transaction_committed"])

    @patch.object(transform.bound_exec,"execute")
    def test_wrong_semantics_roll_back(self,execute):
        pf=transform.preflight({"task_id":"fail","goal":GOAL})
        def fake(*args,**kwargs):
            OUTPUT.write_text(json.dumps([{"id":"b","score":2}]),encoding="utf-8")
            return {"pass":True,"capability_id":transform.CAPABILITY_ID,
                    "result":{"output_verified":True,"output_path":pf["output_path"]}}
        execute.side_effect=fake
        out=transform.run({"task_id":"fail","goal":GOAL})
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertFalse(OUTPUT.exists())

if __name__=="__main__":
    unittest.main(verbosity=2)
