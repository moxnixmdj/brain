"""Play 1, step 1: derive adapters from a module's own AST and its own test, and keep only
the ones that agree with themselves.

The promotion ledger measured the deficit: 641 of 849 modules that implement the five
frontier functions are indexed source with no adapter, so the runtime cannot call them.
Writing 641 adapters by hand is the wrong job -- it has no admission test, so written code
would again be counted as capability.

This tool does the other thing. For a module that ships a test file, it reads

* the module's public callables and their signatures, from the module's ``ast``;
* a call in the *test* whose arguments are all literals, from the test's ``ast``;

and then executes that call **twice** in a fresh interpreter, in a temporary working
directory, with a timeout. The adapter survives only if both runs succeed and produce the
same observable output. A survivor is an adapter with a receipt, and the call it replays is
an exact-target row: the query is the test author's own statement of intent, the target is
the module that answered it, and chance is 1/849.

Nothing here reads the module's docstring for the adapter's arguments (that would be a
guess), nothing calls a model, and nothing is written into the tree being measured.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_AST_ADAPTER_DERIVATION_V1"
LEDGER = "canonical/verification/PROMOTION_LEDGER_20261127_V1.json"
TEST_DIR = "canonical/tests"

RUNNER = r'''
import importlib.util, json, pathlib, sys, traceback
module_path, function, args_json = sys.argv[1], sys.argv[2], sys.argv[3]
args = json.loads(args_json)
out = {"ok": False}
try:
    spec = importlib.util.spec_from_file_location("adapter_target", module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, function)
    value = fn(*args)
    try:
        serialised = json.dumps(value, sort_keys=True, default=str)
    except Exception:
        serialised = repr(value)
    out = {"ok": True, "kind": type(value).__name__,
           "digest": __import__("hashlib").sha256(serialised.encode()).hexdigest()[:16],
           "preview": serialised[:200]}
except BaseException as exc:
    out = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}
print(json.dumps(out))
'''


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _literal(node: ast.AST) -> tuple[bool, Any]:
    """Only literals become arguments. A guess is not an adapter."""
    try:
        value = ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return False, None
    # Only what can cross a process boundary as JSON becomes an argument. A set literal is
    # not a guess we are allowed to make on the caller's behalf.
    def plain(item: Any) -> bool:
        if isinstance(item, (str, int, float, bool)) or item is None:
            return True
        if isinstance(item, (list, tuple)):
            return all(plain(x) for x in item)
        if isinstance(item, dict):
            return all(isinstance(k, str) and plain(v) for k, v in item.items())
        return False
    if not plain(value):
        return False, None
    return True, _jsonable(value)


def module_surface(path: pathlib.Path) -> dict[str, Any]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return {"ok": False, "reason": "MODULE_UNPARSED"}
    functions: dict[str, dict[str, Any]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            args = node.args
            if args.vararg or args.kwarg:
                continue
            names = [a.arg for a in list(args.posonlyargs) + list(args.args)]
            defaults = len(args.defaults)
            required = names[: len(names) - defaults] if defaults else names
            functions[node.name] = {"required": len(required), "params": names,
                                    "doc": (ast.get_docstring(node) or "")[:160]}
    return {"ok": bool(functions), "functions": functions,
            "doc": (ast.get_docstring(tree) or "")[:200],
            "reason": "NO_PUBLIC_FUNCTION" if not functions else ""}


def test_call(test_path: pathlib.Path, functions: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    try:
        tree = ast.parse(test_path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return None
    tests = {n.name: (ast.get_docstring(n) or "") for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        name = node.func.id
        if name not in functions or node.keywords:
            continue
        args: list[Any] = []
        literal = True
        for arg in node.args:
            ok, value = _literal(arg)
            if not ok:
                literal = False
                break
            args.append(value)
        if not literal or len(args) < functions[name]["required"]:
            continue
        enclosing = next((n.name for n in ast.walk(tree)
                          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                          and any(child is node for child in ast.walk(n))), "test_unknown")
        return {"function": name, "args": args, "test": enclosing,
                "test_doc": tests.get(enclosing, "")[:200],
                "line": ast.unparse(node)[:200]}
    return None


def run_once(module_path: pathlib.Path, function: str, args: list[Any], timeout: float) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as workdir:
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                [sys.executable, "-c", RUNNER, str(module_path), function, json.dumps(args)],
                cwd=workdir, capture_output=True, text=True, timeout=timeout,
                env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0", "HOME": workdir},
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "TIMEOUT", "seconds": round(timeout, 2)}
        seconds = round(time.perf_counter() - started, 3)
        line = (completed.stdout or "").strip().splitlines()
        if not line:
            return {"ok": False, "error": "NO_OUTPUT", "seconds": seconds,
                    "stderr": (completed.stderr or "")[-200:]}
        try:
            payload = json.loads(line[-1])
        except ValueError:
            return {"ok": False, "error": "UNPARSEABLE_OUTPUT", "seconds": seconds}
        payload["seconds"] = seconds
        return payload


def derive(root: pathlib.Path, module_rel: str, timeout: float) -> dict[str, Any]:
    module_path = (root / module_rel).resolve()
    stem = module_path.stem
    surface = module_surface(module_path)
    row: dict[str, Any] = {"module": module_rel, "stem": stem, "surface": surface.get("reason") or "OK"}
    if not surface.get("ok"):
        row["outcome"] = surface.get("reason") or "NO_PUBLIC_FUNCTION"
        return row
    test_path = root / TEST_DIR / f"test_{stem}.py"
    if not test_path.is_file():
        row["outcome"] = "NO_TEST_FILE"
        return row
    call = test_call(test_path, surface["functions"])
    if call is None:
        row["outcome"] = "NO_LITERAL_CALL_IN_TEST"
        return row
    first = run_once(module_path, call["function"], call["args"], timeout)
    second = run_once(module_path, call["function"], call["args"], timeout)
    deterministic = bool(first.get("ok") and second.get("ok")
                         and first.get("digest") == second.get("digest"))
    row.update({
        "entrypoint": call["function"], "args": call["args"], "test": call["test"],
        "test_doc": call["test_doc"], "call": call["line"],
        "run1": first, "run2": second, "deterministic": deterministic,
        "outcome": "SURVIVES" if deterministic else ("CALL_ERROR" if not first.get("ok") else "NON_DETERMINISTIC"),
    })
    if deterministic:
        row["receipt"] = hashlib.sha256(json.dumps(
            {"module": module_rel, "function": call["function"], "args": call["args"],
             "digest": first["digest"]}, sort_keys=True).encode()).hexdigest()[:32]
        row["target"] = {"query": f"{call['test'].replace('_', ' ')}: {call['test_doc'] or call['line']}",
                         "module": module_rel}
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default="canonical/verification/PLAY_1_ADAPTERS_20261127_V1.json")
    ap.add_argument("--max", type=int, default=50, help="how many modules to attempt, deterministic order")
    ap.add_argument("--timeout", type=float, default=8.0)
    args = ap.parse_args(argv)
    root = pathlib.Path(args.root)
    ledger = json.loads((root / LEDGER).read_text())
    candidates = sorted((row for row in ledger["rows"] if row["category"] == "SOURCE_ONLY"),
                        key=lambda row: row["path"])
    selected = candidates[: args.max]
    rows = [derive(root, row["path"], args.timeout) for row in selected]
    survivors = [row for row in rows if row["outcome"] == "SURVIVES"]
    outcomes: dict[str, int] = {}
    for row in rows:
        outcomes[row["outcome"]] = outcomes.get(row["outcome"], 0) + 1
    report = {
        "schema": SCHEMA,
        "method": {
            "selection": f"first {args.max} SOURCE_ONLY ledger rows, sorted by path",
            "arguments": "literals only, taken from a call in the module's own same-stem test file",
            "admission": "the call is executed twice in a fresh interpreter, cwd in a temp dir, and must agree",
            "timeout_seconds": args.timeout,
        },
        "attempted": len(rows),
        "survivors": len(survivors),
        "survival_rate": round(len(survivors) / max(1, len(rows)), 3),
        "kill_floor": 0.40,
        "verdict": "SURVIVES" if len(survivors) / max(1, len(rows)) >= 0.40 else "KILLED",
        "outcomes": outcomes,
        "exact_targets": len(survivors),
        "chance_for_an_exact_target": round(1 / 849, 5),
        "claim_limit": (
            "A survivor is a call that twice produced the same output. It is not a claim that the module is correct, "
            "that its output is meaningful, or that the test asserts what the adapter assumes -- none of these tests "
            "was run. Producer-run, one sandbox."
        ),
        "model_calls": 0,
        "network_calls": 0,
        "rows": rows,
    }
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("attempted", "survivors", "survival_rate", "outcomes",
                                             "verdict", "exact_targets")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
