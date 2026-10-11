from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PYTHON_INTERPROCEDURAL_VALUE_PROVENANCE_V1"


class ValueProvenanceError(RuntimeError):
    pass


def _rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return str(path.relative_to(repo)).replace("\\", "/")


def _safe_file(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    path = (repo / str(raw or "")).resolve()
    if (
        path == repo
        or repo not in path.parents
        or not path.is_file()
        or path.is_symlink()
        or path.suffix != ".py"
    ):
        raise ValueProvenanceError("FILE_INVALID")
    return path


def _safe_dir(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    path = (repo / str(raw or ".")).resolve()
    if path != repo and repo not in path.parents:
        raise ValueProvenanceError("PATH_OUTSIDE_REPOSITORY")
    if not path.is_dir() or path.is_symlink():
        raise ValueProvenanceError("DIRECTORY_INVALID")
    return path


def _trace_one(
    repo: pathlib.Path,
    source_root: pathlib.Path,
    test_path: pathlib.Path,
    timeout_s: int,
    max_events: int,
) -> dict[str, Any]:
    code = r"""
import hashlib
import json
import pathlib
import runpy
import sys

repo = pathlib.Path(sys.argv[1]).resolve()
source_root = pathlib.Path(sys.argv[2]).resolve()
target = pathlib.Path(sys.argv[3]).resolve()
cap = int(sys.argv[4])
events = []
frame_ids = {}
next_id = 1
truncated = False

def fingerprint(value):
    try:
        if value is None or isinstance(value, (bool, int, float, str)):
            raw = json.dumps(
                [type(value).__name__, value],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        elif (
            isinstance(value, (tuple, list))
            and len(value) <= 16
            and all(x is None or isinstance(x, (bool, int, float, str)) for x in value)
        ):
            raw = json.dumps(
                [type(value).__name__, list(value)],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        else:
            raw = type(value).__module__ + "." + type(value).__qualname__
    except Exception:
        raw = type(value).__name__
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def inside_source(path):
    return path == source_root or source_root in path.parents

def frame_id(frame):
    global next_id
    key = id(frame)
    if key not in frame_ids:
        frame_ids[key] = next_id
        next_id += 1
    return frame_ids[key]

def trace(frame, event, arg):
    global truncated
    if len(events) >= cap:
        truncated = True
        return trace
    try:
        path = pathlib.Path(frame.f_code.co_filename).resolve()
    except Exception:
        return trace
    if (
        not path.is_file()
        or not inside_source(path)
        or path == target
        or path.suffix != ".py"
    ):
        return trace
    rel = str(path.relative_to(repo)).replace("\\", "/")
    if event == "call":
        parent = frame.f_back
        parent_frame_id = None
        parent_path = None
        parent_line = None
        parent_function = None
        if parent is not None:
            try:
                caller_path = pathlib.Path(parent.f_code.co_filename).resolve()
                if (
                    caller_path.is_file()
                    and (caller_path == repo or repo in caller_path.parents)
                ):
                    parent_frame_id = frame_id(parent)
                    parent_path = str(caller_path.relative_to(repo)).replace("\\", "/")
                    parent_line = parent.f_lineno
                    parent_function = parent.f_code.co_name
            except Exception:
                pass
        argc = frame.f_code.co_argcount + frame.f_code.co_kwonlyargcount
        names = list(frame.f_code.co_varnames[:argc])
        events.append(
            {
                "event": "call",
                "frame_id": frame_id(frame),
                "parent_frame_id": parent_frame_id,
                "path": rel,
                "function": frame.f_code.co_name,
                "line": frame.f_lineno,
                "caller_path": parent_path,
                "caller_line": parent_line,
                "caller_function": parent_function,
                "args": {
                    name: fingerprint(frame.f_locals[name])
                    for name in names
                    if name in frame.f_locals
                },
            }
        )
    elif event == "return":
        events.append(
            {
                "event": "return",
                "frame_id": frame_id(frame),
                "path": rel,
                "function": frame.f_code.co_name,
                "line": frame.f_lineno,
                "return_fingerprint": fingerprint(arg),
            }
        )
    elif event == "exception":
        exc_type = (
            arg[0].__name__
            if isinstance(arg, tuple) and arg and hasattr(arg[0], "__name__")
            else "Exception"
        )
        events.append(
            {
                "event": "exception",
                "frame_id": frame_id(frame),
                "path": rel,
                "function": frame.f_code.co_name,
                "line": frame.f_lineno,
                "exception_type": exc_type,
            }
        )
    return trace

ok = True
error = ""
sys.settrace(trace)
try:
    runpy.run_path(str(target), run_name="__main__")
except SystemExit as exc:
    ok = exc.code in (None, 0, False)
    if not ok:
        error = "SystemExit:" + str(exc.code)
except BaseException as exc:
    ok = False
    error = type(exc).__name__ + ":" + str(exc)
finally:
    sys.settrace(None)

print(
    "__BRAIN_PROVENANCE__"
    + json.dumps(
        {
            "pass": ok,
            "events": events,
            "truncated": truncated,
            "error": error,
        },
        sort_keys=True,
    )
)
"""
    try:
        run = subprocess.run(
            [
                sys.executable,
                "-c",
                code,
                str(repo),
                str(source_root),
                str(test_path),
                str(max_events),
            ],
            cwd=repo,
            text=True,
            capture_output=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueProvenanceError("TEST_TIMEOUT") from exc

    marker = "__BRAIN_PROVENANCE__"
    rows = [line for line in run.stdout.splitlines() if line.startswith(marker)]
    if not rows:
        raise ValueProvenanceError("TRACE_OUTPUT_MISSING")
    out = json.loads(rows[-1][len(marker) :])
    out["returncode"] = run.returncode
    return out


def _callsite(path: pathlib.Path, line: int) -> dict[str, Any] | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception:
        return None

    candidates: list[tuple[ast.Call, ast.AST | None]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (
            getattr(node, "lineno", 0)
            <= line
            <= getattr(node, "end_lineno", getattr(node, "lineno", 0))
        ):
            continue
        owner: ast.AST | None = None
        for statement in ast.walk(tree):
            if not isinstance(statement, (ast.Assign, ast.AnnAssign, ast.Return)):
                continue
            if not (
                getattr(statement, "lineno", 0)
                <= line
                <= getattr(
                    statement,
                    "end_lineno",
                    getattr(statement, "lineno", 0),
                )
            ):
                continue
            if any(child is node for child in ast.walk(statement)):
                owner = statement
                break
        candidates.append((node, owner))

    # Multiple calls on one source line are deliberately unresolved rather than guessed.
    if len(candidates) != 1:
        return None

    call, owner = candidates[0]
    arg_names = [arg.id if isinstance(arg, ast.Name) else None for arg in call.args]
    target_names: list[str] = []
    sink: str | None = None
    if isinstance(owner, ast.Assign):
        for target in owner.targets:
            if isinstance(target, ast.Name):
                target_names.append(target.id)
    elif isinstance(owner, ast.AnnAssign) and isinstance(owner.target, ast.Name):
        target_names.append(owner.target.id)
    elif isinstance(owner, ast.Return):
        sink = "<return>"

    return {
        "arg_names": arg_names,
        "target_names": target_names,
        "sink": sink,
    }


def run(args: Mapping[str, Any], root: str | os.PathLike[str]) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise ValueProvenanceError("ARGS_NOT_OBJECT")

    repo = pathlib.Path(root).resolve()
    source_root = _safe_dir(repo, args.get("source_root", "."))
    tests = [_safe_file(repo, raw) for raw in (args.get("test_paths") or [])]
    if not tests:
        raise ValueProvenanceError("TEST_PATHS_REQUIRED")

    timeout_s = max(1, min(int(args.get("timeout_s", 20)), 120))
    max_events = max(50, min(int(args.get("max_trace_events", 100000)), 1000000))

    traces = [
        {
            "test_path": _rel(repo, test),
            **_trace_one(repo, source_root, test, timeout_s, max_events),
        }
        for test in tests
    ]

    calls: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for test_index, trace in enumerate(traces):
        calls_by_frame: dict[int, dict[str, Any]] = {}
        returns_by_frame: dict[int, dict[str, Any]] = {}
        for event in trace["events"]:
            if event["event"] == "call":
                calls_by_frame[int(event["frame_id"])] = event
            elif event["event"] == "return":
                returns_by_frame[int(event["frame_id"])] = event

        for frame_id, call in calls_by_frame.items():
            caller_path = call.get("caller_path")
            caller_line = call.get("caller_line")
            if not caller_path or caller_line is None:
                continue
            path = (repo / str(caller_path)).resolve()
            if not path.is_file() or repo not in path.parents:
                continue
            site = _callsite(path, int(caller_line))
            if site is None:
                continue

            callee_args = list((call.get("args") or {}).keys())
            call_edges: list[dict[str, Any]] = []
            for index, caller_name in enumerate(site["arg_names"]):
                if caller_name is None or index >= len(callee_args):
                    continue
                callee_name = callee_args[index]
                call_edges.append(
                    {
                        "kind": "ARGUMENT",
                        "from": {
                            "path": caller_path,
                            "function": call.get("caller_function"),
                            "name": caller_name,
                            "line": caller_line,
                        },
                        "to": {
                            "path": call["path"],
                            "function": call["function"],
                            "name": callee_name,
                            "line": call["line"],
                        },
                        "value_fingerprint": call["args"].get(callee_name),
                    }
                )

            returned = returns_by_frame.get(frame_id)
            if returned is not None:
                for name in site["target_names"]:
                    call_edges.append(
                        {
                            "kind": "RETURN_BINDING",
                            "from": {
                                "path": call["path"],
                                "function": call["function"],
                                "name": "<return>",
                                "line": returned["line"],
                            },
                            "to": {
                                "path": caller_path,
                                "function": call.get("caller_function"),
                                "name": name,
                                "line": caller_line,
                            },
                            "value_fingerprint": returned["return_fingerprint"],
                        }
                    )
                if site["sink"] is not None:
                    call_edges.append(
                        {
                            "kind": "RETURN_TO_RETURN",
                            "from": {
                                "path": call["path"],
                                "function": call["function"],
                                "name": "<return>",
                                "line": returned["line"],
                            },
                            "to": {
                                "path": caller_path,
                                "function": call.get("caller_function"),
                                "name": "<return>",
                                "line": caller_line,
                            },
                            "value_fingerprint": returned["return_fingerprint"],
                        }
                    )

            edges.extend(call_edges)
            calls.append(
                {
                    "test_index": test_index,
                    "callee_path": call["path"],
                    "callee_function": call["function"],
                    "caller_path": caller_path,
                    "caller_function": call.get("caller_function"),
                    "caller_line": caller_line,
                    "provenance_edge_count": len(call_edges),
                }
            )

    result = {
        "schema": SCHEMA,
        "status": "PASS__BOUNDED_INTERPROCEDURAL_VALUE_PROVENANCE",
        "pass": True,
        "test_traces": traces,
        "dynamic_calls": calls,
        "value_provenance_edges": edges,
        "edge_count": len(edges),
        "trace_truncated": any(bool(trace.get("truncated")) for trace in traces),
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NO_GENERAL_VALUE_IDENTITY_OR_CAUSALITY_PROOF",
            "NO_ALIAS_OR_MUTABLE_OBJECT_VALUE_PROVENANCE_COMPLETENESS",
            "NO_MULTI_CALLSITE_SAME_LINE_DISAMBIGUATION",
            "NO_NON_PYTHON_SUPPORT",
            "NO_PATCH_CORRECTNESS_MERGEABILITY_OR_BENCHMARK_SCORE_CREDIT",
        ],
    }

    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise ValueProvenanceError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["output_path"] = _rel(repo, output)
    result["output_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    result["output_verified"] = True
    return result
