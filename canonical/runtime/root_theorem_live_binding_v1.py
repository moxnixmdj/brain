#!/usr/bin/env python3
"""Content-addressed live binding checks for the four-root completeness theorem.

This validates R4 currentness only. It never grants terminal credit and does not
claim R1/R2/R3/R4 globally closed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.coverage_root_namespace_guard_v1 import validate_bridge_document


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fail(errors: list[str], code: str, condition: bool) -> None:
    if not condition:
        errors.append(code)


def validate_documents(
    *,
    mission: Mapping[str, Any],
    mission_blob_sha: str,
    root_theorem: Mapping[str, Any],
    root_theorem_blob_sha: str,
    binding: Mapping[str, Any],
    binding_blob_sha: str,
    namespace_bridge: Mapping[str, Any],
    namespace_bridge_blob_sha: str,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    bridge_check = validate_bridge_document(namespace_bridge)
    if not bridge_check.get("pass"):
        errors.extend("ROOT_NAMESPACE_" + e for e in bridge_check.get("errors", []))

    real_objective = mission.get("real_objective")
    _fail(errors, "MISSION_REAL_OBJECTIVE_MISSING", isinstance(real_objective, str) and bool(real_objective))
    _fail(
        errors,
        "ROOT_THEOREM_REAL_OBJECTIVE_DRIFT",
        root_theorem.get("terminal_objective_unchanged") == real_objective,
    )

    mission_binding = root_theorem.get("mission_objective_binding") or {}
    _fail(
        errors,
        "ROOT_THEOREM_MISSION_PATH_DRIFT",
        mission_binding.get("path") == "canonical/governance/CURRENT_MISSION_OBJECTIVE.json",
    )
    _fail(
        errors,
        "ROOT_THEOREM_MISSION_BLOB_STALE",
        mission_binding.get("git_blob_sha") == mission_blob_sha,
    )
    _fail(
        errors,
        "ROOT_THEOREM_MISSION_TEXT_DRIFT",
        mission_binding.get("real_objective") == real_objective,
    )

    checkpoint = root_theorem.get("checkpoint_objective") or {}
    _fail(
        errors,
        "CHECKPOINT_ROLE_DRIFT",
        checkpoint.get("role") == "CURRENT_FRONTIER_CHECKPOINT_AND_ACCEPTANCE_LEDGER_ONLY",
    )

    precedence = authority.get("objective_precedence") or {}
    _fail(
        errors,
        "TERMINAL_AUTHORITY_MISSION_PATH_DRIFT",
        precedence.get("authoritative_path") == "canonical/governance/CURRENT_MISSION_OBJECTIVE.json",
    )
    _fail(
        errors,
        "TERMINAL_AUTHORITY_MISSION_BLOB_STALE",
        precedence.get("authoritative_git_blob_sha") == mission_blob_sha,
    )
    _fail(
        errors,
        "TERMINAL_AUTHORITY_MISSION_TEXT_DRIFT",
        authority.get("terminal_objective") == real_objective
        and precedence.get("real_objective") == real_objective,
    )

    root_ref = binding.get("root_theorem") or {}
    _fail(
        errors,
        "BINDING_ROOT_PATH_DRIFT",
        root_ref.get("path") == "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json",
    )
    _fail(
        errors,
        "BINDING_ROOT_BLOB_STALE",
        root_ref.get("git_blob_sha") == root_theorem_blob_sha,
    )
    _fail(
        errors,
        "BINDING_MISSION_BLOB_STALE",
        (binding.get("mission_objective") or {}).get("git_blob_sha") == mission_blob_sha,
    )
    _fail(
        errors,
        "BINDING_ZERO_CREDIT_VIOLATION",
        (binding.get("accounting") or {}).get("terminal_credit_delta") == 0,
    )

    namespace_ref = binding.get("root_namespace_bridge") or {}
    _fail(
        errors,
        "BINDING_ROOT_NAMESPACE_PATH_DRIFT",
        namespace_ref.get("path") == "canonical/governance/COVERAGE_ROOT_NAMESPACE_BRIDGE_V1.json",
    )
    _fail(
        errors,
        "BINDING_ROOT_NAMESPACE_BLOB_STALE",
        namespace_ref.get("git_blob_sha") == namespace_bridge_blob_sha,
    )

    sources = authority.get("authoritative_sources") or {}
    live_ref = sources.get("coverage_completeness_root_theorem_r1_r4") or {}
    _fail(
        errors,
        "LIVE_AUTHORITY_ROOT_BINDING_MISSING",
        live_ref.get("path")
        == "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_LIVE_BINDING_V1.json",
    )
    _fail(
        errors,
        "LIVE_AUTHORITY_ROOT_BINDING_BLOB_STALE",
        live_ref.get("git_blob_sha") == binding_blob_sha,
    )

    namespace_authority = sources.get("coverage_root_namespace_bridge") or {}
    _fail(
        errors,
        "LIVE_AUTHORITY_ROOT_NAMESPACE_MISSING",
        namespace_authority.get("path")
        == "canonical/governance/COVERAGE_ROOT_NAMESPACE_BRIDGE_V1.json",
    )
    _fail(
        errors,
        "LIVE_AUTHORITY_ROOT_NAMESPACE_BLOB_STALE",
        namespace_authority.get("git_blob_sha") == namespace_bridge_blob_sha,
    )

    return {
        "pass": not errors,
        "status": "PASS__R4_LIVE_BINDING_CURRENT" if not errors else "FAIL_CLOSED__R4_LIVE_BINDING_DRIFT",
        "errors": errors,
        "terminal_credit_delta": 0,
        "root_closed_claimed": False,
    }


def validate_repo(root: Path) -> dict[str, Any]:
    mission_path = root / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
    theorem_path = root / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json"
    binding_path = root / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_LIVE_BINDING_V1.json"
    namespace_bridge_path = root / "canonical/governance/COVERAGE_ROOT_NAMESPACE_BRIDGE_V1.json"
    authority_path = root / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"

    mission_bytes = mission_path.read_bytes()
    theorem_bytes = theorem_path.read_bytes()
    binding_bytes = binding_path.read_bytes()
    namespace_bridge_bytes = namespace_bridge_path.read_bytes()

    return validate_documents(
        mission=load_json(mission_path),
        mission_blob_sha=git_blob_sha(mission_bytes),
        root_theorem=load_json(theorem_path),
        root_theorem_blob_sha=git_blob_sha(theorem_bytes),
        binding=load_json(binding_path),
        binding_blob_sha=git_blob_sha(binding_bytes),
        namespace_bridge=load_json(namespace_bridge_path),
        namespace_bridge_blob_sha=git_blob_sha(namespace_bridge_bytes),
        authority=load_json(authority_path),
    )
