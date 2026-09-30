#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, types, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/source_authority_binding_composite.py"

def load():
    s=importlib.util.spec_from_file_location("authority_composite",P)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class CompositeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()

    def test_provenance_required(self):
        out=self.m.bind_verified_candidate({"url":"https://example.org/"},{"status":"UNVERIFIED"})
        self.assertEqual(out["status"],"AUTHORITY_UNRESOLVED")
        self.assertEqual(out["reason"],"QUALIFIED_PROVENANCE_REQUIRED")

    def test_ror_positive_preserves_narrow_claim(self):
        ror=types.SimpleNamespace(bind_candidate=lambda c,timeout=20:{
          "status":"AUTHORITY_IDENTITY_VERIFIED","authority_status":"VERIFIED",
          "ror_id":"https://ror.org/x","organization_name":"Example"
        })
        wik=types.SimpleNamespace(bind_candidate=lambda c,timeout=20:{
          "status":"AUTHORITY_UNRESOLVED","authority_status":"UNVERIFIED"
        })
        out=self.m.bind_verified_candidate(
          {"url":"https://example.org/"},
          {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":"https://example.org/","final_host":"example.org"},
          ror_module=ror,wikidata_module=wik,
        )
        self.assertEqual(out["status"],"AUTHORITY_IDENTITY_VERIFIED",out)
        self.assertEqual(out["verification_methods"],["ROR_V2_EXACT_ACTIVE_DOMAIN"])
        self.assertEqual(out["primary_source_status"],"UNVERIFIED")
        self.assertEqual(out["relevance_status"],"UNVERIFIED")
        self.assertEqual(out["evidence_sufficiency_status"],"UNVERIFIED")

    def test_wikidata_fallback_positive(self):
        ror=types.SimpleNamespace(bind_candidate=lambda c,timeout=20:{
          "status":"AUTHORITY_UNRESOLVED","authority_status":"UNVERIFIED"
        })
        wik=types.SimpleNamespace(bind_candidate=lambda c,timeout=20:{
          "status":"AUTHORITY_IDENTITY_VERIFIED","authority_status":"VERIFIED",
          "entity_id":"Q1","official_host":"example.org"
        })
        out=self.m.bind_verified_candidate(
          {"url":"https://docs.example.org/","title":"Example"},
          {"status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED"},
          ror_module=ror,wikidata_module=wik,
        )
        self.assertEqual(out["status"],"AUTHORITY_IDENTITY_VERIFIED",out)
        self.assertEqual(out["verification_methods"],["WIKIDATA_P856_OFFICIAL_WEBSITE"])

    def test_no_route_fails_closed(self):
        no=types.SimpleNamespace(bind_candidate=lambda c,timeout=20:{
          "status":"AUTHORITY_UNRESOLVED","authority_status":"UNVERIFIED"
        })
        out=self.m.bind_verified_candidate(
          {"url":"https://example.org/"},
          {"status":"RETRIEVAL_PROVENANCE_VERIFIED"},
          ror_module=no,wikidata_module=no,
        )
        self.assertEqual(out["status"],"AUTHORITY_UNRESOLVED")
        self.assertEqual(out["authority_status"],"UNVERIFIED")

if __name__=="__main__":
    unittest.main(verbosity=2)
