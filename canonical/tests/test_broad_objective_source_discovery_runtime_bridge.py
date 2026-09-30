#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import inspect
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical/runtime/astra_runtime.py"


def load_runtime():
    spec=importlib.util.spec_from_file_location("astra_runtime_bridge_test",RUNTIME)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeDiscovery:
    @staticmethod
    def discover(goal,limit=12,timeout=20):
        return {
          "schema":"PROJECT_BRAIN_OPEN_WEB_SOURCE_CANDIDATE_DISCOVERY_V1",
          "status":"CANDIDATES_DISCOVERED",
          "objective":goal,
          "candidate_count":2,
          "candidates":[
            {"url":"https://example.org/a","authority_status":"UNVERIFIED"},
            {"url":"https://example.edu/b","authority_status":"UNVERIFIED"},
          ],
          "authority_verification":"NOT_PERFORMED",
          "primary_source_verification":"NOT_PERFORMED",
          "model_dependency_count":0,
          "incremental_spend_usd":0,
        }


class FailingDiscovery:
    @staticmethod
    def discover(goal,limit=12,timeout=20):
        raise RuntimeError("offline")


class BroadObjectiveSourceBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=load_runtime()

    @staticmethod
    def grounding():
        return {
          "grounded_clause_count":0,
          "broad_objective_decomposition_available":True,
          "broad_objective_decomposition":{
            "status":"DECOMPOSED",
            "roles":[
              {"role":"SOURCE_DISCOVERY"},
              {"role":"EVIDENCE_ACQUISITION"},
              {"role":"EVIDENCE_EXTRACTION"},
              {"role":"RELATION_EVALUATION"},
              {"role":"DECISION_SYNTHESIS_AND_VERIFICATION"},
            ],
            "model_dependency_count":0,
          },
        }

    def test_bridge_persists_unverified_candidates_without_package_acquisition(self):
        with tempfile.TemporaryDirectory() as td:
            old=self.r.EVID_DIR
            self.r.EVID_DIR=pathlib.Path(td)
            try:
                path,evidence=self.r._run_broad_objective_source_discovery(
                    {"mission_id":"BRIDGE-CANARY"},
                    "Assess whether two measured conditions differ",
                    self.grounding(),
                    discovery_module=FakeDiscovery,
                )
            finally:
                self.r.EVID_DIR=old
        self.assertEqual(evidence["source_candidate_discovery"]["status"],"CANDIDATES_DISCOVERED")
        self.assertEqual(evidence["source_candidate_discovery"]["candidate_count"],2)
        self.assertTrue(evidence["authority_verification_required"])
        self.assertTrue(evidence["primary_source_verification_required"])
        self.assertFalse(evidence["package_capability_acquisition_attempted"])
        self.assertEqual(evidence["model_dependency_count"],0)
        self.assertEqual(evidence["incremental_spend_usd"],0)
        self.assertEqual(path.name,"BRIDGE-CANARY__BROAD_OBJECTIVE_SOURCE_CANDIDATES.json")

    def test_bridge_fail_closed_records_discovery_error(self):
        with tempfile.TemporaryDirectory() as td:
            old=self.r.EVID_DIR
            self.r.EVID_DIR=pathlib.Path(td)
            try:
                _,evidence=self.r._run_broad_objective_source_discovery(
                    {"mission_id":"BRIDGE-ERROR"},
                    "Investigate a technical claim",
                    self.grounding(),
                    discovery_module=FailingDiscovery,
                )
            finally:
                self.r.EVID_DIR=old
        discovery=evidence["source_candidate_discovery"]
        self.assertEqual(discovery["status"],"DISCOVERY_ERROR")
        self.assertEqual(discovery["candidate_count"],0)
        self.assertEqual(discovery["model_dependency_count"],0)

    def test_non_broad_goal_does_not_route(self):
        path,evidence=self.r._run_broad_objective_source_discovery(
            {"mission_id":"NO-BROAD"},"copy a file",
            {"broad_objective_decomposition_available":False},
            discovery_module=FakeDiscovery,
        )
        self.assertIsNone(path)
        self.assertIsNone(evidence)

    def test_runtime_orders_source_bridge_before_package_acquisition(self):
        src=inspect.getsource(self.r._run_goal_unstamped)
        bridge=src.index("_run_broad_objective_source_discovery(")
        package=src.index("_load_auto_capability_acquisition()")
        self.assertLess(bridge,package)
        self.assertIn("BROAD_OBJECTIVE_SOURCE_AUTHORITY_VERIFICATION_REQUIRED",src)
        self.assertIn('"package_capability_acquisition_attempted":False',src)


if __name__=="__main__":
    unittest.main(verbosity=2)
