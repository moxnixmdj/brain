#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import unittest

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = CANONICAL_ROOT.parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

runtime = load("astra_runtime_bound_test", CANONICAL_ROOT/"runtime"/"astra_runtime.py")
adapter = load("pdf_pypdf_bound_test", CANONICAL_ROOT/"runtime"/"bound_capabilities"/"pdf_pypdf.py")

class BoundCapabilityTests(unittest.TestCase):
    def test_registry_is_zero_cost_and_hash_pinned(self):
        data=json.loads((CANONICAL_ROOT/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
        cap=data["capabilities"]["pdf.extract.text.pypdf"]
        self.assertEqual(cap["incremental_spend_usd"],0)
        self.assertEqual(cap["source"]["version"],"6.19.0")
        self.assertEqual(len(cap["source"]["wheel_sha256"]),64)

    def test_adapter_rejects_path_escape(self):
        with self.assertRaisesRegex(RuntimeError,"PATH_OUTSIDE_REPOSITORY"):
            adapter._safe_path(REPO_ROOT,"../outside.pdf")

    def test_action_expectation_contains(self):
        action={"expect":{"type":"field_contains","field":"text","value":"needle"}}
        runtime._verify_action_expectation(action,{"text":"hay needle stack"})

    def test_action_expectation_fails_closed(self):
        action={"expect":{"type":"field_contains","field":"text","value":"needle"}}
        with self.assertRaisesRegex(runtime.Blocker,"ACTION_EXPECTATION_FAILED:text"):
            runtime._verify_action_expectation(action,{"text":"hay only"})

    def test_unknown_bound_capability_rejected(self):
        with self.assertRaisesRegex(runtime.Blocker,"BOUND_CAPABILITY_UNKNOWN"):
            runtime._invoke_bound_capability({"capability_id":"does.not.exist"})

if __name__=="__main__":
    unittest.main(verbosity=2)
