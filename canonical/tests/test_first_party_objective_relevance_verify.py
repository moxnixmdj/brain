#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/first_party_objective_relevance_verify.py"

def load():
    s=importlib.util.spec_from_file_location("first_party_rel",P)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()

    def auth(self,domain="example.org"):
        return {"status":"AUTHORITY_IDENTITY_VERIFIED","matched_domain":domain}
    def prov(self,url="https://example.org/report"):
        return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":url,"final_host":"example.org"}

    def test_relevant_first_party_passes_without_primary_claim(self):
        def fetch(url,timeout):
            return (
              b"<html><title>Floating point summation reference</title><body>Accurate floating point summation reduces cancellation error.</body></html>",
              "https://example.org/report","text/html",200
            )
        out=self.m.verify(
          "Assess floating point summation accuracy under cancellation",
          {"url":"https://example.org/report"},self.prov(),self.auth(),fetch=fetch
        )
        self.assertEqual(out["status"],"FIRST_PARTY_RELEVANT_SOURCE_VERIFIED",out)
        self.assertEqual(out["first_party_source_status"],"VERIFIED")
        self.assertEqual(out["objective_relevance_status"],"VERIFIED")
        self.assertEqual(out["primary_source_status"],"UNVERIFIED")
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED")

    def test_irrelevant_first_party_fails_relevance(self):
        def fetch(url,timeout):
            return (b"<html><title>Admissions</title><body>Campus admissions and student housing.</body></html>","https://example.org/report","text/html",200)
        out=self.m.verify(
          "Assess volcanic sulfur isotope fractionation in magma",
          {"url":"https://example.org/report"},self.prov(),self.auth(),fetch=fetch
        )
        self.assertEqual(out["status"],"FIRST_PARTY_SOURCE_VERIFIED__OBJECTIVE_RELEVANCE_UNRESOLVED",out)
        self.assertEqual(out["objective_relevance_status"],"UNVERIFIED")

    def test_redirect_outside_authority_fails_closed(self):
        def fetch(url,timeout):
            return (b"relevant floating point summation","https://evil.example.net/x","text/plain",200)
        out=self.m.verify(
          "Assess floating point summation accuracy",
          {"url":"https://example.org/report"},self.prov(),self.auth(),fetch=fetch
        )
        self.assertEqual(out["status"],"UNVERIFIED",out)
        self.assertEqual(out["reason"],"FRESH_SOURCE_REDIRECT_OUTSIDE_BOUND_AUTHORITY_DOMAIN")

    def test_authority_and_live_provenance_required(self):
        x=self.m.verify("Assess x",{},{"status":"UNVERIFIED"},self.auth())
        self.assertEqual(x["reason"],"LIVE_RETRIEVAL_PROVENANCE_REQUIRED")
        y=self.m.verify("Assess x",{},self.prov(),{"status":"UNVERIFIED"})
        self.assertEqual(y["reason"],"QUALIFIED_AUTHORITY_IDENTITY_REQUIRED")

if __name__=="__main__": unittest.main(verbosity=2)
