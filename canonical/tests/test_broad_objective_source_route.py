#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME_PATH=ROOT/"canonical/runtime/astra_runtime.py"

def load_runtime():
    spec=importlib.util.spec_from_file_location("broad_role_runtime_test",RUNTIME_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("RUNTIME_LOAD_FAILED")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class _Discovery:
    def __init__(self,candidates):
        self._candidates=candidates
    def discover(self,goal,limit=8,timeout=20):
        return {
            "schema":"PROJECT_BRAIN_OPEN_WEB_SOURCE_CANDIDATE_DISCOVERY_V1",
            "status":"CANDIDATES_DISCOVERED" if self._candidates else "DISCOVERY_UNAVAILABLE",
            "objective":goal,
            "candidates":list(self._candidates),
            "candidate_count":len(self._candidates),
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        }

class _Provenance:
    def verify(self,candidate,timeout=20):
        return {
            "schema":"PROJECT_BRAIN_SOURCE_CANDIDATE_PROVENANCE_VERIFICATION_V1",
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "candidate_url":candidate.get("url"),
            "authority_status":"RETRIEVABILITY_VERIFIED__FACT_AUTHORITY_UNVERIFIED",
            "primary_source_status":"UNVERIFIED",
            "evidence_sufficiency_status":"UNVERIFIED",
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        }

def broad_grounding():
    return {
        "schema":"PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1",
        "grounded_clause_count":0,
        "unresolved_clause_indexes":[0],
        "broad_objective_decomposition_available":True,
        "broad_objective_decomposition":{
            "schema":"PROJECT_BRAIN_BROAD_OBJECTIVE_DECOMPOSITION_V1",
            "status":"DECOMPOSED",
            "objective":"Assess whether two measurements support the same conclusion.",
            "objective_sha256":"fixture",
            "question_shape":"BOOLEAN_ASSESSMENT",
            "roles":[
                {
                    "index":0,
                    "role":"SOURCE_DISCOVERY",
                    "description":"Identify authoritative source candidates that can supply evidence needed to resolve the objective.",
                    "required_capability_class":"authoritative source discovery",
                    "status":"REQUIRES_GROUNDING",
                }
            ],
        },
    }

class BroadObjectiveSourceRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rt=load_runtime()

    def test_role_graph_reaches_source_trust_boundary_without_package_acquisition(self):
        rt=self.rt
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            evidence=root/"canonical/astra_runtime/evidence"
            evidence.mkdir(parents=True)
            with (
                mock.patch.object(rt,"ROOT",root),
                mock.patch.object(rt,"EVID_DIR",evidence),
                mock.patch.object(
                    rt,"_load_open_web_source_candidate_discovery",
                    return_value=_Discovery([{
                        "url":"https://example.org/primary",
                        "title":"Example",
                        "discovery_backend":"TEST",
                        "authority_status":"UNVERIFIED",
                    }]),
                ),
                mock.patch.object(
                    rt,"_load_source_candidate_provenance_verifier",
                    return_value=_Provenance(),
                ),
            ):
                with self.assertRaises(rt.Blocker) as cm:
                    rt._run_broad_objective_source_discovery_route(
                        {"mission_id":"TEST-BROAD-SOURCE-001"},
                        "Assess whether two measurements support the same conclusion.",
                        broad_grounding(),
                    )
            msg=str(cm.exception)
            self.assertIn(
                "BROAD_OBJECTIVE_ROLE_UNRESOLVED:SOURCE_AUTHORITY_PRIMARY_EVIDENCE_AND_RELEVANCE_VERIFICATION",
                msg,
            )
            self.assertIn('"external_capability_acquisition_attempted": false',msg)
            receipt=evidence/"TEST-BROAD-SOURCE-001__BROAD_OBJECTIVE_SOURCE_DISCOVERY.json"
            self.assertTrue(receipt.is_file())
            data=rt.readj(receipt)
            self.assertTrue(data["role_graph_consumed"])
            self.assertFalse(data["package_supplier_discovery_attempted"])
            self.assertEqual(data["provenance_verified_candidate_count"],1)
            self.assertEqual(data["authority_verification"],"NOT_PERFORMED")

    def test_no_source_candidate_fails_closed_before_supplier_acquisition(self):
        rt=self.rt
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            evidence=root/"canonical/astra_runtime/evidence"
            evidence.mkdir(parents=True)
            with (
                mock.patch.object(rt,"ROOT",root),
                mock.patch.object(rt,"EVID_DIR",evidence),
                mock.patch.object(
                    rt,"_load_open_web_source_candidate_discovery",
                    return_value=_Discovery([]),
                ),
                mock.patch.object(
                    rt,"_load_source_candidate_provenance_verifier",
                    return_value=_Provenance(),
                ),
            ):
                with self.assertRaises(rt.Blocker) as cm:
                    rt._run_broad_objective_source_discovery_route(
                        {"mission_id":"TEST-BROAD-SOURCE-EMPTY-001"},
                        "Evaluate whether a technical effect is reproducible.",
                        broad_grounding(),
                    )
            self.assertIn(
                "BROAD_OBJECTIVE_ROLE_UNRESOLVED:SOURCE_DISCOVERY",
                str(cm.exception),
            )
            self.assertIn(
                '"package_supplier_discovery_attempted": false',
                str(cm.exception),
            )

    def test_run_goal_never_reaches_auto_package_acquisition_for_decomposed_broad_goal(self):
        rt=self.rt
        goal="Assess whether two measurements support the same conclusion."
        mission={"mission_id":"TEST-BROAD-INTEGRATION-001","goal":goal}
        grounding=broad_grounding()
        class AutoMustNotRun:
            def __getattr__(self,name):
                raise AssertionError("AUTO_CAPABILITY_ACQUISITION_MUST_NOT_RUN")
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            evidence=root/"canonical/astra_runtime/evidence"
            evidence.mkdir(parents=True)
            gap=evidence/"gap.json"
            gap.write_text("{}\n",encoding="utf-8")
            ground_path=evidence/"grounding.json"
            ground_path.write_text("{}\n",encoding="utf-8")
            with (
                mock.patch.object(rt,"ROOT",root),
                mock.patch.object(rt,"EVID_DIR",evidence),
                mock.patch.object(rt,"_run_verified_capability_proposal",return_value=None),
                mock.patch.object(rt,"_run_capability_planned_goal",return_value=None),
                mock.patch.object(rt,"_run_model_independent_goal",return_value=None),
                mock.patch.object(
                    rt,"_compile_plain_goal",
                    side_effect=rt.Blocker(
                        "GOAL_COMPILATION_FAILED:GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"
                    ),
                ),
                mock.patch.object(rt,"_classify_plain_goal_gap",return_value="CAPABILITY_CANDIDATE"),
                mock.patch.object(
                    rt,"_write_goal_gap_classification",
                    return_value=(gap,{"gap_class":"CAPABILITY_CANDIDATE"}),
                ),
                mock.patch.object(
                    rt,"_ground_plain_goal_to_bound_capabilities",
                    return_value=(ground_path,grounding),
                ),
                mock.patch.object(
                    rt,"_run_broad_objective_source_discovery_route",
                    side_effect=rt.Blocker(
                        "BROAD_OBJECTIVE_ROLE_UNRESOLVED:SOURCE_AUTHORITY_PRIMARY_EVIDENCE_AND_RELEVANCE_VERIFICATION"
                    ),
                ) as route,
                mock.patch.object(
                    rt,"_load_auto_capability_acquisition",
                    return_value=AutoMustNotRun(),
                ) as auto_loader,
            ):
                with self.assertRaises(rt.Blocker) as cm:
                    rt._run_goal_unstamped({},mission)
            self.assertIn("BROAD_OBJECTIVE_ROLE_UNRESOLVED",str(cm.exception))
            route.assert_called_once()
            auto_loader.assert_not_called()

if __name__=="__main__":
    unittest.main(verbosity=2)
