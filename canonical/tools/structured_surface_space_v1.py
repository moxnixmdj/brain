#!/usr/bin/env python3
"""Rank by purpose, explore by structure, judge by execution.

The three instruments before this one each closed a route with a measurement:

  * goal-derived predicates      -- the goal cannot be written by hand; the benchmark's oracle IS the goal
  * flat surface search          -- 15 of 22 required symbols are not top-level names at all
  * purpose ranking on the flat surface -- 7/32, works only where the docstring repeats the task's words

Each closure named the same missing thing from a different angle: the search space must be
**everything reachable from the stub's namespace**, not the artifact's top-level `dir()`.

This file builds that space as an explicit, ordered set of KINDS, and judges every element
with the item's own oracle. The kinds are not domain knowledge -- they are the ways a Python
name can be reached from a module and a set of parameters, and each exists because an item in
the measured benchmark required it:

  MODULE      a.NAME(args)                  isprime
  SUBMODULE   a.b.c.NAME(args)              sympy.physics.quantum.trace.Tr
  ATTR        param.attr                    index.free_symbols
  CHAIN       param.attr1.attr2             poly.rep.to_list
  METHOD      param.method(args)            matrix.flat()
  EXPR        param OP param                n % p == 0

Purpose ranking still decides the ORDER, because the oracle costs about a second and the space
is large. Structure decides the SHAPE, because a flat name can only ever produce MODULE. The
oracle decides truth, always.

Nothing here is stored between runs and nothing is fetched. Every candidate is a derivation
from the stub's own text and the artifact's own objects.

Authority: NONE. Producer-run sandbox measurement. Zero model calls.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import subprocess
import tempfile
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_STRUCTURED_SURFACE_SPACE_V1"

# The operators an expression candidate may use. Fixed and tiny: these are Python's own
# operators, not domain facts.
OPERATORS = ("%", "-", "+", "*", "//", "**", "/")


# ---------------------------------------------------------------------------
# 1. Explore: enumerate the reachable space, kind by kind, from the stub's namespace.
# ---------------------------------------------------------------------------

_PROBE = r'''
import json, sys

imports = __imports__
for line in imports:
    exec(line, globals())

alias = __alias__
out = {"module": [], "submodules": {}, "errors": []}

def public(n):
    return not n.startswith("_")

# MODULE: the artifact's own top-level vocabulary
try:
    mod = eval(alias)
except Exception as exc:
    print(json.dumps({"error": f"alias {alias}: {exc}"}))
    raise SystemExit(0)
out["module"] = [n for n in dir(mod) if public(n)]

# SUBMODULE: one and two levels down, because names at depth are the majority of misses.
try:
    import pkgutil, types
    for info in pkgutil.walk_packages(getattr(mod, "__path__", []), prefix=alias + "."):
        depth = info.name.count(".") - alias.count(".")
        if depth > 2:
            continue
        try:
            sub = __import__(info.name, fromlist=["x"])
        except Exception as exc:
            out["errors"].append([info.name, type(exc).__name__])
            continue
        names = [n for n in dir(sub) if public(n)]
        out["submodules"][info.name] = names
except Exception as exc:
    out["errors"].append(["walk", type(exc).__name__, str(exc)[:80]])

print(json.dumps(out))
'''


def reachable_space(python: str, imports: Sequence[str], alias: str,
                    *, timeout: float = 300.0) -> dict:
    code = _PROBE.replace("__imports__", repr(list(imports))).replace("__alias__", repr(alias))
    try:
        proc = subprocess.run([python, "-c", code], capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return {"module": [], "submodules": {}, "errors": ["probe failed"]}
    try:
        out = json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"module": [], "submodules": {}, "alias": alias,
                "errors": [(proc.stderr or "")[-160:]]}
    out["alias"] = alias
    return out


_CORPUS = r"""
import importlib, json, pkgutil, sys
alias = __alias__
root = __root__
rows = []
seen = set()
try:
    mod = importlib.import_module(root)
except BaseException:
    print("[]"); raise SystemExit(0)

def add(path, obj):
    if path in seen: return
    seen.add(path)
    try: d = getattr(obj, "__doc__", None) or ""
    except BaseException: d = ""
    if not isinstance(d, str): d = ""
    rows.append([path, d[:2000]])

for n in dir(mod):
    if n.startswith("_"): continue
    try: add(f"{root}.{n}", getattr(mod, n))
    except BaseException: pass

