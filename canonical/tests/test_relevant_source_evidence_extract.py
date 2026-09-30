#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/relevant_source_evidence_extract.py"

def load(path,name):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m

class EvidenceExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load(P,"extract_candidate")

    def test_single_fetch_reuse_extracts_provenance_bound_claim_candidates(self):
        calls=[]
        def fetch(url,timeout):
            calls.append(url)
            return (
              b"<html><title>Floating point summation accuracy</title><body>"
              b"Accurate floating point summation reduces cancellation error. "
              b"In one numerical example the relative error was 0.001 percent. "
              b"Unrelated campus information follows.</body></html>",
              "https://example.org/report","text/html",200
            )
        out=self.m.extract(
          "Assess floating point summation accuracy under cancellation error",
          {"url":"https://example.org/report"},
          {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":"https://example.org/report","final_host":"example.org"},
          {"status":"AUTHORITY_IDENTITY_VERIFIED","matched_domain":"example.org"},
          timeout=5,fetch=fetch,max_passages=8
        )
        self.assertEqual(len(calls),1,out)
        self.assertEqual(out["status"],"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",out)
        self.assertGreater(out["evidence_record_count"],0,out)
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED")
        self.assertEqual(out["claim_support_status"],"UNVERIFIED")
        self.assertTrue(any(r["numeric_literals"] for r in out["evidence_records"]),out)
        for row in out["evidence_records"]:
            self.assertEqual(row["record_type"],"OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATE")
            self.assertTrue(row["matched_objective_tokens"])

    def test_irrelevant_source_fails_before_extraction(self):
        def fetch(url,timeout):
            return (b"<html><title>Admissions</title><body>Campus housing application.</body></html>","https://example.org/x","text/html",200)
        out=self.m.extract(
          "Assess volcanic sulfur isotope fractionation magma",
          {"url":"https://example.org/x"},
          {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":"https://example.org/x","final_host":"example.org"},
          {"status":"AUTHORITY_IDENTITY_VERIFIED","matched_domain":"example.org"},
          fetch=fetch
        )
        self.assertEqual(out["status"],"EXTRACTION_BLOCKED",out)
        self.assertEqual(out["reason"],"VERIFIED_RELEVANT_SOURCE_REQUIRED",out)

if __name__=="__main__": unittest.main(verbosity=2)
