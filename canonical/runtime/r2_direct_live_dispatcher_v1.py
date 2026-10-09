"""Stable content-addressed R2 direct live dispatcher V1.

The existing verified direct router is treated as a frozen baseline carrier.
Future independently admitted routes are data in the immutable live-state target,
not new Python router versions. Baseline behavior is preserved exactly unless a
dynamic route also engages the same request, in which case dispatch fails closed.

The mutable CURRENT pointer is authoritative by path identity. Its immutable
target, baseline runtime, dynamic runtimes, and dynamic verification receipts are
all exact Git-blob bound.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import importlib.util
import inspect
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_LIVE_DISPATCHER_V1"
POINTER_SCHEMA = "PROJECT_BRAIN_CURRENT_R2_DIRECT_LIVE_STATE_POINTER_V1"
STATE_SCHEMA = "PROJECT_BRAIN_R2_DIRECT_LIVE_STATE_V1"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_POINTER = ROOT / "canonical/governance/CURRENT_R2_DIRECT_LIVE_STATE.json"


class DirectLiveDispatcherError(ValueError):
    pass


def _base(status: str, *, passed: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "matched": False,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "direct_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _inside(
    root: Path,
    raw: Any,
    *,
    prefix: str | None = None,
    label: str = "PATH",
) -> Path:
    value = str(raw or "").strip()
    if not value:
        raise DirectLiveDispatcherError(label + "_REQUIRED")
    rel = Path(value)
    if rel.is_absolute() or ".." in rel.parts:
        raise DirectLiveDispatcherError(label + "_INVALID")
    if prefix is not None and not value.startswith(prefix):
        raise DirectLiveDispatcherError(label + "_PREFIX_INVALID:" + value)
    resolved_root = root.resolve()
    path = (resolved_root / rel).resolve()
    if path == resolved_root or resolved_root not in path.parents:
        raise DirectLiveDispatcherError(label + "_OUTSIDE_REPOSITORY")
    if not path.is_file() or path.is_symlink():
        raise DirectLiveDispatcherError(label + "_FILE_REQUIRED:" + value)
    return path


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DirectLiveDispatcherError(label + "_JSON_INVALID") from exc
    if not isinstance(value, Mapping):
        raise DirectLiveDispatcherError(label + "_JSON_NOT_OBJECT")
    return dict(value)


def _verify_blob(
    root: Path,
    rel: Any,
    expected: Any,
    *,
    prefix: str,
    label: str,
) -> Path:
    path = _inside(root, rel, prefix=prefix, label=label)
    expected_sha = str(expected or "").strip()
    if not expected_sha:
        raise DirectLiveDispatcherError(label + "_BLOB_SHA_REQUIRED")
    observed = _git_blob_sha(path)
    if observed != expected_sha:
        raise DirectLiveDispatcherError(
            label + "_BLOB_MISMATCH:" + str(rel)
        )
    return path


def load_state(
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    pointer = (
        Path(pointer_path).resolve()
        if pointer_path is not None
        else root / "canonical/governance/CURRENT_R2_DIRECT_LIVE_STATE.json"
    )
    pointer_doc = _load_json(pointer, label="CURRENT_LIVE_POINTER")
    if pointer_doc.get("schema") != POINTER_SCHEMA:
        raise DirectLiveDispatcherError("CURRENT_LIVE_POINTER_SCHEMA_INVALID")
    if pointer_doc.get("status") != "ACTIVE_CURRENT_R2_DIRECT_LIVE_STATE_POINTER":
        raise DirectLiveDispatcherError("CURRENT_LIVE_POINTER_NOT_ACTIVE")
    if pointer_doc.get("binding_semantics") != (
        "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND"
    ):
        raise DirectLiveDispatcherError(
            "CURRENT_LIVE_POINTER_BINDING_SEMANTICS_INVALID"
        )

    target = pointer_doc.get("target")
    if not isinstance(target, Mapping):
        raise DirectLiveDispatcherError("CURRENT_LIVE_POINTER_TARGET_INVALID")
    target_path = _verify_blob(
        root,
        target.get("path"),
        target.get("git_blob_sha"),
        prefix="canonical/governance/",
        label="CURRENT_LIVE_STATE_TARGET",
    )
    state = _load_json(target_path, label="R2_DIRECT_LIVE_STATE")
    if target.get("schema") != STATE_SCHEMA or state.get("schema") != STATE_SCHEMA:
        raise DirectLiveDispatcherError("R2_DIRECT_LIVE_STATE_SCHEMA_INVALID")
    if state.get("status") != "ACTIVE_R2_DIRECT_LIVE_STATE":
        raise DirectLiveDispatcherError("R2_DIRECT_LIVE_STATE_NOT_ACTIVE")
    generation = state.get("generation")
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        raise DirectLiveDispatcherError("R2_DIRECT_LIVE_STATE_GENERATION_INVALID")

    baseline = state.get("baseline")
    if not isinstance(baseline, Mapping):
        raise DirectLiveDispatcherError("R2_DIRECT_LIVE_BASELINE_INVALID")
    for field in (
        "runtime_path",
        "runtime_git_blob_sha",
        "preflight_callable",
        "run_callable",
        "declared_route_count",
        "declared_route_ids",
    ):
        if field not in baseline:
            raise DirectLiveDispatcherError(
                "R2_DIRECT_LIVE_BASELINE_FIELD_MISSING:" + field
            )
    declared_ids = baseline.get("declared_route_ids")
    declared_count = baseline.get("declared_route_count")
    if (
        not isinstance(declared_ids, list)
        or not declared_ids
        or any(not isinstance(x, str) or not x for x in declared_ids)
        or len(declared_ids) != len(set(declared_ids))
        or isinstance(declared_count, bool)
        or not isinstance(declared_count, int)
        or declared_count != len(declared_ids)
    ):
        raise DirectLiveDispatcherError("R2_DIRECT_LIVE_BASELINE_ROUTE_SET_INVALID")
    _verify_blob(
        root,
        baseline.get("runtime_path"),
        baseline.get("runtime_git_blob_sha"),
        prefix="canonical/runtime/",
        label="R2_DIRECT_LIVE_BASELINE_RUNTIME",
    )

    dynamic = state.get("dynamic_routes")
    if not isinstance(dynamic, list):
        raise DirectLiveDispatcherError("R2_DIRECT_LIVE_DYNAMIC_ROUTES_INVALID")
    seen: set[str] = set(declared_ids)
    clean_dynamic: list[dict[str, Any]] = []
    for index, raw in enumerate(dynamic):
        if not isinstance(raw, Mapping):
            raise DirectLiveDispatcherError(
                "R2_DIRECT_LIVE_DYNAMIC_ROUTE_NOT_OBJECT:" + str(index)
            )
        row = dict(raw)
        route_id = str(row.get("route_id") or "")
        if not route_id:
            raise DirectLiveDispatcherError(
                "R2_DIRECT_LIVE_DYNAMIC_ROUTE_ID_REQUIRED:" + str(index)
            )
        if route_id in seen:
            raise DirectLiveDispatcherError(
                "R2_DIRECT_LIVE_ROUTE_ID_COLLISION:" + route_id
            )
        seen.add(route_id)
        for field in (
            "runtime_path",
            "runtime_git_blob_sha",
            "preflight_callable",
            "run_callable",
            "verification_path",
            "verification_git_blob_sha",
        ):
            if not isinstance(row.get(field), str) or not str(row[field]).strip():
                raise DirectLiveDispatcherError(
                    "R2_DIRECT_LIVE_DYNAMIC_FIELD_INVALID:"
                    + route_id
                    + ":"
                    + field
                )
        _verify_blob(
            root,
            row["runtime_path"],
            row["runtime_git_blob_sha"],
            prefix="canonical/runtime/",
            label="R2_DIRECT_LIVE_DYNAMIC_RUNTIME_" + route_id,
        )
        _verify_blob(
            root,
            row["verification_path"],
            row["verification_git_blob_sha"],
            prefix="canonical/verification/",
            label="R2_DIRECT_LIVE_DYNAMIC_VERIFY_" + route_id,
        )
        if row.get("semantic_open_barrier") not in (True, False, None):
            raise DirectLiveDispatcherError(
                "R2_DIRECT_LIVE_DYNAMIC_BARRIER_INVALID:" + route_id
            )
        clean_dynamic.append(row)

    out = deepcopy(state)
    out["baseline"] = deepcopy(dict(baseline))
    out["dynamic_routes"] = clean_dynamic
    out["_target_path"] = str(target.get("path"))
    out["_target_git_blob_sha"] = str(target.get("git_blob_sha"))
    return out


def _load_module(path: Path, *, label: str):
    name = "_brain_r2_live_" + sha1(
        (str(path) + ":" + _git_blob_sha(path)).encode("utf-8")
    ).hexdigest()
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DirectLiveDispatcherError(label + "_MODULE_SPEC_INVALID")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise DirectLiveDispatcherError(
            label + "_MODULE_IMPORT_FAILED:" + type(exc).__name__ + ":" + str(exc)
        ) from exc
    return module


def _callable(module: Any, name: Any, *, label: str):
    raw = str(name or "").strip()
    if not raw:
        raise DirectLiveDispatcherError(label + "_CALLABLE_REQUIRED")
    current = module
    try:
        for part in raw.split("."):
            current = getattr(current, part)
    except AttributeError as exc:
        raise DirectLiveDispatcherError(
            label + "_CALLABLE_MISSING:" + raw
        ) from exc
    if not callable(current):
        raise DirectLiveDispatcherError(label + "_NOT_CALLABLE:" + raw)
    return current


def _invoke(fn, request: Mapping[str, Any], repo_root: Path):
    signature = inspect.signature(fn)
    if "repo_root" in signature.parameters:
        return fn(request, repo_root=repo_root)
    return fn(request)


def _runtime_row(
    row: Mapping[str, Any],
    *,
    root: Path,
    label: str,
) -> tuple[Any, Any]:
    path = _verify_blob(
        root,
        row.get("runtime_path"),
        row.get("runtime_git_blob_sha"),
        prefix="canonical/runtime/",
        label=label + "_RUNTIME",
    )
    module = _load_module(path, label=label)
    return (
        _callable(module, row.get("preflight_callable"), label=label + "_PREFLIGHT"),
        _callable(module, row.get("run_callable"), label=label + "_RUN"),
    )


def _preflight_row(
    row: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    root: Path,
    label: str,
) -> dict[str, Any]:
    preflight_fn, _ = _runtime_row(row, root=root, label=label)
    out = _invoke(preflight_fn, request, root)
    if not isinstance(out, Mapping):
        raise DirectLiveDispatcherError(label + "_PREFLIGHT_RESULT_NOT_OBJECT")
    return dict(out)


def _engaged(out: Mapping[str, Any]) -> bool:
    return (
        out.get("matched") is True
        or out.get("direct_route_semantic_open") is True
    )


def _route_id(out: Mapping[str, Any], fallback: str) -> str:
    return str(out.get("route_id") or fallback)


def _annotate(
    out: Mapping[str, Any],
    *,
    source: str,
    generation: int,
) -> dict[str, Any]:
    result = deepcopy(dict(out))
    result["_live_route_source"] = source
    result["_live_state_generation"] = generation
    result["_live_dispatcher_schema"] = SCHEMA
    return result


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    if not str(request.get("task_id") or "").strip() or not str(
        request.get("goal") or ""
    ).strip():
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}

    root = Path(repo_root).resolve()
    try:
        state = load_state(repo_root=root, pointer_path=pointer_path)
        generation = int(state["generation"])
        baseline = dict(state["baseline"])
        baseline_out = _preflight_row(
            baseline,
            request,
            root=root,
            label="BASELINE",
        )

        dynamic_results: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for row in state["dynamic_routes"]:
            out = _preflight_row(
                row,
                request,
                root=root,
                label="DYNAMIC_" + str(row["route_id"]),
            )
            if _engaged(out):
                dynamic_results.append((row, out))

        baseline_engaged = _engaged(baseline_out)
        if baseline_engaged and dynamic_results:
            matching = [_route_id(baseline_out, "BASELINE")]
            matching.extend(
                _route_id(out, str(row["route_id"]))
                for row, out in dynamic_results
            )
            return {
                **_base("FAIL_CLOSED__DIRECT_ROUTE_COLLISION"),
                "reason": "BASELINE_AND_DYNAMIC_ROUTE_BOTH_ENGAGE",
                "matching_route_ids": sorted(set(matching)),
                "_live_state_generation": generation,
            }

        if baseline_engaged:
            return _annotate(
                baseline_out,
                source="BASELINE",
                generation=generation,
            )

        if len(dynamic_results) > 1:
            return {
                **_base("FAIL_CLOSED__DIRECT_ROUTE_COLLISION"),
                "reason": "MULTIPLE_DYNAMIC_ROUTES_ENGAGE",
                "matching_route_ids": sorted(
                    {
                        _route_id(out, str(row["route_id"]))
                        for row, out in dynamic_results
                    }
                ),
                "_live_state_generation": generation,
            }

        if len(dynamic_results) == 1:
            row, out = dynamic_results[0]
            if out.get("matched") is True:
                return _annotate(
                    out,
                    source="DYNAMIC",
                    generation=generation,
                )
            if out.get("direct_route_semantic_open") is True:
                if row.get("semantic_open_barrier") is True:
                    return _annotate(
                        out,
                        source="DYNAMIC",
                        generation=generation,
                    )
                return {
                    **_base(
                        "FAIL_CLOSED__DYNAMIC_SEMANTIC_OPEN_REQUIRES_BARRIER_AUTHORITY"
                    ),
                    "reason": "DYNAMIC_SEMANTIC_OPEN_NOT_AUTHORIZED_AS_BARRIER",
                    "route_id": str(row["route_id"]),
                    "_live_state_generation": generation,
                }

        return _annotate(
            baseline_out,
            source="BASELINE",
            generation=generation,
        )
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    selected = preflight(
        request,
        repo_root=root,
        pointer_path=pointer_path,
    )
    if selected.get("matched") is not True:
        return selected
    try:
        state = load_state(repo_root=root, pointer_path=pointer_path)
        generation = int(state["generation"])
        source = selected.get("_live_route_source")
        route_id = str(selected.get("route_id") or "")
        if source == "BASELINE":
            row = dict(state["baseline"])
            label = "BASELINE"
        elif source == "DYNAMIC":
            matches = [
                dict(row)
                for row in state["dynamic_routes"]
                if str(row.get("route_id") or "") == route_id
            ]
            if len(matches) != 1:
                raise DirectLiveDispatcherError(
                    "SELECTED_DYNAMIC_ROUTE_NOT_UNIQUE:" + route_id
                )
            row = matches[0]
            label = "DYNAMIC_" + route_id
        else:
            raise DirectLiveDispatcherError("SELECTED_ROUTE_SOURCE_INVALID")

        _, run_fn = _runtime_row(row, root=root, label=label)
        out = _invoke(run_fn, request, root)
        if not isinstance(out, Mapping):
            raise DirectLiveDispatcherError(label + "_RUN_RESULT_NOT_OBJECT")
        result = dict(out)
        observed = str(result.get("route_id") or "")
        if route_id and observed and observed != route_id:
            raise DirectLiveDispatcherError(
                "RUN_ROUTE_ID_MISMATCH:" + route_id + "!=" + observed
            )
        return _annotate(
            result,
            source=str(source),
            generation=generation,
        )
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "route_id": selected.get("route_id"),
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def catalog(
    *,
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    state = load_state(repo_root=repo_root, pointer_path=pointer_path)
    baseline = state["baseline"]
    dynamic = state["dynamic_routes"]
    return {
        "schema": SCHEMA,
        "status": "PASS__R2_DIRECT_LIVE_STATE_LOADED",
        "pass": True,
        "generation": state["generation"],
        "baseline_runtime_path": baseline["runtime_path"],
        "baseline_runtime_git_blob_sha": baseline["runtime_git_blob_sha"],
        "baseline_route_count": baseline["declared_route_count"],
        "baseline_route_ids": deepcopy(baseline["declared_route_ids"]),
        "dynamic_route_count": len(dynamic),
        "dynamic_route_ids": [str(row["route_id"]) for row in dynamic],
        "future_route_source_edit_required": False,
        "future_fixed_point_edit_required": False,
        "dynamic_collision_policy": (
            "BASELINE_OR_DYNAMIC_OVERLAP_FAILS_CLOSED__"
            "MULTIPLE_DYNAMIC_ENGAGEMENT_FAILS_CLOSED"
        ),
        "terminal_authority": False,
    }
