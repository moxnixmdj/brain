#!/usr/bin/env python3
"""Content-addressed live binding checks for the CCRT four-root theorem.

This validates R4 currentness only. It grants no terminal credit and does not
claim R1/R2/R3/R4, claim completeness, carrier factorization, or global mission
completion closed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.coverage_root_namespace_guard_v1 import validate_bridge_document
from canonical.runtime.coverage_claim_root_certificate_registry_guard_v1 import validate as validate_claim_root_registry

MISSION_PATH = "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
THEOREM_PATH = "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json"
BINDING_PATH = "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_LIVE_BINDING_V1.json"
AUTHORITY_PATH = "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
NAMESPACE_PATH = "canonical/governance/COVERAGE_ROOT_NAMESPACE_BRIDGE_V1.json"
CARRIER_PATH = "canonical/governance/MISSION_SUFFICIENT_SEMANTIC_CARRIER_V1.json"
CARRIER_RUNTIME_PATH = "canonical/runtime/mission_carrier_factorization_v1.py"
CARRIER_TESTS_PATH = "canonical/tests/test_mission_carrier_factorization_v1.py"
CLAIM_SCOPE_PATH = "canonical/governance/COVERAGE_COMPLETENESS_CLAIM_SCOPE_V1.json"
CLAIM_ROOT_POINTER_PATH = "canonical/governance/CURRENT_COVERAGE_COMPLETENESS_ROOT_CERTIFICATES.json"
CLAIM_ROOT_REGISTRY_PATH = "canonical/governance/COVERAGE_COMPLETENESS_CLAIM_ROOT_CERTIFICATE_REGISTRY_V1.json"
CLAIM_ROOT_GUARD_PATH = "canonical/runtime/coverage_claim_root_certificate_registry_guard_v1.py"
CLAIM_ROOT_TESTS_PATH = "canonical/tests/test_coverage_claim_root_certificate_registry_guard_v1.py"


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
    carrier: Mapping[str, Any],
    carrier_blob_sha: str,
    carrier_runtime_blob_sha: str,
    carrier_tests_blob_sha: str,
    claim_scope: Mapping[str, Any],
    claim_scope_blob_sha: str,
    claim_root_pointer: Mapping[str, Any],
    claim_root_pointer_blob_sha: str,
    claim_root_registry: Mapping[str, Any],
    claim_root_registry_blob_sha: str,
    claim_root_guard_blob_sha: str,
    claim_root_tests_blob_sha: str,
) -> dict[str, Any]:
    errors: list[str] = []

    bridge_check = validate_bridge_document(namespace_bridge)
    if not bridge_check.get("pass"):
        errors.extend("ROOT_NAMESPACE_" + e for e in bridge_check.get("errors", []))

    real_objective = mission.get("real_objective")
    _fail(errors, "MISSION_REAL_OBJECTIVE_MISSING", isinstance(real_objective, str) and bool(real_objective))
    _fail(errors, "ROOT_THEOREM_REAL_OBJECTIVE_DRIFT", root_theorem.get("terminal_objective_unchanged") == real_objective)

    mission_binding = root_theorem.get("mission_objective_binding") or {}
    _fail(errors, "ROOT_THEOREM_MISSION_PATH_DRIFT", mission_binding.get("path") == MISSION_PATH)
    _fail(errors, "ROOT_THEOREM_MISSION_BLOB_STALE", mission_binding.get("git_blob_sha") == mission_blob_sha)
    _fail(errors, "ROOT_THEOREM_MISSION_TEXT_DRIFT", mission_binding.get("real_objective") == real_objective)

    checkpoint = root_theorem.get("checkpoint_objective") or {}
    _fail(errors, "CHECKPOINT_ROLE_DRIFT", checkpoint.get("role") == "CURRENT_FRONTIER_CHECKPOINT_AND_ACCEPTANCE_LEDGER_ONLY")

    precedence = authority.get("objective_precedence") or {}
    _fail(errors, "TERMINAL_AUTHORITY_MISSION_PATH_DRIFT", precedence.get("authoritative_path") == MISSION_PATH)
    _fail(errors, "TERMINAL_AUTHORITY_MISSION_BLOB_STALE", precedence.get("authoritative_git_blob_sha") == mission_blob_sha)
    _fail(
        errors,
        "TERMINAL_AUTHORITY_MISSION_TEXT_DRIFT",
        authority.get("terminal_objective") == real_objective and precedence.get("real_objective") == real_objective,
    )

    namespace_ref = binding.get("root_namespace_bridge") or {}
    _fail(errors, "BINDING_ROOT_NAMESPACE_PATH_DRIFT", namespace_ref.get("path") == NAMESPACE_PATH)
    _fail(errors, "BINDING_ROOT_NAMESPACE_BLOB_STALE", namespace_ref.get("git_blob_sha") == namespace_bridge_blob_sha)

    carrier_theorem = root_theorem.get("semantic_carrier_precondition") or {}
    carrier_formula = (carrier.get("required_factorization") or {}).get("formula")
    _fail(errors, "ROOT_THEOREM_CARRIER_PATH_MISSING", carrier_theorem.get("path") == CARRIER_PATH)
    _fail(
        errors,
        "ROOT_THEOREM_CARRIER_FORMULA_DRIFT",
        isinstance(carrier_formula, str) and bool(carrier_formula) and carrier_theorem.get("formula") == carrier_formula,
    )
    _fail(errors, "ROOT_THEOREM_CARRIER_NOT_CLAIM_INDEXED", carrier_theorem.get("claim_indexed") is True)
    _fail(
        errors,
        "ROOT_THEOREM_CARRIER_REQUIRED_BINDINGS_DRIFT",
        set(carrier_theorem.get("required_claim_bindings") or []) == {"claim_id", "scope_sha256", "semantics_sha256"},
    )
    _fail(errors, "CARRIER_NEW_ROOT_VIOLATION", (carrier.get("root_effect") or {}).get("new_semantic_root_required") is False)
    _fail(errors, "CARRIER_ZERO_CREDIT_VIOLATION", (carrier.get("current_state") or {}).get("terminal_credit_delta") == 0)

    carrier_claim = carrier.get("claim_scope") or {}
    _fail(
        errors,
        "CARRIER_CLAIM_BINDINGS_DRIFT",
        set(carrier_claim.get("required_bindings") or []) == {"claim_id", "scope_sha256", "semantics_sha256"},
    )
    _fail(
        errors,
        "CARRIER_GLOBAL_COMPLETION_VIOLATION",
        carrier_claim.get("global_open_ended_mission_completion_derivable") is False,
    )

    claim_mission = claim_scope.get("mission") or {}
    _fail(errors, "CLAIM_SCOPE_MISSION_PATH_DRIFT", claim_mission.get("path") == MISSION_PATH)
    _fail(errors, "CLAIM_SCOPE_MISSION_BLOB_STALE", claim_mission.get("git_blob_sha") == mission_blob_sha)
    claim_root = claim_scope.get("root_theorem") or {}
    _fail(errors, "CLAIM_SCOPE_ROOT_PATH_DRIFT", claim_root.get("path") == THEOREM_PATH)
    _fail(errors, "CLAIM_SCOPE_ROOT_BLOB_STALE", claim_root.get("git_blob_sha") == root_theorem_blob_sha)
    claim_carrier = claim_scope.get("carrier_factorization") or {}
    _fail(errors, "CLAIM_SCOPE_CARRIER_PATH_DRIFT", claim_carrier.get("carrier_governance_path") == CARRIER_PATH)
    _fail(errors, "CLAIM_SCOPE_CARRIER_BLOB_STALE", claim_carrier.get("carrier_governance_git_blob_sha") == carrier_blob_sha)
    _fail(
        errors,
        "CLAIM_SCOPE_CARRIER_BINDINGS_DRIFT",
        set(claim_carrier.get("required_same_claim_bindings") or []) == {"claim_id", "scope_sha256", "semantics_sha256"},
    )
    _fail(
        errors,
        "CLAIM_SCOPE_GLOBAL_COMPLETION_VIOLATION",
        claim_carrier.get("global_open_ended_mission_completion_derivable") is False,
    )

    registry_check = validate_claim_root_registry(
        claim_root_registry,
        current_mission_blob_sha=mission_blob_sha,
        current_claim_scope_blob_sha=claim_scope_blob_sha,
    )
    if not registry_check.get("pass"):
        errors.extend("CLAIM_ROOT_REGISTRY_" + e for e in registry_check.get("errors", []))

    pointer_registry = claim_root_pointer.get("registry") or {}
    pointer_guard = claim_root_pointer.get("guard") or {}
    pointer_tests = claim_root_pointer.get("tests") or {}
    _fail(errors, "CLAIM_ROOT_POINTER_REGISTRY_PATH_DRIFT", pointer_registry.get("path") == CLAIM_ROOT_REGISTRY_PATH)
    _fail(errors, "CLAIM_ROOT_POINTER_REGISTRY_BLOB_STALE", pointer_registry.get("git_blob_sha") == claim_root_registry_blob_sha)
    _fail(errors, "CLAIM_ROOT_POINTER_GUARD_PATH_DRIFT", pointer_guard.get("path") == CLAIM_ROOT_GUARD_PATH)
    _fail(errors, "CLAIM_ROOT_POINTER_GUARD_BLOB_STALE", pointer_guard.get("git_blob_sha") == claim_root_guard_blob_sha)
    _fail(errors, "CLAIM_ROOT_POINTER_TESTS_PATH_DRIFT", pointer_tests.get("path") == CLAIM_ROOT_TESTS_PATH)
    _fail(errors, "CLAIM_ROOT_POINTER_TESTS_BLOB_STALE", pointer_tests.get("git_blob_sha") == claim_root_tests_blob_sha)
    _fail(errors, "CLAIM_ROOT_POINTER_NONZERO_PROVED", claim_root_pointer.get("proved") == registry_check.get("proved_root_certificate_count"))
    _fail(errors, "CLAIM_ROOT_POINTER_NONZERO_OPEN", claim_root_pointer.get("open") == registry_check.get("open_root_certificate_count"))
    _fail(errors, "CLAIM_ROOT_POINTER_GLOBAL_CLOSURE_ENABLED", claim_root_pointer.get("r4_proof_closure") is False)

    root_ref = binding.get("root_theorem") or {}
    _fail(errors, "BINDING_ROOT_PATH_DRIFT", root_ref.get("path") == THEOREM_PATH)
    _fail(errors, "BINDING_ROOT_BLOB_STALE", root_ref.get("git_blob_sha") == root_theorem_blob_sha)
    _fail(errors, "BINDING_MISSION_BLOB_STALE", (binding.get("mission_objective") or {}).get("git_blob_sha") == mission_blob_sha)
    _fail(errors, "BINDING_ZERO_CREDIT_VIOLATION", (binding.get("accounting") or {}).get("terminal_credit_delta") == 0)

    carrier_ref = binding.get("semantic_carrier_precondition") or {}
    _fail(errors, "BINDING_CARRIER_PATH_MISSING", carrier_ref.get("path") == CARRIER_PATH)
    _fail(errors, "BINDING_CARRIER_BLOB_STALE", carrier_ref.get("git_blob_sha") == carrier_blob_sha)
    _fail(errors, "BINDING_CARRIER_RUNTIME_PATH_DRIFT", (carrier_ref.get("runtime") or {}).get("path") == CARRIER_RUNTIME_PATH)
    _fail(errors, "BINDING_CARRIER_RUNTIME_BLOB_STALE", (carrier_ref.get("runtime") or {}).get("git_blob_sha") == carrier_runtime_blob_sha)
    _fail(errors, "BINDING_CARRIER_TESTS_PATH_DRIFT", (carrier_ref.get("tests") or {}).get("path") == CARRIER_TESTS_PATH)
    _fail(errors, "BINDING_CARRIER_TESTS_BLOB_STALE", (carrier_ref.get("tests") or {}).get("git_blob_sha") == carrier_tests_blob_sha)

    claim_ref = binding.get("claim_scope_precondition") or {}
    _fail(errors, "BINDING_CLAIM_SCOPE_PATH_MISSING", claim_ref.get("path") == CLAIM_SCOPE_PATH)
    _fail(errors, "BINDING_CLAIM_SCOPE_BLOB_STALE", claim_ref.get("git_blob_sha") == claim_scope_blob_sha)

    claim_root_ref = binding.get("claim_root_certificate_authority") or {}
    _fail(errors, "BINDING_CLAIM_ROOT_POINTER_PATH_DRIFT", claim_root_ref.get("path") == CLAIM_ROOT_POINTER_PATH)
    _fail(errors, "BINDING_CLAIM_ROOT_POINTER_BLOB_STALE", claim_root_ref.get("git_blob_sha") == claim_root_pointer_blob_sha)
    _fail(errors, "BINDING_CLAIM_ROOT_REGISTRY_PATH_DRIFT", (claim_root_ref.get("registry") or {}).get("path") == CLAIM_ROOT_REGISTRY_PATH)
    _fail(errors, "BINDING_CLAIM_ROOT_REGISTRY_BLOB_STALE", (claim_root_ref.get("registry") or {}).get("git_blob_sha") == claim_root_registry_blob_sha)

    sources = authority.get("authoritative_sources") or {}
    live_ref = sources.get("coverage_completeness_root_theorem_r1_r4") or {}
    _fail(errors, "LIVE_AUTHORITY_ROOT_BINDING_MISSING", live_ref.get("path") == BINDING_PATH)
    _fail(errors, "LIVE_AUTHORITY_ROOT_BINDING_BLOB_STALE", live_ref.get("git_blob_sha") == binding_blob_sha)
    namespace_authority = sources.get("coverage_root_namespace_bridge") or {}
    _fail(errors, "LIVE_AUTHORITY_ROOT_NAMESPACE_MISSING", namespace_authority.get("path") == NAMESPACE_PATH)
    _fail(errors, "LIVE_AUTHORITY_ROOT_NAMESPACE_BLOB_STALE", namespace_authority.get("git_blob_sha") == namespace_bridge_blob_sha)
    claim_root_live_ref = sources.get("coverage_claim_root_certificate_registry") or {}
    _fail(errors, "LIVE_AUTHORITY_CLAIM_ROOT_POINTER_MISSING", claim_root_live_ref.get("path") == CLAIM_ROOT_POINTER_PATH)
    _fail(errors, "LIVE_AUTHORITY_CLAIM_ROOT_POINTER_BLOB_STALE", claim_root_live_ref.get("git_blob_sha") == claim_root_pointer_blob_sha)
    _fail(errors, "LIVE_AUTHORITY_CLAIM_ROOT_REGISTRY_BLOB_STALE", (claim_root_live_ref.get("registry") or {}).get("git_blob_sha") == claim_root_registry_blob_sha)

    claim_live_ref = sources.get("coverage_completeness_claim_scope") or {}
    _fail(errors, "LIVE_AUTHORITY_CLAIM_SCOPE_MISSING", claim_live_ref.get("path") == CLAIM_SCOPE_PATH)
    _fail(errors, "LIVE_AUTHORITY_CLAIM_SCOPE_BLOB_STALE", claim_live_ref.get("git_blob_sha") == claim_scope_blob_sha)

    return {
        "pass": not errors,
        "status": "PASS__R4_LIVE_BINDING_CURRENT" if not errors else "FAIL_CLOSED__R4_LIVE_BINDING_DRIFT",
        "errors": errors,
        "terminal_credit_delta": 0,
        "root_closed_claimed": False,
        "claim_completeness_closed_claimed": False,
        "carrier_factorization_closed_claimed": False,
        "global_mission_completion_derivable": False,
        "claim_root_registry_current": not errors,
    }


def validate_repo(root: Path) -> dict[str, Any]:
    mission_path = root / MISSION_PATH
    theorem_path = root / THEOREM_PATH
    binding_path = root / BINDING_PATH
    namespace_bridge_path = root / NAMESPACE_PATH
    authority_path = root / AUTHORITY_PATH
    carrier_path = root / CARRIER_PATH
    carrier_runtime_path = root / CARRIER_RUNTIME_PATH
    carrier_tests_path = root / CARRIER_TESTS_PATH
    claim_scope_path = root / CLAIM_SCOPE_PATH
    claim_root_pointer_path = root / CLAIM_ROOT_POINTER_PATH
    claim_root_registry_path = root / CLAIM_ROOT_REGISTRY_PATH
    claim_root_guard_path = root / CLAIM_ROOT_GUARD_PATH
    claim_root_tests_path = root / CLAIM_ROOT_TESTS_PATH

    mission_bytes = mission_path.read_bytes()
    theorem_bytes = theorem_path.read_bytes()
    binding_bytes = binding_path.read_bytes()
    namespace_bridge_bytes = namespace_bridge_path.read_bytes()
    carrier_bytes = carrier_path.read_bytes()
    claim_scope_bytes = claim_scope_path.read_bytes()
    claim_root_pointer_bytes = claim_root_pointer_path.read_bytes()
    claim_root_registry_bytes = claim_root_registry_path.read_bytes()

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
        carrier=load_json(carrier_path),
        carrier_blob_sha=git_blob_sha(carrier_bytes),
        carrier_runtime_blob_sha=git_blob_sha(carrier_runtime_path.read_bytes()),
        carrier_tests_blob_sha=git_blob_sha(carrier_tests_path.read_bytes()),
        claim_scope=load_json(claim_scope_path),
        claim_scope_blob_sha=git_blob_sha(claim_scope_bytes),
        claim_root_pointer=load_json(claim_root_pointer_path),
        claim_root_pointer_blob_sha=git_blob_sha(claim_root_pointer_bytes),
        claim_root_registry=load_json(claim_root_registry_path),
        claim_root_registry_blob_sha=git_blob_sha(claim_root_registry_bytes),
        claim_root_guard_blob_sha=git_blob_sha(claim_root_guard_path.read_bytes()),
        claim_root_tests_blob_sha=git_blob_sha(claim_root_tests_path.read_bytes()),
    )
