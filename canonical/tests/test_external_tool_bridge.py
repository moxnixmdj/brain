#!/usr/bin/env python3
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

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

    def bind(self,root):
        os.environ["PROJECT_BRAIN_AGENT_ID"]="SUPERWORKER-UNIFIED-1"
        os.environ["PROJECT_BRAIN_TASK_ID"]="SI-REAL-MISSION-001"
        bridge=(
            pathlib.Path(root)
            /"canonical"/"same_identity_worker"/"external_tool_bridge"/"SI-REAL-MISSION-001"
        )
        bridge.mkdir(parents=True,exist_ok=True)
        os.environ["PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR"]=str(bridge)
        return bridge

    def test_request_blocks_then_exact_response_is_accepted(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(runtime,"ROOT",pathlib.Path(td)), \
             mock.patch.object(runtime,"_authorize_external_information",return_value={"pass":True}):
            bridge=self.bind(td)
            payload={"url":"https://example.com/data.json","timeout_s":7,"max_bytes":1234}
            with self.assertRaisesRegex(runtime.Blocker,"EXTERNAL_TOOL_REQUEST_PENDING"):
                runtime._external_tool_bridge("http_get",payload)
            req_path=next(bridge.glob("*.request.json"))
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
            pathlib.Path(bridge,req["request_sha256"]+".response.json").write_text(
                json.dumps(response),encoding="utf-8"
            )
            out=runtime._external_tool_bridge("http_get",payload)
            self.assertEqual(out["status"],200)

    def test_identity_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(runtime,"ROOT",pathlib.Path(td)), \
             mock.patch.object(runtime,"_authorize_external_information",return_value={"pass":True}):
            bridge=self.bind(td)
            payload={"prompt":"inspect current evidence"}
            with self.assertRaisesRegex(runtime.Blocker,"EXTERNAL_TOOL_REQUEST_PENDING"):
                runtime._external_tool_bridge("planner",payload)
            req_path=next(bridge.glob("*.request.json"))
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
            pathlib.Path(bridge,req["request_sha256"]+".response.json").write_text(
                json.dumps(response),encoding="utf-8"
            )
            with self.assertRaisesRegex(runtime.Blocker,"EXTERNAL_TOOL_RESPONSE_IDENTITY_MISMATCH"):
                runtime._external_tool_bridge("planner",payload)


    def test_direct_urlopen_fallback_is_mediated_and_receipted(self):
        fake=runtime._ExternalBridgeHTTPResponse(b"ok",200,"https://example.com/final",{})
        with mock.patch.object(runtime,"_external_tool_bridge",return_value=None), \
             mock.patch.object(runtime,"_ACTIVE_CONTINUOUS_OBS_CONTEXT",{"bound":True}), \
             mock.patch.object(runtime,"_ACTIVE_CONTINUOUS_OBS_MODULE",object()), \
             mock.patch.object(runtime,"_ACTIVE_CONTINUOUS_OBS_MISSION_ID","MISSION-1"), \
             mock.patch.object(runtime,"_ORIGINAL_URLOPEN",return_value=fake) as raw, \
             mock.patch.object(runtime,"_append_admin_jsonl") as append:
            out=runtime._bridge_aware_urlopen("https://example.com/data")
            self.assertIs(out,fake)
            raw.assert_called_once()
            self.assertEqual(append.call_count,2)
            self.assertEqual(append.call_args_list[0].args[1]["phase"],"ATTEMPT")
            self.assertEqual(append.call_args_list[1].args[1]["phase"],"OPENED")

    def test_direct_urlopen_fallback_requires_bound_mission_context(self):
        with mock.patch.object(runtime,"_external_tool_bridge",return_value=None), \
             mock.patch.object(runtime,"_ACTIVE_CONTINUOUS_OBS_CONTEXT",None), \
             mock.patch.object(runtime,"_ACTIVE_CONTINUOUS_OBS_MODULE",None), \
             mock.patch.object(runtime,"_ACTIVE_CONTINUOUS_OBS_MISSION_ID",None), \
             mock.patch.object(runtime,"_ORIGINAL_URLOPEN") as raw:
            with self.assertRaisesRegex(runtime.Blocker,"DIRECT_NETWORK_EFFECT_CONTEXT_NOT_BOUND"):
                runtime._bridge_aware_urlopen("https://example.com/data")
            raw.assert_not_called()

    def test_direct_urlopen_fallback_rejects_non_http_effects(self):
        with mock.patch.object(runtime,"_external_tool_bridge",return_value=None), \
             mock.patch.object(runtime,"_ACTIVE_CONTINUOUS_OBS_CONTEXT",{"bound":True}), \
             mock.patch.object(runtime,"_ACTIVE_CONTINUOUS_OBS_MODULE",object()), \
             mock.patch.object(runtime,"_ACTIVE_CONTINUOUS_OBS_MISSION_ID","MISSION-1"), \
             mock.patch.object(runtime,"_ORIGINAL_URLOPEN") as raw:
            with self.assertRaisesRegex(runtime.Blocker,"DIRECT_NETWORK_EFFECT_URL_NOT_HTTP_S"):
                runtime._bridge_aware_urlopen("file:///etc/passwd")
            raw.assert_not_called()

    def test_arbitrary_bridge_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(runtime,"ROOT",pathlib.Path(td)), \
             mock.patch.object(runtime,"_authorize_external_information",return_value={"pass":True}):
            os.environ["PROJECT_BRAIN_AGENT_ID"]="SUPERWORKER-UNIFIED-1"
            os.environ["PROJECT_BRAIN_TASK_ID"]="SI-REAL-MISSION-001"
            bad=pathlib.Path(td)/"arbitrary-bridge"
            os.environ["PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR"]=str(bad)
            with self.assertRaisesRegex(runtime.Blocker,"EXTERNAL_TOOL_BRIDGE_DIR_IDENTITY_MISMATCH"):
                runtime._external_tool_bridge("http_get",{"url":"https://example.com/"})
            self.assertFalse(bad.exists())

    def test_task_scoped_bridge_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside, \
             mock.patch.object(runtime,"ROOT",pathlib.Path(td)), \
             mock.patch.object(runtime,"_authorize_external_information",return_value={"pass":True}):
            os.environ["PROJECT_BRAIN_AGENT_ID"]="SUPERWORKER-UNIFIED-1"
            os.environ["PROJECT_BRAIN_TASK_ID"]="SI-REAL-MISSION-001"
            bridge=pathlib.Path(td)/"canonical"/"same_identity_worker"/"external_tool_bridge"/"SI-REAL-MISSION-001"
            bridge.parent.mkdir(parents=True,exist_ok=True)
            try:
                bridge.symlink_to(pathlib.Path(outside),target_is_directory=True)
            except (OSError,NotImplementedError):
                self.skipTest("symlink unavailable")
            os.environ["PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR"]=str(bridge)
            with self.assertRaisesRegex(runtime.Blocker,"EXTERNAL_TOOL_BRIDGE_TASK_DIR_SYMLINK_FORBIDDEN"):
                runtime._external_tool_bridge("http_get",{"url":"https://example.com/"})



if __name__=="__main__":
    unittest.main(verbosity=2)
