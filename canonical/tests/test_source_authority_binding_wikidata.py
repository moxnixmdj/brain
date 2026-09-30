#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/source_authority_binding_wikidata.py"

def load():
    spec=importlib.util.spec_from_file_location("source_authority_binding_wikidata",P)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

class SourceAuthorityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_same_site_requires_label_boundary(self):
        self.assertTrue(self.m._same_site("docs.python.org","python.org"))
        self.assertTrue(self.m._same_site("python.org","www.python.org"))
        self.assertFalse(self.m._same_site("evilpython.org","python.org"))

    def test_resolver_host_never_becomes_source_authority(self):
        out=self.m.bind_candidate({
            "url":"https://doi.org/10.17487/RFC9110",
            "title":"RFC 9110 HTTP Semantics",
        })
        self.assertEqual(out["status"],"AUTHORITY_UNRESOLVED",out)
        self.assertEqual(out["authority_status"],"UNVERIFIED")

    def test_unsafe_url_fails_closed(self):
        out=self.m.bind_candidate({"url":"http://localhost/private","title":"anything"})
        self.assertEqual(out["status"],"AUTHORITY_UNRESOLVED",out)
        self.assertEqual(out["authority_status"],"UNVERIFIED")

    def test_live_python_host_matches_independent_p856(self):
        out=self.m.bind_candidate({
            "url":"https://www.python.org/",
            "host":"www.python.org",
            "title":"Welcome to Python.org",
        },timeout=20)
        self.assertEqual(out["status"],"AUTHORITY_IDENTITY_VERIFIED",out)
        self.assertEqual(out["authority_status"],"VERIFIED")
        self.assertTrue(self.m._same_site(out["official_host"],"python.org"))
        self.assertEqual(out["registry_property"],"P856")
        self.assertEqual(out["primary_source_status"],"UNVERIFIED")
        self.assertEqual(out["relevance_status"],"UNVERIFIED")
        self.assertEqual(out["model_dependency_count"],0)
        self.assertEqual(out["incremental_spend_usd"],0)

    def test_run_writes_only_narrow_authority_claim(self):
        rel="canonical/astra_runtime/tmp/source_authority_binding_test_input.json"
        outrel="canonical/astra_runtime/tmp/source_authority_binding_test_output.json"
        inp=ROOT/rel
        inp.parent.mkdir(parents=True,exist_ok=True)
        inp.write_text(json.dumps({
            "objective":"Find documentation for a general-purpose programming language implementation.",
            "candidates":[{
                "url":"https://www.python.org/",
                "host":"www.python.org",
                "title":"Welcome to Python.org",
                "authority_status":"UNVERIFIED"
            }]
        }),encoding="utf-8")
        out=self.m.run({
            "discovery_path":rel,
            "output_path":outrel,
            "timeout":20,
            "max_candidates":4,
        },ROOT)
        self.assertTrue(out["output_verified"],out)
        self.assertGreater(out["verified_candidate_count"],0,out)
        self.assertEqual(out["primary_source_verification"],"NOT_PERFORMED")
        self.assertEqual(out["relevance_verification"],"NOT_PERFORMED")
        self.assertTrue((ROOT/outrel).is_file())

if __name__=="__main__":
    unittest.main(verbosity=2)
