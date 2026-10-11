from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
from collections import defaultdict
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PYTHON_INTERPROCEDURAL_VALUE_PROVENANCE_V1"
CAPABILITY_ID = "python.value.provenance.interprocedural.direct.v1"


class ProvenanceError(RuntimeError):
    pass


def _load_sibling(name: str):
    p = pathlib.Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location("_brain_" + name.replace(".", "_"), p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


_LOCALIZER = _load_sibling("python_dynamic_fault_localizer_v1.py")


def _rel(repo: pathlib.Path, p: pathlib.Path) -> str:
    return str(p.relative_to(repo)).replace("\\", "/")


def _safe_dir(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    p = (repo / str(raw or ".")).resolve()
    if p != repo and repo not in p.parents:
        raise ProvenanceError("PATH_OUTSIDE_REPOSITORY")
    if not p.is_dir() or p.is_symlink():
        raise ProvenanceError("DIRECTORY_INVALID")
    return p


def _safe_file(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p == repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix != ".py":
        raise ProvenanceError("FILE_INVALID")
    return p


def _module_name(source_root: pathlib.Path, path: pathlib.Path) -> str:
    rel = path.resolve().relative_to(source_root.resolve())
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _top_level_defs(path: pathlib.Path, module: str) -> dict[str, dict[str, Any]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        params = [x.arg for x in node.args.posonlyargs + node.args.args]
        kwonly = [x.arg for x in node.args.kwonlyargs]
        out[node.name] = {
            "qname": f"{module}:{node.name}",
            "module": module,
            "name": node.name,
            "path": path,
            "lineno": int(node.lineno),
            "end_lineno": int(getattr(node, "end_lineno", node.lineno)),
            "params": params,
            "kwonly_params": kwonly,
            "node": node,
        }
    return out


def _imports(tree: ast.Module) -> dict[str, str]:
    out: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                out[a.asname or a.name.split(".")[0]] = a.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for a in node.names:
                if a.name == "*":
                    continue
                out[a.asname or a.name] = node.module + "." + a.name
    return out


def _resolve_call(
    node: ast.Call,
    module: str,
    imports: Mapping[str, str],
    defs_by_qname: Mapping[str, dict[str, Any]],
) -> str | None:
    f = node.func
    if isinstance(f, ast.Name):
        same = f"{module}:{f.id}"
        if same in defs_by_qname:
            return same
        target = imports.get(f.id)
        if target and "." in target:
            mod, name = target.rsplit(".", 1)
            q = f"{mod}:{name}"
            return q if q in defs_by_qname else None
        return None
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        mod = imports.get(f.value.id)
        if mod:
            q = f"{mod}:{f.attr}"
            return q if q in defs_by_qname else None
    return None


def _name_arguments(call: ast.Call, callee: Mapping[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    params = list(callee["params"])
    for i, arg in enumerate(call.args):
        if i >= len(params):
            break
        if isinstance(arg, ast.Name):
            out.append((arg.id, params[i]))
    for kw in call.keywords:
        if kw.arg and isinstance(kw.value, ast.Name):
            out.append((kw.value.id, kw.arg))
    return out


def _static_flows(source_root: pathlib.Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    files = [
        p.resolve()
        for p in sorted(source_root.rglob("*.py"))
        if p.is_file() and not p.is_symlink() and not p.name.startswith("test_")
    ]
    defs_by_qname: dict[str, dict[str, Any]] = {}
    module_trees: dict[str, tuple[pathlib.Path, ast.Module, dict[str, str]]] = {}
    ambiguous: list[str] = []

    for p in files:
        module = _module_name(source_root, p)
        if not module:
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except Exception:
            continue
        module_trees[module] = (p, tree, _imports(tree))
        for name, d in _top_level_defs(p, module).items():
            q = d["qname"]
            if q in defs_by_qname:
                ambiguous.append(q)
                defs_by_qname.pop(q, None)
            elif q not in ambiguous:
                defs_by_qname[q] = d

    flows: list[dict[str, Any]] = []
    for caller_q, caller in sorted(defs_by_qname.items()):
        module = caller["module"]
        p, tree, imports = module_trees[module]
        fn = caller["node"]
        assignments: list[dict[str, Any]] = []
        calls: list[tuple[int, ast.Call, str]] = []

        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Call):
                producer = _resolve_call(node.value, module, imports, defs_by_qname)
                if producer:
                    assignments.append({
                        "variable": node.targets[0].id,
                        "producer": producer,
                        "line": int(node.lineno),
                    })
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and isinstance(node.value, ast.Call):
                producer = _resolve_call(node.value, module, imports, defs_by_qname)
                if producer:
                    assignments.append({
                        "variable": node.target.id,
                        "producer": producer,
                        "line": int(node.lineno),
                    })
            if isinstance(node, ast.Call):
                callee = _resolve_call(node, module, imports, defs_by_qname)
                if callee:
                    calls.append((int(getattr(node, "lineno", 0)), node, callee))

        for a in assignments:
            for line, call, consumer_q in calls:
                if line <= a["line"]:
                    continue
                consumer = defs_by_qname[consumer_q]
                for var, param in _name_arguments(call, consumer):
                    if var != a["variable"]:
                        continue
                    flows.append({
                        "producer": a["producer"],
                        "caller": caller_q,
                        "variable": var,
                        "consumer": consumer_q,
                        "consumer_param": param,
                        "producer_call_line": a["line"],
                        "consumer_call_line": line,
                        "caller_path": _rel(source_root, p),
                        "basis": "DIRECT_CALL_ASSIGNED_TO_SIMPLE_NAME_THEN_PASSED_AS_SIMPLE_NAME",
                    })

    flows.sort(key=lambda x: (
        x["caller_path"], x["producer_call_line"], x["consumer_call_line"],
        x["producer"], x["consumer"], x["variable"], x["consumer_param"]
    ))
    return flows, defs_by_qname, sorted(set(ambiguous))


def _trace_test(
    repo: pathlib.Path,
    source_root: pathlib.Path,
    test: pathlib.Path,
    timeout_s: int,
    max_events: int,
) -> dict[str, Any]:
    code = r'''import json,pathlib,runpy,sys,traceback
repo=pathlib.Path(sys.argv[1]).resolve()
src=pathlib.Path(sys.argv[2]).resolve()
target=pathlib.Path(sys.argv[3]).resolve()
cap=int(sys.argv[4])
events=[]
seq=0
call_ids={}
stack=[]

def relmod(p):
    r=p.relative_to(src).with_suffix("")
    parts=list(r.parts)
    if parts and parts[-1]=="__init__": parts=parts[:-1]
    return ".".join(parts)

def safe(v):
    t=type(v)
    if v is None or t in (bool,int,float):
        return {"type":t.__name__,"repr":repr(v)[:128]}
    if t is str:
        return {"type":"str","repr":repr(v[:96])}
    if t in (tuple,list) and len(v)<=8 and all((x is None or type(x) in (bool,int,float,str)) for x in v):
        return {"type":t.__name__,"repr":repr(v)[:256]}
    return {"type":t.__name__}

def tr(frame,event,arg):
    global seq
    if len(events)>=cap:
        return tr
    try:
        p=pathlib.Path(frame.f_code.co_filename).resolve()
    except Exception:
        return tr
    if not p.is_file() or not (p==src or src in p.parents) or p.suffix!=".py":
        return tr
    q=relmod(p)+":"+frame.f_code.co_name
    if event=="call":
        seq+=1
        cid=seq
        call_ids[id(frame)]=cid
        parent=call_ids.get(id(frame.f_back)) if frame.f_back else None
        argc=frame.f_code.co_argcount+frame.f_code.co_kwonlyargcount
        names=list(frame.f_code.co_varnames[:argc])
        bound={n:safe(frame.f_locals[n]) for n in names if n in frame.f_locals}
        events.append({"event":"call","id":cid,"parent":parent,"qname":q,"path":str(p.relative_to(repo)).replace("\\","/"),"line":frame.f_lineno,"bound":bound})
    elif event=="return":
        cid=call_ids.get(id(frame))
        events.append({"event":"return","id":cid,"qname":q,"path":str(p.relative_to(repo)).replace("\\","/"),"line":frame.f_lineno,"value":safe(arg)})
    return tr

ok=True
err=None
sys.settrace(tr)
try:
    runpy.run_path(str(target),run_name="__main__")
except SystemExit as e:
    ok=e.code in (None,0,False)
    if not ok: err="SystemExit:"+repr(e.code)
except BaseException as e:
    ok=False
    err=type(e).__name__+":"+str(e)[:200]
finally:
    sys.settrace(None)
print("__BRAIN_PROVENANCE_TRACE__"+json.dumps({"pass":ok,"error":err,"events":events},sort_keys=True))
'''
    try:
        r = subprocess.run(
            [sys.executable, "-c", code, str(repo), str(source_root), str(test), str(max_events)],
            cwd=repo, text=True, capture_output=True, timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProvenanceError("TEST_TIMEOUT") from exc
    marker = "__BRAIN_PROVENANCE_TRACE__"
    lines = [x for x in r.stdout.splitlines() if x.startswith(marker)]
    if not lines:
        raise ProvenanceError("TRACE_OUTPUT_MISSING")
    out = json.loads(lines[-1][len(marker):])
    out["returncode"] = r.returncode
    out["test_path"] = _rel(repo, test)
    return out


def _runtime_corroboration(flow: Mapping[str, Any], traces: list[Mapping[str, Any]]) -> dict[str, Any]:
    matches = 0
    failing_matches = 0
    for tr in traces:
        events = tr.get("events") or []
        calls = [e for e in events if e.get("event") == "call"]
        returns = [e for e in events if e.get("event") == "return"]
        by_id = {e.get("id"): e for e in calls}
        ret_by_id = {e.get("id"): e for e in returns}
        producer_calls = [e for e in calls if e.get("qname") == flow["producer"]]
        consumer_calls = [e for e in calls if e.get("qname") == flow["consumer"]]
        for pc in producer_calls:
            pr = ret_by_id.get(pc.get("id"))
            if not pr:
                continue
            parent = pc.get("parent")
            for cc in consumer_calls:
                if cc.get("parent") != parent or int(cc.get("id") or 0) <= int(pc.get("id") or 0):
                    continue
                param = (cc.get("bound") or {}).get(flow["consumer_param"])
                if param is not None and param == pr.get("value"):
                    matches += 1
                    if not tr.get("pass"):
                        failing_matches += 1
                    break
    return {
        "runtime_value_summary_matches": matches,
        "failing_runtime_value_summary_matches": failing_matches,
        "corroborated": matches > 0,
        "corroborated_on_failing_test": failing_matches > 0,
        "authority": "CORROBORATING_ONLY__NOT_DYNAMIC_TAINT_IDENTITY",
    }


def run(args: Mapping[str, Any], root: str | os.PathLike[str]) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise ProvenanceError("ARGS_NOT_OBJECT")
    repo = pathlib.Path(root).resolve()
    source_root = _safe_dir(repo, args.get("source_root", "."))
    tests = [_safe_file(repo, x) for x in (args.get("test_paths") or [])]
    if not tests:
        raise ProvenanceError("TEST_PATHS_REQUIRED")
    timeout_s = max(1, min(int(args.get("timeout_s", 20)), 120))
    max_events = max(100, min(int(args.get("max_trace_events", 50000)), 500000))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise ProvenanceError("OUTPUT_PATH_OUTSIDE_REPOSITORY")

    static_flows, defs, ambiguous = _static_flows(source_root)
    traces = [_trace_test(repo, source_root, t, timeout_s, max_events) for t in tests]
    failing = [t for t in traces if not t.get("pass")]
    if not failing:
        raise ProvenanceError("NO_FAILING_TEST")

    observed_fail_qnames = {
        e["qname"]
        for t in failing
        for e in (t.get("events") or [])
        if e.get("event") == "call"
    }

    activated = []
    for flow in static_flows:
        if not {flow["producer"], flow["caller"], flow["consumer"]}.issubset(observed_fail_qnames):
            continue
        rec = dict(flow)
        rec["runtime"] = _runtime_corroboration(flow, traces)
        rec["failing_path_activated"] = True
        activated.append(rec)

    localizer_path = output.parent / (".localizer_" + output.name)
    localizer_args = {
        "source_root": _rel(repo, source_root) if source_root != repo else ".",
        "test_paths": [_rel(repo, t) for t in tests],
        "output_path": _rel(repo, localizer_path),
        "timeout_s": timeout_s,
        "max_trace_events": max_events,
        "max_ranked_lines": int(args.get("max_ranked_lines", 100)),
        "max_ranked_symbols": int(args.get("max_ranked_symbols", 50)),
    }
    try:
        loc = _LOCALIZER.run(localizer_args, repo)
    finally:
        if localizer_path.exists():
            localizer_path.unlink()

    suspicious = {
        (str(x["path"]), str(x["symbol"]))
        for x in (loc.get("ranked_symbols") or [])
    }
    q_to_path_symbol = {
        q: (_rel(repo, d["path"]), d["name"])
        for q, d in defs.items()
    }

    region: set[tuple[str, str]] = set(suspicious)
    provenance_hypotheses = []
    for flow in activated:
        nodes = [flow["producer"], flow["caller"], flow["consumer"]]
        mapped = [q_to_path_symbol[q] for q in nodes if q in q_to_path_symbol]
        intersects = any(x in suspicious for x in mapped)
        if intersects:
            region.update(mapped)
            provenance_hypotheses.append({
                **flow,
                "expansion_reason": "ACTIVATED_INTERPROCEDURAL_FLOW_TOUCHES_DYNAMICALLY_SUSPICIOUS_SYMBOL",
            })

    region_rows = [
        {"path": p, "symbol": s}
        for p, s in sorted(region)
    ]

    result = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": "PASS__BOUNDED_INTERPROCEDURAL_PROVENANCE" if activated else "OPEN__NO_ACTIVATED_DIRECT_VALUE_FLOW",
        "pass": bool(activated),
        "static_flow_count": len(static_flows),
        "activated_flow_count": len(activated),
        "activated_flows": activated,
        "provenance_hypotheses": provenance_hypotheses,
        "repair_region": region_rows,
        "dynamic_localizer_status": loc.get("status"),
        "dynamic_localizer_ranked_symbol_count": len(loc.get("ranked_symbols") or []),
        "ambiguous_definition_qnames": ambiguous,
        "test_trace_count": len(traces),
        "failing_test_count": len(failing),
        "source_mutation_count": 0,
        "source_restored": True,
        "model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "external_capability_provider_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NO_GENERAL_DYNAMIC_TAINT_IDENTITY",
            "NO_HEAP_ALIAS_PROVENANCE_COMPLETENESS",
            "NO_METHOD_OR_CLOSURE_OR_DYNAMIC_DISPATCH_COMPLETENESS",
            "NO_COMPLEX_EXPRESSION_FLOW_COMPLETENESS",
            "NO_PATCH_CORRECTNESS_OR_MERGEABILITY_CLAIM",
            "NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["output_path"] = _rel(repo, output)
    result["output_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    result["output_verified"] = True
    return result
