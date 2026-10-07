#!/usr/bin/env python3
"""Fail-closed validator for the public GDPval-AA v2.1 task-submission contract.

Validates only publicly disclosed Artificial Analysis/Stirrup submission facts.
A PASS is not owner pairwise reproduction, GDPval-AA closure, or terminal credit.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import PurePosixPath
from typing import Any

PROTOCOL = "GDPVAL_AA_V21_PUBLIC_SUBMISSION_CONTRACT_V1"
MAX_TURNS = 250
CONTEXT_SUMMARIZATION_CUTOFF = 0.70
WORKING_DIR = "/home/user"
SANDBOX_KIND = "E2B"
USER_UID = 1000
COMMAND_TIMEOUT_SECONDS = 600
REQUIRED_TOOL_NAMES = frozenset(
    {"fetch_web_page", "web_search", "code_exec", "finish", "abandon_task_finish"}
)
VISION_TOOL_NAME = "view_image"
PUBLIC_STIRRUP_BINDING = {
    "repository": "ArtificialAnalysis/Stirrup",
    "commit": "247f24d56b2108235880ed2a2baea5d35b5a67ee",
    "blobs": {
        "finish.py": "d4f48ffec2295d1ae0600d27ebb050abbbb382ca",
        "web.py": "2544b541ec2db173038753d0af2249eca089468a",
        "view_image.py": "85698cfdc02106c5d4533f891137186e093b5bd6",
        "code_backends/base.py": "a829d7296c5fae6db1db08ed66faed0d47baf111",
        "code_backends/e2b.py": "1cebb2f71dc8c845d20416acc77242b93d1129bd",
        "core/agent.py": "7446c8ee00d49e81dd621d9f9cc6507900964903",
        "constants.py": "03a8579aa42454c4f6f36d075c9cc894f1f2719a",
        "prompts/message_summarizer.txt": "04a3667dd366da0253f9d5ea2062660551b91ce2",
        "prompts/message_summarizer_bridge.txt": "7eaf68ae5d6efa0f5e3f4fe02634ce366efcb193",
    },
}

def _bool(obj: dict[str, Any], key: str, errors: list[str], expected: bool) -> None:
    if obj.get(key) is not expected:
        errors.append(f"{key}: expected {expected!r}, got {obj.get(key)!r}")

def _number(obj: dict[str, Any], key: str, errors: list[str], expected: float) -> None:
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) != float(expected):
        errors.append(f"{key}: expected {expected!r}, got {value!r}")

def _absolute_file_path(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    p = PurePosixPath(value)
    return p.is_absolute() and p.name not in {"", ".", ".."} and ".." not in p.parts

def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if manifest.get("protocol") != PROTOCOL:
        errors.append(f"protocol: expected {PROTOCOL!r}")
    task_id = manifest.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        errors.append("task_id: non-empty string required")
    turns_used = manifest.get("turns_used")
    if isinstance(turns_used, bool) or not isinstance(turns_used, int) or not 0 <= turns_used <= MAX_TURNS:
        errors.append(f"turns_used: integer in [0,{MAX_TURNS}] required")
    _number(manifest, "max_turns", errors, MAX_TURNS)
    _number(manifest, "context_summarization_cutoff", errors, CONTEXT_SUMMARIZATION_CUTOFF)
    _bool(manifest, "user_interaction_allowed", errors, False)

    sandbox = manifest.get("sandbox")
    if not isinstance(sandbox, dict):
        errors.append("sandbox: object required")
    else:
        if sandbox.get("kind") != SANDBOX_KIND:
            errors.append(f"sandbox.kind: expected {SANDBOX_KIND!r}")
        if sandbox.get("working_dir") != WORKING_DIR:
            errors.append(f"sandbox.working_dir: expected {WORKING_DIR!r}")
        _number(sandbox, "user_uid", errors, USER_UID)
        _number(sandbox, "command_timeout_seconds", errors, COMMAND_TIMEOUT_SECONDS)
        _bool(sandbox, "fresh_per_task", errors, True)
        _bool(sandbox, "shell_state_persists_between_calls", errors, False)

    tools = manifest.get("tools")
    if not isinstance(tools, list) or not all(isinstance(x, str) for x in tools):
        errors.append("tools: list[str] required")
        tool_set: set[str] = set()
    else:
        tool_set = set(tools)
        missing = sorted(REQUIRED_TOOL_NAMES - tool_set)
        if missing:
            errors.append(f"tools: missing required public-contract tools {missing}")
    vision_supported = manifest.get("vision_supported")
    if not isinstance(vision_supported, bool):
        errors.append("vision_supported: bool required")
    elif vision_supported and VISION_TOOL_NAME not in tool_set:
        errors.append("tools: view_image required when vision_supported=true")

    refs = manifest.get("reference_files", [])
    if not isinstance(refs, list) or not all(_absolute_file_path(x) for x in refs):
        errors.append("reference_files: every entry must be an absolute POSIX file path")
    _bool(manifest, "task_description_injected", errors, True)
    _bool(manifest, "remaining_turn_budget_warned_near_limit", errors, True)
    _bool(manifest, "context_compaction_enabled", errors, True)
    _bool(manifest, "task_prompt_retained_across_compaction", errors, True)

    completion = manifest.get("completion")
    if not isinstance(completion, dict):
        errors.append("completion: object required")
    else:
        tool = completion.get("tool")
        if tool not in {"finish", "abandon_task_finish"}:
            errors.append("completion.tool: finish or abandon_task_finish required")
        if completion.get("is_final_action") is not True:
            errors.append("completion.is_final_action: must be true")
        reason = completion.get("summary_or_reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append("completion.summary_or_reason: non-empty string required")
        paths = completion.get("paths", [])
        if tool == "finish":
            if not isinstance(paths, list) or not paths:
                errors.append("completion.paths: non-empty list required for finish")
            elif not all(_absolute_file_path(x) for x in paths):
                errors.append("completion.paths: all finish paths must be absolute POSIX file paths")
            elif len(paths) != len(set(paths)):
                errors.append("completion.paths: duplicate path")
        elif paths not in ([], None):
            warnings.append("completion.paths ignored for abandon_task_finish")

    if isinstance(completion, dict) and completion.get("tool") == "finish":
        if manifest.get("finish_path_existence_verified") is not True:
            errors.append("finish_path_existence_verified: true required for finish certification")

    passed = not errors
    return {
        "schema": "GDPVAL_AA_V21_PUBLIC_SUBMISSION_CONTRACT_VALIDATION_V1",
        "status": "PASS" if passed else "FAIL_CLOSED",
        "public_submission_contract_pass": passed,
        "exact_owner_evaluation_reproduced": False,
        "errors": errors,
        "warnings": warnings,
        "stirrup_binding": PUBLIC_STIRRUP_BINDING,
        "hard_nonclaims": [
            "This validator does not reproduce the owner pairwise judge prompt.",
            "This validator does not reproduce realized judge assignments or the owner comparison graph.",
            "This validator does not produce Crowd-BT ratings.",
            "A PASS is not GDPval-AA closure and is not terminal credit.",
        ],
    }

def _valid_example() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "task_id": "example",
        "turns_used": 7,
        "max_turns": 250,
        "context_summarization_cutoff": 0.70,
        "user_interaction_allowed": False,
        "sandbox": {
            "kind": "E2B", "working_dir": "/home/user", "user_uid": 1000,
            "command_timeout_seconds": 600, "fresh_per_task": True,
            "shell_state_persists_between_calls": False,
        },
        "tools": ["fetch_web_page","web_search","view_image","code_exec","finish","abandon_task_finish"],
        "vision_supported": True,
        "reference_files": ["/home/user/input.xlsx"],
        "task_description_injected": True,
        "remaining_turn_budget_warned_near_limit": True,
        "context_compaction_enabled": True,
        "task_prompt_retained_across_compaction": True,
        "completion": {
            "tool": "finish", "is_final_action": True,
            "summary_or_reason": "Completed the requested work.",
            "paths": ["/home/user/output.xlsx"],
        },
        "finish_path_existence_verified": True,
    }

def self_test() -> dict[str, Any]:
    good = validate_manifest(_valid_example())
    bad = _valid_example()
    bad["max_turns"] = 251
    bad["completion"] = {
        "tool": "finish", "is_final_action": False,
        "summary_or_reason": "", "paths": ["relative.xlsx"],
    }
    bad["finish_path_existence_verified"] = False
    bad_result = validate_manifest(bad)
    passed = (
        good["status"] == "PASS"
        and good["exact_owner_evaluation_reproduced"] is False
        and bad_result["status"] == "FAIL_CLOSED"
        and len(bad_result["errors"]) >= 4
    )
    return {
        "schema": "GDPVAL_AA_V21_PUBLIC_SUBMISSION_CONTRACT_SELF_TEST_V1",
        "status": "PASS" if passed else "FAIL",
        "valid_case": good,
        "invalid_case": bad_result,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", help="Path to JSON session manifest")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = self_test()
    else:
        if not args.manifest:
            parser.error("manifest is required unless --self-test is used")
        with open(args.manifest, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            raise SystemExit("manifest root must be a JSON object")
        result = validate_manifest(payload)
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
