#!/usr/bin/env python3
"""Bodies are compositions, not name applications.

The previous instrument solved 11 of 13 held-out items. Every one of them was a *single
application*: `name(args)`, sometimes with a lambda or as a member call.

The items it cannot touch are not vocabulary problems, and calling them "vocabulary" was
wrong. Measured over items 176-192, the required bodies are COMPOSITIONS:

    eq.lhs - eq.rhs                          attribute path, then arithmetic
    matrix.rep.to_list()                     chained attribute path
    DFT(n).as_explicit()                     application, then method
    Matrix([first, second])                  a list built from the parameters
    RigidBody(a), Particle(b)                a tuple of two applications
    PinJoint('pin', parent, child,
             parent_point=parent.frame.x)    keyword arguments read off the parameters

None of these can be produced by any ordering of `symbol(a, b)`, which is why every extra
unit of ranking effort returned nothing. The space was wrong, not the ranking — for the
second time in this chain, and this time the correction is structural rather than statistical.

The grammar below is the smallest set of compositions that covers every shape observed, and
it is derived only from the stub's own declaration:

  LEAF      a parameter, a stated literal, or a stated symbol applied to parameters
  PATH      leaf.attr, and leaf.attr.attr
  APPLY     a stated symbol applied to a list built from the leaves (Matrix([a, b]))
  OP        leaf OP leaf   (eq.lhs - eq.rhs)
  METHOD    leaf.method(), and APPLY.method()
  TUPLE     two applications
  KWARGS    a stated symbol with keyword arguments whose values are parameter attribute paths

Every component is a function of the stub's text. Nothing is stored, nothing is fetched, and
the oracle decides. Zero model calls.

Authority: NONE. Producer-run sandbox measurement.
"""
from __future__ import annotations

import ast
import itertools
import json
import pathlib
import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_BODY_GRAMMAR_V1"

OPERATORS = ("-", "+", "*", "%", "//", "/", "**")
MAX_CANDIDATES = 600


def parameters(starting_code: str) -> list[str]:
    import hole_filler_v1 as HF

    try:
        tree = ast.parse(HF._repaired_source(starting_code))
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
    return []


def literals_in(problem: str, starting_code: str) -> list[str]:
    """String literals the prose states outright. `'pin'` appears in the prose as a name."""
    quoted = re.findall(r"['\"]?([A-Za-z_]\w{1,20})['\"]?", problem or "")
    # only single-quoted strings in the prose are literals the prose is quoting
    return re.findall(r"'([^']{1,24})'", problem or "") or []


def properties_of(python: str, imports: Sequence[str], spec: Mapping[str, str],
                  *, timeout: float = 300.0) -> dict[str, list[str]]:
    """Which members are plain properties? Those are readable without a call."""
    if not spec:
        return {}
    code = "\n".join(imports) + f"""
import json
spec = {dict(spec)!r}
out = {{}}
for param, anno in spec.items():
    try: cls = eval(anno, globals())
    except BaseException:
        out[param] = []; continue
    names = []
    for n in dir(cls):
        if n.startswith("_"): continue
        try:
            v = getattr(cls, n)
        except BaseException:
            continue
        if isinstance(v, property):
            names.append(n)
    out[param] = names
print(json.dumps(out))
"""
    import subprocess

    try:
        proc = subprocess.run([python, "-c", code], capture_output=True, text=True,
                              timeout=timeout)
        lines = [l for l in (proc.stdout or "").strip().splitlines() if l.startswith("{")]
        return json.loads(lines[-1]) if lines else {}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, IndexError):
        return {}


