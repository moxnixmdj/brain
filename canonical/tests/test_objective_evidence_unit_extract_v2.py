#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py"

def load():
    spec=importlib.util.spec_from_file_location("evidence_extract_v2",P)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def prov(self):
        return {
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "final_url":"https://example.org/report",
            "final_host":"example.org",
        }

    def rel(self):
        return {
            "status":"FIRST_PARTY_RELEVANT_SOURCE_VERIFIED",
            "objective_relevance_status":"VERIFIED",
            "verification_method":"EXACT_ROR_DOMAIN_PLUS_FRESH_PAGE_OBJECTIVE_TERM_COVERAGE",
            "fresh_url":"https://example.org/report",
            "bound_domain":"example.org",
        }

    def test_extracts_without_authority_identity_gate(self):
        def fetch(url,timeout):
            return (
                b"<html><body><nav>navigation noise</nav>"
                b"<h1>Post quantum cryptography standards</h1>"
                b"<p>NIST post quantum cryptography standards support migration to quantum resistant encryption.</p>"
                b"<p>General administration and contact information.</p></body></html>",
                "https://example.org/report","text/html",200,
            )
        out=self.m.extract(
            "Assess post quantum cryptography standards for quantum resistant migration",
            {"url":"https://example.org/report"},
            self.prov(),
            self.rel(),
            fetch=fetch,
        )
        self.assertEqual(out["status"],"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",out)
        self.assertEqual(out["evidence_extraction_status"],"VERIFIED",out)
        self.assertGreaterEqual(out["evidence_unit_count"],1,out)
        self.assertEqual(out["claim_relation_status"],"UNVERIFIED",out)
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED",out)
        self.assertEqual(out["evidence_sufficiency_status"],"UNVERIFIED",out)
        self.assertNotIn("authority_identity_status",out)
        for unit in out["evidence_units"]:
            self.assertEqual(len(unit["text_sha256"]),64)
            self.assertGreaterEqual(len(unit["matched_objective_tokens"]),2)
            self.assertLess(unit["visible_text_start"],unit["visible_text_end"])

    def test_unverified_relevance_rejected_before_fetch(self):
        called=[]
        out=self.m.extract(
            "Assess post quantum cryptography",
            {"url":"https://example.org/report"},
            self.prov(),
            {"status":"UNVERIFIED","objective_relevance_status":"UNVERIFIED"},
            fetch=lambda *a: called.append(True),
        )
        self.assertEqual(out["reason"],"QUALIFIED_OBJECTIVE_RELEVANCE_RECEIPT_REQUIRED",out)
        self.assertEqual(called,[])

    def test_relevance_and_provenance_must_name_same_source(self):
        relevance=self.rel()
        relevance["fresh_url"]="https://example.org/other"
        out=self.m.extract(
            "Assess post quantum cryptography",
            {"url":"https://example.org/report"},
            self.prov(),
            relevance,
            fetch=lambda *a: (_ for _ in ()).throw(AssertionError("must not fetch")),
        )
        self.assertEqual(out["reason"],"RELEVANCE_PROVENANCE_SOURCE_MISMATCH",out)

    def test_fresh_redirect_outside_provenance_host_fails_closed(self):
        out=self.m.extract(
            "Assess post quantum cryptography",
            {"url":"https://example.org/report"},
            self.prov(),
            self.rel(),
            fetch=lambda url,timeout:(
                b"<p>post quantum cryptography standards migration</p>",
                "https://evil.example.net/x","text/html",200,
            ),
        )
        self.assertEqual(out["reason"],"FRESH_EVIDENCE_REDIRECT_OUTSIDE_PROVENANCE_HOST",out)

    def test_fresh_page_relevance_drift_fails_closed(self):
        out=self.m.extract(
            "Assess volcanic sulfur isotope fractionation mantle magma",
            {"url":"https://example.org/report"},
            self.prov(),
            {
                **self.rel(),
                "matched_body_tokens":["volcanic","sulfur","isotope","fractionation"],
            },
            fetch=lambda url,timeout:(
                b"<html><body><p>Campus housing admissions schedule and cafeteria menu.</p></body></html>",
                "https://example.org/report","text/html",200,
            ),
        )
        self.assertEqual(out["status"],"UNVERIFIED",out)
        self.assertEqual(out["reason"],"FRESH_PAGE_OBJECTIVE_RELEVANCE_DRIFT",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
