#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import unittest

CANONICAL=pathlib.Path(__file__).resolve().parents[1]
ROOT=CANONICAL.parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

runtime=load("astra_runtime_composition_test",CANONICAL/"runtime"/"astra_runtime.py")

class RuntimeCompositionTests(unittest.TestCase):
    def test_result_reference_resolves_prior_action_field(self):
        trace=[{"cycle":0,"result":{"text":"ALPHA BETA","nested":{"x":7}}}]
        self.assertEqual(
            runtime._resolve_result_refs({"v":{"$result":{"cycle":0,"field":"nested.x"}}},trace),
            {"v":7},
        )

    def test_json_key_assertion_is_layout_insensitive(self):
        p=CANONICAL/"astra_runtime"/"tmp"/"COMPOSITION_KEYS_TEST.json"
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({"items":{"alpha-one":{},"beta.two":{}}}),encoding="utf-8")
        try:
            out=runtime._goal_action({
                "type":"assert_text_contains_json_keys",
                "args":{
                    "text":"ALPHA ONE\nBETA . TWO",
                    "json_path":"canonical/astra_runtime/tmp/COMPOSITION_KEYS_TEST.json",
                    "collection_path":["items"],
                    "normalization":"alnum_upper",
                },
            })
            self.assertTrue(out["verified"])
            self.assertEqual(out["missing_keys"],[])
        finally:
            p.unlink(missing_ok=True)

if __name__=="__main__":
    unittest.main(verbosity=2)
