"""Fail-closed ambient repository dependency guard for composition plans.

This guard uses the source-derived direct resource contracts for Astra goal
actions. It rejects a later literal repository read/write whose resource scope
overlaps an earlier write unless the composition contract already declares a
provider dependency on that earlier cycle.

This closes the *undeclared causal edge* class exemplified by the persistent-file
countermodel. It does NOT prove file-content integrity, initial-resource binding,
transitive helper completeness, dynamic capability effects, or runtime
enforcement until integrated and independently replayed.
"""
from __future__ import annotations

import pathlib
from typing import Any

from canonical.runtime.goal_action_resource_contract_compiler_v1 import (
    ROOT,
    compile_contracts,
)

SCHEMA = "PROJECT_BRAIN_COMPOSITION_RESOURCE_DEPENDENCY_GUARD_V1"


class ResourceDependencyError(RuntimeError):
    pass


def _contract_rows() -> dict[str, dict[str, Any]]:
    source = (ROOT / "canonical/runtime/astra_runtime.py").read_text(encoding="utf-8")
    out = compile_contracts(source)
    if out.get("status") != "PASS__DIRECT_RESOURCE_CONTRACT_PARTITION_COMPILED":
        raise ResourceDependencyError("RESOURCE_CONTRACT_COMPILATION_FAILED")
    return {row["action_type"]: row for row in out["rows"]}


