from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
SUBJECT = ROOT / "canonical/runtime/unified_cognitive_fabric_v1.py"

DIRECT_MODULES = (
    "live_integrated_brain_v1",
    "p3_real_context_v3_admission_v12",
    "autonomous_verified_self_improvement_v1",
    "r3_improvement_queue_driver_v1",
    "live_brain_runtime_v1",
    "h100_verified_capability_registry_v8",
    "exact_linear_parameter_polytope_v1",
    "interval_information_frontier_v1",
    "capability_first_scheduler_v1",
    "brain_owned_python_closure_census_v1",
    "current_authority_runtime_census_v1",
    "live_capability_ownership_v1",
    "live_capability_invoker_v1",
    "live_capability_composition_v1",
    "r1_live_architecture_closure_gate_v1",
    "universal_escape_resolver_v1",
    "certificate_gated_selected_route_runtime_entrypoint_v2",
    "terminal_autopilot_v1",
    "terminal_root_decision_gate_v1",
    "terminal_closure_reducer",
    "verified_bound_capability_execution_adapter_v1",
    "semantic_ambiguity_control_v1",
    "semantic_relation_control_v1",
    "oewn_decision_sense_control_v1",
    "finance_bounded_concept_registry_verify_v1",
    "one_shot_reality_closure_v2",
)


def _module(name: str, **attrs):
    m = types.ModuleType("canonical.runtime." + name)
    for key, value in attrs.items():
        setattr(m, key, value)
    return m


