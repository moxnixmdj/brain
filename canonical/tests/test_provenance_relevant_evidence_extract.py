#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import importlib.util
import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/provenance_relevant_evidence_extract.py"

def load():
    s=importlib.util.spec_from_file_location("provenance_relevant_extract",P)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

class ProvenanceRelevantEvidenceExtractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def prov(self,url="https://example.org/report"):
        return {
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "final_url":url,
          "final_host":"example.org",
        }

    def test_extracts_hashed_units_without_authority_or_relation_claims(self):
        html=(
          b"<html><head><title>Post quantum cryptography standards</title></head><body>"
          b"<nav>site navigation</nav>"
          b"<h1>Post quantum cryptography standards</h1>"
          b"<p>Post quantum cryptography standards guide migration toward quantum resistant systems.</p>"
          b"<p>Administrative contact information.</p></body></html>"
        )
        out=self.m.extract(
          "Assess post quantum cryptography standards migration resilience",
          {"url":"https://example.org/report"},
          self.prov(),
          fetch=lambda url,timeout:(html,"https://example.org/report","text/html",200),
        )
        self.assertEqual(out["status"],"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",out)
        self.assertEqual(out["objective_relevance_status"],"VERIFIED",out)
        self.assertEqual(out["evidence_extraction_status"],"VERIFIED",out)
        self.assertEqual(out["authority_identity_status"],"OPTIONAL_NOT_REQUIRED",out)
        self.assertEqual(out["claim_relation_status"],"UNVERIFIED",out)
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED",out)
        self.assertEqual(out["evidence_sufficiency_status"],"UNVERIFIED",out)
        self.assertGreaterEqual(out["evidence_unit_count"],1,out)
        for unit in out["evidence_units"]:
            self.assertEqual(
              unit["text_sha256"],
              hashlib.sha256(unit["text"].encode("utf-8")).hexdigest(),
            )
            self.assertGreaterEqual(len(unit["matched_objective_tokens"]),2)
            self.assertLess(unit["visible_text_start"],unit["visible_text_end"])

    def test_no_ror_or_authority_argument_is_required(self):
        html=b"<html><title>SQLite backup consistency</title><body><p>SQLite backup consistency uses transaction snapshots during concurrent writes.</p></body></html>"
        out=self.m.extract(
          "Assess SQLite backup consistency transaction snapshots concurrent writes",
          {"url":"https://example.org/sqlite"},
          self.prov("https://example.org/sqlite"),
          fetch=lambda url,timeout:(html,"https://example.org/sqlite","text/html",200),
        )
        self.assertEqual(out["status"],"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",out)
        self.assertNotIn("authority_identity",out)

    def test_irrelevant_fresh_page_fails_closed(self):
        html=b"<html><title>Admissions calendar</title><body><p>Campus housing applications and cafeteria schedules.</p></body></html>"
        out=self.m.extract(
          "Assess volcanic sulfur isotope fractionation mantle magma plumes",
          {"url":"https://example.org/report"},
          self.prov(),
          fetch=lambda url,timeout:(html,"https://example.org/report","text/html",200),
        )
        self.assertEqual(out["status"],"UNVERIFIED",out)
        self.assertEqual(out["reason"],"FRESH_PAGE_OBJECTIVE_RELEVANCE_UNVERIFIED",out)
        self.assertEqual(out["evidence_units"],[])

    def test_redirect_outside_provenance_host_fails_closed(self):
        out=self.m.extract(
          "Assess post quantum cryptography standards",
          {"url":"https://example.org/report"},
          self.prov(),
          fetch=lambda url,timeout:(
            b"<html><p>post quantum cryptography standards</p></html>",
            "https://other.example.net/report","text/html",200
          ),
        )
        self.assertEqual(out["reason"],"FRESH_SOURCE_REDIRECT_OUTSIDE_PROVENANCE_HOST",out)

    def test_bibliographic_only_provenance_is_not_enough(self):
        called=[]
        out=self.m.extract(
          "Assess post quantum cryptography standards",
          {"url":"https://example.org/report"},
          {"status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED"},
          fetch=lambda *a:called.append(a),
        )
        self.assertEqual(out["reason"],"LIVE_RETRIEVAL_PROVENANCE_REQUIRED",out)
        self.assertEqual(called,[])

    def test_unsupported_binary_type_fails_closed(self):
        out=self.m.extract(
          "Assess post quantum cryptography standards",
          {"url":"https://example.org/report"},
          self.prov(),
          fetch=lambda url,timeout:(b"%PDF-not-parsed","https://example.org/report","application/pdf",200),
        )
        self.assertEqual(out["reason"],"UNSUPPORTED_CONTENT_TYPE",out)

    def test_run_writes_fail_closed_result(self):
        inp=ROOT/"canonical/astra_runtime/tmp/provenance_relevant_extract_input.json"
        outp=ROOT/"canonical/astra_runtime/tmp/provenance_relevant_extract_output.json"
        inp.parent.mkdir(parents=True,exist_ok=True)
        inp.write_text(json.dumps({
          "objective":"Assess post quantum cryptography standards",
          "candidate":{"url":"https://example.org/report"},
          "provenance":{"status":"UNVERIFIED"},
        }),encoding="utf-8")
        out=self.m.run({
          "input_path":str(inp.relative_to(ROOT)),
          "output_path":str(outp.relative_to(ROOT)),
          "timeout":5,
        },ROOT)
        self.assertFalse(out["output_verified"],out)
        self.assertTrue(outp.is_file())
        self.assertEqual(json.loads(outp.read_text())["reason"],"LIVE_RETRIEVAL_PROVENANCE_REQUIRED")

if __name__=="__main__":
    unittest.main(verbosity=2)
