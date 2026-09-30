#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py"

def load():
    spec=importlib.util.spec_from_file_location("objective_evidence_unit_extract_v2",P)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def provenance(url="https://example.org/report"):
    return {
        "status":"RETRIEVAL_PROVENANCE_VERIFIED",
        "final_url":url,
        "final_host":"example.org",
    }

def relevance(url="https://example.org/report"):
    return {
        "status":"FIRST_PARTY_RELEVANT_SOURCE_VERIFIED",
        "objective_relevance_status":"VERIFIED",
        "fresh_url":url,
        "primary_source_status":"UNVERIFIED",
        "factual_correctness_status":"UNVERIFIED",
        "evidence_sufficiency_status":"UNVERIFIED",
    }

class ObjectiveEvidenceUnitExtractV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_extracts_without_authority_prerequisite(self):
        raw=(
            b"<html><body><nav>navigation noise</nav>"
            b"<h1>Post quantum cryptography standards</h1>"
            b"<p>NIST post quantum cryptography standards support migration "
            b"to quantum resistant encryption systems.</p>"
            b"<p>Administrative contacts and office hours.</p></body></html>"
        )
        x=self.m.extract(
            "Assess post quantum cryptography standards for quantum resistant migration",
            {"url":"https://example.org/report"},
            provenance(),
            relevance(),
            fetch=lambda url,timeout:(raw,"https://example.org/report","text/html",200),
        )
        self.assertEqual(x["status"],"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",x)
        self.assertEqual(x["evidence_extraction_status"],"VERIFIED",x)
        self.assertGreaterEqual(x["evidence_unit_count"],1,x)
        self.assertEqual(x["claim_relation_status"],"UNVERIFIED",x)
        self.assertEqual(x["semantic_entailment_status"],"UNVERIFIED",x)
        self.assertEqual(x["factual_correctness_status"],"UNVERIFIED",x)
        self.assertEqual(x["evidence_sufficiency_status"],"UNVERIFIED",x)
        self.assertEqual(x["source_independence_status"],"UNVERIFIED",x)
        self.assertEqual(x["model_dependency_count"],0,x)
        self.assertEqual(x["incremental_spend_usd"],0,x)
        self.assertNotIn("authority_identity",x)
        for unit in x["evidence_units"]:
            self.assertEqual(unit["source_url"],"https://example.org/report")
            self.assertEqual(unit["page_raw_sha256"],x["page_raw_sha256"])
            self.assertEqual(unit["visible_text_sha256"],x["visible_text_sha256"])
            self.assertEqual(len(unit["text_sha256"]),64)
            self.assertEqual(len(unit["evidence_unit_id"]),64)
            self.assertGreaterEqual(len(unit["matched_objective_tokens"]),2)
            self.assertLess(unit["visible_text_start"],unit["visible_text_end"])

    def test_modern_div_main_content_is_visible_evidence(self):
        raw=(
            b"<html><body><header>site navigation</header><main>"
            b"<div><section>SymPy is a Python library for symbolic mathematics "
            b"and computer algebra.</section></div></main><footer>links</footer></body></html>"
        )
        x=self.m.extract(
            "SymPy Python symbolic mathematics library",
            {"url":"https://example.org/report"},
            provenance(),
            relevance(),
            fetch=lambda url,timeout:(raw,"https://example.org/report","text/html",200),
        )
        self.assertEqual(x["status"],"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",x)
        self.assertGreaterEqual(x["evidence_unit_count"],1,x)
        self.assertTrue(any("symbolic mathematics" in u["text"] for u in x["evidence_units"]),x)

    def test_nested_modern_containers_do_not_duplicate_visible_text(self):
        raw=(
            b"<html><body><main><div><section>"
            b"SymPy is a Python library for symbolic mathematics and computer algebra."
            b"</section></div></main></body></html>"
        )
        x=self.m.extract(
            "SymPy Python symbolic mathematics library",
            {"url":"https://example.org/report"},
            provenance(),
            relevance(),
            fetch=lambda url,timeout:(raw,"https://example.org/report","text/html",200),
        )
        self.assertEqual(x["status"],"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",x)
        matching=[u for u in x["evidence_units"] if "symbolic mathematics" in u["text"]]
        self.assertEqual(len(matching),1,x)
        self.assertEqual(x["visible_block_count"],1,x)
        self.assertNotIn(
            "SymPy is a Python library for symbolic mathematics and computer algebra.\n"
            "SymPy is a Python library for symbolic mathematics and computer algebra.",
            "\n".join(u["text"] for u in x["evidence_units"]),
        )

    def test_custom_container_and_inline_descendants_are_captured(self):
        raw=(
            b"<html><body><research-card><span>SQLite WAL checkpoint behavior "
            b"copies write ahead logging frames back to the database.</span>"
            b"</research-card></body></html>"
        )
        x=self.m.extract(
            "Assess SQLite WAL write ahead logging checkpoint behavior",
            {"url":"https://example.org/report"},
            provenance(),
            relevance(),
            fetch=lambda url,timeout:(raw,"https://example.org/report","text/html",200),
        )
        self.assertEqual(x["status"],"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",x)
        self.assertTrue(any("checkpoint behavior" in u["text"] for u in x["evidence_units"]),x)

    def test_inline_only_body_content_is_captured_once(self):
        raw=(
            b"<html><body><span>Python hashlib sha256 secure hash digest algorithms "
            b"are available through the standard library.</span></body></html>"
        )
        x=self.m.extract(
            "Assess Python hashlib sha256 secure hash digest algorithms",
            {"url":"https://example.org/report"},
            provenance(),
            relevance(),
            fetch=lambda url,timeout:(raw,"https://example.org/report","text/html",200),
        )
        self.assertEqual(x["status"],"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",x)
        self.assertEqual(x["visible_block_count"],1,x)
        self.assertEqual(len(x["evidence_units"]),1,x)

    def test_relevance_is_mandatory_and_checked_before_fetch(self):
        calls={"fetch":0}
        def fetch(*args):
            calls["fetch"]+=1
            raise AssertionError("must not fetch")
        x=self.m.extract(
            "Assess post quantum cryptography",
            {"url":"https://example.org/report"},
            provenance(),
            {"status":"UNVERIFIED","objective_relevance_status":"UNVERIFIED"},
            fetch=fetch,
        )
        self.assertEqual(x["status"],"UNVERIFIED",x)
        self.assertEqual(x["reason"],"VERIFIED_OBJECTIVE_RELEVANCE_REQUIRED",x)
        self.assertEqual(calls["fetch"],0)

    def test_provenance_is_mandatory_and_checked_before_fetch(self):
        x=self.m.extract(
            "Assess post quantum cryptography",
            {"url":"https://example.org/report"},
            {"status":"UNVERIFIED"},
            relevance(),
            fetch=lambda *args: (_ for _ in ()).throw(AssertionError("must not fetch")),
        )
        self.assertEqual(x["reason"],"LIVE_RETRIEVAL_PROVENANCE_REQUIRED",x)

    def test_provenance_and_relevance_must_name_same_admitted_source(self):
        x=self.m.extract(
            "Assess post quantum cryptography",
            {"url":"https://example.org/report"},
            provenance("https://example.org/report"),
            relevance("https://example.org/other"),
            fetch=lambda *args: (_ for _ in ()).throw(AssertionError("must not fetch")),
        )
        self.assertEqual(x["reason"],"ADMITTED_SOURCE_IDENTITY_MISMATCH",x)

    def test_fresh_refetch_must_resolve_to_same_admitted_source(self):
        x=self.m.extract(
            "Assess post quantum cryptography standards",
            {"url":"https://example.org/report"},
            provenance(),
            relevance(),
            fetch=lambda url,timeout:(
                b"<p>post quantum cryptography standards migration</p>",
                "https://example.org/different",
                "text/html",
                200,
            ),
        )
        self.assertEqual(x["reason"],"FRESH_EVIDENCE_SOURCE_IDENTITY_MISMATCH",x)

    def test_irrelevant_visible_blocks_fail_closed_even_after_page_relevance_admission(self):
        x=self.m.extract(
            "Assess volcanic sulfur isotope fractionation in mantle magma",
            {"url":"https://example.org/report"},
            provenance(),
            relevance(),
            fetch=lambda url,timeout:(
                b"<html><body><p>Campus housing admissions schedule and cafeteria menu.</p></body></html>",
                "https://example.org/report","text/html",200
            ),
        )
        self.assertEqual(x["status"],"UNVERIFIED",x)
        self.assertEqual(x["reason"],"NO_OBJECTIVE_GROUNDED_EVIDENCE_UNITS",x)

    def test_suppressed_navigation_cannot_become_evidence(self):
        x=self.m.extract(
            "Assess volcanic sulfur isotope fractionation magma",
            {"url":"https://example.org/report"},
            provenance(),
            relevance(),
            fetch=lambda url,timeout:(
                b"<html><body><nav>volcanic sulfur isotope fractionation magma</nav>"
                b"<p>General campus administration and schedules.</p></body></html>",
                "https://example.org/report","text/html",200
            ),
        )
        self.assertEqual(x["reason"],"NO_OBJECTIVE_GROUNDED_EVIDENCE_UNITS",x)

    def test_run_writes_fail_closed_result_without_claim_inflation(self):
        inp=ROOT/"canonical/astra_runtime/tmp/evidence_extract_v2_input.json"
        outp=ROOT/"canonical/astra_runtime/tmp/evidence_extract_v2_output.json"
        inp.parent.mkdir(parents=True,exist_ok=True)
        inp.write_text(json.dumps({
            "objective":"Assess post quantum cryptography",
            "candidate":{"url":"https://example.org/report"},
            "provenance":{"status":"UNVERIFIED"},
            "relevance":relevance(),
        }),encoding="utf-8")
        x=self.m.run({
            "input_path":str(inp.relative_to(ROOT)),
            "output_path":str(outp.relative_to(ROOT)),
            "timeout":5,
        },ROOT)
        self.assertFalse(x["output_verified"],x)
        saved=json.loads(outp.read_text(encoding="utf-8"))
        self.assertEqual(saved["reason"],"LIVE_RETRIEVAL_PROVENANCE_REQUIRED",saved)
        self.assertEqual(saved["claim_relation_status"],"UNVERIFIED",saved)

if __name__=="__main__":
    unittest.main(verbosity=2)