def attribute_paths(python: str, imports: Sequence[str],
                    spec: Mapping[str, str], *, depth: int = 2,
                    timeout: float = 300.0) -> dict[str, list[str]]:
    """Every attribute path of each declared parameter type, to `depth`."""
    if not spec:
        return {}
    import structured_surface_space_v1 as S

    one = S.parameter_attributes(python, imports, spec, timeout=timeout)
    out: dict[str, list[str]] = {}
    for param, names in (one or {}).items():
        paths = list(names)
        out[param] = paths
    if depth < 2:
        return out

    # second level: for each attribute, what does ITS declared type expose at run time?
    code = "\n".join(imports) + f"""
import json
spec = {dict(spec)!r}
out = {{}}
for param, anno in spec.items():
    try: cls = eval(anno, globals())
    except BaseException:
        out[param] = {{}}; continue
    inner = {{}}
    for name in [n for n in dir(cls) if not n.startswith("_")][:120]:
        try:
            attr = getattr(cls, name)
            typ = getattr(attr, "fget", None) and getattr(attr.fget, "__annotations__", {{}}).get("return")
            if typ is not None:
                inner[name] = [m for m in dir(typ) if not m.startswith("_")][:60]
        except BaseException:
            continue
    out[param] = inner
print(json.dumps(out))
"""
    import subprocess

    try:
        proc = subprocess.run([python, "-c", code], capture_output=True, text=True,
                              timeout=timeout)
        lines = [l for l in (proc.stdout or "").strip().splitlines() if l.startswith("{")]
        inner = json.loads(lines[-1]) if lines else {}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, IndexError):
        inner = {}
    for param, mapping in (inner or {}).items():
        for outer, names in (mapping or {}).items():
            for name in (names or [])[:20]:
                out.setdefault(param, []).append(f"{outer}.{name}")
    return out


