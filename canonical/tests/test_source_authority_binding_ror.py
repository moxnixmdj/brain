#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/source_authority_binding_ror.py"

def load():
    spec=importlib.util.spec_from_file_location("source_authority_binding_ror",P)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

class RorAuthorityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_normalizes_www_only(self):
        self.assertEqual(self.m._safe_host("https://www.harvard.edu/x"),"harvard.edu")
        self.assertEqual(self.m._safe_host("docs.harvard.edu"),"docs.harvard.edu")

    def test_private_host_rejected(self):
        self.assertIsNone(self.m._safe_host("http://localhost/x"))

    def test_unique_exact_active_match_verifies(self):
        old=self.m._fetch_ror
        try:
            self.m._fetch_ror=lambda d,t: ({
                "number_of_results":3,
                "items":[
                    {"id":"https://ror.org/01","status":"active","domains":["example.org"],"names":[{"types":["ror_display"],"value":"Example Institute"}],"types":["education"]},
                    {"id":"https://ror.org/02","status":"active","domains":["sub.example.org"],"names":[{"types":["ror_display"],"value":"Sub Unit"}],"types":["facility"]},
                    {"id":"https://ror.org/03","status":"inactive","domains":["example.org"],"names":[{"types":["ror_display"],"value":"Old Example"}],"types":["education"]},
                ]
            },"https://api.ror.org/v2/organizations?q=x",200)
            out=self.m.bind_candidate({"url":"https://www.example.org/page"})
            self.assertEqual(out["status"],"AUTHORITY_IDENTITY_VERIFIED",out)
            self.assertEqual(out["ror_id"],"https://ror.org/01")
            self.assertEqual(out["organization_name"],"Example Institute")
            self.assertEqual(out["primary_source_status"],"UNVERIFIED")
            self.assertEqual(out["relevance_status"],"UNVERIFIED")
            self.assertEqual(out["model_dependency_count"],0)
        finally:
            self.m._fetch_ror=old

    def test_lexical_or_subdomain_match_does_not_verify_parent(self):
        old=self.m._fetch_ror
        try:
            self.m._fetch_ror=lambda d,t: ({
                "number_of_results":2,
                "items":[
                    {"id":"https://ror.org/01","status":"active","domains":["example.org"],"names":[]},
                    {"id":"https://ror.org/02","status":"active","domains":["unit.docs.example.org"],"names":[]},
                ]
            },"https://api.ror.org/v2/organizations?q=x",200)
            out=self.m.bind_candidate({"url":"https://docs.example.org/page"})
            self.assertEqual(out["status"],"AUTHORITY_UNRESOLVED",out)
            self.assertEqual(out["reason"],"NO_ACTIVE_EXACT_ROR_DOMAIN_BINDING")
        finally:
            self.m._fetch_ror=old

    def test_duplicate_exact_binding_is_ambiguous(self):
        old=self.m._fetch_ror
        try:
            self.m._fetch_ror=lambda d,t: ({
                "number_of_results":2,
                "items":[
                    {"id":"https://ror.org/01","status":"active","domains":["example.org"],"names":[]},
                    {"id":"https://ror.org/02","status":"active","domains":["example.org"],"names":[]},
                ]
            },"https://api.ror.org/v2/organizations?q=x",200)
            out=self.m.bind_candidate({"url":"https://example.org"})
            self.assertEqual(out["status"],"AUTHORITY_AMBIGUOUS",out)
            self.assertEqual(out["authority_status"],"UNVERIFIED")
        finally:
            self.m._fetch_ror=old

    def test_api_failure_fails_closed(self):
        old=self.m._fetch_ror
        try:
            def boom(d,t): raise TimeoutError("nope")
            self.m._fetch_ror=boom
            out=self.m.bind_candidate({"url":"https://example.org"})
            self.assertEqual(out["status"],"AUTHORITY_UNRESOLVED")
            self.assertEqual(out["authority_status"],"UNVERIFIED")
        finally:
            self.m._fetch_ror=old

    def test_run_writes_narrow_claim_only(self):
        old=self.m._fetch_ror
        try:
            self.m._fetch_ror=lambda d,t: ({
                "number_of_results":1,
                "items":[{"id":"https://ror.org/01","status":"active","domains":["example.org"],"names":[{"types":["ror_display"],"value":"Example Institute"}],"types":["education"]}]
            },"https://api.ror.org/v2/organizations?q=x",200)
            inp=ROOT/"canonical/astra_runtime/tmp/ror_authority_input.json"
            outp=ROOT/"canonical/astra_runtime/tmp/ror_authority_output.json"
            inp.parent.mkdir(parents=True,exist_ok=True)
            inp.write_text(json.dumps({"candidates":[{"url":"https://example.org/a"}]}),encoding="utf-8")
            out=self.m.run({"discovery_path":str(inp.relative_to(ROOT)),"output_path":str(outp.relative_to(ROOT))},ROOT)
            self.assertTrue(out["output_verified"],out)
            self.assertEqual(out["verified_candidate_count"],1)
            self.assertEqual(out["primary_source_verification"],"NOT_PERFORMED")
            self.assertTrue(outp.is_file())
        finally:
            self.m._fetch_ror=old

if __name__=="__main__":
    unittest.main(verbosity=2)
