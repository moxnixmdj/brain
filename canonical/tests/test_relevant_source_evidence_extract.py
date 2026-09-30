#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/relevant_source_evidence_extract.py"

def load(path,name):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    sys.modules[name]=m
    s.loader.exec_module(m)
    return m

class EvidenceExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load(P,"extract_candidate")

    def prov(self,url="https://example.org/report"):
        return {
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "final_url":url,
          "final_host":"example.org",
        }

    def test_single_fetch_extracts_existing_contract_without_authority_gate(self):
        calls=[]
        def fetch(url,timeout):
            calls.append(url)
            return (
              b"<html><title>Floating point summation accuracy</title><body>"
              b"Accurate floating point summation reduces cancellation error. "
              b"In one numerical example the floating point relative error was 0.001 percent. "
              b"Unrelated campus information follows.</body></html>",
              "https://example.org/report","text/html",200
            )
        out=self.m.extract(
          "Assess floating point summation accuracy under cancellation error",
          {"url":"https://example.org/report"},self.prov(),
          timeout=5,fetch=fetch,max_passages=8
        )
        self.assertEqual(len(calls),1,out)
        self.assertEqual(out["status"],"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",out)
        self.assertEqual(out["schema"],"PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1",out)
        self.assertEqual(out["authority_identity_status"],"OPTIONAL_NOT_REQUIRED",out)
        self.assertGreater(out["evidence_record_count"],0,out)
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED")
        self.assertEqual(out["claim_support_status"],"UNVERIFIED")
        self.assertTrue(any(r["numeric_literals"] for r in out["evidence_records"]),out)
        for row in out["evidence_records"]:
            self.assertEqual(row["record_type"],"OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATE")
            self.assertTrue(row["matched_objective_tokens"])
            self.assertEqual(
              row["text_sha256"],
              hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
            )

    def test_legacy_authority_argument_is_ignored_not_required(self):
        html=b"<html><title>SQLite backup API</title><body>The SQLite online backup API copies a live database into another database file while database users continue operating.</body></html>"
        out=self.m.extract(
          "Assess SQLite online backup database copy",
          {"url":"https://example.org/sqlite"},self.prov("https://example.org/sqlite"),
          {"status":"UNVERIFIED","reason":"NO_ROR_MATCH"},
          fetch=lambda url,timeout:(html,"https://example.org/sqlite","text/html",200),
        )
        self.assertEqual(out["status"],"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",out)
        self.assertEqual(out["authority_identity_status"],"OPTIONAL_NOT_REQUIRED",out)

    def test_irrelevant_source_fails_before_extraction(self):
        def fetch(url,timeout):
            return (
              b"<html><title>Admissions</title><body>Campus housing application and dining schedules.</body></html>",
              "https://example.org/x","text/html",200
            )
        out=self.m.extract(
          "Assess volcanic sulfur isotope fractionation magma",
          {"url":"https://example.org/x"},self.prov("https://example.org/x"),fetch=fetch
        )
        self.assertEqual(out["status"],"EXTRACTION_BLOCKED",out)
        self.assertEqual(out["reason"],"VERIFIED_RELEVANT_SOURCE_REQUIRED",out)
        self.assertEqual(out["evidence_records"],[])

    def test_redirect_outside_provenance_host_fails_closed(self):
        out=self.m.extract(
          "Assess post quantum cryptography standards",
          {"url":"https://example.org/x"},self.prov("https://example.org/x"),
          fetch=lambda url,timeout:(
            b"<html><title>Post quantum cryptography standards</title></html>",
            "https://other.example.net/x","text/html",200
          )
        )
        self.assertEqual(out["reason"],"FRESH_SOURCE_REDIRECT_OUTSIDE_PROVENANCE_HOST",out)

    def test_bibliographic_only_provenance_is_rejected_before_fetch(self):
        calls=[]
        out=self.m.extract(
          "Assess post quantum cryptography standards",
          {"url":"https://example.org/x"},
          {"status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED"},
          fetch=lambda *a:calls.append(a)
        )
        self.assertEqual(out["reason"],"LIVE_RETRIEVAL_PROVENANCE_REQUIRED",out)
        self.assertEqual(calls,[])

if __name__=="__main__":
    unittest.main(verbosity=2)