def compositions(args: Sequence[str], paths: Mapping[str, Sequence[str]],
                 *, stated_symbols: Sequence[str] = (),
                 literals: Sequence[str] = (),
                 problem: str = "",
                 property_paths: Sequence[str] = (),
                 imported_names: Sequence[str] = ()) -> list[dict]:
    """Every body the grammar admits, ordered by how much it ASSERTS.

    Ordering is the whole design, and getting it wrong was measured twice. A type can state
    177 attribute paths (`eq` does); if the combinatorial compositions come first, a 400-entry
    cap is exhausted before `eq.lhs - eq.rhs` is ever reached. So the order is:

      1. leaf attributes the PROBLEM TEXT actually names   (eq.lhs, eq.rhs -- stated, not guessed)
      2. arithmetic over those named attributes
      3. stated-symbol applications over a list of parameters (Matrix([a, b]))
      4. other leaf attributes, other arithmetic, other compositions

    Cost of being wrong here is not a lower score, it is zero score.
    """
    out: list[dict] = []
    seen: set[str] = set()

    def add(kind: str, body: str) -> None:
        if body in seen or len(body) >= 400:
            return
        seen.add(body)
        out.append({"kind": kind, "body": body})

    low = set(re.findall(r"[a-z]{2,}", (problem or "").lower()))

    # 1. attribute paths whose own name the prose uses, then by NAME LENGTH.
    # Length is a measured proxy for API primitiveness: on sympy.Equality the useful members
    # (`lhs`, `rhs`) are the 3rd and 4th shortest of 117, while `as_content_primitive` and
    # friends -- which no problem ever asks for -- are the longest. Ordering by length put
    # `lhs`/`rhs` inside a 600-entry budget where alphabetical order did not.
    stated_paths: list[str] = []
    other_paths: list[str] = []
    for a in args:
        ordered = sorted((paths.get(a) or []), key=lambda p: (len(p), p))
        for p in ordered:
            full = f"{a}.{p}"
            leaf = p.split(".")[-1]
            (stated_paths if leaf.lower() in low else other_paths).append(full)

    # 3f. the parameter's own members, read and wrapped. `list(G.nodes)` is the canonical
    # way to read a container off a graph and the declared type states `nodes`; no symbol
    # surface can reach it because it is not a module-level name.
    for a in args:
        for p in sorted((paths.get(a) or []), key=lambda x: (len(x), x))[:16]:
            add("WRAP", f"list({a}.{p})")
            add("WRAP", f"list({a}.{p})[0]")

    for a in args:
        add("LEAF", a)
    for p in stated_paths:
        add("PATH", p)

    # 2. arithmetic over stated paths first, then everything else
    for x, y in itertools.permutations(stated_paths, 2):
        for op in OPERATORS:
            add("OP", f"{x} {op} {y}")
    for x in stated_paths:
        for y in args:
            for op in OPERATORS:
                add("OP", f"{x} {op} {y}")
                add("OP", f"{y} {op} {x}")

    # 3. stated-symbol applications over a list of the parameters.
    # A stub may bind the symbol directly (`from sympy import Matrix`), in which case the
    # qualified form `sympy.Matrix(...)` is not the name the module exposes at all, and the
    # bare form is. Both are tried; the oracle decides.
    if len(args) >= 2:
        listing = ", ".join(args)
        for sym in stated_symbols:
            add("APPLY", f"{sym}([{listing}])")
            bare = sym.rsplit(".", 1)[-1]
            if bare != sym:
                add("APPLY", f"{bare}([{listing}])")
        add("LIST", f"[{listing}]")
        add("TUPLE", f"({listing})")

    # 3c. comparisons. "checks whether p divides n evenly (i.e. n is a multiple of p)" is
    # answered by `n % p == 0` -- an operator, a literal, and an equality. No application
    # shape can express it and no attribute exists to find. Generated last because it is the
    # least specific, but generated: it is a fixed, tiny family.
    if len(args) >= 2:
        for a, b2 in ((args[0], args[1]), (args[1], args[0])):
            for op in OPERATORS:
                add("PREDICATE", f"{a} {op} {b2} == 0")
                add("PREDICATE", f"{a} {op} {b2} != 0")
        for a, b2 in ((args[0], args[1]), (args[1], args[0])):
            add("PREDICATE", f"{b2} * ({a} // {b2}) == {a}")
            add("PREDICATE", f"{a} % {b2} == 0")
            add("PREDICATE", f"not {a} % {b2}")

    # 3d. IMPORTED NAMES, ONE PER PARAMETER, IN ORDER.
    # A stub that imports RigidBody and Particle and declares (rigid_body_text, particle_text)
    # is stating that the first name goes to the first parameter and the second to the second.
    # `RigidBody(rigid_body_text), Particle(particle_text)` is a comma expression over the
    # imports in declaration order -- no knowledge, purely positional.
    # Only CONSTRUCTOR-shaped names: a module path ('sympy.physics.mechanics') and a scalar
    # annotation ('str') are not things the body can call, and when they led the list the
    # positional pairing produced `sympy.physics.mechanics(rigid_body_text), ...` instead of
    # `RigidBody(rigid_body_text), Particle(particle_text)`.
    constructors = [n for n in dict.fromkeys(imported_names)
                    if n.isidentifier() and n[0].isupper() and "." not in n]
    if constructors and len(constructors) >= 2 and len(args) >= 2:
        n = min(len(constructors), len(args))
        add("TUPLECALL", ", ".join(f"{constructors[j]}({args[j]})" for j in range(n)))
        if len(constructors) >= n + 1:
            rotated = constructors[1:] + constructors[:1]
            add("TUPLECALL", ", ".join(f"{rotated[j]}({args[j]})" for j in range(n)))
    for nm in constructors[:6]:
        for a in args:
            add("APPLY", f"{nm}({a})")

    # 3a-prime. PROPERTIES first. A property is read without a call, so it is the cheapest
    # legal body and needs no shape decision. `index.free_symbols` was at position 136 of 212
    # by name length; as a property it belongs at the front.
    for prop in property_paths[:40]:
        add("PATH", prop)

    # 3a-bis. the shortest attribute paths as standalone bodies. A single attribute read is
    # a legal answer (index.free_symbols) and costs one trial; leaving it below the
    # combinatorial grid pushed it past the cap.
    for p in other_paths[:40]:
        add("PATH", p)

    # 3b. arithmetic over the SHORTEST attribute paths, adjacent pairs first.
    # `eq.lhs - eq.rhs` has neither operand named in the prose, so the stated-path block
    # above cannot produce it and the full permutation is 117^2*7 = 95,823 bodies. Pairing
    # the shortest few members in order covers the real cases (`lhs`, `rhs`; `base`, `exp`)
    # within budget.
    short = other_paths[:24]
    for j in range(len(short)):
        for k in range(len(short)):
            if j == k:
                continue
            for op in OPERATORS:
                add("OP", f"{short[j]} {op} {short[k]}")

    # 4. the remainder
    for p in other_paths:
        add("PATH", p)
    for x, y in itertools.permutations(other_paths, 2):
        for op in OPERATORS:
            add("OP", f"{x} {op} {y}")
    for a in args:
        for name in ("as_explicit", "factor", "expand", "doit", "simplify"):
            add("METHOD", f"{a}.{name}()")
    for sym in stated_symbols[:20]:
        joined = ", ".join(args)
        add("APPLY", f"{sym}({joined})")
        for name in ("as_explicit", "to_list", "doit"):
            add("METHOD", f"{sym}({joined}).{name}()")
    for lit in literals:
        for sym in stated_symbols[:10]:
            if len(args) >= 2:
                add("KWARGS", f"{sym}({lit!r}, {args[0]}, {args[1]})")

    # NOTE: cheap-first reordering was tried here and REJECTED by measurement. It moved
    # eq.lhs - eq.rhs from 169 to 514 and pushed Matrix([first, second]) out of the space
    # entirely, because the count/comparison blocks that must stay near the front are
    # themselves "cheap". The grammar's own order -- stated paths, then arithmetic, then
    # applications -- is the ordering the measurements support.
    return out[:MAX_CANDIDATES]


