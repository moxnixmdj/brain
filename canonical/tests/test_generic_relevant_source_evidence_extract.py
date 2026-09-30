#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/generic_relevant_source_evidence_extract.py"
def load():
    s=importlib.util.spec_from_file_location("generic_extract",P)
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); return m
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=load()
    def verified(self):
        return [
          {"candidate":{"url":"https://docs.example.org/fsum","title":"Floating point summation accuracy","snippet":"accurate stable summation cancellation"},
           "verification":{"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":"https://docs.example.org/fsum","final_host":"docs.example.org"}},
          {"candidate":{"url":"https://other.example.net/garden","title":"Garden plants","snippet":"watering flowers"},
           "verification":{"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":"https://other.example.net/garden","final_host":"other.example.net"}},
        ]
    def test_extracts_without_ror_and_reuses_bm25(self):
        calls=[]
        def fetch(url,timeout):
            calls.append(url)
            return (b"<html><title>Floating point summation accuracy</title><body>Stable floating point summation reduces cancellation error. The observed error was 0.001 percent.</body></html>",url,"text/html",200)
        x=self.m.extract("Assess floating point summation accuracy cancellation",self.verified(),fetch=fetch)
        self.assertEqual(x["status"],"GENERIC_OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",x)
        self.assertTrue(x["fresh_same_host_verified"])
        self.assertFalse(x["authority_identity_required"])
        self.assertEqual(x["ror_metadata_requirement"],"OPTIONAL")
        self.assertEqual(len(calls),1)
        self.assertGreater(x["evidence_record_count"],0)
        self.assertEqual(x["factual_correctness_status"],"UNVERIFIED")
    def test_fresh_cross_host_redirect_fails_closed(self):
        def fetch(url,timeout):
            return (b"floating point summation accuracy","https://evil.example/x","text/plain",200)
        x=self.m.extract("Assess floating point summation accuracy",self.verified(),fetch=fetch)
        self.assertEqual(x["status"],"EXTRACTION_BLOCKED",x)
        self.assertTrue(any(y.get("reason")=="FRESH_HOST_MISMATCH" for y in x.get("candidate_failures") or []),x)
    def test_unverified_candidate_not_admitted(self):
        x=self.m.extract("Assess anything",[{"candidate":{"url":"https://example.org/x"},"verification":{"status":"UNVERIFIED"}}])
        self.assertEqual(x["reason"],"RETRIEVAL_PROVENANCE_VERIFIED_CANDIDATE_REQUIRED")
if __name__=="__main__":unittest.main(verbosity=2)
