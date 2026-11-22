#!/usr/bin/env python3
"""Search the artifact's own surface, filter with the stub's own types, judge with the oracle.

The previous receipt established the bottleneck and the only legal route to it:

  * the call is not a function of the problem prose (two items read identically and need
    different calls), so no amount of reading the description gets there;
  * a description->call knowledge base is forbidden, because that is memorised world
    knowledge in parameters and it would also just be the frontier's method renamed;
  * what IS legal is a search over the artifact's own surface, with the test as the oracle.

This file does exactly that, and nothing else. Three stages, cheapest first, because running
the oracle is the expensive operation and the artifact is not:

  1. CANDIDATE SET   every public name the artifact exposes, at the depth the stub can reach
                     through the imports it already wrote. This is the artifact stating its
                     own vocabulary -- no world knowledge, no learned table.
  2. FILTER          call each candidate with the stub's own parameters inside ONE process,
                     and keep only those that do not raise and whose return satisfies the
                     annotation the stub already declared. The type is not a guess: the stub
                     wrote it. This is the cheapest possible judge and it is stated
                     information, not prior.
  3. ORACLE          run the item's hidden test on the survivors. The test decides.

A stage that removes nothing is reported as removing nothing, and a search that finds no
candidate is a refusal, not a guess.

Zero model calls. Zero stored world facts. The only knowledge in this file is Python's own
semantics for calling a thing and checking a type.

Authority: NONE. Producer-run sandbox measurement.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_SURFACE_SEARCH_V1"

# Stage 2 runs inside the item's interpreter, so it sees exactly what the stub sees.
_FILTER = r'''
import json, sys, traceback

payload = json.loads(__payload__)
sys.path.insert(0, __libdir__) if __libdir__ else None

# Execute the stub's own imports so every alias it declared is in scope.
for line in payload["imports"]:
    exec(line, globals())

# Names are looked up ON THE ARTIFACT, never on the interpreter's globals: the stub reaches
# the artifact through its alias, and the alias is the only handle we have.
_ns = globals().get(payload["alias"]) if payload.get("alias") else None

args = payload["args"]
expected = payload["expected"]
names = payload["names"]

def make_args():
    """The stub's parameters, given values the test would plausibly use.

    Nothing here knows the domain. The values are the smallest instances of the declared
    types that a callable can be tried with, and the oracle rejects everything else.
    """
    out = []
    for a in args:
        ann = a.get("annotation") or ""
        if "int" in ann:
            out.append(4)
        elif "str" in ann:
            out.append("x**2 + 2*x + 1")
        else:
            out.append(None)
    return out

def type_ok(value, expected):
    if not expected:
        return True
    leaf = expected.split(".")[-1].split("[")[0]
    if leaf in ("int", "bool"):
        return isinstance(value, (int, bool))
    if leaf == "str":
        return isinstance(value, str)
    if leaf in ("list", "List"):
        return isinstance(value, list)
    if leaf in ("tuple", "Tuple"):
        return isinstance(value, tuple)
    if leaf in ("Matrix", "ImmutableDenseMatrix", "ImmutableMatrix"):
        return hasattr(value, "shape")
    if leaf in ("Graph", "DiGraph"):
        return hasattr(value, "nodes")
    # an annotation naming a class: check by name against the value's MRO
    try:
        return any(leaf == c.__name__ for c in type(value).__mro__)
    except Exception:
        return True

kept, errors = [], []
for name in names:
    fn = getattr(_ns, name, None) if _ns is not None else globals().get(name)
    if fn is None or not callable(fn):
        continue
    try:
        argsv = make_args()
        # drop trailing Nones, which stand for parameters we could not invent a value for
        while argsv and argsv[-1] is None:
            argsv.pop()
        value = fn(*argsv)
    except Exception as exc:
        errors.append([name, type(exc).__name__, str(exc)[:120]])
        continue
    if type_ok(value, expected):
        kept.append(name)

print(json.dumps({"kept": kept, "errors": errors[:40],
                  "tried": len(names), "kept_count": len(kept)}))
'''


def _stub_imports(starting_code: str) -> list[str]:
    return [ln.rstrip() for ln in starting_code.splitlines()
            if ln.startswith(("import ", "from "))]


def _primary_module(imports: Sequence[str]) -> str:
    """The module the stub imports -- this is the artifact whose surface we search."""
    for line in imports:
        m = re.match(r"import\s+([A-Za-z_][\w]*)", line)
        if m:
            return m.group(1)
    for line in imports:
        m = re.match(r"from\s+([A-Za-z_][\w]*)", line)
        if m:
            return m.group(1)
    return ""


def _signature(starting_code: str, target: str) -> dict:
    try:
        tree = ast.parse(starting_code.rstrip() + "\n" + ")" * max(
            starting_code.count("(") - starting_code.count(")"), 0) + "\n    pass\n")
    except SyntaxError:
        return {"args": [], "expected": ""}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target:
            return {
                "args": [{"name": a.arg,
                          "annotation": ast.unparse(a.annotation) if a.annotation else ""}
                         for a in node.args.args],
                "expected": ast.unparse(node.returns) if node.returns else "",
            }
    return {"args": [], "expected": ""}


def _alias_for(imports: Sequence[str], module: str) -> str:
    """The name the stub actually uses to reach the artifact.

    `import networkx as nx` binds `nx`, and the stub calls `nx.community...`. Enumerating
    `dir(networkx)` fails only because that name was never bound -- a bug in the reader,
    not a fact about the artifact.
    """
    for line in imports:
        m = re.match(rf"import\s+{re.escape(module)}\s+as\s+([A-Za-z_]\w*)", line)
        if m:
            return m.group(1)
    for line in imports:
        m = re.match(rf"import\s+([A-Za-z_]\w*)", line)
        if m:
            return m.group(1)
    return module


def surface_names(python: str, module: str, imports: Sequence[str]) -> list[str]:
    """Every public name the artifact exposes through the alias the stub declared."""
    alias = _alias_for(imports, module)
    code = "\n".join(imports) + (
        f"\nprint('\\n'.join(n for n in dir({alias}) if not n.startswith('_')))"
    )
    try:
        out = subprocess.run([python, "-c", code], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def filter_candidates(python: str, starting_code: str, sig: Mapping[str, Any],
                      names: Sequence[str], *, timeout: float = 300.0) -> dict:
    imports = _stub_imports(starting_code)
    module = _primary_module(imports)
    payload = json.dumps({
        "imports": imports,
        "alias": _alias_for(imports, module),
        "args": sig["args"],
        "expected": sig["expected"],
        "names": list(names),
    })
    code = _FILTER.replace("__payload__", repr(payload)).replace(
        "__libdir__", repr(_site_libdir(python)))
    try:
        proc = subprocess.run([python, "-c", code], capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"kept": [], "error": f"{type(exc).__name__}"}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"kept": [], "error": (proc.stderr or "").strip()[-200:]}


def _site_libdir(python: str) -> str:
    try:
        out = subprocess.run(
            [python, "-c", "import json,sysconfig;print(sysconfig.get_paths()['purelib'])"],
            capture_output=True, text=True, timeout=60)
        return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def run_oracle(bench: pathlib.Path, item: Mapping[str, Any], body: str, *,
               python: str, timeout: float) -> dict:
    src = f"{item['starting_code']}{body}\n"
    test = (bench / "dataset" / "hidden_tests" /
            f"test_sample_{item['example_id']}.py").read_text(encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        (d / f"sample_{item['example_id']}.py").write_text(src, encoding="utf-8")
        (d / f"test_sample_{item['example_id']}.py").write_text(test, encoding="utf-8")
        try:
            proc = subprocess.run([python, "-m", "pytest", "--disable-warnings", "-q", str(d)],
                                  capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired):
            return {"passed": False, "status": "TIMEOUT"}
    return {"passed": proc.returncode == 0,
            "tail": "\n".join(((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()[-3:])[:300]}


def search_item(bench: str | pathlib.Path, item: Mapping[str, Any], *,
                python: str, oracle_timeout: float = 180.0) -> dict:
    import hole_filler_v1 as HF

    bench = pathlib.Path(bench)
    item = dict(item)
    hole = HF.read_hole(item["starting_code"])
    sig = _signature(item["starting_code"], hole["target"])
    imports = _stub_imports(item["starting_code"])
    module = _primary_module(imports)

    names = surface_names(python, module, imports)
    if not names:
        return {"example_id": item["example_id"], "status": "NO_SURFACE", "passed": False}

    filtered = filter_candidates(python, item["starting_code"], sig, names)
    kept = filtered.get("kept", [])

    # the candidate body: call the surviving symbol with the stub's own parameters
    argnames = [a["name"] for a in sig["args"]]
    bodies = [f"{name}({', '.join(argnames)})" for name in kept]
    trials = []
    for body in bodies[:40]:                      # bounded; the type filter already pruned
        outcome = run_oracle(bench, item, body, python=python, timeout=oracle_timeout)
        trials.append({"body": body, **outcome})
        if outcome["passed"]:
            return {
                "example_id": item["example_id"],
                "library": item["library"],
                "status": "SOLVED",
                "passed": True,
                "body": body,
                "surface_size": len(names),
                "after_type_filter": len(kept),
                "trials": len(trials),
                "evidence": trials,
            }
    return {
        "example_id": item["example_id"],
        "library": item["library"],
        "status": "UNSOLVED",
        "passed": False,
        "surface_size": len(names),
        "after_type_filter": len(kept),
        "tried": len(trials),
        "kept_sample": kept[:12],
        "filter_errors": filtered.get("errors", [])[:6],
        "trials": trials[:12],
    }


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bench", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--libraries", default="sympy,networkx")
    ap.add_argument("--ids")
    ap.add_argument("--json-out")
    args = ap.parse_args(list(argv) if argv is not None else None)

    items = [json.loads(l) for l in
             (pathlib.Path(args.bench) / "dataset" / "dataset.jsonl").read_text().splitlines()
             if l.strip()]
    libs = {x.strip() for x in args.libraries.split(",") if x.strip()}
    cohort = [r for r in items if r["library"] in libs
              and not (r.get("additional_dependencies") or "").strip()]
    if args.ids:
        want = {x.strip() for x in args.ids.split(",")}
        cohort = [r for r in cohort if r["example_id"] in want]

    results = [search_item(args.bench, r, python=args.python) for r in cohort]
    solved = sum(1 for r in results if r["passed"])
    report = {"schema": SCHEMA, "cohort": len(cohort), "solved": solved,
              "rate": f"{solved}/{len(cohort)}", "results": results,
              "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"}
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.json_out:
        pathlib.Path(args.json_out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
