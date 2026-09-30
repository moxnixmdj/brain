#!/usr/bin/env python3
import importlib.util
import os
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=ROOT/"runtime"/"enforce_goal_hierarchy.py"
spec=importlib.util.spec_from_file_location("project_brain_mistake_guard_test",PATH)
guard=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=guard
spec.loader.exec_module(guard)

class MistakeImmunityGuardTests(unittest.TestCase):
    def setUp(self):
        guard.FAIL.clear()
        self.old_current=os.environ.get("CURRENT_PR_NUMBER")

    def tearDown(self):
        guard.FAIL.clear()
        if self.old_current is None:
            os.environ.pop("CURRENT_PR_NUMBER",None)
        else:
            os.environ["CURRENT_PR_NUMBER"]=self.old_current

    def intent(self):
        return {
            "canonical_generation":"g",
            "capability_target":"cap",
            "causal_blocker":"block",
            "action_kind":"REAL_CAPABILITY_ACQUISITION",
            "blocker_lease_key":"g::cap::block::REAL_CAPABILITY_ACQUISITION",
        }

    def test_lowest_pr_is_deterministic_duplicate_lease_owner(self):
        current=self.intent()
        peer=self.intent()
        old=guard._open_pr_intents
        try:
            guard._open_pr_intents=lambda:[{"pr":257,"intent":peer}]
            os.environ["CURRENT_PR_NUMBER"]="256"
            guard.enforce_blocker_lease(current)
            self.assertEqual(guard.FAIL,[])
        finally:
            guard._open_pr_intents=old

    def test_later_duplicate_fails_closed(self):
        current=self.intent()
        peer=self.intent()
        old=guard._open_pr_intents
        try:
            guard._open_pr_intents=lambda:[{"pr":256,"intent":peer}]
            os.environ["CURRENT_PR_NUMBER"]="257"
            guard.enforce_blocker_lease(current)
            self.assertIn("DUPLICATE_BLOCKER_LEASE_OWNER_EXISTS:256",guard.FAIL)
        finally:
            guard._open_pr_intents=old

    def test_explicit_route_race_is_not_accidental_duplicate(self):
        current=self.intent(); peer=self.intent()
        current.update({"intentional_route_race":True,"route_race_id":"race-1"})
        peer.update({"intentional_route_race":True,"route_race_id":"race-1"})
        old=guard._open_pr_intents
        try:
            guard._open_pr_intents=lambda:[{"pr":256,"intent":peer}]
            os.environ["CURRENT_PR_NUMBER"]="257"
            guard.enforce_blocker_lease(current)
            self.assertEqual(guard.FAIL,[])
        finally:
            guard._open_pr_intents=old

    def test_child_cognitive_capability_inherits_parent_model_independence(self):
        intent={
            "action_kind":"REAL_CAPABILITY_ACQUISITION",
            "capability_target":"MODEL_INDEPENDENT_GROUNDED_CAPABILITY_TO_EXECUTABLE_COMPOSITION_V1",
        }
        obs={"route_frontier":{"selected_route_preflight":{"execution_dependencies":[
            {"kind":"MODEL_API","dependency":"frontier-model"}
        ]}}}
        guard.enforce_model_independent_cognition(intent,obs)
        self.assertTrue(any(x.startswith("MODEL_PRESENT_IN_COGNITION_EXECUTION_PATH") for x in guard.FAIL),guard.FAIL)

    def test_child_cognitive_capability_without_model_dependency_passes(self):
        intent={
            "action_kind":"REAL_CAPABILITY_ACQUISITION",
            "capability_target":"MODEL_INDEPENDENT_GROUNDED_CAPABILITY_TO_EXECUTABLE_COMPOSITION_V1",
        }
        obs={"route_frontier":{"selected_route_preflight":{"execution_dependencies":[
            {"kind":"LOCAL_RUNTIME","dependency":"deterministic-runtime"}
        ]}}}
        guard.enforce_model_independent_cognition(intent,obs)
        self.assertEqual(guard.FAIL,[])


    def test_silent_active_target_change_fails_closed(self):
        old=guard.load_at_ref
        try:
            guard.load_at_ref=lambda ref,path:{"active_capability_target":"PARENT"}
            intent={"action_kind":"REAL_CAPABILITY_ACQUISITION"}
            hierarchy={"active_capability_target":"PROXY"}
            guard.enforce_target_continuity(intent,"base",hierarchy)
            self.assertTrue(any(x.startswith("ACTIVE_CAPABILITY_TARGET_CHANGE_REQUIRES_EXPLICIT_RECONCILIATION") for x in guard.FAIL),guard.FAIL)
        finally:
            guard.load_at_ref=old

    def test_scoreboard_increase_without_promotion_evidence_fails_closed(self):
        old_ref=guard.load_at_ref
        old_load=guard.load
        try:
            guard.load_at_ref=lambda ref,path:{
                "counters_since_epoch_start":{
                    "reusable_capabilities_inherited":0,
                    "verified_real_tasks_completed":0,
                    "fresh_reuse_passes":0,
                    "frontier_dependencies_removed":0,
                    "residual_gaps_localized":0,
                }
            }
            guard.load=lambda path:{
                "counters_since_epoch_start":{
                    "reusable_capabilities_inherited":1,
                    "verified_real_tasks_completed":0,
                    "fresh_reuse_passes":0,
                    "frontier_dependencies_removed":0,
                    "residual_gaps_localized":0,
                }
            }
            intent={
                "action_kind":"CAPABILITY_INHERITANCE",
                "capability_target":"MODEL_INDEPENDENT_GROUNDED_CAPABILITY_TO_EXECUTABLE_COMPOSITION_V1",
            }
            guard.enforce_promotion_truth(
                intent,
                ["canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json"],
                "base",
            )
            self.assertIn("PROMOTION_EVIDENCE_REQUIRED_FOR_SCOREBOARD_INCREASE",guard.FAIL)
        finally:
            guard.load_at_ref=old_ref
            guard.load=old_load

    def test_frontier_surface_consistency_detects_drift(self):
        pointer={
            "current_frontier":{
                "critical_blocker":"BLOCK",
                "highest_leverage_capability_gap":"BLOCK",
                "next_step":"NEXT",
                "last_real_output_event":{
                    "scoreboard":{
                        "reusable_capabilities_inherited":1,
                        "verified_real_tasks_completed":2,
                        "fresh_reuse_passes":3,
                        "frontier_dependencies_removed":4,
                        "residual_gaps_localized":5,
                    }
                },
            }
        }
        hierarchy={
            "active_capability_target":"CAP",
            "current_parent_blocker":"BLOCK",
            "next_required_action_class":"DRIFTED",
            "next_progress_event_target":"NEXT",
        }
        queue={"immediate_frontier":{
            "selected_capability":"CAP",
            "exact_blocker":"BLOCK",
            "next_action":"NEXT",
        }}
        target={"capability_id":"CAP","residual_gap":"BLOCK","next_action":"NEXT"}
        scoreboard={
            "counters_since_epoch_start":{
                "reusable_capabilities_inherited":1,
                "verified_real_tasks_completed":2,
                "fresh_reuse_passes":3,
                "frontier_dependencies_removed":4,
                "residual_gaps_localized":5,
            },
            "active_frontier_accounting":{"parent_frontier_capability":"CAP"},
            "progress_events":[{"residual_gap":"BLOCK"}],
        }
        old=guard.load
        try:
            def fake_load(path):
                path=str(path)
                if path=="canonical/capabilities/frontier/CAP.json":
                    return target
                if path=="canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json":
                    return scoreboard
                raise AssertionError(path)
            guard.load=fake_load
            guard.enforce_frontier_surface_consistency(pointer,hierarchy,queue)
            self.assertTrue(
                any(x.startswith("FRONTIER_NEXT_ACTION_MISMATCH:") for x in guard.FAIL),
                guard.FAIL,
            )
        finally:
            guard.load=old

    def test_frontier_surface_consistency_accepts_exact_state(self):
        counters={
            "reusable_capabilities_inherited":1,
            "verified_real_tasks_completed":2,
            "fresh_reuse_passes":3,
            "frontier_dependencies_removed":4,
            "residual_gaps_localized":5,
        }
        pointer={"current_frontier":{
            "critical_blocker":"BLOCK",
            "highest_leverage_capability_gap":"BLOCK",
            "next_step":"NEXT",
            "last_real_output_event":{"scoreboard":dict(counters)},
        }}
        hierarchy={
            "active_capability_target":"CAP",
            "current_parent_blocker":"BLOCK",
            "next_required_action_class":"NEXT",
            "next_progress_event_target":"NEXT",
        }
        queue={"immediate_frontier":{
            "selected_capability":"CAP",
            "exact_blocker":"BLOCK",
            "next_action":"NEXT",
        }}
        old=guard.load
        try:
            guard.load=lambda path: (
                {"capability_id":"CAP","residual_gap":"BLOCK","next_action":"NEXT"}
                if str(path)=="canonical/capabilities/frontier/CAP.json"
                else {
                    "counters_since_epoch_start":dict(counters),
                    "active_frontier_accounting":{"parent_frontier_capability":"CAP"},
                    "progress_events":[{"residual_gap":"BLOCK"}],
                }
            )
            guard.enforce_frontier_surface_consistency(pointer,hierarchy,queue)
            self.assertEqual(guard.FAIL,[])
        finally:
            guard.load=old

if __name__=="__main__":
    unittest.main(verbosity=2)
