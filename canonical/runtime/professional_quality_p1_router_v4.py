"""Professional-quality P1 Router V4: target-instance-bound wrapper over V3.

V4 closes one R1 structural seam only: every routed result is bound to an exact
runtime target instance and to the current canonical professional target
contract. It does not claim arbitrary-language understanding, quality,
acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v3 as base
from canonical.runtime import professional_target_semantic_certificate_v1 as target_sem

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V4"
CONTRACT_REGISTRY_PATH = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json"
CONTRACT_REGISTRY_BLOB = "ae250d5bc5da73b23600670be354ffba31e65e53"
PROFILE_PATH = "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json"
PROFILE_BLOB = "f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"
TARGET_FIELDS = (
    "objective",
    "audience",
    "source_evidence",
    "artifact_type",
    "constraints",
    "current_draft_or_render",
)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def _base(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "target_binding_authority": False,
        "semantic_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return _base("FAIL_CLOSED", reason=reason, **extra)


def _root(repo_root: str | Path | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _load_json_bound(root: Path, rel: str, blob: str) -> dict[str, Any]:
    path = (root / rel).resolve()
    path.relative_to(root.resolve())
    if not path.is_file() or path.is_symlink():
        raise ValueError("BOUND_FILE_INVALID")
    if _git_blob_sha(path) != blob:
        raise ValueError("BOUND_FILE_STALE")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("BOUND_DOCUMENT_INVALID")
    return doc


def _contract(root: Path) -> dict[str, Any]:
    registry = _load_json_bound(root, CONTRACT_REGISTRY_PATH, CONTRACT_REGISTRY_BLOB)
    rows = registry.get("active_contracted_residuals")
    if not isinstance(rows, list):
        raise ValueError("CONTRACT_REGISTRY_ROWS_INVALID")
    matches = [
        row for row in rows
        if isinstance(row, Mapping) and row.get("behavior_id") == target_sem.BEHAVIOR_ID
    ]
    if len(matches) != 1:
        raise ValueError("TARGET_CONTRACT_NOT_UNIQUE")
    return deepcopy(dict(matches[0]))


def _semantic_binding(contract: Mapping[str, Any]) -> dict[str, Any]:
    roles = {
        "objective": "required_output_or_action",
        "audience": "inputs",
        "hard_constraints": "allowed_information",
        "success_semantics": "success_condition",
        "failure_semantics": "failure_condition",
        "target_construct": "success_condition",
        "claim_scope": "scope",
        "evidence_boundary": "dependency_boundary",
    }
    return {
        "behavior_id": target_sem.BEHAVIOR_ID,
        "contract_sha256": target_sem.digest(dict(contract)),
        "role_bindings": {
            role: {
                "source_field": field,
                "source_value_sha256": target_sem.digest(contract[field]),
            }
            for role, field in roles.items()
        },
        "ambiguity_policy": {
            "unique_optimum_claimed": False,
            "admissible_plan_definition": "ANY_PLAN_SATISFYING_SUCCESS_AND_AVOIDING_FAILURE_WITHIN_DECLARED_SCOPE",
            "unresolved_runtime_task_ambiguity_must_remain_open": True,
        },
        "hard_nonclaims": [
            "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS",
            "NO_SOURCE_EXTRACTION_COMPLETENESS",
            "NO_UNIQUE_BEST_PLAN",
            "NO_GLOBAL_R1_SEMANTIC_LEAF_CLOSURE",
            "NO_GLOBAL_R1_ROOT_CLOSURE",
        ],
    }


def _validate_target_instance(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, Mapping):
        return None, "TARGET_INSTANCE_NOT_OBJECT"
    extra = sorted(set(value) - set(TARGET_FIELDS))
    missing = [field for field in TARGET_FIELDS if field not in value]
    if extra:
        return None, "TARGET_INSTANCE_UNKNOWN_FIELDS:" + ",".join(extra)
    if missing:
        return None, "TARGET_INSTANCE_MISSING_FIELDS:" + ",".join(missing)
    out = {field: deepcopy(value[field]) for field in TARGET_FIELDS}
    for field in ("objective", "audience", "artifact_type"):
        if not isinstance(out[field], str) or not out[field].strip():
            return None, "TARGET_INSTANCE_REQUIRED_TEXT_INVALID:" + field
    for field in ("source_evidence", "constraints"):
        if out[field] is None:
            return None, "TARGET_INSTANCE_REQUIRED_VALUE_MISSING:" + field
    return out, None


def route(state: Mapping[str, Any], *, repo_root: str | Path | None = None) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        return _fail("STATE_NOT_OBJECT")
    target, error = _validate_target_instance(state.get("target_instance"))
    if error is not None or target is None:
        return _fail(error or "TARGET_INSTANCE_INVALID")

    root = _root(repo_root)
    try:
        profile = _load_json_bound(root, PROFILE_PATH, PROFILE_BLOB)
        contract = _contract(root)
    except Exception as exc:
        return _fail("TARGET_BINDING_DEPENDENCY_INVALID:" + type(exc).__name__)

    if profile.get("behavior_id") != target_sem.BEHAVIOR_ID:
        return _fail("PROFILE_BEHAVIOR_ID_MISMATCH")

    semantic = target_sem.certify(contract, _semantic_binding(contract))
    if semantic.get("pass") is not True:
        return _fail(
            "TARGET_SEMANTIC_CERTIFICATE_FAILED",
            target_semantic_status=semantic.get("status"),
            target_semantic_errors=deepcopy(semantic.get("errors") or []),
        )

    delegated = deepcopy(dict(state))
    delegated.pop("target_instance", None)
    out = base.route(delegated, repo_root=root)
    if not isinstance(out, Mapping):
        return _fail("V3_RESULT_NOT_OBJECT")

    result = deepcopy(dict(out))
    result["schema"] = SCHEMA
    result["target_instance_binding"] = {
        "behavior_id": target_sem.BEHAVIOR_ID,
        "target_instance_sha256": _digest(target),
        "contract_sha256": semantic.get("contract_sha256"),
        "contract_registry_git_blob_sha": CONTRACT_REGISTRY_BLOB,
        "profile_git_blob_sha": PROFILE_BLOB,
        "target_fields": list(TARGET_FIELDS),
        "exact_target_instance": target,
        "arbitrary_prompt_semantic_completeness": False,
        "target_binding_authority": True,
    }
    result["target_semantic_certificate"] = {
        "schema": semantic.get("schema"),
        "status": semantic.get("status"),
        "pass": semantic.get("pass") is True,
        "claim_scope": deepcopy(semantic.get("claim_scope")),
        "global_leaf_closure": False,
        "terminal_authority": False,
    }
    result["target_instance_bound"] = True
    result["semantic_truth_authority"] = False
    result["quality_authority"] = False
    result["acceptance_authority"] = False
    result["promotion_authority"] = False
    result["terminal_authority"] = False
    result["terminal_credit_delta"] = 0
    result["incremental_spend_usd"] = 0
    return result


if __name__ == "__main__":
    print(json.dumps(_base("NOT_EXECUTED"), indent=2, sort_keys=True))
