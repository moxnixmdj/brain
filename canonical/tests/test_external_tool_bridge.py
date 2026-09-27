#!/usr/bin/env python3
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH=CANONICAL_ROOT/"runtime"/"astra_runtime.py"
spec=importlib.util.spec_from_file_location("astra_runtime_external_bridge_test_target",RUNTIME_PATH)
runtime=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class ExternalToolBridgeTests(unittest.TestCase):
    def setUp(self):
        self.old={
            k:os.environ.get(k)
            for k in (
                "PROJECT_BRAIN_AGENT_ID",
                "PROJECT_BRAIN_TASK_ID",
                "PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR",
            )
        }

    def tearDown(self):
        for k,v in self.old.items():
            if v is None: os.environ.pop(k,None)
            else: os.environ[k]=v

    def bind(self,td):
        os.environ["PROJECT_BRAIN_AGENT_ID"]="SUPERWORKER-UNIFIED-1"
        os.environ["PROJECT_BRAIN_TASK_ID"]="SI-REAL-MISSION-001"
        os.environ["PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR"]=td

    def test_request_blocks_then_exact_response_is_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            self.bind(td)
            payload={"url":"https://example.com/data.json","timeout_s":7,"max_bytes":1234}
            with self.assertRaisesRegex(runtime.Blocker,"EXTERNAL_TOOL_REQUEST_PENDING"):
                runtime._external_tool_bridge("http_get",payload)
            req_path=next(pathlib.Path(td).glob("*.request.json"))
            req=json.loads(req_path.read_text(encoding="utf-8"))
            self.assertEqual(req["agent_id"],"SUPERWORKER-UNIFIED-1")
            self.assertEqual(req["task_id"],"SI-REAL-MISSION-001")
            response={
                "schema":"PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1",
                "request_sha256":req["request_sha256"],
                "kind":"http_get",
                "agent_id":"SUPERWORKER-UNIFIED-1",
                "task_id":"SI-REAL-MISSION-001",
                "status":"ok",
                "result":{"url":"https://example.com/data.json","status":200,
                          "body_sha256":"a"*64,"body_excerpt":"ok"},
            }
            pathlib.Path(td,req["request_sha256"]+".response.json").write_text(
                json.dumps(response),encoding="utf-8"
            )
            out=runtime._external_tool_bridge("http_get",payload)
            self.assertEqual(out["status"],200)

    def test_identity_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            self.bind(td)
            payload={"prompt":"inspect current evidence"}
            with self.assertRaisesRegex(runtime.Blocker,"EXTERNAL_TOOL_REQUEST_PENDING"):
                runtime._external_tool_bridge("planner",payload)
            req_path=next(pathlib.Path(td).glob("*.request.json"))
            req=json.loads(req_path.read_text(encoding="utf-8"))
            response={
                "schema":"PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1",
                "request_sha256":req["request_sha256"],
                "kind":"planner",
                "agent_id":"OTHER",
                "task_id":"SI-REAL-MISSION-001",
                "status":"ok",
                "result":{"text":"{}"},
            }
            pathlib.Path(td,req["request_sha256"]+".response.json").write_text(
                json.dumps(response),encoding="utf-8"
            )
            with self.assertRaisesRegex(runtime.Blocker,"EXTERNAL_TOOL_RESPONSE_IDENTITY_MISMATCH"):
                runtime._external_tool_bridge("planner",payload)


if __name__=="__main__":
    unittest.main(verbosity=2)
