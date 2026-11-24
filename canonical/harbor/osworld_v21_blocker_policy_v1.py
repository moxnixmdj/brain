#!/usr/bin/env python3
"""Computed, zero-model OSWorld 2.1 reproducibility blocker classifier.

This module does not import a model, network client, benchmark loader, hidden
task, solution, verifier or browser controller. It receives a sanitized runner
probe and pinned-release source verification and decides whether a
reproducible OSWorld 2.1 evaluation is allowed. A negative decision is a
measured authority boundary, not a benchmark run and not a score.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

SCHEMA = "BRAIN_OSWORLD_V21_REPRODUCIBILITY_BLOCKER_POLICY_V1"
RELEASE_TAG = "osworld-v2.1"
CODE_TAG_COMMIT = "3d778a3c9a34a079316f70df023b166700445792"
MANIFEST_BASE_COMMIT = "325ab352e2ff7410854bf8e3324c391bc60e7526"
WEBSITE_TAG_COMMIT = "60c89fe6a8ed934668619d8d26132848239eb8ee"

UNVERIFIED_FRONTIERS = [
    "OSWorld 2.1 tasks and official reward vectors",
    "Any aggregate OSWorld 2.1 benchmark score",
    "Remaining SWE-bench Pro V2 / HARD-51 tasks",
    "Remaining Terminal-Bench 4.1 CPU and GPU tasks",
    "Arbitrary natural-language purpose understanding",
    "Authored repair content",
    "GUI or browser computer use",
    "Independent section 6 verification",
]


def _bool(probe: dict[str, Any], key: str) -> bool:
    return bool(probe.get(key))


def _status(probe: dict[str, Any], key: str) -> int:
    try:
        return int(probe.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _gated_conditions_accepted(probe: dict[str, Any]) -> bool:
    return _bool(probe, "hf_token_present") and _bool(probe, "gated_conditions_accepted")


def _gated_task_classes_available(probe: dict[str, Any]) -> bool:
    return (
        _gated_conditions_accepted(probe)
        and _status(probe, "hf_task_metadata_http_status") == 200
        and _bool(probe, "task_class_directory_present")
    )


def _gated_complete_assets_available(probe: dict[str, Any]) -> bool:
    return (
        _gated_conditions_accepted(probe)
        and _status(probe, "hf_asset_metadata_http_status") == 200
        and _bool(probe, "complete_asset_directory_present")
    )


def run_prerequisites(probe: dict[str, Any]) -> dict[str, bool]:
    return {
        "gated_task_classes_available": _gated_task_classes_available(probe),
        "gated_complete_assets_available": _gated_complete_assets_available(probe),
        "osworld_file_base_url_set": _bool(probe, "osworld_file_base_url_present"),
        "website_host_suffix_set": _bool(probe, "website_host_suffix_present"),
        "self_hosted_websites_deployed": _bool(probe, "websites_deployed"),
        "provider_vm_image_available": _bool(probe, "qcow2_archive_present"),
        "kvm_or_equivalent_available": _bool(probe, "kvm_device_present") or _status(probe, "kvm_cpu_flags_count") > 0,
        "desktop_display_available": _bool(probe, "display_present") or _bool(probe, "xvfb_present"),
        "pinned_evaluator_dependencies_installed": _bool(probe, "evaluator_dependencies_installed"),
        "maintainer_style_verifier_available": _bool(probe, "maintainer_verifier_present"),
        "no_hidden_test_or_raw_task_leakage": (
            not _bool(probe, "hidden_test_reading")
            and not _bool(probe, "raw_benchmark_tasks_saved_in_workspace")
            and not _bool(probe, "borrowed_outputs")
        ),
    }


def evaluate(probe: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    source_checks = dict((source.get("checks") or {}))
    source_all_true = bool(source_checks) and all(bool(v) for v in source_checks.values())
    prereqs = run_prerequisites(probe)
    blockers = sorted(k for k, v in prereqs.items() if not v)
    failed: list[str] = []
    for key, value in source_checks.items():
        if not value:
            failed.append("SOURCE_VERIFICATION_CHECK_FALSE:" + key)
    decision = "RUN_ALLOWED_SYNTHETIC_PROBE_ONLY" if source_all_true and not blockers else "BLOCKED_REPRODUCIBLE_OSWORLD_V21_EVALUATION"
    verified = []
    if source_all_true:
        verified.append("PINNED_OSWORLD_V21_RELEASE_WEBSITE_AND_TASK_HASH_MANIFEST_BYTES")
    if _bool(probe, "static_source_binding_pass"):
        verified.append("EXACT_BRAIN_OWNED_SOURCE_SHA256_BINDINGS")
    if not _bool(probe, "raw_benchmark_tasks_saved_in_workspace"):
        verified.append("NO_RAW_BENCHMARK_TASKS_SAVED_IN_WORKSPACE")
    if not _bool(probe, "hidden_test_reading") and not _bool(probe, "borrowed_outputs"):
        verified.append("NO_HIDDEN_TESTS_OR_BORROWED_OUTPUTS")
    if _status(probe, "external_network_probe_calls") >= 2:
        verified.append("GATED_DATASET_ACCESS_STATUSES_PROBED_WITHOUT_BODY_DOWNLOAD")
    if blockers:
        verified.append("RUNNER_ENVIRONMENT_BLOCKERS_CLASSIFIED_FAIL_CLOSED")
    verified.append("NO_BENCHMARK_SCORE_OR_CAPABILITY_CREDIT")
    return {
        "schema": SCHEMA,
        "release_tag": RELEASE_TAG,
        "code_tag_commit": CODE_TAG_COMMIT,
        "manifest_base_commit": MANIFEST_BASE_COMMIT,
        "website_tag_commit": WEBSITE_TAG_COMMIT,
        "decision": decision,
        "benchmark_run_allowed": decision == "RUN_ALLOWED_SYNTHETIC_PROBE_ONLY",
        "benchmark_run_attempted": False,
        "source_verification": {"checks": source_checks, "all_true": source_all_true},
        "run_prerequisites": prereqs,
        "blocked_reasons": blockers,
        "probe_sanitized": {
            "hf_token_present": _bool(probe, "hf_token_present"),
            "gated_conditions_accepted": _gated_conditions_accepted(probe),
            "hf_task_metadata_http_status": _status(probe, "hf_task_metadata_http_status"),
            "hf_asset_metadata_http_status": _status(probe, "hf_asset_metadata_http_status"),
            "task_class_directory_present": _bool(probe, "task_class_directory_present"),
            "complete_asset_directory_present": _bool(probe, "complete_asset_directory_present"),
            "qcow2_archive_present": _bool(probe, "qcow2_archive_present"),
            "kvm_device_present": _bool(probe, "kvm_device_present"),
            "kvm_cpu_flags_count": _status(probe, "kvm_cpu_flags_count"),
            "docker_present": _bool(probe, "docker_present"),
            "qemu_system_present": _bool(probe, "qemu_system_present"),
            "display_present": _bool(probe, "display_present"),
            "xvfb_present": _bool(probe, "xvfb_present"),
            "websites_deployed": _bool(probe, "websites_deployed"),
            "maintainer_verifier_present": _bool(probe, "maintainer_verifier_present"),
            "evaluator_dependencies_installed": _bool(probe, "evaluator_dependencies_installed"),
            "external_network_probe_calls": _status(probe, "external_network_probe_calls"),
            "runtime_network_calls_in_agent_cognition": 0,
        },
        "verified": verified,
        "unverified": list(UNVERIFIED_FRONTIERS),
        "failed": failed,
        "hidden_test_reading": False,
        "borrowed_outputs": False,
        "raw_benchmark_tasks_saved_in_workspace": False,
        "benchmark_score_authority": False,
        "aggregate_benchmark_score": None,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "terminal_credit_delta": 0,
        "truth": {"achieved": False, "section_6": "NOT_MET"},
        "numeric_measurements": {
            "source_verification_checks": len(source_checks),
            "source_verification_checks_true": sum(1 for v in source_checks.values() if v),
            "run_prerequisites": len(prereqs),
            "blocked_reasons": len(blockers),
            "gated_dataset_status_probes": 2,
            "external_network_probe_calls": _status(probe, "external_network_probe_calls"),
            "hard_benchmark_tasks_consumed": 0,
            "reward_vectors": 0,
            "benchmark_score_claims": 0,
            "model_calls": 0,
            "runtime_network_calls_in_agent_cognition": 0,
            "hidden_test_reading_events": 0,
            "borrowed_output_events": 0,
            "section_6_verifications": 0,
        },
        "rule": "A pinned-release blocker probe is authority only for the listed source bytes and sanitized runner facts; it is not an OSWorld task run, score, capability credit or section 6 verification.",
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
        "OSWORLD_V21_BLOCKER_DECISION_PASS",
        json.dumps(
            {
                "decision": decision["decision"],
                "benchmark_run_allowed": decision["benchmark_run_allowed"],
                "blocked_reasons": len(decision["blocked_reasons"]),
                "tasks_consumed": decision["numeric_measurements"]["hard_benchmark_tasks_consumed"],
                "score_authority": decision["benchmark_score_authority"],
                "truth": decision["truth"],
            },
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    main()