def _literal_repo_path(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        if set(value) == {"$result"}:
            return None
        raise ResourceDependencyError("RESOURCE_PATH_OBJECT_UNSUPPORTED")
    if not isinstance(value, str):
        raise ResourceDependencyError("RESOURCE_PATH_NOT_STRING")
    text = value.strip().replace("\\", "/")
    if text.startswith("/"):
        text = text.lstrip("/")
    rel = pathlib.PurePosixPath(text)
    if not text or rel.is_absolute() or ".." in rel.parts:
        raise ResourceDependencyError("RESOURCE_PATH_INVALID:" + text)
    return rel.as_posix()


def _is_result_ref(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"$result"}


def _result_provider_cycle(value: Any) -> int | None:
    if not _is_result_ref(value):
        return None
    spec = value.get("$result")
    if not isinstance(spec, dict):
        raise ResourceDependencyError("RESULT_REFERENCE_INVALID")
    try:
        cycle = int(spec.get("cycle"))
    except Exception as exc:
        raise ResourceDependencyError("RESULT_REFERENCE_CYCLE_INVALID") from exc
    if cycle < 0:
        raise ResourceDependencyError("RESULT_REFERENCE_CYCLE_INVALID")
    return cycle


def _scope(path: str, field: str) -> dict[str, Any]:
    prefix = str(field).lower().endswith(("dir", "root", "prefix"))
    return {"path": path, "prefix": prefix}


def _overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    pa = pathlib.PurePosixPath(a["path"])
    pb = pathlib.PurePosixPath(b["path"])
    if pa == pb:
        return True
    if a["prefix"]:
        try:
            pb.relative_to(pa)
            return True
        except ValueError:
            pass
    if b["prefix"]:
        try:
            pa.relative_to(pb)
            return True
        except ValueError:
            pass
    return False


def _declared_dependency(contract_row: dict[str, Any], provider_cycle: int) -> bool:
    bindings = contract_row.get("provider_bindings") or {}
    if not isinstance(bindings, dict):
        return False
    for binding in bindings.values():
        if not isinstance(binding, dict):
            continue
        try:
            cycle = int(binding.get("cycle"))
        except Exception:
            continue
        if cycle == provider_cycle:
            return True
    return False


def validate_resource_dependencies(
    actions: list[dict[str, Any]],
    composition_contract: list[dict[str, Any]],
    *,
    rows: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(actions, list) or not isinstance(composition_contract, list):
        raise ResourceDependencyError("PLAN_OR_CONTRACT_INVALID")
    rows = rows or _contract_rows()
    if len(actions) != len(composition_contract) + 1:
        raise ResourceDependencyError("ACTION_CONTRACT_LENGTH_MISMATCH")
    if actions[-1].get("type") != "finish":
        raise ResourceDependencyError("FINAL_FINISH_ACTION_REQUIRED")

    prior_writes: list[dict[str, Any]] = []
    compiled = []
    for cycle, contract_row in enumerate(composition_contract):
        action = actions[cycle]
        if not isinstance(action, dict) or not isinstance(contract_row, dict):
            raise ResourceDependencyError("ROW_INVALID:" + str(cycle))
        action_type = str(action.get("type") or "")
        row = rows.get(action_type)
        if not isinstance(row, dict):
            raise ResourceDependencyError("ACTION_RESOURCE_CLASS_UNKNOWN:" + action_type)
        if row.get("status") != "DIRECT_CONTRACTIBLE":
            raise ResourceDependencyError(
                "ACTION_BLOCKED_PENDING_GATEWAY_PROOF:" + action_type
            )
        args = action.get("args") or {}
        if not isinstance(args, dict):
            raise ResourceDependencyError("ACTION_ARGS_INVALID:" + str(cycle))

        row_reads = []
        row_writes = []
        dynamic_refs = []

        for field in row.get("repo_read_argument_fields") or []:
            raw = args.get(field)
            provider_cycle = _result_provider_cycle(raw)
            if provider_cycle is not None:
                if provider_cycle >= cycle:
                    raise ResourceDependencyError(
                        "RESOURCE_RESULT_REFERENCE_NOT_PRIOR:"
                        + str(cycle) + ":" + field
                    )
                if not _declared_dependency(contract_row, provider_cycle):
                    raise ResourceDependencyError(
                        "RESOURCE_RESULT_PROVIDER_NOT_DECLARED:"
                        + str(cycle) + ":" + field + ":" + str(provider_cycle)
                    )
                dynamic_refs.append({
                    "mode": "READ",
                    "field": field,
                    "provider_cycle": provider_cycle,
                })
                continue
            path = _literal_repo_path(raw)
            if path is None:
                continue
            scope = {**_scope(path, field), "mode": "READ", "field": field}
            for prior in prior_writes:
                if _overlap(scope, prior) and not _declared_dependency(
                    contract_row, prior["cycle"]
                ):
                    raise ResourceDependencyError(
                        "UNDECLARED_AMBIENT_RESOURCE_DEPENDENCY:"
                        + str(cycle) + ":READ:" + path
                        + ":PRODUCER_CYCLE:" + str(prior["cycle"])
                    )
            row_reads.append(scope)

        for field in row.get("repo_write_argument_fields") or []:
            raw = args.get(field)
            provider_cycle = _result_provider_cycle(raw)
            if provider_cycle is not None:
                if provider_cycle >= cycle:
                    raise ResourceDependencyError(
                        "RESOURCE_RESULT_REFERENCE_NOT_PRIOR:"
                        + str(cycle) + ":" + field
                    )
                if not _declared_dependency(contract_row, provider_cycle):
                    raise ResourceDependencyError(
                        "RESOURCE_RESULT_PROVIDER_NOT_DECLARED:"
                        + str(cycle) + ":" + field + ":" + str(provider_cycle)
                    )
                dynamic_refs.append({
                    "mode": "WRITE",
                    "field": field,
                    "provider_cycle": provider_cycle,
                })
                continue
            path = _literal_repo_path(raw)
            if path is None:
                continue
            scope = {**_scope(path, field), "mode": "WRITE", "field": field}
            for prior in prior_writes:
                if _overlap(scope, prior) and not _declared_dependency(
                    contract_row, prior["cycle"]
                ):
                    raise ResourceDependencyError(
                        "UNDECLARED_AMBIENT_RESOURCE_DEPENDENCY:"
                        + str(cycle) + ":WRITE:" + path
                        + ":PRODUCER_CYCLE:" + str(prior["cycle"])
                    )
            row_writes.append(scope)

        for item in row_writes:
            prior_writes.append({**item, "cycle": cycle})

        compiled.append({
            "cycle": cycle,
            "action_type": action_type,
            "reads": row_reads,
            "writes": row_writes,
            "dynamic_result_bound_resources": dynamic_refs,
        })

    return {
        "schema": SCHEMA,
        "status": "PASS__NO_UNDECLARED_DIRECT_REPOSITORY_CROSS_STEP_DEPENDENCY",
        "row_count": len(compiled),
        "rows": compiled,
        "residuals": [
            "RESOURCE_CONTENT_HASH_AND_TYPE_BINDING",
            "INITIAL_RESOURCE_SNAPSHOT_BINDING",
            "TRANSITIVE_HELPER_EFFECT_COMPLETENESS",
            "RUNTIME_GATEWAY_ENFORCEMENT",
            "DYNAMIC_CAPABILITY_AND_PROCESS_CONFINEMENT",
            "EXTERNAL_INFORMATION_BROKER_ENFORCEMENT",
        ],
        "no_bypass_credit": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
