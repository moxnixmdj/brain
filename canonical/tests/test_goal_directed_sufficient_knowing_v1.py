#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import pathlib

from canonical.runtime import goal_directed_sufficient_knowing_v1 as s

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / "canonical/runtime/goal_directed_sufficient_knowing_v1.py"
STORE = ROOT / "canonical/astra_runtime/state/GOAL_DIRECTED_SUFFICIENT_KNOWLEDGE_STORE_V1.json"


def _packet(**overrides):
    packet = {
        "schema": "PROJECT_BRAIN_GOAL_DIRECTED_SUFFICIENT_KNOWING_PACKET_V1",
        "goal": {
            "id": "goal_repair_workflow",
            "effect": "complete long horizon coding workflow",
            "success_predicate": "independent_verifier_accepts_final_state",
            "value": 2.0,
            "risk": 1.0,
        },
        "environment": {
            "id": "env_unseen_repo_a",
            "environment_class": "software_repository",
            "recompute_terms": ["test_exit", "file_state"],
        },
        "store": {
            "schema": s.STORE_SCHEMA,
            "facts": [],
            "relations": [],
        },
        "actions": [
            {"id": "A1", "requires": ["u_test_command"], "effect": "run_local_tests"},
            {"id": "A2", "requires": ["u_test_command"], "effect": "edit_then_run_tests"},
        ],
        "unknowns": [
            {
                "id": "u_test_command",
                "question": "Which exact command does this repository use to run the decisive test?",
                "source_class": "local_guide",
                "falsifier": "command_exit_code_or_test_manifest_mismatch",
                "bounded_enumeration": True,
                "cost": 0.1,
                "hypotheses": [
                    {
                        "id": "guide_exists",
                        "probability": 0.7,
                        "utilities": {"A1": 1.0, "A2": 0.0},
                    },
                    {
                        "id": "guide_absent",
                        "probability": 0.3,
                        "utilities": {"A1": 0.0, "A2": 1.0},
                    },
                ],
                "action_values": {"A1": 1.0, "A2": 0.0},
            }
        ],
        "scan": [
            {"id": "atom_decisive", "decision_terms": ["test", "repository"], "content": "test manifest exists"},
            {"id": "atom_irrelevant", "decision_terms": ["wallpaper"], "content": "desktop wallpaper color"},
        ],
        "independent_verifier_present": True,
        "producer_id": "arena-agent",
        "verifier_id": "github-actions-oidc:distinct-runner",
        "max_queries": 1,
    }
    packet.update(overrides)
    return packet


def _fact(**overrides):
    fact = {
        "id": "fact_test_command",
        "unknown_id": "u_test_command",
        "value": "pytest -q",
        "authenticated": True,
        "source_bound": True,
        "source_class": "local_guide",
        "evidence_hash": "sha256:local-help",
        "policy_authority": False,
        "answer_authority": False,
        "capability_credit_delta": 0,
        "freshness_ok": True,
        "completeness_required": False,
        "bounded_enumeration": True,
        "scope": {
            "goal_effect": "complete long horizon coding workflow",
            "environment_class": "software_repository",
            "environment_ids": ["env_unseen_repo_a"],
        },
    }
    fact.update(overrides)
    return fact


def test_static_audit_has_no_model_or_network_runtime_imports():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    forbidden = {
        "urllib", "requests", "httpx", "socket", "http", "openai", "anthropic",
        "litellm", "transformers", "torch", "tensorflow", "boto3", "subprocess",
        "huggingface_hub", "docker", "yaml", "selenium", "playwright",
    }
    assert not (roots & forbidden), sorted(roots & forbidden)
    assert "argparse" in roots and "json" in roots and "pathlib" in roots


def test_external_store_is_empty_inspectable_and_not_a_weight_warehouse():
    store = json.loads(STORE.read_text(encoding="utf-8"))
    assert store["schema"] == s.STORE_SCHEMA
    assert store["facts"] == []
    assert store["relations"] == []
    assert store["parameters"] == {}
    assert store["weights"] == {}
    assert store["knowledge_lives_outside_weights"] is True
    assert store["editable_without_retraining"] is True


def test_goal_directed_query_selects_only_the_decision_discriminating_unknown():
    packet = _packet()
    packet["unknowns"].append({
        "id": "u_irrelevant_wallpaper",
        "question": "What color is the wallpaper?",
        "source_class": "authenticated_observation",
        "falsifier": "pixel_mismatch",
        "bounded_enumeration": True,
        "cost": 0.0,
        "action_values": {"A1": 0.0, "A2": 0.0},
    })
    result = s.evaluate(packet)
    assert result["decision"] == s.K1_QUERY_REQUIRED
    assert result["selected_query_count"] == 1
    assert result["selected_queries"][0]["unknown_id"] == "u_test_command"
    assert result["selected_queries"][0]["value_of_information_basis"] == "EXACT_EVPI"
    assert result["selected_queries"][0]["question_source"] == "SUPPLIED_K1_TEMPLATE"
    assert result["learn_everything_rejected"] is True
    assert result["exhaustive_scan_rejected"] is True
    assert "atom_irrelevant" in result["deleted_scan_atoms"]
    assert result["runtime_model_calls"] == 0
    assert result["runtime_network_calls"] == 0
    assert result["parameters_written"] == 0


