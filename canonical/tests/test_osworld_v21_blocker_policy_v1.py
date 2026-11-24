#!/usr/bin/env python3
"""Contract tests for the zero-model OSWorld 2.1 blocker classifier."""
from __future__ import annotations

import ast
import json
import pathlib
import sys

from canonical.harbor import osworld_v21_blocker_policy_v1 as policy

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _source() -> dict:
    return {
        "schema": "BRAIN_OSWORLD_V21_SOURCE_VERIFICATION_V1",
        "checks": {
            "release_tag": True,
            "code_tag_commit": True,
            "website_tag_commit": True,
            "manifest_sha256": True,
            "task_hash_manifest_sha256": True,
            "public_task_id_count": True,
            "gated_repositories_declared": True,
            "no_full_agent_evaluation_in_release_notes": True,
            "no_hosted_website_deployment_in_release_notes": True,
            "no_raw_task_files_in_workspace": True,
        },
    }


def _blocked_probe() -> dict:
    return {
        "hf_token_present": False,
        "gated_conditions_accepted": False,
        "hf_task_metadata_http_status": 401,
        "hf_asset_metadata_http_status": 403,
        "task_class_directory_present": False,
        "complete_asset_directory_present": False,
        "osworld_file_base_url_present": False,
        "website_host_suffix_present": False,
        "gitlab_credentials_present": False,
        "aws_credentials_present": False,
        "websites_deployed": False,
        "qcow2_archive_present": False,
        "kvm_device_present": False,
        "kvm_cpu_flags_count": 0,
        "docker_present": True,
        "qemu_system_present": False,
        "display_present": False,
        "xvfb_present": False,
        "maintainer_verifier_present": False,
        "evaluator_dependencies_installed": False,
        "hidden_test_reading": False,
        "raw_benchmark_tasks_saved_in_workspace": False,
        "borrowed_outputs": False,
        "static_source_binding_pass": True,
        "external_network_probe_calls": 2,
    }


def _allowed_probe() -> dict:
    probe = _blocked_probe()
    probe.update(
        {
            "hf_token_present": True,
            "gated_conditions_accepted": True,
            "hf_task_metadata_http_status": 200,
            "hf_asset_metadata_http_status": 200,
            "task_class_directory_present": True,
            "complete_asset_directory_present": True,
            "osworld_file_base_url_present": True,
            "website_host_suffix_present": True,
            "websites_deployed": True,
            "qcow2_archive_present": True,
            "kvm_device_present": True,
            "kvm_cpu_flags_count": 2,
            "display_present": True,
            "xvfb_present": True,
            "maintainer_verifier_present": True,
            "evaluator_dependencies_installed": True,
        }
    )
    return probe


def test_realistic_blocked_probe_fails_closed() -> None:
    decision = policy.evaluate(_blocked_probe(), _source())
    assert decision["schema"] == "BRAIN_OSWORLD_V21_REPRODUCIBILITY_BLOCKER_POLICY_V1"
    assert decision["decision"] == "BLOCKED_REPRODUCIBLE_OSWORLD_V21_EVALUATION"
    assert decision["benchmark_run_allowed"] is False
    assert decision["benchmark_run_attempted"] is False
    for key in (
        "gated_task_classes_available",
        "gated_complete_assets_available",
        "osworld_file_base_url_set",
        "website_host_suffix_set",
        "self_hosted_websites_deployed",
        "provider_vm_image_available",
        "kvm_or_equivalent_available",
        "desktop_display_available",
        "pinned_evaluator_dependencies_installed",
        "maintainer_style_verifier_available",
    ):
        assert key in decision["blocked_reasons"]
    assert decision["benchmark_score_authority"] is False
    assert decision["aggregate_benchmark_score"] is None
    assert decision["numeric_measurements"]["hard_benchmark_tasks_consumed"] == 0
    assert decision["numeric_measurements"]["reward_vectors"] == 0
    assert decision["truth"] == {"achieved": False, "section_6": "NOT_MET"}


def test_synthetic_all_prerequisites_run_allowed_but_not_authority() -> None:
    decision = policy.evaluate(_allowed_probe(), _source())
    assert decision["decision"] == "RUN_ALLOWED_SYNTHETIC_PROBE_ONLY"
    assert decision["benchmark_run_allowed"] is True
    assert decision["blocked_reasons"] == []
    assert decision["benchmark_run_attempted"] is False
    assert decision["benchmark_score_authority"] is False
    assert decision["aggregate_benchmark_score"] is None
    assert decision["numeric_measurements"]["hard_benchmark_tasks_consumed"] == 0
    assert decision["capability_credit_delta"] == 0
    assert decision["family_credit_delta"] == 0
    assert decision["terminal_credit_delta"] == 0


def test_source_verification_failure_fails_closed() -> None:
    source = _source()
    source["checks"]["manifest_sha256"] = False
    decision = policy.evaluate(_allowed_probe(), source)
    assert decision["decision"] == "BLOCKED_REPRODUCIBLE_OSWORLD_V21_EVALUATION"
    assert decision["source_verification"]["all_true"] is False
    assert "SOURCE_VERIFICATION_CHECK_FALSE:manifest_sha256" in decision["failed"]


def test_non_numeric_gated_status_fails_closed() -> None:
    probe = _allowed_probe()
    probe["hf_task_metadata_http_status"] = "forbidden"
    decision = policy.evaluate(probe, _source())
    assert decision["decision"] == "BLOCKED_REPRODUCIBLE_OSWORLD_V21_EVALUATION"
    assert "gated_task_classes_available" in decision["blocked_reasons"]
    assert decision["probe_sanitized"]["hf_task_metadata_http_status"] == 0


def test_decision_does_not_echo_arbitrary_probe_payload() -> None:
    probe = _blocked_probe()
    probe["raw_payload"] = "synthetic-secret"
    decision = policy.evaluate(probe, _source())
    assert "synthetic-secret" not in json.dumps(decision, sort_keys=True)
    assert "raw_payload" not in decision["probe_sanitized"]


def test_policy_source_has_no_model_network_or_hidden_task_readers() -> None:
    path = ROOT / "canonical/harbor/osworld_v21_blocker_policy_v1.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    forbidden = {"urllib", "requests", "httpx", "socket", "http", "openai", "anthropic", "litellm", "transformers", "torch", "tensorflow", "boto3", "subprocess", "huggingface_hub"}
    assert not (roots & forbidden), sorted(roots & forbidden)
    lowered = source.casefold()
    assert "task_001.py" not in lowered
    assert "instruction.md" not in lowered
    assert "gold_patch.diff" not in lowered
    assert "test_patch.patch" not in lowered


def test_cli_writes_sanitized_decision(tmp_path: pathlib.Path) -> None:
    probe_path = tmp_path / "probe.json"
    source_path = tmp_path / "source.json"
    out_path = tmp_path / "decision.json"
    probe_path.write_text(json.dumps(_blocked_probe()), encoding="utf-8")
    source_path.write_text(json.dumps(_source()), encoding="utf-8")
    old_argv = sys.argv
    try:
        sys.argv = [
            "osworld_v21_blocker_policy_v1.py",
            "--probe", str(probe_path),
            "--source", str(source_path),
            "--out", str(out_path),
        ]
        policy.main()
    finally:
        sys.argv = old_argv
    decision = json.loads(out_path.read_text(encoding="utf-8"))
    assert decision["decision"] == "BLOCKED_REPRODUCIBLE_OSWORLD_V21_EVALUATION"
    assert decision["numeric_measurements"]["hard_benchmark_tasks_consumed"] == 0
    assert decision["benchmark_score_authority"] is False
