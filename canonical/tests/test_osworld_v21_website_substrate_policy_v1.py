#!/usr/bin/env python3
"""Contract tests for the zero-model OSWorld 2.1 website-substrate classifier."""
from __future__ import annotations

import ast
import json
import pathlib
import sys

from canonical.harbor import osworld_v21_website_substrate_policy_v1 as policy

ROOT = pathlib.Path(__file__).resolve().parents[2]
WEBSITE_TAG_COMMIT = "60c89fe6a8ed934668619d8d26132848239eb8ee"


def _source() -> dict:
    return {
        "schema": "BRAIN_OSWORLD_V21_WEBSITE_SUBSTRATE_SOURCE_VERIFICATION_V1",
        "website_tag_commit": WEBSITE_TAG_COMMIT,
        "gitlink_pin_count": 25,
        "runtime_compose_include_count": 24,
        "web_compose_hash_count": 24,
        "checks": {
            "website_tag_commit": True,
            "gitlink_pin_count": True,
            "gitlink_bytes_exact": True,
            "runtime_compose_include_count": True,
            "basesite_excluded_from_runtime_compose": True,
            "root_compose_bytes_exact": True,
            "web_compose_bytes_exact": True,
            "no_nested_compose_includes": True,
            "no_gated_body_download_literals": True,
            "no_raw_task_files_in_workspace": True,
            "public_website_source_only": True,
        },
    }


def _probe() -> dict:
    return {
        "website_tag_commit": WEBSITE_TAG_COMMIT,
        "static_source_binding_pass": True,
        "source_verification_all_true": True,
        "compose_config_command_is_config_only": True,
        "compose_config_exit_code": 0,
        "compose_config_json_parsed": True,
        "compose_service_count": 40,
        "compose_service_names": ["caddy", "careerlink_web"],
        "public_github_api_calls": 24,
        "gated_dataset_status_probes": 0,
        "external_network_probe_calls": 0,
        "image_pulls": 0,
        "container_starts": 0,
        "docker_build_calls": 0,
        "website_http_responses": 0,
        "self_hosted_websites_deployed": False,
        "raw_gated_bodies_downloaded": False,
        "hidden_test_reading": False,
        "raw_benchmark_tasks_saved_in_workspace": False,
        "borrowed_outputs": False,
        "benchmark_run_attempted": False,
        "benchmark_score_authority": False,
        "model_calls": 0,
        "runtime_network_calls_in_agent_cognition": 0,
    }


def test_config_verified_probe_still_blocks_benchmark_run() -> None:
    decision = policy.evaluate(_probe(), _source())
    assert decision["schema"] == "BRAIN_OSWORLD_V21_WEBSITE_SUBSTRATE_POLICY_V1"
    assert decision["decision"] == policy.CONFIG_VERIFIED_DECISION
    assert decision["website_substrate_config_verified"] is True
    assert decision["website_substrate_deployment_allowed"] is False
    assert decision["website_substrate_deployment_attempted"] is False
    assert decision["benchmark_run_allowed"] is False
    assert decision["benchmark_run_attempted"] is False
    assert decision["benchmark_score_authority"] is False
    assert decision["aggregate_benchmark_score"] is None
    assert decision["truth"] == {"achieved": False, "section_6": "NOT_MET"}
    assert decision["numeric_measurements"]["hard_benchmark_tasks_consumed"] == 0
    assert decision["numeric_measurements"]["section_6_verifications"] == 0
    assert len(decision["blocked_reasons"]) == 9


def test_source_check_failure_fails_closed() -> None:
    source = _source()
    source["checks"]["web_compose_bytes_exact"] = False
    decision = policy.evaluate(_probe(), source)
    assert decision["decision"] == policy.BLOCKED_DECISION
    assert decision["website_substrate_config_verified"] is False
    assert "CHECK_FALSE:web_compose_bytes_exact" in decision["failed"]
    assert decision["source_verification"]["all_true"] is False


def test_nonzero_compose_config_exit_fails_closed() -> None:
    probe = _probe()
    probe["compose_config_exit_code"] = 2
    decision = policy.evaluate(probe, _source())
    assert decision["decision"] == policy.BLOCKED_DECISION
    assert "CHECK_FALSE:compose_config_exit_code_zero" in decision["failed"]


def test_container_or_image_activity_fails_closed() -> None:
    for key in ("image_pulls", "container_starts", "docker_build_calls", "website_http_responses"):
        probe = _probe()
        probe[key] = 1
        decision = policy.evaluate(probe, _source())
        assert decision["decision"] == policy.BLOCKED_DECISION, key


def test_deployment_or_benchmark_claim_fails_closed() -> None:
    for key in ("self_hosted_websites_deployed", "raw_gated_bodies_downloaded", "benchmark_run_attempted", "benchmark_score_authority"):
        probe = _probe()
        probe[key] = True
        decision = policy.evaluate(probe, _source())
        assert decision["decision"] == policy.BLOCKED_DECISION, key
        assert len(decision["failed"]) >= 1


def test_wrong_website_tag_fails_closed() -> None:
    probe = _probe()
    probe["website_tag_commit"] = "0" * 40
    decision = policy.evaluate(probe, _source())
    assert decision["decision"] == policy.BLOCKED_DECISION
    assert "CHECK_FALSE:exact_website_tag_commit" in decision["failed"]


def test_decision_does_not_echo_arbitrary_probe_payload() -> None:
    probe = _probe()
    probe["raw_payload"] = "synthetic-secret"
    decision = policy.evaluate(probe, _source())
    assert "synthetic-secret" not in json.dumps(decision, sort_keys=True)
    assert "raw_payload" not in decision["probe_sanitized"]


def test_policy_source_has_no_model_network_or_container_runtime_imports() -> None:
    path = ROOT / "canonical/harbor/osworld_v21_website_substrate_policy_v1.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
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
    lowered = source.casefold()
    assert "task_001.py" not in lowered
    assert "instruction.md" not in lowered
    assert "gold_patch.diff" not in lowered
    assert "test_patch.patch" not in lowered
    assert "benchmark_score_authority" in source
    assert "model_calls" in source


def test_cli_writes_sanitized_decision(tmp_path: pathlib.Path) -> None:
    probe_path = tmp_path / "probe.json"
    source_path = tmp_path / "source.json"
    out_path = tmp_path / "decision.json"
    probe_path.write_text(json.dumps(_probe()), encoding="utf-8")
    source_path.write_text(json.dumps(_source()), encoding="utf-8")
    old_argv = sys.argv
    try:
        sys.argv = [
            "osworld_v21_website_substrate_policy_v1.py",
            "--probe", str(probe_path),
            "--source", str(source_path),
            "--out", str(out_path),
        ]
        policy.main()
    finally:
        sys.argv = old_argv
    decision = json.loads(out_path.read_text(encoding="utf-8"))
    assert decision["decision"] == policy.CONFIG_VERIFIED_DECISION
    assert decision["benchmark_run_allowed"] is False
    assert decision["website_substrate_deployment_attempted"] is False
    assert decision["numeric_measurements"]["reward_vectors"] == 0
    assert decision["benchmark_score_authority"] is False