def _load_subject():
    import canonical.runtime as runtime_pkg

    fake = {}
    fake["live_integrated_brain_v1"] = _module(
        "live_integrated_brain_v1",
        load_verified_registry=lambda: {"cap.a": {"id": "cap.a"}},
    )
    fake["p3_real_context_v3_admission_v12"] = _module(
        "p3_real_context_v3_admission_v12",
        evaluate=lambda payload, repo_root=None: {"pass": True, "status": "P3_OK"},
    )
    fake["autonomous_verified_self_improvement_v1"] = _module(
        "autonomous_verified_self_improvement_v1",
        DEFAULT_STATE_PATH=Path("/tmp/project-brain-direct-contract-state.json"),
        load_state=lambda path=None: {"stats": {"verified_skill_count": 2, "active_skill_count": 1}},
        run_learning_episode=lambda *a, **k: {"pass": True, "status": "LEARNING_OK"},
    )
    fake["r3_improvement_queue_driver_v1"] = _module(
        "r3_improvement_queue_driver_v1",
        drain=lambda **kwargs: {"pass": True, "status": "DRAIN_OK"},
    )

    def default_runtime_run(request, **kwargs):
        mode = request.get("mode")
        if mode == "decision":
            return {
                "pass": True,
                "status": "RUNTIME_OK",
                "decision_output": {"pass": True, "status": "DECISION_OK"},
            }
        if mode in {"raw_bound", "compiled_bound"}:
            return {
                "pass": True,
                "status": "RUNTIME_OK",
                "raw_result": {"pass": True, "status": "BOUND_OK"},
            }
        return {
            "pass": True,
            "status": "RUNTIME_OK",
            "solver_output": {"pass": True, "status": "SOLVER_OK"},
        }

    fake["live_brain_runtime_v1"] = _module(
        "live_brain_runtime_v1",
        SURFACES=("A", "B"),
        run=default_runtime_run,
        observe_runtime_outcome=lambda *a, **k: {"pass": True, "status": "OBSERVED"},
        synthesize_failure_repair=lambda *a, **k: {"pass": True, "status": "REPAIR_SYNTHESIS_OK"},
        execute_failure_repair_cycle=lambda *a, **k: {"pass": True, "status": "REPAIR_CYCLE_OK"},
    )
    fake["h100_verified_capability_registry_v8"] = _module(
        "h100_verified_capability_registry_v8",
        SCHEMA="H100_V8",
        registry_snapshot=lambda: {"status": "SNAPSHOT_OK", "count": 1},
        resolve_verified_capability=lambda *a, **k: {"status": "LIBRARY_HIT__VERIFY_BEFORE_USE"},
        predict=lambda *a, **k: 7,
    )
    fake["exact_linear_parameter_polytope_v1"] = _module(
        "exact_linear_parameter_polytope_v1",
        solve=lambda problem: {"pass": True, "status": "POLYTOPE_OK"},
    )
    fake["interval_information_frontier_v1"] = _module(
        "interval_information_frontier_v1",
        solve=lambda problem: {"pass": True, "status": "INTERVAL_OK"},
    )
    fake["capability_first_scheduler_v1"] = _module(
        "capability_first_scheduler_v1",
        rank_work=lambda work: {"status": "CAPABILITY_FIRST_RANKING", "ranked": list(work)},
    )
    fake["brain_owned_python_closure_census_v1"] = _module(
        "brain_owned_python_closure_census_v1",
        census=lambda root, starts: {
            "brain_owned_file_count": 3,
            "brain_owned_transitive_source_bytes": 123,
            "brain_owned_transitive_files": [{"path": "canonical/runtime/unified_cognitive_fabric_v1.py"}],
        },
    )
    fake["current_authority_runtime_census_v1"] = _module(
        "current_authority_runtime_census_v1",
        run=lambda root: {
            "pass": True,
            "authority_pointer_reference_missing_count": 0,
            "authority_pointer_reference_missing_paths": [],
        },
    )
    fake["live_capability_ownership_v1"] = _module(
        "live_capability_ownership_v1",
        evaluate=lambda engines: {
            "r1_structural_closure": True,
            "live_owned_capability_count": 1,
            "live_owned_capability_ids": ["cap.a"],
            "live_owned_equals_fabric_reachable": True,
            "provider_coverage_complete": True,
        },
    )
    fake["live_capability_invoker_v1"] = _module(
        "live_capability_invoker_v1",
        coverage=lambda ids: {"pass": True, "covered": list(ids)},
        invoke=lambda capability_id, payload, **kwargs: {
            "pass": True,
            "status": "LIVE_CAPABILITY_OK",
            "capability_id": capability_id,
        },
    )
    fake["live_capability_composition_v1"] = _module(
        "live_capability_composition_v1",
        execute=lambda payload, **kwargs: {"pass": True, "status": "COMPOSITION_OK"},
    )
    fake["r1_live_architecture_closure_gate_v1"] = _module(
        "r1_live_architecture_closure_gate_v1",
        evaluate=lambda *a, **k: {"pass": True, "errors": []},
    )
    fake["universal_escape_resolver_v1"] = _module(
        "universal_escape_resolver_v1",
        resolve=lambda **kwargs: {"pass": True, "status": "ESCAPE_OK"},
    )
    fake["certificate_gated_selected_route_runtime_entrypoint_v2"] = _module(
        "certificate_gated_selected_route_runtime_entrypoint_v2",
        preflight=lambda: {"pass": True, "status": "PREFLIGHT_OK"},
        dispatch=lambda context, payload: {"status": "DISPATCH_OK"},
    )
    fake["terminal_autopilot_v1"] = _module(
        "terminal_autopilot_v1",
        build_manifest_from_repo=lambda *a, **k: {"manifest": {}},
        plan=lambda manifest: {"pass": True, "status": "PLAN_OK"},
    )
    fake["terminal_root_decision_gate_v1"] = _module(
        "terminal_root_decision_gate_v1",
        evaluate=lambda payload, repo_root=None: {"pass": False, "status": "ROOT_OPEN"},
    )
    fake["terminal_closure_reducer"] = _module(
        "terminal_closure_reducer",
        evaluate_manifest=lambda manifest, repo_root=None: {"achieved": False},
        evaluate_frontier_state=lambda *a: {"status": "OPEN"},
    )
    fake["verified_bound_capability_execution_adapter_v1"] = _module(
        "verified_bound_capability_execution_adapter_v1",
        execute=lambda capability_id, inputs=None: {"pass": True, "status": "BOUND_EXEC_OK"},
    )
    fake["semantic_ambiguity_control_v1"] = _module(
        "semantic_ambiguity_control_v1",
        decide=lambda payload: {"pass": True, "status": "AMBIGUITY_OK"},
    )
    fake["semantic_relation_control_v1"] = _module(
        "semantic_relation_control_v1",
        resolve=lambda payload, **kwargs: {"pass": True, "status": "RELATION_OK"},
    )
    fake["oewn_decision_sense_control_v1"] = _module(
        "oewn_decision_sense_control_v1",
        resolve=lambda **kwargs: {"pass": True, "status": "OEWN_OK"},
    )
    fake["finance_bounded_concept_registry_verify_v1"] = _module(
        "finance_bounded_concept_registry_verify_v1",
        CLAIM_SCHEMA="FINANCE_CLAIM",
        verify_claim=lambda value, repo_root=None: {"pass": True},
    )
    fake["one_shot_reality_closure_v2"] = _module(
        "one_shot_reality_closure_v2",
        run=lambda **kwargs: {"pass": True, "status": "ONE_SHOT_OK"},
    )

    old = {}
    for name in DIRECT_MODULES:
        fq = "canonical.runtime." + name
        old[fq] = sys.modules.get(fq)
        sys.modules[fq] = fake[name]
        setattr(runtime_pkg, name, fake[name])

    spec = importlib.util.spec_from_file_location(
        "canonical.runtime._unified_cognitive_fabric_direct_contract_subject",
        SUBJECT,
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)
    return mod, fake, old


