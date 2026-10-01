#!/usr/bin/env python3
"""Fail-closed continuous OBS admission for Project Brain work.

This is an execution membrane, not a scheduler.  Work receives authority only
while every material canonical and external dependency it declares remains
current.  Material unknowns fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from datetime import datetime, timezone
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CONTINUOUS_OBS_CONTEXT_V1"
REQUIRED_STATE_PATHS = (
    "canonical/CANONICAL_POINTER.json",
    "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json",
    "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json",
)
REQUIRED_LAYERS = (
    "goal","capability","blocker","solution","verification",
    "inherited_system","obs_process",
)
ALLOWED_CLASSES = {
    "CANONICAL_STATE","EXECUTION_AUTHORITY","VERIFICATION_RECEIPT",
    "EXECUTION_SURFACE","TOOL_OR_SERVICE","DATA_SOURCE","PACKAGE_OR_MODEL",
    "NETWORK_OR_CAPACITY","COST_OR_RATE_LIMIT","BENCHMARK_OR_TARGET_VERSION",
    "EXTERNAL_WORLD_STATE",
}
ALLOWED_VOLATILITY = {"STATIC","VOLATILE"}
INFORMATION_MODES = {"OPEN_DISCOVERY","EXACT_FETCH_ONLY","NO_EXTERNAL_INFORMATION"}
INFORMATION_ACTIONS = {"EXACT_FETCH","DISCOVERY_SEARCH","EXTERNAL_TOOL","PACKAGE_INSTALL","PLANNER"}
ALLOWED_SCOPE = {"GLOBAL","ACCOUNT_SPECIFIC","LOCAL","REGION_SPECIFIC","TASK_SPECIFIC"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing")
    raw=value.strip()
    if raw.endswith("Z"):
        raw=raw[:-1]+"+00:00"
    dt=datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        raise ValueError("naive")
    return dt.astimezone(timezone.utc)


def _sha(path: pathlib.Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(x, str) and bool(x.strip()) for x in value
    )


def validate_context(
    context: Any,
    *,
    root: pathlib.Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors: list[str] = []
    if not isinstance(context, dict):
        return {"pass":False,"errors":["CONTINUOUS_OBS_CONTEXT_MISSING"]}
    if context.get("schema") != SCHEMA:
        errors.append("CONTINUOUS_OBS_SCHEMA_INVALID")
    if context.get("status") != "CURRENT":
        errors.append("CONTINUOUS_OBS_STATUS_NOT_CURRENT")
    if context.get("dependency_inventory_complete") is not True:
        errors.append("DEPENDENCY_INVENTORY_NOT_COMPLETE")
    if context.get("material_world_state_dependencies_complete") is not True:
        errors.append("MATERIAL_WORLD_STATE_INVENTORY_NOT_COMPLETE")
    if context.get("information_boundary_complete") is not True:
        errors.append("INFORMATION_BOUNDARY_NOT_COMPLETE")
    info=context.get("information_policy")
    if not isinstance(info,dict):
        errors.append("INFORMATION_POLICY_MISSING")
    else:
        if info.get("mode") not in INFORMATION_MODES:
            errors.append("INFORMATION_POLICY_MODE_INVALID")
        if not isinstance(info.get("allowed_exact_sources"),list):
            errors.append("INFORMATION_ALLOWED_EXACT_SOURCES_INVALID")
        if not isinstance(info.get("allowed_external_tool_kinds"),list):
            errors.append("INFORMATION_ALLOWED_EXTERNAL_TOOL_KINDS_INVALID")
    unknown=context.get("unknown_material_dependencies")
    if not isinstance(unknown, list) or unknown:
        errors.append("UNKNOWN_MATERIAL_DEPENDENCIES_PRESENT")
    if context.get("stale_authority_absent") is not True:
        errors.append("STALE_AUTHORITY_NOT_CLEARED")
    if context.get("valid_proof_action_priority") is not True:
        errors.append("PROOF_ACTION_PRIORITY_NOT_ASSERTED")

    layers=context.get("obs_layers_current")
    if not isinstance(layers, dict):
        errors.append("OBS_LAYERS_CURRENT_MISSING")
    else:
        for layer in REQUIRED_LAYERS:
            if layers.get(layer) is not True:
                errors.append("OBS_LAYER_NOT_CURRENT:"+layer)

    pointer_path=root/"canonical/CANONICAL_POINTER.json"
    try:
        pointer=json.loads(pointer_path.read_text(encoding="utf-8"))
        generation=str(pointer.get("canonical_generation") or "")
    except Exception:
        generation=""
        errors.append("CANONICAL_POINTER_UNREADABLE")
    if not generation or context.get("canonical_generation") != generation:
        errors.append("CANONICAL_GENERATION_MISMATCH")

    state=context.get("canonical_state_dependencies")
    if not isinstance(state, list):
        errors.append("CANONICAL_STATE_DEPENDENCIES_MISSING")
        state=[]
    by_path={}
    for i,item in enumerate(state):
        if not isinstance(item, dict):
            errors.append(f"CANONICAL_STATE_DEPENDENCY_INVALID:{i}")
            continue
        rel=str(item.get("path") or "")
        digest=str(item.get("sha256") or "").lower()
        by_path[rel]=item
        if not rel or rel.startswith("/") or ".." in pathlib.PurePosixPath(rel).parts:
            errors.append(f"CANONICAL_STATE_PATH_INVALID:{i}")
            continue
        if _SHA256.fullmatch(digest) is None:
            errors.append(f"CANONICAL_STATE_DIGEST_INVALID:{rel}")
            continue
        p=(root/rel).resolve()
        try:
            p.relative_to(root.resolve())
        except ValueError:
            errors.append(f"CANONICAL_STATE_PATH_OUTSIDE_ROOT:{rel}")
            continue
        if not p.is_file():
            errors.append(f"CANONICAL_STATE_PATH_MISSING:{rel}")
        elif _sha(p) != digest:
            errors.append(f"CANONICAL_STATE_CHANGED:{rel}")
    for rel in REQUIRED_STATE_PATHS:
        if rel not in by_path:
            errors.append("REQUIRED_CANONICAL_STATE_NOT_BOUND:"+rel)

    deps=context.get("dependencies")
    if not isinstance(deps, list):
        errors.append("MATERIAL_DEPENDENCY_LIST_MISSING")
        deps=[]
    seen=set()
    for i,dep in enumerate(deps):
        if not isinstance(dep, dict):
            errors.append(f"DEPENDENCY_INVALID:{i}")
            continue
        did=str(dep.get("dependency_id") or "").strip()
        if not did:
            errors.append(f"DEPENDENCY_ID_MISSING:{i}")
        elif did in seen:
            errors.append("DEPENDENCY_ID_DUPLICATE:"+did)
        seen.add(did)
        cls=str(dep.get("class") or "")
        if cls not in ALLOWED_CLASSES:
            errors.append(f"DEPENDENCY_CLASS_INVALID:{did or i}")
        material=dep.get("material")
        if material is not True and material is not False:
            errors.append(f"DEPENDENCY_MATERIAL_NOT_BOOLEAN:{did or i}")
            material=True
        volatility=str(dep.get("volatility") or "")
        if volatility not in ALLOWED_VOLATILITY:
            errors.append(f"DEPENDENCY_VOLATILITY_INVALID:{did or i}")
        scope=str(dep.get("scope") or "")
        if scope not in ALLOWED_SCOPE:
            errors.append(f"DEPENDENCY_SCOPE_INVALID:{did or i}")
        status=str(dep.get("status") or "")
        if material and status != "READY":
            errors.append(f"MATERIAL_DEPENDENCY_NOT_READY:{did or i}:{status or 'MISSING'}")
        if material and not _nonempty_list(dep.get("evidence")):
            errors.append(f"MATERIAL_DEPENDENCY_EVIDENCE_MISSING:{did or i}")
        if volatility == "VOLATILE":
            try:
                observed=_utc(dep.get("observed_at_utc"))
            except Exception:
                errors.append(f"VOLATILE_DEPENDENCY_OBSERVED_AT_INVALID:{did or i}")
                observed=None
            max_age=dep.get("max_age_seconds")
            if not isinstance(max_age,(int,float)) or isinstance(max_age,bool) or not (0 < float(max_age) <= 86400):
                errors.append(f"VOLATILE_DEPENDENCY_MAX_AGE_INVALID:{did or i}")
            elif observed is not None:
                age=(now-observed).total_seconds()
                if age < -300:
                    errors.append(f"VOLATILE_DEPENDENCY_TIMESTAMP_IN_FUTURE:{did or i}")
                elif age > float(max_age):
                    errors.append(f"VOLATILE_DEPENDENCY_STALE:{did or i}")

    return {
        "schema":"PROJECT_BRAIN_CONTINUOUS_OBS_ADMISSION_V1",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "checked_at_utc":now.isoformat(),
        "canonical_generation":generation,
        "dependency_count":len(deps),
        "rule":"NO_MATERIAL_UNKNOWN_OR_STALE_DEPENDENCY_MAY_AUTHORIZE_WORK",
    }


def authorize_information_action(
    context: Any,
    action: Mapping[str, Any],
    *,
    root: pathlib.Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    base=validate_context(context,root=root,now=now)
    errors=list(base.get("errors") or [])
    kind=str(action.get("kind") or "")
    source=str(action.get("source") or "")
    tool_kind=str(action.get("tool_kind") or "")
    if kind not in INFORMATION_ACTIONS:
        errors.append("INFORMATION_ACTION_KIND_INVALID")
    info=context.get("information_policy") if isinstance(context,dict) else None
    if isinstance(info,dict):
        mode=info.get("mode")
        allowed=[str(x) for x in info.get("allowed_exact_sources") or [] if str(x)]
        allowed_tools=[str(x) for x in info.get("allowed_external_tool_kinds") or [] if str(x)]
        if mode=="NO_EXTERNAL_INFORMATION":
            errors.append("EXTERNAL_INFORMATION_FORBIDDEN")
        elif mode=="EXACT_FETCH_ONLY":
            if kind!="EXACT_FETCH":
                errors.append("DISCOVERY_FORBIDDEN_EXACT_FETCH_ONLY")
            elif not source or source not in allowed:
                errors.append("EXACT_FETCH_SOURCE_NOT_PREDECLARED")
        elif mode=="OPEN_DISCOVERY":
            if tool_kind and allowed_tools and tool_kind not in allowed_tools:
                errors.append("EXTERNAL_TOOL_KIND_NOT_ALLOWED")
    return {
        "schema":"PROJECT_BRAIN_CONTINUOUS_OBS_INFORMATION_ADMISSION_V1",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "action":{"kind":kind,"source":source,"tool_kind":tool_kind},
        "mode":info.get("mode") if isinstance(info,dict) else None,
        "checked_at_utc":base.get("checked_at_utc"),
    }


def context_at_path(doc: Mapping[str, Any], dotted: str) -> Any:
    cur: Any=doc
    for key in dotted.split("."):
        if not isinstance(cur, Mapping) or key not in cur:
            return None
        cur=cur[key]
    return cur


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=pathlib.Path,default=pathlib.Path.cwd())
    ap.add_argument("--work-file",type=pathlib.Path,required=True)
    ap.add_argument("--context-path",default="continuous_obs")
    ap.add_argument("--receipt",type=pathlib.Path)
    args=ap.parse_args()
    root=args.root.resolve()
    work=json.loads(args.work_file.read_text(encoding="utf-8"))
    verdict=validate_context(context_at_path(work,args.context_path),root=root)
    raw=json.dumps(verdict,indent=2,sort_keys=True)+"\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True,exist_ok=True)
        args.receipt.write_text(raw,encoding="utf-8")
    print(raw,end="")
    return 0 if verdict["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
