#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/source_primary_relevance_verify.py"

def load():
    s=importlib.util.spec_from_file_location("primary_relevance",P)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

class SourcePrimaryRelevanceVerifyTests(unittest.TestCase):
    def setUp(self):
        self.m=load()
        self.old_fetch=self.m._fetch
        self.provenance={
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "final_url":"https://research.example.org/report",
            "final_host":"research.example.org",
        }
        self.authority={
            "status":"AUTHORITY_IDENTITY_VERIFIED",
            "matched_domain":"research.example.org",
            "organization_name":"Example Research Organization",
        }

    def tearDown(self):
        self.m._fetch=self.old_fetch

    def test_exact_host_and_objective_anchors_verify_narrowly(self):
        html=b"""<html><head><title>Lithium ion battery calendar aging and temperature</title>
        <meta name="description" content="Experimental study of temperature effects on lithium ion battery calendar aging"></head>
        <body><h1>Battery calendar aging under temperature variation</h1></body></html>"""
        self.m._fetch=lambda url,timeout:(html,"text/html",200,url)
        x=self.m.verify(
            "Assess whether lithium ion battery calendar aging is influenced by temperature using published experimental evidence",
            {"url":"https://research.example.org/report"},
            self.provenance,
            self.authority,
            timeout=5,
        )
        self.assertEqual(x["status"],"PRIMARY_SOURCE_AND_OBJECTIVE_RELEVANCE_VERIFIED",x)
        self.assertEqual(x["primary_source_status"],"VERIFIED",x)
        self.assertEqual(x["relevance_status"],"VERIFIED",x)
        self.assertEqual(x["factual_correctness_status"],"UNVERIFIED",x)
        self.assertEqual(x["evidence_sufficiency_status"],"UNVERIFIED",x)
        self.assertEqual(x["model_dependency_count"],0,x)

    def test_host_mismatch_fails_before_fetch(self):
        called=[]
        self.m._fetch=lambda url,timeout:called.append(url)
        bad=dict(self.provenance)
        bad["final_url"]="https://other.example.net/report"
        bad["final_host"]="other.example.net"
        x=self.m.verify(
            "Assess whether lithium ion battery aging is influenced by temperature",
            {"url":"https://other.example.net/report"},
            bad,
            self.authority,
            timeout=5,
        )
        self.assertEqual(x["status"],"UNVERIFIED",x)
        self.assertEqual(x["reason"],"FINAL_HOST_DOES_NOT_EQUAL_VERIFIED_ROR_DOMAIN",x)
        self.assertEqual(called,[])

    def test_primary_publication_can_verify_while_relevance_stays_unresolved(self):
        html=b"<html><head><title>Annual governance report</title></head><body><h1>Governance</h1></body></html>"
        self.m._fetch=lambda url,timeout:(html,"text/html",200,url)
        x=self.m.verify(
            "Assess whether lithium ion battery calendar aging is influenced by temperature",
            {"url":"https://research.example.org/report"},
            self.provenance,
            self.authority,
            timeout=5,
        )
        self.assertEqual(x["status"],"PRIMARY_SOURCE_VERIFIED_RELEVANCE_UNRESOLVED",x)
        self.assertEqual(x["primary_source_status"],"VERIFIED",x)
        self.assertEqual(x["relevance_status"],"UNVERIFIED",x)
        self.assertNotIn("output_verified",x)

    def test_cross_host_redirect_fails_closed(self):
        html=b"<html><head><title>Lithium ion battery calendar aging temperature</title></head></html>"
        self.m._fetch=lambda url,timeout:(html,"text/html",200,"https://mirror.example.net/report")
        x=self.m.verify(
            "Assess whether lithium ion battery calendar aging is influenced by temperature",
            {"url":"https://research.example.org/report"},
            self.provenance,
            self.authority,
            timeout=5,
        )
        self.assertEqual(x["status"],"UNVERIFIED",x)
        self.assertEqual(x["reason"],"LIVE_RETRIEVAL_LEFT_VERIFIED_ROR_DOMAIN",x)

if __name__=="__main__":
    unittest.main(verbosity=2)