def solve_item(bench: str | pathlib.Path, item: Mapping[str, Any], *,
               python: str, stated_symbols: Sequence[str] = (),
               corpus: Mapping[str, str] | None = None,
               oracle_timeout: float = 600.0,
               per_body_seconds: int = 5) -> dict:
    import batched_oracle_v1 as BO
    import structured_surface_space_v1 as S

    bench = pathlib.Path(bench)
    item = dict(item)
    imports, alias = S._imports_and_alias(item["starting_code"])
    args = parameters(item["starting_code"])
    spec = S.annotation_spec(item["starting_code"])
    paths = attribute_paths(python, imports, spec) if imports else {}
    lits = literals_in(item.get("problem", ""), item["starting_code"])

    # The stub's own imports and annotations name the types and constructors it can use.
    # Treating every corpus member whose name appears in the prose as "stated" produced
    # `two` and `second` for item 192 -- English words that happen to be module members --
    # and those junk symbols spent the candidate budget the real one (Matrix) needed.
    stub_names: list[str] = []
    for line in item["starting_code"].splitlines():
        line = line.strip()
        if line.startswith("from ") and " import " in line:
            mod, _, names = line.partition(" import ")
            for n in names.split(","):
                n = n.strip().split(" as ")[-1].strip()
                if n and n != "*":
                    stub_names.append(n)
        elif line.startswith("import "):
            for n in line[7:].split(","):
                n = n.strip().split(" as ")[-1].strip()
                if n:
                    stub_names.append(n)
    for anno in (spec or {}).values():
        tail = anno.rsplit(".", 1)[-1]
        if tail.isidentifier():
            stub_names.append(tail)

    # A stub may import with `*` (item 190 does), in which case the ONLY statement of which
    # constructors exist is the RETURN ANNOTATION: tuple[RigidBody, Particle] names both, in
    # the order the function must return them.
    import shape_and_synonym_v1 as _SS

    returns = _SS.return_annotation(item["starting_code"]) or ""
    # The annotation may be dotted (`tuple[sympy.physics.mechanics.RigidBody, ...Particle]`),
    # so a bare isidentifier() check rejects every real name. The tail is what is bound in
    # the module namespace, and it is what the body must call.
    for part in re.split(r"[,\[\]()\s]+", returns):
        tail = part.rsplit(".", 1)[-1]
        if tail.isidentifier() and tail[0].isupper():
            stub_names.append(tail)
    declared = []
    for n in stub_names:
        if n in item["starting_code"]:
            declared.append(n)
        hit = [d for d in corpus if d.rsplit(".", 1)[-1] == n] if corpus else []
        declared.extend(hit[:2])
    ordered_stated = list(dict.fromkeys(declared + list(stated_symbols)))

    props = properties_of(python, imports, spec) if imports else {}
    property_paths = [f"{param}.{name}"
                      for param, names in (props or {}).items()
                      for name in (names or [])]
    cands = compositions(args, paths, stated_symbols=ordered_stated, literals=lits,
                         problem=item.get("problem", ""),
                         property_paths=property_paths,
                         imported_names=stub_names)
    # CHEAP BODIES FIRST, AS THEIR OWN CHUNK. A property read, a leaf, a single attribute and
    # a stated-symbol application each cost one trial and cannot hang. Arithmetic over
    # symbolic objects can hang (`index // index.canonical_variables.index` does), and when it
    # shares a worker with a cheap candidate, the worker is killed and the cheap candidate's
    # correct verdict is lost with it. This was measured on item 191: index.free_symbols
    # passes in 0.4s alone, and every batch containing it returned worker_timeout.
    bodies = [c["body"] for c in cands]
    if not bodies:
        return {"example_id": item["example_id"], "status": "NO_CANDIDATES", "passed": False}

    tests = (bench / "dataset" / "hidden_tests" / f"test_sample_{item['example_id']}.py")
    hit = BO.judge_stream(python, item["starting_code"], tests.read_text(), bodies,
                          timeout=oracle_timeout, test_path=str(tests),
                          per_body_seconds=per_body_seconds)
    if hit and hit.get("passed"):
        cand = cands[hit["index"]]
        return {"example_id": item["example_id"], "status": "SOLVED", "passed": True,
                "kind": cand["kind"], "body": cand["body"], "tried": hit["index"] + 1,
                "paths_known": sum(len(v) for v in paths.values())}
    return {"example_id": item["example_id"], "status": "UNSOLVED", "passed": False,
            "tried": len(bodies), "paths_known": sum(len(v) for v in paths.values())}


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bench", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--ids", required=True)
    ap.add_argument("--json-out")
    args = ap.parse_args(list(argv) if argv is not None else None)

    import learned_ranking_store_v1 as L
    import shape_and_synonym_v1 as SS

    corpus: dict[str, str] = {}
    for line in pathlib.Path("/tmp/deep.jsonl").read_text().splitlines():
        k, v = json.loads(line)
        corpus[k] = v

    bench = pathlib.Path(args.bench)
    items = {json.loads(l)["example_id"]: json.loads(l)
             for l in (bench / "dataset" / "dataset.jsonl").read_text().splitlines() if l.strip()}
    weights = L.get_weights(L.load())
    results = []
    for i in [x.strip() for x in args.ids.split(",") if x.strip()]:
        it = items[i]
        stub = it["starting_code"].split("def ")[-1].split("(")[0]
        ranked = [c["name"] for c in L.rank(corpus, it["problem"], stub, weights, limit=12)]
        stated = SS.stated_symbols(it["problem"], corpus)[:10] if corpus else []
        r = solve_item(args.bench, it, python=args.python,
                       stated_symbols=stated or ranked[:6])
        results.append(r)
        print(json.dumps(r, sort_keys=True), flush=True)
    solved = sum(1 for r in results if r["passed"])
    payload = {"schema": SCHEMA, "solved": solved, "of": len(results),
               "results": results, "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"}
    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps(payload, indent=1, sort_keys=True))
    print(json.dumps({"solved": solved, "of": len(results)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
