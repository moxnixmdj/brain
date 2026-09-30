#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/broad_objective_source_role_binding.py"

def load():
    spec=importlib.util.spec_from_file_location("role_binding",P)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class FakeDiscovery:
    @staticmethod
    def discover(goal,limit=8,timeout=15):
        return {
            "status":"CANDIDATES_DISCOVERED",
            "candidates":[
                {"url":"https://example.org/a","authority_status":"UNVERIFIED"},
                {"url":"https://example.net/b","authority_status":"UNVERIFIED"},
            ],
        }

class FakeVerifier:
    @staticmethod
    def verify(candidate,timeout=15):
        if candidate["url"].endswith("/a"):
            return {
                "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                "authority_status":"RETRIEVABILITY_VERIFIED__FACT_AUTHORITY_UNVERIFIED",
                "primary_source_status":"UNVERIFIED",
            }
        return {"status":"UNVERIFIED","authority_status":"UNVERIFIED"}

class EmptyDiscovery:
    @staticmethod
    def discover(goal,limit=8,timeout=15):
        return {"status":"DISCOVERY_UNAVAILABLE","candidates":[]}

class BroadObjectiveRoleBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def decomposition(self):
        return {
            "status":"DECOMPOSED",
            "roles":[
                {"role":"SOURCE_DISCOVERY"},
                {"role":"EVIDENCE_ACQUISITION"},
                {"role":"EVIDENCE_EXTRACTION"},
                {"role":"RELATION_EVALUATION"},
                {"role":"DECISION_SYNTHESIS_AND_VERIFICATION"},
            ],
        }

    def test_executes_discovery_and_provenance_without_authority_upgrade(self):
        out=self.m.run(
            "Assess whether X is greater than Y",
            self.decomposition(),FakeDiscovery,FakeVerifier,
        )
        self.assertEqual(out["status"],"SOURCE_PROVENANCE_READY")
        self.assertEqual(out["provenance_verified_count"],1)
        self.assertEqual(out["authority_status"],"UNVERIFIED")
        self.assertEqual(out["primary_source_status"],"UNVERIFIED")
        self.assertEqual(out["relevance_status"],"UNVERIFIED")
        self.assertEqual(out["final_answer_status"],"NOT_ATTEMPTED")
        self.assertEqual(out["model_dependency_count"],0)
        self.assertEqual(out["incremental_spend_usd"],0)
        self.assertNotIn("SOURCE_DISCOVERY",out["remaining_roles"])

    def test_no_candidates_fails_closed(self):
        out=self.m.run(
            "Investigate X",self.decomposition(),EmptyDiscovery,FakeVerifier,
        )
        self.assertEqual(out["status"],"SOURCE_PROVENANCE_UNAVAILABLE")
        self.assertEqual(out["provenance_verified_count"],0)
        self.assertEqual(out["authority_status"],"UNVERIFIED")

    def test_requires_exact_source_role(self):
        with self.assertRaises(self.m.BroadObjectiveRoleBindingError):
            self.m.run("Assess X",{"status":"DECOMPOSED","roles":[]},FakeDiscovery,FakeVerifier)

if __name__=="__main__":
    unittest.main(verbosity=2)