class UnifiedCognitiveFabricDirectContractTests(unittest.TestCase):
    def setUp(self):
        self.subject, self.fake, self.old = _load_subject()

    def test_auto_mode_is_structural_and_fails_closed_on_unknown_shape(self):
        s = self.subject
        self.assertEqual(s._auto_mode({"task_id": "t", "goal": "g"}, {}), "ADEQUATE_DECISION")
        self.assertEqual(s._auto_mode({"work": []}, {}), "CAPABILITY_SCHEDULER")
        self.assertEqual(
            s._auto_mode(
                {
                    "left_id": "a",
                    "right_id": "b",
                    "scope_id": "s",
                    "required_relation": "ENTAILS",
                },
                {},
            ),
            "SEMANTIC_RELATION",
        )
        with self.assertRaises(s.CognitiveFabricError):
            s._auto_mode({"unknown": True}, {})

    def test_auto_adequate_decision_dispatch_preserves_zero_authority_wrapper(self):
        s = self.subject
        run_spy = Mock(
            return_value={
                "pass": True,
                "status": "RUNTIME_OK",
                "decision_output": {"pass": True, "status": "DECISION_OK"},
            }
        )
        s.live_runtime.run = run_spy
        out = s.run({"mode": "AUTO", "payload": {"task_id": "t", "goal": "g"}, "options": {"learn": False}})
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertEqual(out["mode"], "ADEQUATE_DECISION")
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["inner_status"], "DECISION_OK")
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)
        self.assertEqual(run_spy.call_args.args[0]["mode"], "decision")

    def test_capability_scheduler_dispatches_only_to_scheduler_contract(self):
        s = self.subject
        spy = Mock(return_value={"status": "CAPABILITY_FIRST_RANKING", "ranked": []})
        s.capability_scheduler.rank_work = spy
        out = s.run({"mode": "AUTO", "payload": {"work": []}, "options": {"learn": False}})
        self.assertEqual(out["mode"], "CAPABILITY_SCHEDULER")
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertTrue(out["inner_pass"])
        spy.assert_called_once_with([])

    def test_semantic_relation_forwards_same_authority_verifier_to_all_relation_checks(self):
        s = self.subject
        captured = {}
        def resolve(payload, **kwargs):
            captured.update(kwargs)
            return {"pass": True, "status": "RELATION_OK"}
        s.semantic_relation.resolve = resolve
        verifier = lambda claim: {"pass": True}
        out = s.run(
            {
                "mode": "AUTO",
                "payload": {
                    "left_id": "a",
                    "right_id": "b",
                    "scope_id": "s",
                    "required_relation": "ENTAILS",
                },
                "options": {"learn": False},
            },
            semantic_authority_verifier=verifier,
        )
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertIs(captured["concept_identity_verifier"], verifier)
        self.assertIs(captured["terminal_signature_verifier"], verifier)
        self.assertIs(captured["relation_edge_verifier"], verifier)

    def test_certified_route_preflight_is_wrapped_without_new_credit(self):
        s = self.subject
        spy = Mock(return_value={"pass": True, "status": "PREFLIGHT_OK"})
        s.certified_route.preflight = spy
        out = s.run(
            {"mode": "CERTIFIED_ROUTE", "payload": {"operation": "PREFLIGHT"}, "options": {"learn": False}}
        )
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertEqual(out["inner_status"], "PREFLIGHT_OK")
        self.assertEqual(out["terminal_credit_delta"], 0)
        spy.assert_called_once_with()

    def test_terminal_root_open_result_stays_nonterminal(self):
        s = self.subject
        out = s.run({"mode": "TERMINAL_ROOT", "payload": {}, "options": {"learn": False}})
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertFalse(out["inner_pass"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_catalog_projects_direct_collaborator_contracts_without_terminal_credit(self):
        s = self.subject
        out = s.catalog()
        self.assertEqual(out["status"], "LIVE_FEDERATED_COGNITIVE_FABRIC")
        self.assertTrue(out["single_front_door"])
        self.assertEqual(out["verified_bound_capability_count"], 1)
        self.assertTrue(out["authority_pointer_runtime_reference_reachability_complete"])
        self.assertTrue(out["r1_structural_closure"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_unknown_auto_payload_fails_closed(self):
        out = self.subject.run({"mode": "AUTO", "payload": {"unknown": True}, "options": {}})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertFalse(out["pass"])
        self.assertIn("AUTO_ROUTE_AMBIGUOUS_OR_UNMODELED", out["reason"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
