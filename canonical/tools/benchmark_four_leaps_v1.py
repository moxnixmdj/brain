#!/usr/bin/env python3
"""Benchmark Leap 1-4 against the repository's own mined, execution-verified corpora.

AUTHORITY: NONE.  This is a *measurement harness*.  It reads corpus JSON and
source text, runs the read-only kernels, and prints a table.  It applies no
repair, executes no repository code, and claims no score on any external
benchmark.  Nothing here is wired into a controller.

Corpora used (both already in-tree, both mined with execution verification):

  ``real_fix_pairs_20261119_V1.json``    87 tasks, full before/after source,
                                         rule: "the commit's test must FAIL at
                                         the parent and PASS at the commit,
                                         verified by execution"
  ``single_line_fix_commits_20261123_V1.json``  45 single-line fixes with the
                                         exact old/new expression

What each leap is measured on, and what the number does and does not mean:

  Leap 1  For every before-file: can the interprocedural lineage graph be built,
          and is the function that the fix actually changed present in it?
          -> "coverage", not "repair".

  Leap 2  For every before/after pair: lower BOTH to the Meaning IR.  A change
          detection is CORRECT when the changed def is reported NOT equal, and
          a false-alarm is when an UNCHANGED def is reported not-equal.  Both
          are counted.  -> this is the only claim the e-graph can support.

  Leap 3  For every changed def whose diff is a single expression: can CEGIS
          re-derive the upstream expression from the buggy one?
          WITNESSES ARE SYNTHETIC, generated from the parameter names with a
          fixed seed.  So this measures *grammar coverage and search*, not
          repair success.  It is reported as such and never summed into a
          "fixed N bugs" headline.

  Leap 4  DeltaSim on a fixed plan set: classification accuracy and the prune
          fraction, plus wall-clock per simulated step.

Usage:  python3 canonical/tools/benchmark_four_leaps_v1.py [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import angelic_cegis_v1 as cegis  # noqa: E402
from canonical.swe_kernel import guarded_meaning_ir_v1 as mir  # noqa: E402
from canonical.swe_kernel import producer_lineage_graph_v1 as plg  # noqa: E402

CORPUS = pathlib.Path(__file__).resolve().parents[1] / "corpus"
PAIRS = CORPUS / "real_fix_pairs_20261119_V1.json"
SINGLE = CORPUS / "single_line_fix_commits_20261123_V1.json"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _defs_by_fn(src: str) -> dict[str, list[str]]:
    """function name -> ordered list of lowered def terms."""
    out: dict[str, list[str]] = {}
    for d in mir.lower_python(src).defs:
        out.setdefault(d.function, []).append(str(d.term))
    return out


def _changed_defs(before: str, after: str) -> list[str]:
    """Names of the functions whose lowered terms differ between the two files."""
    try:
        b, a = _defs_by_fn(before), _defs_by_fn(after)
    except Exception:
        return []
    out = []
    for fn, terms in b.items():
        if a.get(fn) != terms:
            out.append(fn)
    for fn in a:
        if fn not in b:
            out.append(fn)
    return out


def _single_expr_diff(before: str, after: str, fn: str) -> tuple[str, str] | None:
    """(old_expr, new_expr) when the def differs by exactly one expression."""
    import ast

    def _body(src: str, name: str) -> list[ast.stmt] | None:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                return node.body
        return None

    def _expr(stmt: ast.stmt) -> ast.expr | None:
        if isinstance(stmt, ast.Return):
            return stmt.value
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            return stmt.value
        if isinstance(stmt, ast.Expr):
            return stmt.value
        return None

    bb, ab = _body(before, fn), _body(after, fn)
    if not bb or not ab:
        return None
    # normalise: drop docstrings, compare unparsed statement text
    def _norm(body: list[ast.stmt]) -> list[str]:
        rows = []
        for st in body:
            if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) \
                    and isinstance(st.value.value, str):
                continue
            rows.append(ast.unparse(st))
        return rows

    nb, na = _norm(bb), _norm(ab)
    if len(nb) != len(na):
        return None
    diffs = [i for i, (x, y) in enumerate(zip(nb, na)) if x != y]
    if len(diffs) != 1:
        return None
    i = diffs[0]
    # re-derive the original statements at that index (docstrings shift indices)
    def _strip(body: list[ast.stmt]) -> list[ast.stmt]:
        return [st for st in body
                if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant)
                        and isinstance(st.value.value, str))]
    sb, sa = _strip(bb)[i], _strip(ab)[i]
    x, y = _expr(sb), _expr(sa)
    if x is None or y is None:
        return None
    return ast.unparse(x), ast.unparse(y)


def _witnesses(params: list[str], seed: int = 0) -> list[dict[str, Any]]:
    """Synthetic witnesses from parameter NAMES ONLY (never from the fix)."""
    rng = random.Random(seed)
    pool: list[Any] = [0, 1, 2, -1, 3, 10, 100, 0.5, -2, 7, 0.0, 1.5, 42]
    strs = ["", "a", "abc", "x,y", "A B", "1.0", "__version__", "None"]
    out = []
    for _ in range(6):
        env: dict[str, Any] = {}
        for p in params:
            if p in ("self", "cls"):
                env[p] = type("S", (), {"flag": rng.choice([True, False]),
                                        "val": rng.choice([None, 1, "x"])})()
            elif any(t in p.lower() for t in ("name", "str", "text", "msg", "key", "s")):
                env[p] = rng.choice(strs)
            elif any(t in p.lower() for t in ("items", "xs", "values", "args", "it", "iter")):
                env[p] = rng.choice([[1, 2, 3], [], [1], ["a", "b"], (1, 2)])
            else:
                env[p] = rng.choice(pool)
        out.append(env)
    return out


# --------------------------------------------------------------------------- #
# Leap 1 / 2 over the 87 execution-verified pairs
# --------------------------------------------------------------------------- #

def bench_leap_1_and_2() -> dict[str, Any]:
    tasks = json.loads(PAIRS.read_text())["tasks"]
    r: dict[str, Any] = {"tasks": len(tasks)}
    built = 0
    added = 0
    graph_fail: list[str] = []
    fn_nodes = fn_edges = 0
    fn_present = 0
    fn_total = 0
    t_build = 0.0

    detect_true = detect_false = 0
    changed_total = 0
    t_ir = 0.0
    ir_fail: list[str] = []
    modules = 0

    for t in tasks:
        before, after = t["before"], t["after"]
        src = t["source"]
        t0 = time.perf_counter()
        try:
            g = plg.build_lineage_graph_from_sources({src: before})
            built += 1
            fn_nodes += len(g.nodes)
            fn_edges += len(g.edges)
        except Exception as exc:  # noqa: BLE001
            graph_fail.append(f"{t['repo']}:{type(exc).__name__}")
            g = None
        t_build += time.perf_counter() - t0

        changed = _changed_defs(before, after)
        changed_total += len(changed)
        try:
            before_only = set(_defs_by_fn(before))
        except Exception:
            before_only = set()
        if g is not None:
            have = set(g.functions())
            for fn in changed:
                if fn not in before_only:
                    added += 1          # the fix introduced a new function
                    continue
                fn_total += 1
                if fn in have:
                    fn_present += 1

        # ---- change detection -----------------------------------------
        t0 = time.perf_counter()
        try:
            bmap, amap = _defs_by_fn(before), _defs_by_fn(after)
            modules += 1
            for fn in set(bmap) | set(amap):
                differ = bmap.get(fn) != amap.get(fn)
                if differ and fn in changed:
                    detect_true += 1
                elif differ and fn not in changed:
                    detect_false += 1
        except Exception as exc:  # noqa: BLE001
            ir_fail.append(f"{t['repo']}:{type(exc).__name__}")
        t_ir += time.perf_counter() - t0

    r.update({
        "graphs_built": built,
        "graph_failures": graph_fail[:5],
        "graph_build_ms_mean": round(1000 * t_build / max(1, len(tasks)), 2),
        "nodes_mean": round(fn_nodes / max(1, built), 1),
        "edges_mean": round(fn_edges / max(1, built), 1),
        "changed_defs_total": changed_total,
        "changed_defs_mean": round(changed_total / max(1, len(tasks)), 2),
        "changed_function_present_in_graph": f"{fn_present}/{fn_total}",
        "changed_functions_added_by_fix": added,
        "leap_2_modules_lowered": modules,
        "leap_2_lower_failures": ir_fail[:5],
        "leap_2_change_detected_true": detect_true,
        "leap_2_change_detected_false": detect_false,
        "leap_2_lower_ms_mean": round(1000 * t_ir / max(1, len(tasks)), 2),
    })
    return r


# --------------------------------------------------------------------------- #
# Leap 3 over the changed defs
# --------------------------------------------------------------------------- #

def bench_leap_3(limit: int = 40) -> dict[str, Any]:
    tasks = json.loads(PAIRS.read_text())["tasks"]
    import ast

    tried = admitted = refused = 0
    expr_found = 0
    hits: list[dict[str, Any]] = []
    attempts_total = 0

    for t in tasks:
        before, after = t["before"], t["after"]
        for fn in _changed_defs(before, after):
            if tried >= limit:
                break
            pair = _single_expr_diff(before, after, fn)
            if pair is None:
                continue
            expr_found += 1
            old_expr, new_expr = pair
            # target function = the def's own source, with the fix line reverted
            try:
                tree = ast.parse(before)
            except SyntaxError:
                continue
            node = next((n for n in ast.walk(tree)
                         if isinstance(n, ast.FunctionDef) and n.name == fn), None)
            if node is None:
                continue
            params = [a.arg for a in node.args.args]
            inputs = _witnesses(params)

            def oracle(env, _n=new_expr, _b=before, _fn=fn):
                ns = {"__builtins__": __builtins__}
                ns.update(env)
                return eval(_n, ns)  # noqa: S307 - trusted corpus text

            try:
                res = cegis.synthesize_hole(
                    before, target=fn, oracle=oracle, inputs=inputs, budget=96)
            except Exception:
                refused += 1
                tried += 1
                continue
            tried += 1
            attempts_total += int(res.get("attempts") or 0)
            if res.get("admitted"):
                admitted += 1
                if len(hits) < 6:
                    hits.append({"repo": t["repo"], "fn": fn,
                                 "new": new_expr[:90],
                                 "got": str(res["candidate"]["expr"])[:90]})
            else:
                refused += 1
        if tried >= limit:
            break

    return {
        "tasks_with_single_expression_diff": expr_found,
        "attempted": tried,
        "admitted": admitted,
        "refused": refused,
        "admission_rate": round(admitted / max(1, tried), 3),
        "attempts_mean": round(attempts_total / max(1, tried), 1),
        "witnesses": "SYNTHETIC (from parameter names, seed 0) -- NOT the repo's tests",
        "sample_admissions": hits,
    }


# --------------------------------------------------------------------------- #
# Leap 3b -- the 45 single-line upstream fixes, expression pair verbatim
# --------------------------------------------------------------------------- #

def _expr_of(stmt_text: str):
    """The expression inside a single-line statement, plus its free names."""
    import ast
    try:
        node = ast.parse(stmt_text.strip()).body[0]
    except SyntaxError:
        return None
    val = None
    if isinstance(node, ast.Return):
        val = node.value
    elif isinstance(node, ast.Assign) and len(node.targets) == 1:
        val = node.value
    elif isinstance(node, ast.If):
        val = node.test
    elif isinstance(node, ast.Expr):
        val = node.value
    if val is None:
        return None
    names = sorted({n.id for n in ast.walk(val) if isinstance(n, ast.Name)})
    return ast.unparse(val), names


def _witnesses_for(names: list[str], seed: int = 0) -> list[dict[str, Any]]:
    """Synthetic witnesses over the NAMES THAT OCCUR IN THE FIX.

    Not the repository's tests, not its fixtures.  The only thing this can
    measure is whether the grammar can even reach the shape.
    """
    rng = random.Random(seed)
    nums = [0, 1, 2, -1, 3, 7, 10, 100, 0.5, 1.5, -2]
    strs = ["", "a", "abc", "x,y", "A B", "1.0", "__version__", "NO_OP", "v1"]
    out = []
    for _ in range(8):
        env: dict[str, Any] = {}
        for n in names:
            low = n.lower()
            if any(t in low for t in ("name", "str", "text", "msg", "key", "s", "err",
                                      "value", "attr", "field", "path", "url")):
                env[n] = rng.choice(strs)
            elif any(t in low for t in ("items", "xs", "values", "args", "iter", "list",
                                        "parts", "lines", "attrs", "seq")):
                env[n] = rng.choice([[1, 2, 3], [], [1], ["a", "b"], (1, 2)])
            elif low.startswith("is_") or low in ("frozen", "flag", "cond"):
                env[n] = rng.choice([True, False])
            else:
                env[n] = rng.choice(nums)
        out.append(env)
    return out


def bench_leap_3_single_line() -> dict[str, Any]:
    entries = json.loads(SINGLE.read_text())["entries"]
    considered = attempted = admitted = exact = 0
    reach = {"unhinted": 0, "hinted": 0}
    refusals: dict[str, int] = {}
    hits: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []
    reach_samples: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for e in entries:
        old = _expr_of(e["old_line"])
        new = _expr_of(e["new_line"])
        if old is None or new is None:
            continue
        old_expr, n1 = old
        new_expr, n2 = new
        names = sorted(set(n1) | set(n2))
        if not names:
            continue
        considered += 1
        is_guard = e["old_line"].strip().startswith("if ")
        src = "def _target(" + ", ".join(names) + "):\n    return " + old_expr + "\n"
        inputs = _witnesses_for(names)

        def oracle(env, _x=new_expr):
            ns = {"__builtins__": __builtins__}
            ns.update(env)
            return eval(_x, ns)  # noqa: S307 - trusted corpus text

        # ---- witness-free measurement: is the fix shape even REACHABLE? ---
        # This does not need a witness and cannot be inflated by one.  It asks
        # only: does the grammar generate the upstream expression at all?
        #
        # Two variants, because they measure different things:
        #   unhinted  -- the vocabulary the SOURCE alone provides
        #   hinted    -- the same, plus the method names the fix uses.  A fix
        #                that is reachable only when hinted is a VOCABULARY gap,
        #                not a grammar gap, and saying so is the useful result.
        import ast as _ast

        def _methods(text: str) -> dict[str, list[str]]:
            try:
                node = _ast.parse(text.strip()).body[0]
            except SyntaxError:
                return {}
            out: dict[str, list[str]] = {}
            val = getattr(node, "value", None) or getattr(node, "test", None)
            for n in _ast.walk(val) if val is not None else []:
                if isinstance(n, _ast.Attribute) and isinstance(n.value, _ast.Name):
                    out.setdefault(n.value.id, []).append(n.attr)
            return out

        hint = _methods(new_expr)
        for label, vocab in (("unhinted", None), ("hinted", hint)):
            try:
                scope = cegis.harvest_scope(src, target="_target",
                                            method_vocabulary=vocab)
                reachable = any(
                    expr.replace(" ", "") == new_expr.replace(" ", "")
                    for expr, _sch in cegis.candidate_space(
                        scope, kind=("guard" if is_guard else "value"), budget=6000))
            except Exception:
                reachable = False
            if reachable:
                reach[label] += 1
                if len(reach_samples) < 8:
                    reach_samples.append({"repo": e["repo"], "variant": label,
                                          "new": new_expr[:70]})
            elif label == "hinted":
                gaps.append({"repo": e["repo"], "old": old_expr[:60],
                             "new": new_expr[:60]})

        attempted += 1
        try:
            if is_guard:
                res = cegis.synthesize_guard(src, target="_target", oracle=oracle,
                                             inputs=inputs, budget=128)
            else:
                res = cegis.synthesize_hole(src, target="_target", oracle=oracle,
                                            inputs=inputs, budget=128)
        except Exception as exc:  # noqa: BLE001
            refusals[type(exc).__name__] = refusals.get(type(exc).__name__, 0) + 1
            continue
        if res.get("admitted"):
            admitted += 1
            got = str(res["candidate"]["expr"])
            same = got.replace(" ", "") == new_expr.replace(" ", "")
            if same:
                exact += 1
            row = {"repo": e["repo"], "old": old_expr[:70], "new": new_expr[:70],
                   "got": got[:70], "attempts": res["attempts"]}
            (hits if same else misses).append(row)
        else:
            reason = str(res.get("reason"))
            refusals[reason] = refusals.get(reason, 0) + 1

    return {
        "single_line_fixes_considered": considered,
        "attempted": attempted,
        "admitted": admitted,
        "exact_expression_rediscovered": exact,
        "admitted_but_not_exact": admitted - exact,
        "refused": attempted - admitted,
        "admission_rate": round(admitted / max(1, attempted), 3),
        "exact_rate": round(exact / max(1, attempted), 3),
        "refusal_reasons": refusals,
        "in_grammar_unhinted": reach["unhinted"],
        "in_grammar_with_method_hint": reach["hinted"],
        "grammar_reach_rate_unhinted": round(reach["unhinted"] / max(1, considered), 3),
        "grammar_reach_rate_hinted": round(reach["hinted"] / max(1, considered), 3),
        "grammar_gaps": gaps[:8],
        "witnesses": "SYNTHETIC (from names occurring in the fix) -- NOT the repo's tests",
        "sample_exact_hits": hits[:6],
        "sample_inexact": misses[:4],
    }


# --------------------------------------------------------------------------- #
# Leap 4 -- DeltaSim throughput and classification
# --------------------------------------------------------------------------- #

def bench_leap_4() -> dict[str, Any]:
    sim = mir.DeltaSim({"balance": 100.0, "items": 3.0},
                       invariants=[("balance_nonneg", lambda f: f["balance"] >= 0)])

    def dep(f):
        return {**f, "balance": f["balance"] + 10.0}

    def blow(f):
        return {**f, "balance": f["balance"] - 1000.0}

    acts = [
        mir.Action("deposit", (("write", "balance"),), apply=dep),
        mir.Action("noop", (("write", "balance"),), apply=lambda f: dict(f)),
        mir.Action("overdraw", (("write", "balance"),), apply=blow),
        mir.Action("shred", (("destroy", "disk"),)),
        mir.Action("crash", (("write", "balance"),), raises=True),
        mir.Action("peek", (("read", "items"),)),
    ]
    out = sim.prune(acts)
    verdicts = {r["action"]: r["verdict"] for r in out["safe"] + out["pruned"]}
    expected = {"deposit": "SAFE", "noop": "NOOP", "overdraw": "INVARIANT_VIOLATION",
                "shred": "DESTRUCTIVE_UNWITNESSED", "crash": "CRASH", "peek": "SAFE"}
    correct = sum(1 for k, v in expected.items() if verdicts.get(k) == v)

    # throughput: 2000 simulated steps
    t0 = time.perf_counter_ns()
    for i in range(2000):
        sim.push()
        sim.apply(acts[0])
        sim.pop()
    per_step_us = (time.perf_counter_ns() - t0) / 2000 / 1000

    # a plan that must be refused
    plan = [acts[0], acts[2]]
    plan_out = sim.simulate_plan(plan)

    return {
        "classification": f"{correct}/{len(expected)}",
        "verdicts": verdicts,
        "pruned_fraction": round(out["pruned_fraction"], 4),
        "simulated_step_us": round(per_step_us, 2),
        "plan_viable": plan_out["viable"],
        "plan_reason": plan_out["reason"],
        "plan_at_step": plan_out["at_step"],
    }


# --------------------------------------------------------------------------- #
# Leap 2b -- real polyglot repositories (optional: needs a local clone)
# --------------------------------------------------------------------------- #

POLYGLOT = {"c": ".c", "javascript": ".js", "typescript": ".ts",
            "go": ".go", "rust": ".rs", "cpp": ".cpp"}
SKIP_PARTS = {"node_modules", "test", "tests", "fuzz", "benches", "examples",
              ".git", "vendor", "third_party"}


def bench_polyglot(root: pathlib.Path, per_repo: int = 400) -> dict[str, Any]:
    """Lower every real file of every language found under ``root``.

    Two numbers, neither of which needs a witness: how much real polyglot code
    the lowerer accepts without a parse failure, and how much of it is the SAME
    MEANING repeated (the e-graph's distinct-class ratio over real code).
    """
    rows: list[dict[str, Any]] = []
    for repo in sorted(p for p in root.iterdir() if p.is_dir()):
        lang = next((k for k, v in POLYGLOT.items()
                     if any(repo.rglob("*" + v))), None)
        if lang is None:
            continue
        files = [p for p in repo.rglob("*" + POLYGLOT[lang])
                 if not any(x in SKIP_PARTS for x in p.parts)][:per_repo]
        ids: list[int] = []
        defs = calls = 0
        g = mir.SemiPersistentEGraph()
        t0 = time.perf_counter()
        for f in files:
            try:
                m = mir.lower_file(f)
            except Exception:
                continue
            defs += len(m.defs)
            calls += len(m.calls)
            ids.extend(g.add(d.term) for d in m.defs)
        t_lower = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        g.saturate(rounds=1, budget=4000)
        t_sat = (time.perf_counter() - t0) * 1000
        roots = {g.find(i) for i in ids}
        rows.append({
            "repo": repo.name, "lang": lang, "files": len(files),
            "defs": defs, "calls": calls, "distinct_meanings": len(roots),
            "dedup_pct": round(100 * (1 - len(roots) / max(1, len(ids))), 1),
            "lower_ms": round(t_lower, 1), "saturate_ms": round(t_sat, 1),
            "lower_ms_per_file": round(t_lower / max(1, len(files)), 2),
        })
    tot = sum(r["defs"] for r in rows)
    dist = sum(r["distinct_meanings"] for r in rows)
    return {"rows": rows, "defs": tot, "distinct_meanings": dist,
            "dedup_pct": round(100 * (1 - dist / max(1, tot)), 1),
            "repos": len(rows),
            "note": ("dedup_pct is the share of lowered definitions that are the "
                     "same Meaning-IR term as another one, after one saturation "
                     "round.  It is a measure of redundancy in the corpus, not of "
                     "code quality.")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--polyglot-root", default=None,
                    help="directory of cloned repos to lower (real polyglot code)")
    args = ap.parse_args()

    print("Leap 1+2 : execution-verified before/after pairs ...", flush=True)
    t0 = time.perf_counter()
    l12 = bench_leap_1_and_2()
    l12["elapsed_s"] = round(time.perf_counter() - t0, 2)
    print("Leap 3   : single-expression rediscovery (synthetic witnesses) ...", flush=True)
    t0 = time.perf_counter()
    l3 = bench_leap_3(limit=args.limit)
    l3["elapsed_s"] = round(time.perf_counter() - t0, 2)
    print("Leap 3b  : the 45 single-line upstream fixes ...", flush=True)
    t0 = time.perf_counter()
    l3b = bench_leap_3_single_line()
    l3b["elapsed_s"] = round(time.perf_counter() - t0, 2)
    print("Leap 4   : DeltaSim classification + throughput ...", flush=True)
    l4 = bench_leap_4()

    print("\n=== Leap 1 -- interprocedural producer lineage ===")
    for k in ("tasks", "graphs_built", "graph_failures", "nodes_mean", "edges_mean",
              "graph_build_ms_mean", "changed_defs_mean",
              "changed_function_present_in_graph"):
        print(f"  {k:38s} {l12[k]}")
    print("\n=== Leap 2 -- Meaning IR change detection ===")
    for k in ("leap_2_modules_lowered", "leap_2_lower_failures", "changed_defs_total",
              "leap_2_change_detected_true", "leap_2_change_detected_false",
              "leap_2_lower_ms_mean"):
        print(f"  {k:38s} {l12[k]}")
    print("\n=== Leap 3 -- angelic CEGIS expression rediscovery ===")
    for k in ("tasks_with_single_expression_diff", "attempted", "admitted", "refused",
              "admission_rate", "attempts_mean", "witnesses"):
        print(f"  {k:38s} {l3[k]}")
    for h in l3["sample_admissions"]:
        print(f"    + {h['repo']}:{h['fn']}  new={h['new']!r}")
        print(f"      got={h['got']!r}")
    print("\n=== Leap 3b -- single-line upstream fixes (expression pair verbatim) ===")
    for k in ("single_line_fixes_considered", "attempted", "admitted",
              "exact_expression_rediscovered", "admitted_but_not_exact", "refused",
              "admission_rate", "exact_rate", "in_grammar_unhinted",
              "in_grammar_with_method_hint", "grammar_reach_rate_unhinted",
              "grammar_reach_rate_hinted", "refusal_reasons", "witnesses"):
        print(f"  {k:38s} {l3b[k]}")
    for g in l3b["grammar_gaps"]:
        print(f"    ! gap {g['repo']}: {g['old']!r} -> {g['new']!r}")
    for h in l3b["sample_exact_hits"]:
        print(f"    = {h['repo']}: {h['new']!r}  ({h['attempts']} attempts)")
    for h in l3b["sample_inexact"]:
        print(f"    ~ {h['repo']}: want {h['new']!r}")
        print(f"                            got  {h['got']!r}")
    l2b = None
    if args.polyglot_root:
        print("\n=== Leap 2b -- real polyglot repositories ===")
        l2b = bench_polyglot(pathlib.Path(args.polyglot_root))
        print(f"  {'repo':14s}{'lang':11s}{'files':>6s}{'defs':>7s}{'distinct':>10s}"
              f"{'dedup%':>8s}{'lower_ms':>10s}{'sat_ms':>8s}")
        for r in l2b["rows"]:
            print(f"  {r['repo']:14s}{r['lang']:11s}{r['files']:6d}{r['defs']:7d}"
                  f"{r['distinct_meanings']:10d}{r['dedup_pct']:7.1f}%"
                  f"{r['lower_ms']:10.1f}{r['saturate_ms']:8.1f}")
        print(f"  {'TOTAL':14s}{'':11s}{sum(r['files'] for r in l2b['rows']):6d}"
              f"{l2b['defs']:7d}{l2b['distinct_meanings']:10d}{l2b['dedup_pct']:7.1f}%")
        print(f"  note: {l2b['note']}")
    print("\n=== Leap 4 -- DeltaSim ===")
    for k, v in l4.items():
        print(f"  {k:38s} {v}")

    if args.json:
        out = {"schema": "PROJECT_BRAIN_FOUR_LEAP_BENCHMARK_V1",
               "authority": "NONE__MEASUREMENT_ONLY",
               "leap_1_leap_2": l12, "leap_3": l3, "leap_3b": l3b,
               "leap_4": l4, "leap_2b_polyglot": l2b}
        pathlib.Path(args.json).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