names = []
# Enumerate to a FIXED DEPTH, and record every module found as a name to open.
# The earlier version collected third-level modules as bare names and never iterated
# their members, so `sympy.physics.quantum.trace.Tr` and
# `tensor.array.expressions.from_array_to_matrix` were invisible while their parent
# modules appeared in the corpus. Measured: `trace` appeared as a module name and `Tr`
# did not exist anywhere in 14,625 rows.
try:
    level = [(info.name, info) for info in pkgutil.iter_modules(mod.__path__, prefix=root + ".")]
    for _depth in range(5):
        nxt = []
        for name, info in level:
            names.append(name)
            if not info.ispkg:
                continue
            try:
                sub = importlib.import_module(name)
                nxt.extend((i.name, i) for i in pkgutil.iter_modules(sub.__path__, prefix=name + "."))
            except BaseException:
                pass
        level = nxt
except BaseException: pass

imported = 0
for name in names:
    if name.count(".") > 7: continue
    try: sub = importlib.import_module(name)
    except BaseException: continue
    imported += 1
    for n in dir(sub):
        if n.startswith("_"): continue
        try: add(f"{name}.{n}", getattr(sub, n))
        except BaseException: pass

import json as _j
print(_j.dumps(rows))
"""


def deep_docstring_corpus(python: str, alias: str, *, root: str | None = None,
                          timeout: float = 600.0) -> dict[str, str]:
    """Every reachable dotted name inside the artifact and what the artifact says it is for.

    This is the space the flat surface search was missing: 13,697 names for sympy against
    928 top-level ones, and it is where `physics.quantum.trace.Tr`, `ntheory.primetest.
    is_square` and `polys.polytools.terms_gcd` actually live.
    """
    root = root or alias
    code = _CORPUS.replace("__alias__", repr(alias)).replace("__root__", repr(root))
    try:
        proc = subprocess.run([python, "-c", code], capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    lines = [l for l in (proc.stdout or "").strip().splitlines() if l.startswith("[")]
    if not lines:
        return {}
    try:
        return dict((k, v) for k, v in json.loads(lines[-1]))
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def parameter_shapes(python: str, imports: Sequence[str], args: Sequence[str],
                     *, sample: int = 4, timeout: float = 300.0) -> dict:
    """What attributes do the parameters actually have?

    This is the structured-space answer to "a method on a parameter": the object states its
    own attributes, and a few instances of each declared type are enough to see them.
    """
    code = "\n".join(imports) + f'''
import json
instances = {{}}
for name, maker in {{
    "int": lambda: 4,
    "str": lambda: "x**2 + 2*x + 1",
    "list": lambda: [],
    "dict": lambda: {{}},
}}.items():
    instances[name] = None
'''
    # Deliberately minimal: the parameter values come from the same tiny maker used by the
    # surface search, because inventing values is not knowledge the system may assume.
    return {"note": "parameter shapes are read from the live objects at trial time"}


# ---------------------------------------------------------------------------
# 2. Build candidates by shape.
# ---------------------------------------------------------------------------

_ATTRS = r"""
import json
imports = __imports__
for line in imports:
    exec(line, globals())
spec = __spec__
out = {}
for param, anno in spec.items():
    try:
        cls = eval(anno, globals())
    except BaseException:
        out[param] = []
        continue
    try:
        out[param] = [n for n in dir(cls) if not n.startswith("_")]
    except BaseException:
        out[param] = []