def test_question_is_derived_from_the_action_partition_when_no_sentence_is_supplied():
    packet = _packet()
    packet["unknowns"][0].pop("question")
    result = s.evaluate(packet)
    query = result["selected_queries"][0]
    assert query["question_source"] == "DERIVED_FROM_ACTION_PARTITION"
    assert "u_test_command" in query["question"]
    assert "A1" in query["question"] and "A2" in query["question"]
    assert query["value_of_information_basis"] == "EXACT_EVPI"


def test_exact_evpi_probability_model_rejects_non_normalized_or_incomplete_hypotheses():
    packet = _packet()
    packet["unknowns"][0]["hypotheses"][1]["probability"] = 0.8
    result = s.evaluate(packet)
    assert result["decision"].startswith(s.REFUSED_PREFIX)
    assert "HYPOTHESIS_PROBABILITIES_NOT_NORMALIZED" in result["query_candidates"][0]["reasons"]
    packet = _packet()
    packet["unknowns"][0]["hypotheses"][1]["utilities"].pop("A2")
    result = s.evaluate(packet)
    assert result["decision"].startswith(s.REFUSED_PREFIX)
    assert "HYPOTHESIS_UTILITY_MISSING" in " ".join(result["query_candidates"][0]["reasons"])


def test_store_add_and_remove_changes_decision_without_parameter_writes():
    bound = _packet(store={"schema": s.STORE_SCHEMA, "facts": [_fact()], "relations": []})
    empty = _packet(store={"schema": s.STORE_SCHEMA, "facts": [], "relations": []})
    with_fact = s.evaluate(bound)
    without_fact = s.evaluate(empty)
    assert with_fact["decision"] == s.READY_FOR_DISTINCT_VERIFIER
    assert without_fact["decision"] == s.K1_QUERY_REQUIRED
    assert with_fact["parameters_written"] == 0
    assert without_fact["parameters_written"] == 0
    assert with_fact["knowledge_written_to_weights"] == 0


def test_exhaustive_scan_or_zero_value_query_is_deleted_not_asked():
    packet = _packet()
    packet["unknowns"] = [{
        "id": "u_test_command",
        "question": "Which exact command does this repository use to run the decisive test?",
        "source_class": "local_guide",
        "falsifier": "command_exit_code_or_test_manifest_mismatch",
        "bounded_enumeration": True,
        "cost": 5.0,
        "hypotheses": [
            {"probability": 0.5, "utilities": {"A1": 0.0, "A2": 0.0}},
            {"probability": 0.5, "utilities": {"A1": 0.0, "A2": 0.0}},
        ],
        "action_values": {"A1": 0.0, "A2": 0.0},
    }]
    result = s.evaluate(packet)
    assert result["decision"].startswith(s.REFUSED_PREFIX)
    assert result["selected_queries"] == []
    assert any("VOI_NOT_POSITIVE" in q["reasons"] for q in result["query_candidates"])


def test_open_world_completeness_without_bounded_enumeration_fails_closed():
    packet = _packet()
    packet["unknowns"][0]["completeness_required"] = True
    packet["unknowns"][0]["bounded_enumeration"] = False
    result = s.evaluate(packet)
    assert result["decision"].startswith(s.REFUSED_PREFIX)
    assert "OPEN_WORLD_COMPLETENESS_NOT_PROVEN" in result["decision"]


def test_model_or_ready_made_answer_as_source_fails_closed():
    packet = _packet()
    packet["unknowns"][0]["source_class"] = "runtime_model"
    packet["unknowns"][0]["ready_made_answer"] = True
    result = s.evaluate(packet)
    assert result["decision"].startswith(s.REFUSED_PREFIX)
    candidates = result["query_candidates"][0]["reasons"]
    assert "SOURCE_CLASS_NOT_K1" in candidates
    assert "K1_MAY_NOT_SUPPLY_PLAN_OR_ANSWER" in candidates


def test_bound_k1_fact_removes_the_unknown_and_no_question_is_asked():
    packet = _packet(store={"schema": s.STORE_SCHEMA, "facts": [_fact()], "relations": []})
    result = s.evaluate(packet)
    assert result["decision"] == s.READY_FOR_DISTINCT_VERIFIER
    assert result["known_unknowns"] == {"u_test_command": "fact_test_command"}
    assert result["selected_queries"] == []
    assert result["environment_action_executed"] is False
    assert result["execution_authority"] is False


