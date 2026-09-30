#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py"

def load():
    spec=importlib.util.spec_from_file_location("source_discovery",PATH)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class SourceCandidateDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_ddg_parser_and_redirect_unwrap(self):
        p=self.m._DDGParser()
        p.feed("""<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fspec">Example Spec</a>""")
        self.assertEqual(len(p.items),1)
        self.assertEqual(self.m._unwrap_ddg(p.items[0][0]),"https://example.org/spec")

    def test_query_is_objective_not_invented_recipe(self):
        q="Assess whether a standards document changed between two editions"
        self.assertEqual(self.m._query(q),q)

    def test_local_urls_fail_closed(self):
        self.assertIsNone(self.m._safe_url("http://localhost/x"))
        self.assertIsNone(self.m._safe_url("file:///tmp/x"))
        self.assertEqual(self.m._safe_url("https://example.org/x"),"https://example.org/x")

    def test_live_cross_domain_candidate_discovery(self):
        objectives=[
            "RFC 9110 HTTP semantics official specification",
            "lithium ion battery calendar aging temperature experimental study",
            "Python urllib request library official documentation",
        ]
        for objective in objectives:
            out=self.m.discover(objective,limit=10,timeout=20)
            self.assertEqual(out["status"],"CANDIDATES_DISCOVERED",out)
            self.assertGreaterEqual(out["candidate_count"],1,out)
            self.assertEqual(out["query"],objective)
            self.assertEqual(out["model_dependency_count"],0)
            self.assertEqual(out["incremental_spend_usd"],0)
            self.assertEqual(out["authority_verification"],"NOT_PERFORMED")
            for c in out["candidates"]:
                self.assertEqual(c["authority_status"],"UNVERIFIED")
                self.assertTrue(c["url"].startswith(("http://","https://")))

if __name__=="__main__":
    unittest.main(verbosity=2)
