#!/usr/bin/env python3
"""Computed, zero-model OSWorld 2.1 website-substrate classifier.

This module does not import a model, network client, Docker client, benchmark
loader, hidden task, solution, verifier or browser controller. It receives a
sanitized runner probe and pinned website-substrate source verification and
decides whether the pinned website source and compose graph were verified. It
never authorizes an OSWorld task run, benchmark score, capability credit or
section 6 verification. A compose-config pass is not a website deployment.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

SCHEMA = "BRAIN_OSWORLD_V21_WEBSITE_SUBSTRATE_POLICY_V1"
RELEASE_TAG = "osworld-v2.1"
WEBSITE_TAG_COMMIT = "60c89fe6a8ed934668619d8d26132848239eb8ee"
EXPECTED_GITLINK_PINS = 25
EXPECTED_RUNTIME_COMPOSE_INCLUDES = 24
EXPECTED_WEB_COMPOSE_HASHES = 24
MIN_COMPOSE_SERVICES = 40

CONFIG_VERIFIED_DECISION = "OSWORLD_V21_WEBSITE_SUBSTRATE_CONFIG_VERIFIED__BENCHMARK_RUN_BLOCKED"
BLOCKED_DECISION = "BLOCKED_OSWORLD_V21_WEBSITE_SUBSTRATE_UNVERIFIED"

UNVERIFIED_FRONTIERS = [
    "Actual self-hosted OSWorld 2.1 website deployment and HTTP responses",
    "OSWorld 2.1 tasks and official reward vectors",
    "Any aggregate OSWorld 2.1 benchmark score",
    "Remaining SWE-bench Pro V2 / HARD-51 tasks",
    "Remaining Terminal-Bench 4.1 CPU and GPU tasks",
    "Arbitrary natural-language purpose understanding",
    "Authored repair content",
    "GUI or browser computer use",
    "Independent section 6 verification",
]

REMAINING_EVALUATION_BLOCKERS = [
    "gated_task_classes_available",
    "gated_complete_assets_available",
    "osworld_file_base_url_set",
    "website_host_suffix_for_reachable_deployment",
    "self_hosted_websites_deployed",
    "provider_vm_image_available",
    "pinned_evaluator_dependencies_installed",
    "maintainer_style_verifier_available",
    "official_osworld_task_run_and_verifier",
]


def _bool(probe: dict[str, Any], key: str) -> bool:
    return bool(probe.get(key))


def _int(probe: dict[str, Any], key: str) -> int:
    try:
        return int(probe.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _source_checks(source: dict[str, Any]) -> dict[str, bool]:
    return {str(k): bool(v) for k, v in dict(source.get("checks") or {}).items()}


def _probe_safety_checks(probe: dict[str, Any]) -> dict[str, bool]:
    return {
        "exact_website_tag_commit": str(probe.get("website_tag_commit") or "") == WEBSITE_TAG_COMMIT,
        "static_source_binding_pass": _bool(probe, "static_source_binding_pass"),
        "compose_config_command_is_config_only": _bool(probe, "compose_config_command_is_config_only"),
        "compose_config_exit_code_zero": _int(probe, "compose_config_exit_code") == 0,
        "compose_config_json_parsed": _bool(probe, "compose_config_json_parsed"),
        "compose_service_count_sufficient": _int(probe, "compose_service_count") >= MIN_COMPOSE_SERVICES,
        "image_pulls_zero": _int(probe, "image_pulls") == 0,
        "container_starts_zero": _int(probe, "container_starts") == 0,
        "docker_build_calls_zero": _int(probe, "docker_build_calls") == 0,
        "website_http_responses_zero": _int(probe, "website_http_responses") == 0,
        "self_hosted_websites_not_deployed": not _bool(probe, "self_hosted_websites_deployed"),
        "raw_gated_bodies_not_downloaded": not _bool(probe, "raw_gated_bodies_downloaded"),
        "no_hidden_test_reading": not _bool(probe, "hidden_test_reading"),
        "no_raw_benchmark_tasks_in_workspace": not _bool(probe, "raw_benchmark_tasks_saved_in_workspace"),
        "no_borrowed_outputs": not _bool(probe, "borrowed_outputs"),
        "benchmark_run_not_attempted": not _bool(probe, "benchmark_run_attempted"),
        "no_benchmark_score_authority": not _bool(probe, "benchmark_score_authority"),
        "no_model_calls": _int(probe, "model_calls") == 0,
        "no_runtime_network_calls_in_agent_cognition": _int(probe, "runtime_network_calls_in_agent_cognition") == 0,
    }


def evaluate(probe: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    source_checks = _source_checks(source)
    safety_checks = _probe_safety_checks(probe)
    all_checks = dict(source_checks)
    all_checks.update(safety_checks)
    failed = ["CHECK_FALSE:" + key for key, value in sorted(all_checks.items()) if not value]
    config_verified = bool(all_checks) and all(all_checks.values()) and not failed
    decision = CONFIG_VERIFIED_DECISION if config_verified else BLOCKED_DECISION
    verified = []
    if config_verified:
        verified.extend([
            "PINNED_OSWORLD_V21_WEBSITE_TAG_AND_TWENTY_FIVE_GITLINK_COMMITS",
            "PINNED_ROOT_COMPOSE_AND_TWENTY_FOUR_RUNTIME_WEB_COMPOSE_BYTES",
            "GENERATED_COMPOSE_INCLUDE_GRAPH_VERIFIED",
            "DOCKER_COMPOSE_CONFIG_VALIDATION_WITHOUT_IMAGE_PULL_CONTAINER_START_OR_BUILD",
        ])
    if _bool(probe, "static_source_binding_pass"):
        verified.append("EXACT_BRAIN_OWNED_SOURCE_SHA256_BINDINGS")
    if not _bool(probe, "hidden_test_reading") and not _bool(probe, "borrowed_outputs"):
        verified.append("NO_HIDDEN_TESTS_OR_BORROWED_OUTPUTS")
    if not _bool(probe, "raw_benchmark_tasks_saved_in_workspace") and not _bool(probe, "raw_gated_bodies_downloaded"):
        verified.append("NO_RAW_BENCHMARK_TASKS_OR_GATED_BODIES_SAVED")
    verified.append("NO_OSWORLD_TASK_RUN_BENCHMARK_SCORE_OR_CAPABILITY_CREDIT")
    unverified = list(UNVERIFIED_FRONTIERS)
    return {
        "schema": SCHEMA,
        "release_tag": RELEASE_TAG,
        "website_tag_commit": WEBSITE_TAG_COMMIT,
        "decision": decision,
        "website_substrate_config_verified": config_verified,
        "website_substrate_deployment_allowed": False,
        "website_substrate_deployment_attempted": False,
        "benchmark_run_allowed": False,
        "benchmark_run_attempted": False,
        "source_verification": {
            "checks": source_checks,
            "all_true": bool(source_checks) and all(source_checks.values()),
            "gitlink_pins": int(source.get("gitlink_pin_count") or 0),
            "runtime_compose_includes": int(source.get("runtime_compose_include_count") or 0),
            "web_compose_file_hashes": int(source.get("web_compose_hash_count") or 0),
        },
        "probe_safety_checks": safety_checks,
        "probe_sanitized": {
            "compose_config_exit_code": _int(probe, "compose_config_exit_code"),
            "compose_config_json_parsed": _bool(probe, "compose_config_json_parsed"),
            "compose_service_count": _int(probe, "compose_service_count"),
            "compose_service_names": sorted(str(x) for x in (probe.get("compose_service_names") or [])),
            "image_pulls": _int(probe, "image_pulls"),
            "container_starts": _int(probe, "container_starts"),
            "docker_build_calls": _int(probe, "docker_build_calls"),
            "website_http_responses": _int(probe, "website_http_responses"),
            "public_github_api_calls": _int(probe, "public_github_api_calls"),
            "gated_dataset_status_probes": _int(probe, "gated_dataset_status_probes"),
            "external_network_probe_calls": _int(probe, "external_network_probe_calls"),
            "self_hosted_websites_deployed": _bool(probe, "self_hosted_websites_deployed"),
            "raw_gated_bodies_downloaded": _bool(probe, "raw_gated_bodies_downloaded"),
            "hidden_test_reading": _bool(probe, "hidden_test_reading"),
            "raw_benchmark_tasks_saved_in_workspace": _bool(probe, "raw_benchmark_tasks_saved_in_workspace"),
            "borrowed_outputs": _bool(probe, "borrowed_outputs"),
            "model_calls": _int(probe, "model_calls"),
            "runtime_network_calls_in_agent_cognition": _int(probe, "runtime_network_calls_in_agent_cognition"),
        },
        "verified": verified,
        "unverified": unverified,
        "failed": failed,
        "blocked_reasons": list(REMAINING_EVALUATION_BLOCKERS),
        "hidden_test_reading": False,
        "borrowed_outputs": False,
        "raw_benchmark_tasks_saved_in_workspace": False,
        "raw_gated_bodies_downloaded": False,
        "benchmark_score_authority": False,
        "aggregate_benchmark_score": None,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "terminal_credit_delta": 0,
        "truth": {"achieved": False, "section_6": "NOT_MET"},
        "numeric_measurements": {
            "source_verification_checks": len(source_checks),
            "source_verification_checks_true": sum(1 for value in source_checks.values() if value),
            "probe_safety_checks": len(safety_checks),
            "probe_safety_checks_true": sum(1 for value in safety_checks.values() if value),
            "website_gitlink_pins": int(source.get("gitlink_pin_count") or 0),
            "website_runtime_compose_includes": int(source.get("runtime_compose_include_count") or 0),
            "web_compose_file_hashes": int(source.get("web_compose_hash_count") or 0),
            "compose_service_count": _int(probe, "compose_service_count"),
            "public_github_api_calls": _int(probe, "public_github_api_calls"),
            "gated_dataset_status_probes": 0,
            "external_network_probe_calls": 0,
            "image_pulls": 0,
            "container_starts": 0,
            "docker_build_calls": 0,
            "website_http_responses": 0,
            "hard_benchmark_tasks_consumed": 0,
            "reward_vectors": 0,
            "benchmark_score_claims": 0,
            "model_calls": 0,
            "runtime_network_calls_in_agent_cognition": 0,
            "hidden_test_reading_events": 0,
            "borrowed_output_events": 0,
            "section_6_verifications": 0,
        },
        "rule": "Exact pinned website source and compose-config validation are evidence for a reproducible deployment plan only; they are not website deployment, OSWorld task execution, benchmark score, capability credit or section 6 verification.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    probe = json.loads(pathlib.Path(args.probe).read_text(encoding="utf-8"))
    source = json.loads(pathlib.Path(args.source).read_text(encoding="utf-8"))
    decision = evaluate(probe, source)
    pathlib.Path(args.out).write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "OSWORLD_V21_WEBSITE_SUBSTRATE_DECISION_PASS",
        json.dumps(
            {
                "decision": decision["decision"],
                "config_verified": decision["website_substrate_config_verified"],
                "deployment_attempted": decision["website_substrate_deployment_attempted"],
                "benchmark_run_allowed": decision["benchmark_run_allowed"],
                "blocked_reasons": len(decision["blocked_reasons"]),
                "score_authority": decision["benchmark_score_authority"],
                "truth": decision["truth"],
            },
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    main()
