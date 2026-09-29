#!/usr/bin/env python3
"""Fail-closed execution interlock for Project Brain.

This module turns the canonical active-goal hierarchy into an executable
admission boundary. A runnable task must be content-bound to the exact current
hierarchy and every runtime adapter/action must be explicitly allowlisted.

Unknown, stale, missing, or broadened authority is denied.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import urllib.parse
from typing import Any

HIERARCHY_REL = pathlib.PurePosixPath("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json")
POLICY_SCHEMA = "PROJECT_BRAIN_ANTIDRIFT_EXECUTION_INTERLOCK_V2"
BINDING_SCHEMA = "PROJECT_BRAIN_ANTIDRIFT_TASK_BINDING_V2"
ENV_BINDING = "PROJECT_BRAIN_ANTIDRIFT_BINDING_JSON"
ENV_REQUIRED = "PROJECT_BRAIN_ANTIDRIFT_REQUIRED"

_PATH_ARG_KEYS = {
    "path", "prefix", "output_path", "audit_path", "source_root", "yaml_path",
    "evidence_path", "mission_path", "input_path", "artifact_path",
}
_URL_ARG_KEYS = {"url", "source_url", "metadata_url"}
_CAPABILITY_ACTIONS = {
    "invoke_capability", "invoke_capability_by_runtime_value",
    "invoke_capability_fanout", "invoke_capability_fallback",
    "invoke_capability_until",
}


class DriftDenied(RuntimeError):
    pass


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DriftDenied("ANTIDRIFT_JSON_OBJECT_REQUIRED")
    return value


def _hierarchy_path(root: pathlib.Path) -> pathlib.Path:
    return root.resolve() / HIERARCHY_REL


def _load_hierarchy(root: pathlib.Path) -> tuple[dict[str, Any], str]:
    path = _hierarchy_path(root)
    if not path.is_file():
        raise DriftDenied("ANTIDRIFT_HIERARCHY_MISSING")
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise DriftDenied("ANTIDRIFT_HIERARCHY_INVALID")
    policy = value.get("antidrift_interlock")
    if not isinstance(policy, dict):
        raise DriftDenied("ANTIDRIFT_POLICY_MISSING")
    if policy.get("schema") != POLICY_SCHEMA:
        raise DriftDenied("ANTIDRIFT_POLICY_SCHEMA_INVALID")
    if policy.get("mode") != "FAIL_CLOSED":
        raise DriftDenied("ANTIDRIFT_NOT_FAIL_CLOSED")
    if policy.get("deny_unknown_authority") is not True:
        raise DriftDenied("ANTIDRIFT_UNKNOWN_AUTHORITY_NOT_DENIED")
    return value, _sha_bytes(raw)


def _require_string(value: Any, code: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise DriftDenied(code)
    return text


def _require_string_list(value: Any, code: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise DriftDenied(code)
    out = [x.strip() for x in value]
    if len(set(out)) != len(out):
        raise DriftDenied(code + "_DUPLICATE")
    if any(x == "*" for x in out):
        raise DriftDenied(code + "_WILDCARD_FORBIDDEN")
    return out


def _binding_fields(hierarchy: dict[str, Any]) -> dict[str, str]:
    return {
        "active_capability_target": _require_string(
            hierarchy.get("active_capability_target"), "ANTIDRIFT_ACTIVE_CAPABILITY_MISSING"
        ),
        "current_parent_blocker": _require_string(
            hierarchy.get("current_parent_blocker"), "ANTIDRIFT_PARENT_BLOCKER_MISSING"
        ),
        "next_required_action_class": _require_string(
            hierarchy.get("next_required_action_class"), "ANTIDRIFT_ACTION_CLASS_MISSING"
        ),
        "active_probe": _require_string(
            hierarchy.get("active_probe"), "ANTIDRIFT_ACTIVE_PROBE_MISSING"
        ),
    }


def validate_binding(root: pathlib.Path, binding: dict[str, Any]) -> dict[str, Any]:
    hierarchy, hierarchy_sha = _load_hierarchy(root)
    if not isinstance(binding, dict) or binding.get("schema") != BINDING_SCHEMA:
        raise DriftDenied("ANTIDRIFT_BINDING_SCHEMA_INVALID")
    if binding.get("hierarchy_sha256") != hierarchy_sha:
        raise DriftDenied("ANTIDRIFT_HIERARCHY_HASH_MISMATCH")

    live = _binding_fields(hierarchy)
    expected = {
        "capability_target": live["active_capability_target"],
        "causal_blocker": live["current_parent_blocker"],
        "action_class": live["next_required_action_class"],
        "active_probe": live["active_probe"],
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            raise DriftDenied("ANTIDRIFT_BINDING_MISMATCH:" + key)

    adapters = _require_string_list(binding.get("allowed_adapters"), "ANTIDRIFT_ALLOWED_ADAPTERS_INVALID")
    action_types = _require_string_list(binding.get("allowed_action_types"), "ANTIDRIFT_ALLOWED_ACTIONS_INVALID")
    repo_prefixes = _require_string_list(binding.get("allowed_repo_prefixes"), "ANTIDRIFT_REPO_PREFIXES_INVALID")
    url_hosts = _require_string_list(binding.get("allowed_url_hosts"), "ANTIDRIFT_URL_HOSTS_INVALID")
    shell_hashes = _require_string_list(binding.get("allowed_shell_sha256"), "ANTIDRIFT_SHELL_HASHES_INVALID")
    capability_ids = _require_string_list(binding.get("allowed_capability_ids"), "ANTIDRIFT_CAPABILITY_IDS_INVALID")

    for digest in shell_hashes:
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise DriftDenied("ANTIDRIFT_SHELL_HASH_INVALID")

    denied = set(_require_string_list(
        hierarchy["antidrift_interlock"].get("denied_action_classes", []),
        "ANTIDRIFT_DENIED_ACTION_CLASSES_INVALID",
    ))
    if str(binding.get("action_class")) in denied:
        raise DriftDenied("ANTIDRIFT_ACTION_CLASS_EXPLICITLY_DENIED")

    return {
        **binding,
        "allowed_adapters": adapters,
        "allowed_action_types": action_types,
        "allowed_repo_prefixes": repo_prefixes,
        "allowed_url_hosts": [x.lower() for x in url_hosts],
        "allowed_shell_sha256": shell_hashes,
        "allowed_capability_ids": capability_ids,
    }


def authorize_task(root: pathlib.Path, task: dict[str, Any]) -> dict[str, Any]:
    if float(task.get("incremental_spend_usd", 0)) != 0.0:
        raise DriftDenied("ANTIDRIFT_NONZERO_SPEND")
    binding = task.get("antidrift")
    if not isinstance(binding, dict):
        raise DriftDenied("ANTIDRIFT_TASK_BINDING_MISSING")
    return validate_binding(root, binding)


def binding_environment(binding: dict[str, Any]) -> dict[str, str]:
    return {
        ENV_REQUIRED: "1",
        ENV_BINDING: json.dumps(binding, sort_keys=True, separators=(",", ":")),
    }


def _binding_from_env(root: pathlib.Path, *, require: bool) -> dict[str, Any] | None:
    raw_required = os.environ.get(ENV_REQUIRED, "").strip()
    raw = os.environ.get(ENV_BINDING, "").strip()
    if not raw:
        if require or raw_required == "1":
            raise DriftDenied("ANTIDRIFT_RUNTIME_CONTEXT_MISSING")
        return None
    try:
        binding = json.loads(raw)
    except Exception as exc:
        raise DriftDenied("ANTIDRIFT_RUNTIME_CONTEXT_INVALID") from exc
    return validate_binding(root, binding)


def require_runtime_context(root: pathlib.Path) -> dict[str, Any]:
    return _binding_from_env(root, require=True) or {}


def _normalize_repo_arg(value: str) -> str:
    text = value.strip().replace("\\", "/")
    while text.startswith("/"):
        text = text[1:]
    return text


def _repo_arg_allowed(value: str, prefixes: list[str]) -> bool:
    text = _normalize_repo_arg(value)
    for raw in prefixes:
        prefix = _normalize_repo_arg(raw).rstrip("/")
        if text == prefix or text.startswith(prefix + "/"):
            return True
    return False


def _url_allowed(value: str, hosts: list[str]) -> bool:
    try:
        parsed = urllib.parse.urlsplit(value)
    except Exception:
        return False
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return any(host == allowed or host.endswith("." + allowed) for allowed in hosts)


def authorize_step_from_env(root: pathlib.Path, step: dict[str, Any]) -> None:
    binding = _binding_from_env(root, require=False)
    if binding is None:
        return
    if not isinstance(step, dict):
        raise DriftDenied("ANTIDRIFT_STEP_NOT_OBJECT")
    adapter = _require_string(step.get("adapter"), "ANTIDRIFT_ADAPTER_MISSING")
    if adapter not in binding["allowed_adapters"]:
        raise DriftDenied("ANTIDRIFT_ADAPTER_DENIED:" + adapter)
    if adapter == "shell":
        command = _require_string(step.get("command"), "ANTIDRIFT_SHELL_COMMAND_MISSING")
        digest = _sha_bytes(command.encode("utf-8"))
        if digest not in binding["allowed_shell_sha256"]:
            raise DriftDenied("ANTIDRIFT_SHELL_COMMAND_DENIED:" + digest)
    if adapter == "http":
        url = _require_string(step.get("url"), "ANTIDRIFT_HTTP_URL_MISSING")
        if not _url_allowed(url, binding["allowed_url_hosts"]):
            raise DriftDenied("ANTIDRIFT_HTTP_HOST_DENIED")


def authorize_action_from_env(root: pathlib.Path, action: dict[str, Any]) -> None:
    binding = _binding_from_env(root, require=False)
    if binding is None:
        return
    if not isinstance(action, dict):
        raise DriftDenied("ANTIDRIFT_ACTION_NOT_OBJECT")
    typ = _require_string(action.get("type"), "ANTIDRIFT_ACTION_TYPE_MISSING")
    if typ not in binding["allowed_action_types"]:
        raise DriftDenied("ANTIDRIFT_ACTION_TYPE_DENIED:" + typ)
    args = action.get("args", {})
    if not isinstance(args, dict):
        raise DriftDenied("ANTIDRIFT_ACTION_ARGS_INVALID")

    for key in _PATH_ARG_KEYS:
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            if not _repo_arg_allowed(value, binding["allowed_repo_prefixes"]):
                raise DriftDenied("ANTIDRIFT_REPO_SCOPE_DENIED:" + key)

    for key in _URL_ARG_KEYS:
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            if not _url_allowed(value, binding["allowed_url_hosts"]):
                raise DriftDenied("ANTIDRIFT_URL_SCOPE_DENIED:" + key)

    if typ in _CAPABILITY_ACTIONS:
        cid = str(args.get("capability_id") or "").strip()
        if not cid or cid not in binding["allowed_capability_ids"]:
            raise DriftDenied("ANTIDRIFT_CAPABILITY_DENIED:" + cid)
