#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py"

def load():
    s=importlib.util.spec_from_file_location("evidence_extract",P)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()

    def prov(self):
        return {
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "final_url":"https://example.org/report",
          "final_host":"example.org",
        }
    def auth(self):
        return {"status":"AUTHORITY_IDENTITY_VERIFIED","matched_domain":"example.org"}
    def rel(self):
        return {
          "status":"FIRST_PARTY_RELEVANT_SOURCE_VERIFIED",
          "objective_relevance_status":"VERIFIED",
          "verification_method":"EXACT_ROR_DOMAIN_PLUS_FRESH_PAGE_OBJECTIVE_TERM_COVERAGE",
          "bound_domain":"example.org",
          "fresh_url":"https://example.org/report",
          "matched_token_coverage":0.8,
        }

    def test_extracts_hashed_objective_grounded_units_without_relation_claim(self):
        def fetch(url,timeout):
            return (
              b"<html><body><nav>unrelated navigation</nav>"
              b"<h1>Post quantum cryptography standards</h1>"
              b"<p>NIST post quantum cryptography standards support migration to quantum resistant encryption.</p>"
              b"<p>Contact information and general administration.</p></body></html>",
              "https://example.org/report","text/html",200
            )
        x=self.m.extract(
          "Assess post quantum cryptography standards for quantum resistant migration",
          {"url":"https://example.org/report"},self.prov(),self.auth(),self.rel(),fetch=fetch
        )
        self.assertEqual(x["status"],"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",x)
        self.assertEqual(x["evidence_extraction_status"],"VERIFIED",x)
        self.assertGreaterEqual(x["evidence_unit_count"],1,x)
        self.assertEqual(x["claim_relation_status"],"UNVERIFIED",x)
        self.assertEqual(x["factual_correctness_status"],"UNVERIFIED",x)
        self.assertEqual(x["evidence_sufficiency_status"],"UNVERIFIED",x)
        for unit in x["evidence_units"]:
            self.assertEqual(len(unit["text_sha256"]),64)
            self.assertGreaterEqual(len(unit["matched_objective_tokens"]),2)
            self.assertLess(unit["visible_text_start"],unit["visible_text_end"])

    def test_irrelevant_blocks_fail_closed(self):
        def fetch(url,timeout):
            return (
              b"<html><body><p>Campus housing admissions schedule and cafeteria menu.</p></body></html>",
              "https://example.org/report","text/html",200
            )
        x=self.m.extract(
          "Assess volcanic sulfur isotope fractionation in mantle magma",
          {"url":"https://example.org/report"},self.prov(),self.auth(),self.rel(),fetch=fetch
        )
        self.assertEqual(x["status"],"UNVERIFIED",x)
        self.assertEqual(x["reason"],"FRESH_PAGE_OBJECTIVE_RELEVANCE_DRIFT",x)

    def test_forged_or_unqualified_relevance_shape_is_rejected_before_fetch(self):
        x=self.m.extract(
          "Assess post quantum cryptography",
          {"url":"https://example.org/report"},self.prov(),self.auth(),
          {
            "status":"FIRST_PARTY_RELEVANT_SOURCE_VERIFIED",
            "objective_relevance_status":"VERIFIED",
            "fresh_url":"https://example.org/report",
          },
          fetch=lambda *a: (_ for _ in ()).throw(AssertionError("must not fetch")),
        )
        self.assertEqual(x["reason"],"QUALIFIED_OBJECTIVE_RELEVANCE_RECEIPT_REQUIRED",x)

    def test_relevance_bound_domain_must_match_authority(self):
        rel=self.rel(); rel["bound_domain"]="other.example.net"
        x=self.m.extract(
          "Assess post quantum cryptography",
          {"url":"https://example.org/report"},self.prov(),self.auth(),rel,
          fetch=lambda *a: (_ for _ in ()).throw(AssertionError("must not fetch")),
        )
        self.assertEqual(x["reason"],"RELEVANCE_RECEIPT_BOUND_DOMAIN_MISMATCH",x)

    def test_fresh_page_drift_fails_before_unit_promotion(self):
        def fetch(url,timeout):
            return (
              b"<html><body><p>Post quantum overview and unrelated administration material.</p></body></html>",
              "https://example.org/report","text/html",200
            )
        x=self.m.extract(
          "Assess post quantum cryptography standards migration resilience",
          {"url":"https://example.org/report"},self.prov(),self.auth(),self.rel(),fetch=fetch
        )
        self.assertEqual(x["reason"],"FRESH_PAGE_OBJECTIVE_RELEVANCE_DRIFT",x)
        self.assertLess(x["fresh_page_objective_token_coverage"],0.5,x)

    def test_unverified_relevance_is_rejected_before_fetch(self):
        x=self.m.extract(
          "Assess post quantum cryptography",
          {"url":"https://example.org/report"},self.prov(),self.auth(),
          {"status":"UNVERIFIED","objective_relevance_status":"UNVERIFIED"},
          fetch=lambda *a: (_ for _ in ()).throw(AssertionError("must not fetch")),
        )
        self.assertEqual(x["reason"],"QUALIFIED_OBJECTIVE_RELEVANCE_RECEIPT_REQUIRED",x)

    def test_redirect_outside_bound_domain_fails_closed(self):
        x=self.m.extract(
          "Assess post quantum cryptography",
          {"url":"https://example.org/report"},self.prov(),self.auth(),self.rel(),
          fetch=lambda url,timeout: (
            b"<p>post quantum cryptography standards migration</p>",
            "https://evil.example.net/x","text/html",200
          )
        )
        self.assertEqual(x["reason"],"FRESH_EVIDENCE_REDIRECT_OUTSIDE_BOUND_DOMAIN",x)

    def test_run_writes_fail_closed_result(self):
        inp=ROOT/"canonical/astra_runtime/tmp/evidence_extract_input.json"
        outp=ROOT/"canonical/astra_runtime/tmp/evidence_extract_output.json"
        inp.parent.mkdir(parents=True,exist_ok=True)
        inp.write_text(json.dumps({
          "objective":"Assess post quantum cryptography",
          "candidate":{"url":"https://example.org/report"},
          "provenance":{"status":"UNVERIFIED"},
          "authority_identity":self.auth(),
          "relevance":self.rel(),
        }),encoding="utf-8")
        x=self.m.run({
          "input_path":str(inp.relative_to(ROOT)),
          "output_path":str(outp.relative_to(ROOT)),
          "timeout":5,
        },ROOT)
        self.assertFalse(x["output_verified"],x)
        self.assertTrue(outp.is_file())
        self.assertEqual(json.loads(outp.read_text())["reason"],"LIVE_RETRIEVAL_PROVENANCE_REQUIRED")

if __name__=="__main__": unittest.main(verbosity=2)
