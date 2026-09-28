import json
import os
import pathlib
import tempfile
import threading
import time
import unittest
from unittest import mock

from canonical.runtime import astra_runtime


class ExternalToolBridgeWaitTests(unittest.TestCase):
    def test_waits_for_identity_bound_response_without_runtime_restart(self):
        with tempfile.TemporaryDirectory() as td:
            bridge = pathlib.Path(td)
            env = {
                "PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR": str(bridge),
                "PROJECT_BRAIN_AGENT_ID": "SUPERWORKER-UNIFIED-1",
                "PROJECT_BRAIN_TASK_ID": "SI-REAL-UBJSON-SNAPSHOT-001",
                "PROJECT_BRAIN_EXTERNAL_TOOL_WAIT_SECONDS": "2",
            }

            def responder():
                deadline = time.monotonic() + 1.0
                request_path = None
                while time.monotonic() < deadline:
                    matches = list(bridge.glob("*.request.json"))
                    if matches:
                        request_path = matches[0]
                        break
                    time.sleep(0.01)
                self.assertIsNotNone(request_path)
                request = json.loads(request_path.read_text(encoding="utf-8"))
                sha = request["request_sha256"]
                response = {
                    "schema": "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1",
                    "request_sha256": sha,
                    "kind": request["kind"],
                    "agent_id": request["agent_id"],
                    "task_id": request["task_id"],
                    "status": "ok",
                    "result": {"marker": "concurrent-response"},
                }
                (bridge / f"{sha}.response.json").write_text(
                    json.dumps(response, sort_keys=True) + "\n",
                    encoding="utf-8",
                )

            thread = threading.Thread(target=responder, daemon=True)
            with mock.patch.dict(os.environ, env, clear=False):
                thread.start()
                result = astra_runtime._external_tool_bridge(
                    "urlopen",
                    {
                        "url": "https://registry.npmjs.org/-/v1/search?text=ubj&size=40",
                        "method": "GET",
                        "headers": {},
                        "timeout_s": 20,
                        "data_b64": None,
                    },
                )
                thread.join(timeout=1.0)

            self.assertEqual(result, {"marker": "concurrent-response"})
            self.assertFalse(thread.is_alive())

    def test_default_behavior_remains_fail_fast(self):
        with tempfile.TemporaryDirectory() as td:
            env = {
                "PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR": td,
                "PROJECT_BRAIN_AGENT_ID": "SUPERWORKER-UNIFIED-1",
                "PROJECT_BRAIN_TASK_ID": "SI-REAL-UBJSON-SNAPSHOT-001",
            }
            with mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(
                    astra_runtime.Blocker, "EXTERNAL_TOOL_REQUEST_PENDING"
                ):
                    astra_runtime._external_tool_bridge(
                        "urlopen",
                        {
                            "url": "https://registry.npmjs.org/-/v1/search?text=ubj&size=40",
                            "method": "GET",
                            "headers": {},
                            "timeout_s": 20,
                            "data_b64": None,
                        },
                    )


if __name__ == "__main__":
    unittest.main()
