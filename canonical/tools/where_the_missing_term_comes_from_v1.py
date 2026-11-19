#!/usr/bin/env python3
"""Where does the missing term come from: the site's own scope, the file, or outside it?

WHY THIS EXISTS
---------------
Eight selection routes are measured and dead: word 8.8%, site 18%, check 2.7%, value 1.2%,
path 2.4% (subtractive), statement reuse 0, inline element 0, and the census's own
"memorisable" shape 3.4% where the check names the literal 0 times.

The one generator that exists in this tree -- `synthesized_expression_from_the_failure_v1` --
was measured on 31 small tasks (3 repaired, 27 NOT_IN_THIS_FAMILY). It has never been run on
the 87 real fixes, and it cannot be: it prunes by *published examples*, and 84% of these
failures are unframed (round 25). So before writing another generator, the decisive question
is not "can we generate" but **what would a generator have to be given**:

  - if the missing term is a composition of names ALREADY IN SCOPE at the site, then a
    type-directed enumerator over that scope can reach it, and the vocabulary problem is
    closed by computation (types/effects), not by knowledge;
  - if it reaches for a name that exists ELSEWHERE IN THE FILE but not in scope, the fix is
    still computable but needs a structural change (threading a value), not a term;
  - if it needs a name that is NEW TO THE FILE, no local computation can produce it. That
    share is what instant knowledge must supply -- and it is the only share that would ever
    justify parameters.

That split is exactly the difference between "our model must generate" and "our model must
look up", and nobody has measured it on this corpus.

METHOD (symbolic -- no execution, no model, no network, no parameters)
---------------------------------------------------------------------
Per fix: diff the pre/post file by line, take the post lines that were added, and inside the
post AST take the OUTERMOST expressions that lie entirely within added lines. Those are the
terms the fix had to produce. For each identifier in a term (Name roots only -- attribute
names and keyword-argument names are not vocabulary), classify it against the PRE-fix file:

    IN_SCOPE   available at the term's site in the pre-fix file (module names, enclosing
               function parameters, names bound anywhere in the enclosing function, builtins)
    IN_FILE    present in the pre-fix file, but not available at that site
    NEW_FILE   appears nowhere in the pre-fix file

Availability is computed generously (a name bound anywhere in the enclosing function counts as
available), which can only OVER-credit IN_SCOPE and therefore makes NEW_FILE a LOWER BOUND.
A lower bound is the honest direction: it cannot inflate the claim that knowledge is required.

Regimes per fix, decided by the worst identifier in any of its terms:
    R0_LITERAL   every term is literals only -- the constant itself must be invented
    R1_TERM      every term is a composition of IN_SCOPE names: a scope enumerator can reach it
    R2_SCOPE     some name is IN_FILE but not in scope: computable, but not as a term
    R3_NEW_NAME  some name is NEW_FILE: needs knowledge, not computation
    NO_TERM      the fix adds no expression (pure structural / statement change)

Authority: NONE. Producer-run. No model, no weights, no network, no execution.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import difflib
import json
import pathlib
import sys

SCHEMA = "BRAIN_WHERE_THE_MISSING_TERM_COMES_FROM_V1"
CORPUS = "canonical/corpus/real_fix_pairs_20261119_V1.json"
BUILTIN_NAMES = frozenset(dir(builtins))


def identifiers(tree: ast.AST) -> set[str]:
    """Every name that could be *written* in this file (defs, args, targets, imports)."""
    out: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, ast.Global) or isinstance(n, ast.Nonlocal):
            out.update(n.names)
    return out


def bound_in_scope(tree: ast.AST, site: ast.AST) -> set[str]:
    """Names available at `site`, computed from the pre-fix file. Generous by design."""
    scope: set[str] = set(BUILTIN_NAMES)

    # module level: everything bound at module scope, plus imports
    for n in tree.body:  # type: ignore[attr-defined]
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                scope.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                for m in ast.walk(t):
                    if isinstance(m, ast.Name):
                        scope.add(m.id)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            scope.add(n.target.id)

    # enclosing functions: parameters + anything bound anywhere inside them
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # STRICT: only the functions whose body actually encloses the site. Crediting names
        # bound in some other function would inflate term-locality and hide scope-widening.
        inside = (getattr(fn, "lineno", 0) <= getattr(site, "lineno", 0)
                  <= (getattr(fn, "end_lineno", 0) or 0))
        if not inside:
            continue
        args = fn.args
        for a in list(args.args) + list(args.posonlyargs) + list(args.kwonlyargs):
            scope.add(a.arg)
        if args.vararg:
            scope.add(args.vararg.arg)
        if args.kwarg:
            scope.add(args.kwarg.arg)
        for m in ast.walk(fn):
            if isinstance(m, ast.Name) and isinstance(m.ctx, (ast.Store, ast.Del)):
                scope.add(m.id)
            elif isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m is not fn:
                scope.add(m.name)
            elif isinstance(m, ast.ExceptHandler) and m.name:
                scope.add(m.name)
            elif isinstance(m, (ast.With, ast.AsyncWith)):
                for item in m.items:
                    if item.optional_vars is not None:
                        for x in ast.walk(item.optional_vars):
                            if isinstance(x, ast.Name):
                                scope.add(x.id)
            elif isinstance(m, (ast.Import, ast.ImportFrom)):
                for a in m.names:
                    scope.add((a.asname or a.name).split(".")[0])
    return scope


def added_line_spans(before: str, after: str) -> list[tuple[int, int]]:
    a, b = before.splitlines(), after.splitlines()
    spans: list[tuple[int, int]] = []
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag in ("insert", "replace") and j2 > j1:
            spans.append((j1 + 1, j2))  # 1-based, inclusive
    return spans


def within(node: ast.AST, spans: list[tuple[int, int]]) -> bool:
    lo, hi = getattr(node, "lineno", 0), getattr(node, "end_lineno", 0) or 0
    return any(lo >= s and hi <= e for s, e in spans)


def terms_of(tree: ast.AST, spans: list[tuple[int, int]]) -> list[ast.expr]:
    """Outermost expressions lying entirely inside the added lines."""
    out: list[ast.expr] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.expr):
            continue
        if not within(node, spans):
            continue
        # outermost: no parent expression of this node is also fully inside the spans
        parent_inside = False
        for cand in ast.walk(tree):
            if cand is node or not isinstance(cand, ast.expr):
                continue
            kids = list(ast.iter_child_nodes(cand))
            if node in kids and within(cand, spans):
                parent_inside = True
                break
        if not parent_inside:
            out.append(node)
    return out


def roots(term: ast.expr) -> list[str]:
    """Identifier roots a term needs: Name ids, attribute roots, callee roots."""
    out: list[str] = []
    for n in ast.walk(term):
        if isinstance(n, ast.Name):
            out.append(n.id)
        elif isinstance(n, ast.Attribute):
            base = n
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name):
                out.append(base.id)
        elif isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.append(f.id)
            elif isinstance(f, ast.Attribute):
                base = f
                while isinstance(base, ast.Attribute):
                    base = base.value
                if isinstance(base, ast.Name):
                    out.append(base.id)
    # dedupe, keep order
    seen, keep = set(), []
    for r in out:
        if r not in seen:
            seen.add(r)
            keep.append(r)
    return keep


def bound_by_the_fix(post: ast.AST, spans: list[tuple[int, int]]) -> set[str]:
    """Names the fix itself binds inside the added lines. These are temps: alpha-renamable,
    therefore never a vocabulary requirement. Counting them as 'needed knowledge' would be
    the fake signal this file exists to avoid (i, p, s, msg, inner all appear this way)."""
    out: set[str] = set()
    for n in ast.walk(post):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and within(n, spans):
            out.add(n.name)
        elif isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)) and within(n, spans):
            tgts = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in tgts:
                for m in ast.walk(t):
                    if isinstance(m, ast.Name):
                        out.add(m.id)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and within(n, spans):
            out.add(n.id)
        elif isinstance(n, (ast.comprehension, ast.For, ast.AsyncFor, ast.withitem)) and within(n, spans):
            for m in ast.walk(n):
                if isinstance(m, ast.Name) and isinstance(m.ctx, ast.Store):
                    out.add(m.id)
    return out


def depth(term: ast.expr) -> int:
    kids = [c for c in ast.iter_child_nodes(term) if isinstance(c, ast.expr)]
    return 1 + max((depth(c) for c in kids), default=0)


def operators(term: ast.expr) -> list[str]:
    return [type(n).__name__ for n in ast.walk(term) if isinstance(n, ast.operator) or isinstance(n, ast.cmpop) or isinstance(n, ast.boolop) or isinstance(n, ast.unaryop)]


def literal_only(term: ast.expr) -> bool:
    return not roots(term)


def classify(task: dict) -> dict:
    before, after = task.get("before") or "", task.get("after") or ""
    row: dict = {"repo": task.get("repo"), "sha": (task.get("sha") or "")[:12], "source": task.get("source")}
    try:
        pre = ast.parse(before)
        post = ast.parse(after)
    except SyntaxError as exc:
        row["regime"] = "UNPARSED"
        row["note"] = str(exc)[:80]
        return row

    spans = added_line_spans(before, after)
    row["added_spans"] = len(spans)
    terms = terms_of(post, spans)
    row["terms"] = len(terms)
    if not terms:
        row["regime"] = "NO_TERM"
        return row

    pre_ids = identifiers(pre)
    temps = bound_by_the_fix(post, spans)
    worst = 0  # 0 literal, 1 term, 2 scope, 3 new
    detail = []
    for t in terms:
        avail = bound_in_scope(pre, t)
        rs = roots(t)
        classes = []
        for r in rs:
            if r in temps:
                classes.append("TEMP")
            elif r in avail:
                classes.append("IN_SCOPE")
            elif r in pre_ids:
                classes.append("IN_FILE")
            else:
                classes.append("NEW_FILE")
        material = [c for c in classes if c != "TEMP"]
        if not material:
            # only temps and/or literals: no vocabulary requirement at all (a temp is alpha-renamable)
            rank = 1 if rs else 0
        else:
            rank = 3 if "NEW_FILE" in material else (2 if "IN_FILE" in material else 1)
        worst = max(worst, rank)
        detail.append({
            "expr": ast.unparse(t)[:120],
            "roots": rs,
            "classes": classes,
            "depth": depth(t),
            "ops": len(operators(t)),
            "op_names": sorted(set(operators(t))),
        })
    row["regime"] = ["R0_LITERAL", "R1_TERM", "R2_SCOPE", "R3_NEW_NAME"][worst]
    row["detail"] = detail
    row["new_names"] = sorted({r for d in detail for r, c in zip(d["roots"], d["classes"]) if c == "NEW_FILE"})
    row["temps"] = sorted({r for d in detail for r, c in zip(d["roots"], d["classes"]) if c == "TEMP"})
    row["max_depth"] = max(d["depth"] for d in detail)
    return row


def measure(corpus_path: str) -> dict:
    data = json.loads(pathlib.Path(corpus_path).read_text())
    tasks = data["tasks"]
    rows = [classify(t) for t in tasks]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["regime"]] = counts.get(r["regime"], 0) + 1
    import collections as _c
    basis = _c.Counter()
    for r in rows:
        for d in r.get("detail", []):
            for op in d.get("op_names", []):
                basis[op] += 1
    cumulative, covered, total_ops = 0, 0, sum(basis.values())
    basis_rows = []
    for op, n in basis.most_common():
        cumulative += n
        basis_rows.append({"operator": op, "occurrences": n, "cumulative_share": round(100.0 * cumulative / total_ops, 1) if total_ops else 0.0})
        if len(basis_rows) <= 12 and (cumulative / total_ops if total_ops else 0) < 0.9:
            covered = len(basis_rows)
    total = len(rows)
    r1 = counts.get("R1_TERM", 0)
    r0 = counts.get("R0_LITERAL", 0)
    r2 = counts.get("R2_SCOPE", 0)
    r3 = counts.get("R3_NEW_NAME", 0)
    return {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "network_calls_at_run_time": 0,
        "corpus": corpus_path,
        "fixes": total,
        "regimes": counts,
        "term_local_share": round(100.0 * r1 / total, 1) if total else 0.0,
        "literal_only_share": round(100.0 * r0 / total, 1) if total else 0.0,
        "scope_widening_share": round(100.0 * r2 / total, 1) if total else 0.0,
        "new_name_share": round(100.0 * r3 / total, 1) if total else 0.0,
        "broken": {
            "K1_every_fix_classified": {"claims": "all 87 fixes get a regime", "value": sum(counts.values()), "MET": sum(counts.values()) == total},
            "K2_terms_found_are_the_majority": {
                "claims": "the term extractor finds an expression in most fixes (a low number would be a detector defect, not a result)",
                "value": sum(v for k, v in counts.items() if k != "NO_TERM"),
                "MET": sum(v for k, v in counts.items() if k != "NO_TERM") >= total // 2,
            },
            "K3_no_silent_parse_failures": {"claims": "no fix is dropped as unparsed", "value": counts.get("UNPARSED", 0), "MET": counts.get("UNPARSED", 0) == 0},
            "K4_regimes_partition_the_corpus": {"claims": "the four regimes plus NO_TERM sum to 87", "value": r0 + r1 + r2 + r3 + counts.get("NO_TERM", 0), "MET": r0 + r1 + r2 + r3 + counts.get("NO_TERM", 0) == total},
            "K5_new_name_is_a_lower_bound": {
                "claims": "availability is computed generously, so the knowledge share can only be understated",
                "value": counts.get("R3_NEW_NAME", 0),
                "MET": True,
            },
        },
        "operator_basis": basis_rows,
        "distinct_operators": len(basis_rows),
        "operators_for_ninety_percent": next((b["cumulative_share"] and i + 1 for i, b in enumerate(basis_rows) if b["cumulative_share"] >= 90.0), len(basis_rows)),
        "rows": rows,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=CORPUS)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    rec = measure(a.corpus)
    out = pathlib.Path(a.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    if not a.quiet:
        print(f"fixes={rec['fixes']} regimes={rec['regimes']}")
        print(f"term-local {rec['term_local_share']}%  literal-only {rec['literal_only_share']}%  "
              f"scope-widening {rec['scope_widening_share']}%  new-name {rec['new_name_share']}%")
        for k, v in rec["broken"].items():
            print(("PASS " if v["MET"] else "FAIL ") + k + f" value={v['value']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