def test_unscoped_or_policy_asserting_fact_cannot_become_knowledge():
    packet = _packet(store={"schema": s.STORE_SCHEMA, "facts": [_fact(scope={"goal_effect": "different goal"})], "relations": []})
    result = s.evaluate(packet)
    assert result["decision"] == s.K1_QUERY_REQUIRED
    assert "u_test_command" in result["unknown_unknowns"]
    assert "FACT_SCOPE_MISMATCH" in result["fact_failures"]["u_test_command"]


def test_missing_distinct_verifier_fails_closed_even_when_all_unknowns_are_bound():
    packet = _packet(store={"schema": s.STORE_SCHEMA, "facts": [_fact()], "relations": []},
                     independent_verifier_present=False)
    result = s.evaluate(packet)
    assert result["decision"].startswith(s.REFUSED_PREFIX)
    assert "DISTINCT_VERIFIER_MISSING" in result["decision"]


def test_goal_change_changes_which_fact_is_usable():
    fact = _fact(scope={"goal_effect": "different goal", "environment_class": "software_repository"})
    packet = _packet(store={"schema": s.STORE_SCHEMA, "facts": [fact], "relations": []})
    packet["goal"]["effect"] = "different goal"
    result = s.evaluate(packet)
    assert result["decision"] == s.READY_FOR_DISTINCT_VERIFIER
    assert result["known_unknowns"]["u_test_command"] == "fact_test_command"


def test_one_experience_saves_scoped_relation_not_exact_actions_or_world_facts():
    experience = {
        "environment_class": "software_repository",
        "goal_effect": "complete long horizon coding workflow",
        "relation": "test_exit_zero_implies_state_acceptance_candidate",
        "variables": ["repository_id", "test_command", "exit_code"],
        "preconditions": ["independent_test_manifest_present", "no_hidden_test_reading"],
        "falsifier": "verifier_rejects_state_or_exit_code_mismatch",
        "evidence_hash": "sha256:run_a",
        "producer_id": "arena-agent",
        "verifier_id": "github-actions-oidc:run_a",
        "independent_verifier": True,
        "model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
    }
    result = s.distill(experience)
    assert result["decision"] == "RELATION_ADMITTED__SCOPE_BOUND"
    assert result["facts"] == []
    assert len(result["relations"]) == 1
    relation = result["relations"][0]
    assert relation["generalization_license"] is False
    assert relation["single_experience_scope"] is True
    assert relation["exact_action_trajectory_saved"] is False
    assert relation["world_fact_saved_in_weights"] is False
    assert relation["executable_predicate_saved"] is False
    assert result["parameters_written"] == 0


def test_generalization_requires_an_independent_cross_environment_contrast():
    experience = {
        "environment_class": "software_repository",
        "goal_effect": "complete long horizon coding workflow",
        "relation": "test_exit_zero_implies_state_acceptance_candidate",
        "variables": ["repository_id", "test_command", "exit_code"],
        "preconditions": ["independent_test_manifest_present", "no_hidden_test_reading"],
        "falsifier": "verifier_rejects_state_or_exit_code_mismatch",
        "evidence_hash": "sha256:run_a",
        "producer_id": "arena-agent",
        "verifier_id": "github-actions-oidc:run_a",
        "independent_verifier": True,
    }
    contrast = {
        "environment_class": "browser_web_application",
        "relation": "test_exit_zero_implies_state_acceptance_candidate",
        "verifier_id": "github-actions-oidc:run_b",
        "evidence_hash": "sha256:run_b",
        "independent_verifier": True,
    }
    result = s.distill(experience, contrast)
    assert result["decision"] == "RELATION_ADMITTED__SCOPE_BOUND"
    assert result["relation"]["generalization_license"] is True
    assert result["relation"]["single_experience_scope"] is False
    assert result["relation"]["contrast_hash"] == s.stable_hash(contrast)


def test_distillation_rejects_exact_trajectory_and_self_verification():
    bad = {
        "environment_class": "software_repository",
        "goal_effect": "complete long horizon coding workflow",
        "relation": "typed_relation",
        "variables": ["repository_id"],
        "preconditions": ["verified_manifest"],
        "falsifier": "state_mismatch",
        "evidence_hash": "sha256:run_a",
        "producer_id": "same-identity",
        "verifier_id": "same-identity",
        "independent_verifier": False,
        "action_trace": ["click", "type", "save"],
    }
    result = s.distill(bad)
    assert result["decision"].startswith(s.REFUSED_PREFIX)
    assert result["relations"] == []
    assert "FORBIDDEN_EXACT_EXPERIENCE_KEY:action_trace" in result["failed"]
    assert "VERIFIER_NOT_DISTINCT_FROM_PRODUCER" in result["failed"]
    assert "DISTINCT_VERIFIER_MISSING" in result["failed"]
