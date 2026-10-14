"""Professional-quality declared-subject dependency delta.

Reuse the existing transitive runtime-closure compiler to compare the current
declared professional system subject with the verified P1 V6 minimal
goal-binding route.

This module is deliberately diagnostic. It may prove exact byte currentness and
an exact Brain-local Python runtime closure for the declared runtime roots. It
does not prove that all non-Python configuration, external evidence, execution
environment, or future root-specific dependencies are complete.

The V6 replacement removes the broad general R2 controller from the P1
goal-binding dependency cone, but pruning any declared subject component remains
forbidden until full subject-dependency closure is separately proved.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.python_transitive_runtime_closure_v1 import (
    ClosureError,
    compute_closure,
)

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_SUBJECT_DEPENDENCY_DELTA_V1"
ROOT = Path(__file__).resolve().parents[2]

SUBJECT_PATH = (
    "canonical/governance/"
    "PROFESSIONAL_QUALITY_P1_V5_DECLARED_SYSTEM_SUBJECT_20261010_V4.json"
)
SUBJECT_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V2"

SUPERSEDED_RUNTIME_ROOTS = {
    "canonical/runtime/professional_quality_p1_router_v5.py",
    "canonical/runtime/general_adequate_decision_controller_v1.py",
}
V6_RUNTIME_ROOT = "canonical/runtime/professional_quality_p1_router_v6.py"

# These are already-established load-bearing configuration dependencies from
# the P1 router chain and the current R6 dependency worklist. This list is
# intentionally not called globally complete.
KNOWN_CONFIG_DEPENDENCIES = {
    "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V1.json": {
        "git_blob_sha": "a01ef78846ce22996128cc2a5858341d8418074c",
        "reason": "P1_ROUTER_V2_LOADS_PROFILE_V1_AT_RUNTIME",
    },
    "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json": {
        "git_blob_sha": "f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5",
        "reason": "P1_ROUTER_V3_AND_V4_LOAD_PROFILE_V3_AT_RUNTIME",
    },
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json": {
        "git_blob_sha": "ae250d5bc5da73b23600670be354ffba31e65e53",
        "reason": "P1_ROUTER_V4_LOADS_CURRENT_PROFESSIONAL_BEHAVIOR_CONTRACT",
    },
    "canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json": {
        "git_blob_sha": "a7cad32c9fd969ff2c3857bb924c7bd746237ec2",
        "reason": "LEAF_BINDER_V2_LOADS_MANIFEST_AT_RUNTIME",
    },
    "canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json": {
        "git_blob_sha": "03530e29d70206b46b690b33a04c66765ff86ad7",
        "reason": "LEAF_BINDER_V2_LOADS_ASSURANCE_GRAPH_AT_RUNTIME",
    },
    "canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json": {
        "git_blob_sha": "d25cb6fe746eef992f71b138446dc999c0f2a307",
        "reason": "LEAF_BINDER_V2_LOADS_LEAF_EVIDENCE_REGISTRY_AT_RUNTIME",
    },
    "canonical/governance/PROFESSIONAL_QUALITY_CLOSURE_NORMAL_FORM_20261009_V1.json": {
        "git_blob_sha": "ebcfe5a48efce9df7fbc69a3817ac2f9adb1ff93",
        "reason": "SAME_SUBJECT_GATE_BINDS_THE_NORMAL_FORM_AT_RUNTIME",
    },
}


def _git_blob(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return doc


def _safe_repo_path(root: Path, rel: str) -> Path:
    raw = Path(rel)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError("UNSAFE_REPOSITORY_PATH:" + rel)
    path = (root / raw).resolve()
    path.relative_to(root.resolve())
    return path


def evaluate(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    base = {
        "schema": SCHEMA,
        "pass": False,
        "subject_dependency_closure_complete": False,
        "subject_refresh_authority": False,
        "root_subject_binding_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
    try:
        subject_file = _safe_repo_path(root, SUBJECT_PATH)
        subject = _load(subject_file)
        if subject.get("schema") != SUBJECT_SCHEMA:
            raise ValueError("SUBJECT_SCHEMA_INVALID")

        components = (subject.get("system_material") or {}).get("components")
        if not isinstance(components, list) or not components:
            raise ValueError("SUBJECT_COMPONENTS_INVALID")

        declared: dict[str, str] = {}
        currentness_errors: list[str] = []
        for row in components:
            if not isinstance(row, Mapping):
                currentness_errors.append("SUBJECT_COMPONENT_NOT_OBJECT")
                continue
            rel = row.get("path")
            expected = row.get("git_blob_sha")
            if not isinstance(rel, str) or not rel:
                currentness_errors.append("SUBJECT_COMPONENT_PATH_INVALID")
                continue
            if not isinstance(expected, str) or len(expected) != 40:
                currentness_errors.append("SUBJECT_COMPONENT_BLOB_INVALID:" + rel)
                continue
            path = _safe_repo_path(root, rel)
            if not path.is_file() or path.is_symlink():
                currentness_errors.append("SUBJECT_COMPONENT_FILE_INVALID:" + rel)
                continue
            actual = _git_blob(path)
            if actual != expected:
                currentness_errors.append("SUBJECT_COMPONENT_STALE:" + rel)
            declared[rel] = expected

        if currentness_errors:
            return {
                **base,
                "status": "FAIL_CLOSED__CANDIDATE_SUBJECT_NOT_CURRENT",
                "errors": sorted(set(currentness_errors)),
            }

        declared_runtime_roots = sorted(
            rel
            for rel in declared
            if rel.startswith("canonical/runtime/") and rel.endswith(".py")
        )
        replacement_runtime_roots = sorted(
            (set(declared_runtime_roots) - SUPERSEDED_RUNTIME_ROOTS)
            | {V6_RUNTIME_ROOT}
        )

        closure = compute_closure(root, replacement_runtime_roots)
        if closure.get("pass") is not True:
            return {
                **base,
                "status": "FAIL_CLOSED__V6_RUNTIME_CLOSURE_UNRESOLVED",
                "candidate_subject_current": True,
                "replacement_runtime_roots": replacement_runtime_roots,
                "runtime_closure": closure,
            }

        closure_rows = closure.get("files") or []
        closure_paths = {
            str(row.get("path"))
            for row in closure_rows
            if isinstance(row, Mapping) and row.get("path")
        }
        declared_paths = set(declared)

        missing_runtime = sorted(closure_paths - declared_paths)
        candidate_runtime_only = sorted(
            set(declared_runtime_roots) - closure_paths
        )

        config_records: list[dict[str, Any]] = []
        missing_config: list[str] = []
        config_errors: list[str] = []
        for rel, meta in sorted(KNOWN_CONFIG_DEPENDENCIES.items()):
            path = _safe_repo_path(root, rel)
            expected = meta["git_blob_sha"]
            if not path.is_file() or path.is_symlink():
                config_errors.append("KNOWN_CONFIG_FILE_INVALID:" + rel)
                actual = None
            else:
                actual = _git_blob(path)
                if actual != expected:
                    config_errors.append("KNOWN_CONFIG_BLOB_DRIFT:" + rel)
            present = rel in declared_paths
            if not present:
                missing_config.append(rel)
            config_records.append({
                "path": rel,
                "expected_git_blob_sha": expected,
                "actual_git_blob_sha": actual,
                "current": actual == expected,
                "already_in_subject": present,
                "reason": meta["reason"],
            })

        if config_errors:
            return {
                **base,
                "status": "FAIL_CLOSED__KNOWN_CONFIG_DEPENDENCY_DRIFT",
                "candidate_subject_current": True,
                "runtime_closure": closure,
                "known_config_dependencies": config_records,
                "errors": sorted(config_errors),
            }

        # V6 is independently verified elsewhere. This diagnostic only proves
        # that its Brain-local runtime cone is smaller/different and identifies
        # exact subject deltas. It does not authorize removing candidate-only
        # files until all remaining root dependencies are classified.
        return {
            **base,
            "pass": True,
            "status": "PASS__V6_RUNTIME_CLOSURE_AND_KNOWN_CONFIG_DELTA_BOUND",
            "candidate_subject": {
                "path": SUBJECT_PATH,
                "git_blob_sha": _git_blob(subject_file),
                "subject_id": subject.get("subject_id"),
                "subject_sha256": subject.get("subject_sha256"),
            },
            "candidate_subject_current": True,
            "declared_component_count": len(declared),
            "declared_runtime_root_count": len(declared_runtime_roots),
            "replacement_runtime_roots": replacement_runtime_roots,
            "runtime_closure_file_count": closure.get("closure_file_count"),
            "runtime_closure": closure,
            "missing_runtime_components": missing_runtime,
            "known_config_dependencies": config_records,
            "known_missing_config_components": missing_config,
            "candidate_only_runtime_components": candidate_runtime_only,
            "candidate_only_runtime_pruning_authority": False,
            "v6_minimal_goal_binding_kernel_in_runtime_closure": (
                "canonical/runtime/goal_to_decision_binding_authority_v1.py"
                in closure_paths
            ),
            "general_r2_controller_in_v6_replacement_closure": (
                "canonical/runtime/general_adequate_decision_controller_v1.py"
                in closure_paths
            ),
            "router_v5_in_v6_replacement_closure": (
                "canonical/runtime/professional_quality_p1_router_v5.py"
                in closure_paths
            ),
            "next_required_edge": (
                "ADD_MISSING_RUNTIME_AND_KNOWN_CONFIG_COMPONENTS_TO_ONE_NEW_"
                "DECLARED_SUBJECT_GENERATION__THEN_CLASSIFY_REMAINING_NON_PYTHON_"
                "AND_ROOT_SPECIFIC_DEPENDENCIES_BEFORE_ANY_PRUNING_OR_MORE_ROOT_BINDINGS"
            ),
            "hard_nonclaims": [
                "NO_GLOBAL_NON_PYTHON_DEPENDENCY_COMPLETENESS",
                "NO_EXTERNAL_EVIDENCE_INPUT_COMPLETENESS",
                "NO_SUBJECT_REFRESH_AUTHORITY",
                "NO_COMPONENT_PRUNING_AUTHORITY",
                "NO_NEW_ROOT_SUBJECT_BINDING",
                "NO_SAME_SUBJECT_COMPOSITION_PASS",
                "NO_PROFESSIONAL_QUALITY_CLOSURE",
                "NO_LIVE_DEFAULT_PROMOTION",
                "NO_TERMINAL_CREDIT",
            ],
        }
    except (ValueError, OSError, ClosureError, json.JSONDecodeError) as exc:
        return {
            **base,
            "status": "FAIL_CLOSED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
        }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
