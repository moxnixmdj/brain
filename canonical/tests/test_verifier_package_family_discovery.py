#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"runtime"
sys.path.insert(0,str(RUNTIME))

spec=importlib.util.spec_from_file_location("verifier_family_discovery_test",RUNTIME/"verify_pending_cli_binding.py")
v=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=v
spec.loader.exec_module(v)

class VerifierFamilyDiscoveryTests(unittest.TestCase):
    def test_family_tokens_remove_packaging_noise(self):
        self.assertIn("zxing",v._package_family_tokens("libzxing-java"))
        self.assertIn("example",v._package_family_tokens("python3-example-tools"))

    def test_semantic_hit_can_reveal_cli_sibling_without_hardcoded_name(self):
        calls=[]
        def fake_search(effect,limit=12):
            calls.append(effect)
            if "decode" in effect and "read" in effect:
                return {
                  "candidate_count":1,"errors":[],
                  "candidates":[{
                    "name":"libvision-java",
                    "description":"machine-readable symbol scanning library",
                    "score":70,
                    "integration_friction":3,
                    "zero_cost_eligible":True,
                    "matched_terms":["scan"]
                  }]
                }
            if effect=="vision":
                return {
                  "candidate_count":1,"errors":[],
                  "candidates":[{
                    "name":"vision-tools",
                    "description":"command-line utilities",
                    "score":40,
                    "integration_friction":0,
                    "zero_cost_eligible":True,
                    "matched_terms":["vision"]
                  }]
                }
            return {"candidate_count":0,"errors":[],"candidates":[]}
        with mock.patch.object(v.capability_discovery,"search_apt_packages",side_effect=fake_search):
            out=v._merge_verifier_discovery(
                "Generate a machine-readable matrix image.",limit_per_query=24
            )
        names=[x["name"] for x in out["candidates"]]
        self.assertIn("vision-tools",names)
        self.assertEqual(names[0],"vision-tools")
        self.assertEqual(calls.count("vision"),1)
        self.assertLessEqual(len(calls),7)

if __name__=="__main__":
    unittest.main(verbosity=2)
