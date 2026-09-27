#!/usr/bin/env python3
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=CANONICAL_ROOT/"runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0,str(RUNTIME))

spec=importlib.util.spec_from_file_location("independent_npm_codec_verifier_bridge_target",RUNTIME/"independent_npm_codec_verifier.py")
verifier=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=verifier
spec.loader.exec_module(verifier)

class IndependentNpmVerifierBridgeTests(unittest.TestCase):
    def test_network_constrained_verifier_emits_bridge_request(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            (root/"canonical"/"input.json").parent.mkdir(parents=True)
            (root/"canonical"/"input.json").write_text('{"x":1}\n',encoding="utf-8")
            (root/"canonical"/"out.ubj").write_bytes(b"{}")
            bridge=root/"bridge"
            with mock.patch.dict(os.environ,{
                "PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR":str(bridge),
                "PROJECT_BRAIN_AGENT_ID":"SUPERWORKER-UNIFIED-1",
                "PROJECT_BRAIN_TASK_ID":"SI-REAL-UBJSON-SNAPSHOT-001",
            },clear=False):
                with self.assertRaisesRegex(
                    verifier.IndependentNpmCodecVerifierFailure,
                    "EXTERNAL_TOOL_REQUEST_PENDING"
                ):
                    verifier.verify(
                        "ubj","canonical/input.json","canonical/out.ubj",
                        "NeuroJSON/pybj",root
                    )
            requests=list(bridge.glob("*.request.json"))
            self.assertEqual(len(requests),2)
            reqs=[json.loads(p.read_text(encoding="utf-8")) for p in requests]
            for req in reqs:
                self.assertEqual(req["schema"],"PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1")
                self.assertEqual(req["kind"],"urlopen")
                self.assertEqual(req["agent_id"],"SUPERWORKER-UNIFIED-1")
                self.assertEqual(req["task_id"],"SI-REAL-UBJSON-SNAPSHOT-001")
                self.assertIn("registry.npmjs.org/-/v1/search",req["payload"]["url"])
            urls=[req["payload"]["url"] for req in reqs]
            self.assertTrue(any("text=ubj&" in u for u in urls))
            self.assertTrue(any("text=ubjson&" in u for u in urls))


    def test_builtin_runtime_dependency_is_accepted_without_install(self):
        policy=verifier.npm_package_utils.validate_builtin_only_runtime_dependencies({
            "dependencies":{"buffer":"^5.0.0"},
            "scripts":{},
        })
        self.assertEqual(policy["builtin_dependencies"],["buffer"])
        self.assertEqual(policy["dependency_count"],1)

    def test_external_runtime_dependency_remains_rejected(self):
        with self.assertRaisesRegex(
            verifier.npm_package_utils.NpmPackageFailure,
            "NPM_EXTERNAL_RUNTIME_DEPENDENCIES_UNSUPPORTED"
        ):
            verifier.npm_package_utils.validate_builtin_only_runtime_dependencies({
                "dependencies":{"left-pad":"^1.0.0"},
                "scripts":{},
            })


if __name__=="__main__":
    unittest.main(verbosity=2)
