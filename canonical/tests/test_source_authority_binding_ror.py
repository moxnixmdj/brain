#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/source_authority_binding_ror.py"

def load():
    s=importlib.util.spec_from_file_location("source_authority_binding_ror",P)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

class RORAuthorityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()

    def test_host_normalization_is_exact_and_safe(self):
        self.assertEqual(self.m._candidate_host({"url":"https://www.harvard.edu/x"}),"harvard.edu")
        self.assertIsNone(self.m._candidate_host({"url":"http://localhost/x"}))

    def test_unique_active_exact_domain_is_verified_but_nonclaims_remain(self):
        old=self.m._fetch_ror
        try:
            self.m._fetch_ror=lambda domain,timeout=20: ({
                "number_of_results":1,
                "items":[{
                    "id":"https://ror.org/03vek6s52",
                    "status":"active",
                    "domains":[domain],
                    "types":["education"],
                    "names":[{"value":"Example University","types":["ror_display"]}]
                }]
            },"https://api.ror.org/v2/organizations",200)
            out=self.m.bind_candidate({"url":"https://research.example.edu/"},timeout=5)
            self.assertEqual(out["status"],"AUTHORITY_IDENTITY_VERIFIED",out)
            self.assertEqual(out["authority_status"],"VERIFIED")
            self.assertEqual(out["primary_source_status"],"UNVERIFIED")
            self.assertEqual(out["relevance_status"],"UNVERIFIED")
            self.assertEqual(out["evidence_sufficiency_status"],"UNVERIFIED")
        finally:
            self.m._fetch_ror=old

    def test_zero_exact_matches_fail_closed(self):
        old=self.m._fetch_ror
        try:
            self.m._fetch_ror=lambda domain,timeout=20: ({"number_of_results":0,"items":[]},"https://api.ror.org/v2/organizations",200)
            out=self.m.bind_candidate({"url":"https://unsupported.example.org/"},timeout=5)
            self.assertEqual(out["status"],"AUTHORITY_UNRESOLVED",out)
            self.assertEqual(out["authority_status"],"UNVERIFIED")
        finally:
            self.m._fetch_ror=old

    def test_multiple_exact_matches_fail_closed(self):
        old=self.m._fetch_ror
        try:
            self.m._fetch_ror=lambda domain,timeout=20: ({
                "number_of_results":2,
                "items":[
                    {"id":"https://ror.org/01","status":"active","domains":[domain],"names":[]},
                    {"id":"https://ror.org/02","status":"active","domains":[domain],"names":[]}
                ]
            },"https://api.ror.org/v2/organizations",200)
            out=self.m.bind_candidate({"url":"https://ambiguous.example.org/"},timeout=5)
            self.assertEqual(out["status"],"AUTHORITY_AMBIGUOUS",out)
            self.assertEqual(out["authority_status"],"UNVERIFIED")
        finally:
            self.m._fetch_ror=old

if __name__=="__main__": unittest.main(verbosity=2)