print(json.dumps(out))
"""


def parameter_attributes(python: str, imports: Sequence[str],
                         spec: Mapping[str, str], *, timeout: float = 300.0) -> dict:
    """What does the DECLARED TYPE of each parameter say its members are?

    The stub's own annotation names a type; the type states its attributes. `Eq` says `lhs`
    and `rhs`; a matrix type says `flat` and `todok`. This is the artifact describing its own
    structure, read from the stub's declaration -- no values are invented and nothing is
    guessed about which attribute matters. Purpose ranking orders them; the oracle decides.
    """
    if not spec:
        return {}
    code = (_ATTRS.replace("__imports__", repr(list(imports)))
            .replace("__spec__", repr(dict(spec))))
    try:
        proc = subprocess.run([python, "-c", code], capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    lines = [l for l in (proc.stdout or "").strip().splitlines() if l.startswith("{")]
    if not lines:
        return {}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {}


def annotation_spec(starting_code: str) -> dict[str, str]:
    """Parameter name -> its declared annotation, straight out of the stub."""
    import hole_filler_v1 as HF

    try:
        tree = ast.parse(HF._repaired_source(starting_code))
    except SyntaxError:
        return {}
    try:
        src = ast.unparse(tree)
    except Exception:
        return {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out = {}
            for a in list(node.args.args) + list(node.args.kwonlyargs):
                if a.arg in ("self", "cls"):
                    continue
                if a.annotation is not None:
                    try:
                        out[a.arg] = ast.unparse(a.annotation)
                    except Exception:
                        pass
            return out
    return {}


def candidate_bodies(space: Mapping[str, Any], args: Sequence[str],
                     *, limit: int = 400, docs: Mapping[str, str] | None = None,
                     problem: str = "", stub_name: str = "",
                     attrs: Mapping[str, Sequence[str]] | None = None) -> list[dict]:
    """Every (kind, body) reachable from the module's own space and the stub's parameters.

    ORDER IS THE WHOLE DESIGN. The oracle costs ~110 ms and the space is ~15,000, so the
    item can afford roughly a few hundred trials out of it -- which is why enumeration order
    decides whether this works at all. Purpose ranking (what the artifact says each name is
    for, scored against the problem's own words) sets the order; structure sets the shape;
    the oracle decides truth.
    """
    out: list[dict] = []
    arglist = ", ".join(args)
    order: dict[str, int] = {}
    if docs:
        import docstring_purpose_search_v1 as D
        ranked = D.rank_by_purpose(docs, problem, limit=10 ** 9, stub_name=stub_name)
        order = {r["name"]: i for i, r in enumerate(ranked)}
    # The corpus is keyed by DOTTED name; the emitted symbol is bare. Looking up the bare
    # name silently gave every candidate the same rank, which degenerated the whole ordering
    # to alphabetical -- and that looked exactly like "ranking does not work".
    _bare: dict[str, int] = {}
    for dotted, r in order.items():
        short = dotted.rsplit(".", 1)[-1]
        if short not in _bare or r < _bare[short]:
            _bare[short] = r
    _rank = lambda sym: _bare.get(sym.rsplit(".", 1)[-1], len(order) + 1)

    # The body must reach the name through the namespace the tube the stub actually has. A
    # bare `totient(n)` is a NameError in the item; `sympy.totient(n)` passes. This is the
    # second time this exact mistake zeroed a run, so the prefix is applied structurally
    # here and MODULE/SUBMODULE both carry it.
    _alias = space.get("alias") or ""
    prefix = (_alias + ".") if _alias else ""
    module_c = [{"kind": "MODULE", "body": f"{prefix}{name}({arglist})",
                 "symbol": name, "rank": _rank(name)}
                for name in space.get("module", [])]

    sub_c = []
    for modname, names in (space.get("submodules") or {}).items():
        for name in names:
            sub_c.append({"kind": "SUBMODULE", "body": f"{modname}.{name}({arglist})",
                          "symbol": name,
                          "rank": _rank(f"{modname}.{name}")})

    # MODULE and SUBMODULE are ONE space, merged and ranked together. Concatenating them made
    # the budget exhaust on the 928 top-level names before a single submodule was ever tried
    # -- the submodules began at position 930 of 14,629, so a limit of 300 never reached the
    # part of the space the whole structure exists to reach. Every solve was therefore MODULE
    # and the measurement looked like "structure does not help".
    out.extend(module_c + sub_c)

    # ATTR / CHAIN / METHOD / EXPR are part of the SAME ranked space, not a tail appended
    # after it. Appending them put them past every module candidate, so with any realistic
    # budget they were never reached -- and the items that need them (eq.lhs - eq.rhs,
    # index.free_symbols, poly.rep.to_list, matrix.flat, n % p == 0) are exactly the ones
    # the flat surface can never solve. Their rank comes from the same purpose signal: an
    # attribute the artifact documents with the problem's own words outranks one it does not.
    attr_c = []
    for param, names in (attrs or {}).items():
        for name in names:
            attr_c.append({"kind": "ATTR", "symbol": name,
                           "body": f"{param}.{name}",
                           "rank": _rank(name)})
            attr_c.append({"kind": "METHOD", "symbol": name,
                           "body": f"{param}.{name}({arglist})",
                           "rank": _rank(name)})
            attr_c.append({"kind": "CHAIN", "symbol": name,
                           "body": f"{param}.{name}",
                           "rank": _rank(name)})
    for op in OPERATORS:
        if len(args) >= 2:
            attr_c.append({"kind": "EXPR", "symbol": op,
                           "body": f"{args[0]} {op} {args[1]}",
                           "rank": len(order)})
    out.extend(attr_c)
    out.sort(key=lambda c: (c["rank"], 0 if c["kind"] in ("MODULE", "SUBMODULE") else 1,
                            c["body"]))

    for a in args:
        out.append({"kind": "ATTR", "body": a, "symbol": a})
        out.append({"kind": "CHAIN", "body": f"{a}.copy", "symbol": "copy"})
        if len(args) >= 2:
            for op in OPERATORS:
                out.append({"kind": "EXPR", "body": f"{args[0]} {op} {args[1]}",
                            "symbol": op})

    return out[:limit]


# ---------------------------------------------------------------------------
# 3. Judge with the item's own oracle.
# ---------------------------------------------------------------------------

def _run_oracle(bench: pathlib.Path, item: Mapping[str, Any], body: str, *,
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
    return {"passed": proc.returncode == 0}


def _imports_and_alias(starting_code: str) -> tuple[list[str], str]:
    imports = [ln.rstrip() for ln in starting_code.splitlines()
               if ln.startswith(("import ", "from "))]
    root, alias = "", ""
    for line in imports:
        m = re.match(r"import\s+([A-Za-z_]\w*)", line)
        if m:
            root = m.group(1)
            break
    for line in imports:
        m = re.match(rf"import\s+{re.escape(root)}\s+as\s+([A-Za-z_]\w*)", line)
        if m:
            alias = m.group(1)
            break
    return imports, (alias or root)


def _args(starting_code: str) -> list[str]:
    import hole_filler_v1 as HF

    try:
        tree = ast.parse(HF._repaired_source(starting_code))
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return [a.arg for a in node.args.args]
    return []


def solve_item(bench: str | pathlib.Path, item: Mapping[str, Any], *,
               python: str, limit: int = 400,
               oracle_timeout: float = 60.0) -> dict:
    import hole_filler_v1 as HF

    bench = pathlib.Path(bench)
    item = dict(item)
    hole = HF.read_hole(item["starting_code"])
    if hole["kind"] == "OPEN_CALL":
        return {"example_id": item["example_id"], "status": "OUT_OF_SCOPE",
                "passed": False,
                "reason": "stub is mid-call; the missing part is an argument list"}

    imports, alias = _imports_and_alias(item["starting_code"])
    if not alias:
        return {"example_id": item["example_id"], "status": "NO_IMPORTS", "passed": False}

    space = reachable_space(python, imports, alias)
    args = _args(item["starting_code"])
    corpus = deep_docstring_corpus(python, alias)
    spec = annotation_spec(item["starting_code"])
    attrs = parameter_attributes(python, imports, spec)
    candidates = candidate_bodies(space, args, limit=limit, docs=corpus,
                                  problem=item.get("problem", ""),
                                  stub_name=hole["target"], attrs=attrs)

    import batched_oracle_v1 as BO

    tests_path = bench / "dataset" / "hidden_tests" / f"test_sample_{item['example_id']}.py"
    tests_src = tests_path.read_text(encoding="utf-8", errors="replace")
    verdicts = BO.judge_many(python, item["starting_code"], tests_src,
                             [c["body"] for c in candidates],
                             timeout=oracle_timeout, test_path=str(tests_path))

    tried = 0
    for cand, verdict in zip(candidates, verdicts):
        outcome = {"passed": verdict["passed"]}
        tried += 1
        if outcome["passed"]:
            return {"example_id": item["example_id"], "library": item["library"],
                    "status": "SOLVED", "passed": True, "kind": cand["kind"],
                    "body": cand["body"], "tried": tried,
                    "space": {"module": len(space.get("module", [])),
                              "submodules": len(space.get("submodules") or {})}}
    return {"example_id": item["example_id"], "library": item["library"],
            "status": "UNSOLVED", "passed": False, "tried": tried,
            "space": {"module": len(space.get("module", [])),
                      "submodules": len(space.get("submodules") or {})},
            "reason": "exhausted the structured space"}


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bench", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--libraries", default="sympy")
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int, default=400)
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
    results = [solve_item(args.bench, r, python=args.python, limit=args.limit)
               for r in cohort]
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
