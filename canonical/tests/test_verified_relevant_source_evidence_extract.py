#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical/runtime/bound_capabilities/verified_relevant_source_evidence_extract.py"
spec=importlib.util.spec_from_file_location("evidence_extract_under_test",PATH)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def receipt(objective="measure earthquake magnitude energy threshold"):
    return {
      "status":"FIRST_PARTY_RELEVANT_SOURCE_VERIFIED",
      "first_party_source_status":"VERIFIED",
      "objective_relevance_status":"VERIFIED",
      "verification_method":"EXACT_ROR_DOMAIN_PLUS_FRESH_PAGE_OBJECTIVE_TERM_COVERAGE",
      "bound_domain":"example.org",
      "fresh_url":"https://example.org/report",
      "objective_tokens":mod._tokens(objective),
    }

def good_fetch(url,timeout):
    html=b"""<html><head><title>Earthquake energy report</title></head><body>
    <p>The measured earthquake magnitude was 6.2 during the observation window.</p>
    <p>Independent energy analysis estimated 1.8e14 joules for the event.</p>
    <p>The operational threshold used for comparison was 1e14 joules.</p>
    </body></html>"""
    return html,"https://example.org/report","text/html",200

class EvidenceExtractionTests(unittest.TestCase):
    def test_positive_verbatim_extraction(self):
        objective="measure earthquake magnitude energy threshold"
        out=mod.extract(objective,receipt(objective),fetch=good_fetch)
        self.assertEqual(out["status"],"VERBATIM_EVIDENCE_PASSAGES_EXTRACTED")
        self.assertTrue(out["output_verified"])
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED")
        self.assertEqual(out["evidence_sufficiency_status"],"UNVERIFIED")
        self.assertTrue(out["passages"])
        visible=" ".join(mod._visible(good_fetch(None,None)[0],"text/html")[0])
        for row in out["passages"]:
            self.assertIn(row["text"],visible)

    def test_wrong_upstream_status_fails_closed(self):
        r=receipt(); r["status"]="UNVERIFIED"
        out=mod.extract("measure earthquake magnitude energy threshold",r,fetch=good_fetch)
        self.assertEqual(out["reason"],"VERIFIED_RELEVANT_SOURCE_RECEIPT_REQUIRED")
        self.assertFalse(out.get("output_verified",False))

    def test_objective_binding_mismatch_fails_closed(self):
        out=mod.extract("completely different objective",receipt(),fetch=good_fetch)
        self.assertEqual(out["reason"],"OBJECTIVE_TOKEN_BINDING_MISMATCH")

    def test_redirect_domain_drift_fails_closed(self):
        def fetch(url,timeout):
            return b"<p>earthquake magnitude energy threshold</p>","https://evil.example.net/x","text/html",200
        out=mod.extract("measure earthquake magnitude energy threshold",receipt(),fetch=fetch)
        self.assertEqual(out["reason"],"FRESH_SOURCE_REDIRECT_OUTSIDE_BOUND_DOMAIN")

    def test_irrelevant_text_fails_closed(self):
        def fetch(url,timeout):
            return b"<p>gardening soil tomatoes irrigation greenhouse plants</p>","https://example.org/report","text/html",200
        out=mod.extract("measure earthquake magnitude energy threshold",receipt(),fetch=fetch)
        self.assertEqual(out["status"],"EXTRACTION_UNRESOLVED")
        self.assertEqual(out["reason"],"NO_PASSAGE_WITH_BOUNDED_OBJECTIVE_SUPPORT")

    def test_short_objective_can_extract_one_supported_term(self):
        objective="earthquake magnitude"
        r=receipt(objective)
        out=mod.extract(objective,r,fetch=good_fetch)
        self.assertEqual(out["status"],"VERBATIM_EVIDENCE_PASSAGES_EXTRACTED")

    def test_private_domain_receipt_rejected(self):
        r=receipt(); r["bound_domain"]="localhost"; r["fresh_url"]="http://localhost/report"
        out=mod.extract("measure earthquake magnitude energy threshold",r,fetch=good_fetch)
        self.assertEqual(out["reason"],"UPSTREAM_URL_DOMAIN_BINDING_INVALID")

if __name__=="__main__":
    unittest.main(verbosity=2)
