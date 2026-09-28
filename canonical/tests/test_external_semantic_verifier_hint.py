#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"runtime"
sys.path.insert(0,str(RUNTIME))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

v=load("external_semantic_hint_test",RUNTIME/"verify_pending_cli_binding.py")

class ExternalSemanticVerifierHintTests(unittest.TestCase):
    def test_resolved_external_hint_is_not_rejected_for_missing_search_terms(self):
        pending={
          "selected_supplier":{"name":"producer"},
          "goal":"Generate an unfamiliar machine-readable image.",
          "semantic_verification":{
            "expected_text":"HELLO",
            "goal":"Generate an unfamiliar machine-readable image.",
            "verifier_package_hints":[{"name":"independent-reader"}]
          }
        }
        candidate={
          "name":"independent-reader","version":"1",
          "archive_sha256":"a"*64,
          "binding_kind":"apt",
          "discovery_source":"EXTERNAL_SEMANTIC_PACKAGE_HINT",
          "zero_cost_eligible":True,
          "integration_friction":0,
          "required_secret_count":0,
          "required_environment_count":0,
          "matched_terms":[],
          "score":1000
        }
        probe={"executables":[{"executable":"/usr/bin/reader","help_attempts":[{
          "text":"Usage: reader IMAGE\nRead and decode image symbols. Decoded content is written to standard output.\n"
        }]}]}
        proc=mock.Mock(returncode=0,stdout="HELLO\n",stderr="")
        with (
          mock.patch.object(v,"_resolve_apt_candidate_name",return_value=candidate),
          mock.patch.object(v.capability_discovery,"search_apt_packages",return_value={"candidates":[]}),
          mock.patch.object(v.apt_cli_probe,"probe",return_value=probe),
          mock.patch.object(v.subprocess,"run",return_value=proc),
        ):
            out=v._acquire_and_run_semantic_verifier(pending,"/tmp/out.png")
        self.assertTrue(out["verified"])
        self.assertEqual(out["verifier_package"],"independent-reader")

if __name__=="__main__":
    unittest.main(verbosity=2)
