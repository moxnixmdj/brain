#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import inspect
import json
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical/runtime/astra_runtime.py"


def load_runtime():
    spec=importlib.util.spec_from_file_location("project_brain_astra_runtime_source_frontier_test",PATH)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeDiscovery:
    def __init__(self,result):
        self.result=result
        self.calls=[]
    def discover(self,objective,limit=12,timeout=15):
        self.calls.append((objective,limit,timeout))
        return self.result


class _FakeVerifier:
    def __init__(self):
        self.calls=[]
    def verify(self,candidate,timeout=15):
        self.calls.append((candidate,timeout))
        return {
            "schema":"PROJECT_BRAIN_SOURCE_CANDIDATE_PROVENANCE_VERIFICATION_V1",
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "candidate_url":candidate["url"],
            "final_url":candidate["url"],
            "authority_status":"RETRIEVABILITY_VERIFIED__FACT_AUTHORITY_UNVERIFIED",
            "primary_source_status":"UNVERIFIED",
            "evidence_sufficiency_status":"UNVERIFIED",
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        }


def broad_grounding():
    return {
        "broad_objective_decomposition":{
            "status":"DECOMPOSED",
            "roles":[
                {
                    "index":0,
                    "role":"SOURCE_DISCOVERY",
                    "description":"Identify authoritative source candidates.",
                    "required_capability_class":"authoritative source discovery",
                    "status":"REQUIRES_GROUNDING",
                },
                {
                    "index":1,
                    "role":"EVIDENCE_ACQUISITION",
                    "description":"Acquire provenance-bearing evidence.",
                    "required_capability_class":"provenance-bearing evidence acquisition",
                    "status":"REQUIRES_GROUNDING",
                },
            ],
        }
    }


class BroadObjectiveSourceProvenanceRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load_runtime()

    def test_exact_objective_routes_to_discovery_then_provenance_and_stops_before_authority_claim(self):
        goal="Assess whether an unfamiliar technical mechanism remains valid under a changed operating condition"
        discovery=_FakeDiscovery({
            "status":"CANDIDATES_DISCOVERED",
            "candidate_count":2,
            "candidates":[
                {"url":"https://example.org/a","authority_status":"UNVERIFIED"},
                {"url":"https://example.net/b","authority_status":"UNVERIFIED"},
            ],
            "authority_verification":"NOT_PERFORMED",
            "primary_source_verification":"NOT_PERFORMED",
            "evidence_sufficiency_verification":"NOT_PERFORMED",
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        })
        verifier=_FakeVerifier()
        with tempfile.TemporaryDirectory() as td:
            evidence_dir=pathlib.Path(td)
            grounding_path=evidence_dir/"grounding.json"
            grounding_path.write_text("{}\n",encoding="utf-8")
            with (
                mock.patch.object(self.m,"EVID_DIR",evidence_dir),
                mock.patch.object(self.m,"_load_open_web_source_candidate_discovery",return_value=discovery),
                mock.patch.object(self.m,"_load_source_candidate_provenance_verifier",return_value=verifier),
            ):
                with self.assertRaises(self.m.Blocker) as cm:
                    self.m._run_broad_objective_source_provenance_frontier(
                        {"mission_id":"TEST-BROAD-SOURCE-PROVENANCE"},
                        goal,
                        broad_grounding(),
                        grounding_path,
                    )
            message=str(cm.exception)
            self.assertTrue(
                message.startswith("SOURCE_AUTHORITY_PRIMARY_EVIDENCE_AND_RELEVANCE_VERIFICATION_REQUIRED:"),
                message,
            )
            self.assertEqual(discovery.calls,[(goal,12,15)])
            self.assertGreaterEqual(len(verifier.calls),1)
            payload=json.loads(message.split(":",1)[1])
            self.assertFalse(payload["fact_authority_verified"])
            self.assertFalse(payload["primary_source_status_verified"])
            self.assertFalse(payload["relevance_verified"])
            self.assertFalse(payload["evidence_sufficiency_verified"])
            self.assertFalse(payload["external_capability_acquisition_attempted"])
            self.assertEqual(payload["model_dependency_count"],0)
            self.assertEqual(payload["incremental_spend_usd"],0)
            self.assertEqual(payload["next_declared_role"],"EVIDENCE_ACQUISITION")
            persisted=json.loads(
                (evidence_dir/"TEST-BROAD-SOURCE-PROVENANCE__BROAD_OBJECTIVE_SOURCE_DISCOVERY.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(persisted["objective"],goal)
            self.assertEqual(persisted["discovery"]["candidates"][0]["authority_status"],"UNVERIFIED")

    def test_discovery_unavailable_fails_closed_without_package_acquisition(self):
        discovery=_FakeDiscovery({
            "status":"DISCOVERY_UNAVAILABLE",
            "candidate_count":0,
            "candidates":[],
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        })
        goal="Determine whether a generic technical claim is supported"
        with tempfile.TemporaryDirectory() as td:
            evidence_dir=pathlib.Path(td)
            grounding_path=evidence_dir/"grounding.json"
            grounding_path.write_text("{}\n",encoding="utf-8")
            with (
                mock.patch.object(self.m,"EVID_DIR",evidence_dir),
                mock.patch.object(self.m,"_load_open_web_source_candidate_discovery",return_value=discovery),
            ):
                with self.assertRaises(self.m.Blocker) as cm:
                    self.m._run_broad_objective_source_provenance_frontier(
                        {"mission_id":"TEST-BROAD-SOURCE-NONE"},
                        goal,
                        broad_grounding(),
                        grounding_path,
                    )
            self.assertTrue(str(cm.exception).startswith("BROAD_OBJECTIVE_SOURCE_DISCOVERY_UNAVAILABLE:"))
            payload=json.loads(str(cm.exception).split(":",1)[1])
            self.assertFalse(payload["external_capability_acquisition_attempted"])

    def test_non_broad_grounding_does_not_claim_route(self):
        self.assertIsNone(
            self.m._run_broad_objective_source_provenance_frontier(
                {"mission_id":"TEST-NON-BROAD"},
                "read one known file",
                {"broad_objective_decomposition":None},
                pathlib.Path("unused-grounding.json"),
            )
        )

    def test_broad_route_precedes_legacy_auto_acquisition_in_controller(self):
        source=inspect.getsource(self.m._run_goal_unstamped)
        broad=source.index("_run_broad_objective_source_provenance_frontier")
        legacy=source.index("_load_auto_capability_acquisition")
        self.assertLess(broad,legacy)
        helper=inspect.getsource(self.m._run_broad_objective_source_provenance_frontier)
        self.assertNotIn("auto.dispatch",helper)
        self.assertNotIn("_load_auto_capability_acquisition",helper)
        self.assertNotIn("SQLite",helper)
        self.assertNotIn("viscosity",helper)


if __name__=="__main__":
    unittest.main(verbosity=2)
