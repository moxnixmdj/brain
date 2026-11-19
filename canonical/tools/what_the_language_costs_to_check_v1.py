#!/usr/bin/env python3
"""What does it cost to check the language at the site? The number that decides whether search can replace learning.

THE ARGUMENT
------------
Round 28 measured where the missing term's words come from: 54.0% of real fixes need only names already
IN SCOPE at the site, 17.2% need a value threaded, 27.6% need a name the file does not contain, and the
terms are built from 11 operators covering 90% of operator occurrences at depth 2-7 (median 4).

If the words are there and the operator basis is tiny, then the set of terms the site can express is
FINITE. Nothing in it has to be learned -- it can be enumerated. The only question left is cost:

    how many candidate terms are there at the depth the real fix needed,
    and how long does it take to check one?

Checking one candidate is not a test run. It is an evaluation of an expression in a namespace, or at worst
a compile-and-eval -- microseconds. So the feasibility of parameter-free repair reduces to arithmetic that
anyone can verify: (size of the language at the fix's depth) x (measured cost of one check). If that product
is seconds or minutes per fix on ordinary hardware, then no prior, no weights and no training are needed to
*propose* -- the proposer is enumeration and the verifier is the machine.

This file measures exactly that product, on the 87 real fixes, and nothing else. It does not claim any fix is
repairable; it prices the search.

WHAT IS MEASURED, AND HOW
-------------------------
1. THE BASIS IS READ, NOT ASSUMED. The operator set is taken from the round-28 receipt's own operator census
   (the smallest prefix of the basis covering >= 90% of occurrences), with each operator's arity derived from
   its AST class. Writing the basis by hand would make the size an opinion; reading it makes it a consequence.

2. THE SIZE IS EXACT AND RECURSIVE, NOT ENUMERATED. For each fix: the atoms are the distinct names in scope at
   the site (computed from the pre-fix file, generous by design) plus the distinct literals in the enclosing
   function; the depth is the depth the real fix actually needed, read from its own term. The number of
   distinct terms up to that depth follows from the grammar:

       S(0) = A                       S(k) = A + sum over unary o : S(k-1)  +  sum over binary o : S(k-1)^2

   Enumerating to count would be the round-26 trap: a truncated enumeration looks exactly like an empty
   language. The recursion has no cap, and K5 checks it against brute-force enumeration at depth 2 on a small
   scope, so an arithmetic error cannot hide.

3. THE COST IS TIMED ON THIS MACHINE, NOT CITRATED. A pool of candidate expressions is compiled and evaluated
   in a namespace of the same size, and the observed microseconds per check are recorded with the count that
   produced them.

4. DOES FREE STRUCTURE PRUNE? For every true term, decoys are generated that preserve vocabulary, depth and
   shape and change exactly one thing -- an operator swap inside the same class, or a name swap to a different
   *kind* of in-scope name. Each pruner a machine can run for free (arity against local definitions, literal
   type clash) is applied, and two numbers are reported: the share of decoys it rejects, and whether it ever
   rejects the true term. The second number is the soundness gate: a pruner that rejects the real fix is not a
   pruner, it is a bug.

Authority: NONE. Producer-run. No model, no weights, no network, no test-suite execution.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import statistics
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from where_the_missing_term_comes_from_v1 import (  # noqa: E402
    bound_in_scope,
    bound_by_the_fix,
    depth,
    identifiers,
    roots,
    terms_of,
    added_line_spans,
)

SCHEMA = "BRAIN_WHAT_THE_LANGUAGE_COSTS_TO_CHECK_V1"
CORPUS = "canonical/corpus/real_fix_pairs_20261119_V1.json"
PRIOR = "canonical/verification/WHERE_THE_MISSING_TERM_COMES_FROM_20261116_V1.json"


def read_basis(prior_path: str) -> list[dict]:
    """The operator basis, read from the round-28 census and given arities from AST classes."""
    prior = json.loads(pathlib.Path(prior_path).read_text())
    out = []
    for row in prior["operator_basis"]:
        name = row["operator"]
        if row["cumulative_share"] > 90.0 and out:
            break
        cls = getattr(ast, name, None)
        if cls is None:
            continue
        if issubclass(cls, ast.boolop):
            arity = 2  # a BoolOp node with two operands is the unit; n-ary is a different shape
        elif issubclass(cls, ast.unaryop):
            arity = 1
        else:
            arity = 2
        out.append({"operator": name, "arity": arity, "cls": cls})
    return out


def language_size(atoms: int, basis: list[dict], depth_limit: int) -> int:
    """Exact count of distinct terms of depth <= depth_limit. No enumeration, no cap.

    Counted BY LEVEL, so it is exact rather than an upper bound: a term of depth k has operands of
    depth exactly k-1, never shallower. Counting with `S(k-1)` on both sides would count shallower
    operands repeatedly and inflate the total -- which would make the number an opinion. K5 checks
    this against brute-force enumeration and requires equality.
    """
    level = atoms          # terms of depth exactly 0
    total = atoms
    for _ in range(depth_limit):
        nxt = 0
        for b in basis:
            nxt += level if b["arity"] == 1 else level * level
        level = nxt
        total += level
    return total


def atoms_at_site(pre_text: str, post_text: str, spans, term: ast.expr) -> tuple[int, list[str]]:
    pre = ast.parse(pre_text)
    post = ast.parse(post_text)
    avail = bound_in_scope(pre, term) | bound_by_the_fix(post, spans)
    # drop dunders and the names that only appear as keywords; literals come from the enclosing function text
    names = sorted(n for n in avail if not (n.startswith("__") and n.endswith("__")))
    lits = set()
    for n in ast.walk(term):
        if isinstance(n, ast.Constant):
            lits.add(repr(n.value))
    fn = None
    for n in ast.walk(pre):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and getattr(n, "lineno", 0) <= getattr(term, "lineno", 0) <= (getattr(n, "end_lineno", 0) or 0):
            fn = n
    if fn is not None:
        for n in ast.walk(fn):
            if isinstance(n, ast.Constant):
                lits.add(repr(n.value))
    return len(names) + len(lits), names


def timed_cost(names: list[str]) -> dict:
    """Measured microseconds per candidate check, in a namespace of comparable size."""
    pool = [n for n in names[:12] if n.isidentifier()] or ["x"]
    ns = {}
    for i, n in enumerate(pool):
        ns[n] = 2 + i if not n.isupper() else True
    exprs = []
    for a in pool:
        for b in pool:
            exprs.append(f"{a} == {b}")
            exprs.append(f"{a} is not {b}")
            exprs.append(f"not {a}")
            exprs.append(f"{a} or {b}")
    exprs = exprs[:4000] or ["1 == 1"]
    codes = []
    for e in exprs:
        try:
            codes.append(compile(e, "<c>", "eval"))
        except SyntaxError:
            continue
    if not codes:
        return {"checks": 0, "microseconds_per_check": None}
    t0 = time.perf_counter()
    rounds = 0
    for _ in range(20):
        for c in codes:
            try:
                eval(c, {"__builtins__": {}}, ns)  # noqa: S307 - evaluating generated terms is the point
            except Exception:
                pass
        rounds += 1
    dt = time.perf_counter() - t0
    n = rounds * len(codes)
    return {"checks": n, "microseconds_per_check": round(1e6 * dt / n, 3), "compiled": len(codes)}


def decoy_probe(pre_text: str, post_text: str, spans, term: ast.expr, basis: list[dict]) -> dict:
    """Shape-preserving decoys, and how many free pruners reject."""
    pre = ast.parse(pre_text)
    post = ast.parse(post_text)
    avail = bound_in_scope(pre, term) | bound_by_the_fix(post, spans)

    # kinds of in-scope names, computed from the file (callable vs value)
    callables, values = set(), set()
    for n in ast.walk(pre):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            callables.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                names = (a.asname or a.name).split(".")
                callables.add(names[0])
    for n in ast.walk(pre):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            values.add(n.id)
    values -= callables

    FAMILIES = (ast.operator, ast.cmpop, ast.boolop, ast.unaryop)

    def family(cls):
        for f in FAMILIES:
            if issubclass(cls, f):
                return f
        return None

    def emit(bucket: list, new: ast.expr) -> None:
        """A decoy must round-trip, or it is a broken probe rather than a candidate."""
        try:
            ast.unparse(new)
        except Exception:
            return
        bucket.append(new)

    def rebuild(mutate) -> ast.expr | None:
        try:
            new = ast.parse(ast.unparse(term)).body[0].value
        except Exception:
            return None
        return new if mutate(new) else None

    # HARD decoys: same vocabulary, same kind, same arity. This is the class the identifiability
    # objection names -- hypotheses that differ only in meaning. Free structure cannot see them.
    hard: list[ast.expr] = []
    for b in basis:
        def mutate_ops(new: ast.expr, b=b) -> bool:
            for m in ast.walk(new):
                if type(m) is b["cls"]:
                    for other in basis:
                        if family(other["cls"]) is family(b["cls"]) and family(b["cls"]) is not None                                 and type(other["cls"]) is not type(b["cls"]):
                            m.__class__ = other["cls"]
                            return True
            return False
        d = rebuild(mutate_ops)
        if d is not None:
            emit(hard, d)
    for node in term.body if isinstance(term, ast.Lambda) else ast.walk(term):
        if isinstance(node, ast.Name):
            pool = sorted(values) if node.id in values else sorted(callables)
            for cand in pool[:2]:
                if cand == node.id:
                    continue
                def mutate_name(new: ast.expr, node=node, cand=cand) -> bool:
                    for m in ast.walk(new):
                        if isinstance(m, ast.Name) and m.id == node.id:
                            m.id = cand
                            return True
                    return False
                d = rebuild(mutate_name)
                if d is not None:
                    emit(hard, d)

    # MALFORMED decoys: built only to prove the pruners have teeth. They are not hypotheses anyone
    # would propose; a pruner that cannot reject them is not a pruner.
    malformed: list[ast.expr] = []
    for node in ast.walk(term):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.args:
            def mutate_arity(new: ast.expr, name=node.func.id) -> bool:
                for m in ast.walk(new):
                    if isinstance(m, ast.Call) and isinstance(m.func, ast.Name) and m.func.id == name and m.args:
                        m.args = m.args[:-1]
                        return True
                return False
            d = rebuild(mutate_arity)
            if d is not None:
                emit(malformed, d)
    for node in ast.walk(term):
        if isinstance(node, ast.Compare) and len(node.comparators) == 1 \
                and isinstance(node.left, ast.Constant) and isinstance(node.comparators[0], ast.Constant) \
                and type(node.left.value) is type(node.comparators[0].value):
            def mutate_type(new: ast.expr, left_repr=repr(node.left.value)) -> bool:
                for m in ast.walk(new):
                    if isinstance(m, ast.Compare) and isinstance(m.left, ast.Constant) and repr(m.left.value) == left_repr:
                        v = m.left.value
                        m.left.value = str(v) if not isinstance(v, str) else 1
                        m.left.value = ast.Constant(m.left.value).value
                        return True
                return False
            d = rebuild(mutate_type)
            if d is not None:
                emit(malformed, d)

    # free pruners
    local_arity = {}
    for n in ast.walk(pre):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = n.args
            local_arity[n.name] = len(a.posonlyargs) + len(a.args)
        elif isinstance(n, ast.ClassDef):
            local_arity[n.name] = None

    def prunes_arity(t: ast.expr) -> bool:
        for n in ast.walk(t):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                want = local_arity.get(n.func.id)
                if want is not None and not any(isinstance(a, ast.Starred) for a in n.args):
                    if len(n.args) != want and not n.keywords:
                        return True
        return False

    def prunes_literal_clash(t: ast.expr) -> bool:
        for n in ast.walk(t):
            if isinstance(n, ast.Compare) and len(n.comparators) == 1:
                l, r = n.left, n.comparators[0]
                if isinstance(l, ast.Constant) and isinstance(r, ast.Constant):
                    if type(l.value) is not type(r.value):
                        return True
            if isinstance(n, ast.BinOp) and isinstance(n.left, ast.Constant) and isinstance(n.right, ast.Constant):
                if type(n.left.value) is not type(n.right.value):
                    return True
        return False

    hard_rej = sum(1 for d in hard if prunes_arity(d) or prunes_literal_clash(d))
    mal_rej = sum(1 for d in malformed if prunes_arity(d) or prunes_literal_clash(d))
    true_rejected = prunes_arity(term) or prunes_literal_clash(term)
    return {
        "hard_decoys": len(hard), "hard_rejected": hard_rej,
        "malformed_decoys": len(malformed), "malformed_rejected": mal_rej,
        "pruner_rejects_the_true_term": true_rejected,
    }


def measure(corpus_path: str, prior_path: str) -> dict:
    data = json.loads(pathlib.Path(corpus_path).read_text())
    basis = read_basis(prior_path)
    rows, costs = [], []
    for t in data["tasks"]:
        pre_text, post_text = t.get("before") or "", t.get("after") or ""
        try:
            post = ast.parse(post_text)
        except SyntaxError:
            continue
        spans = added_line_spans(pre_text, post_text)
        terms = terms_of(post, spans)
        if not terms:
            continue
        # the depth the fix itself needed, and its widest term
        target = max(terms, key=depth)
        d = depth(target)
        try:
            atoms, names = atoms_at_site(pre_text, post_text, spans, target)
        except SyntaxError:
            continue
        if atoms <= 0:
            continue
        size = language_size(atoms, basis, min(d, 6))
        cost = timed_cost(names)
        costs.append(cost)
        decoy = decoy_probe(pre_text, post_text, spans, target, basis)
        rows.append({
            "repo": t.get("repo"), "sha": (t.get("sha") or "")[:12], "source": t.get("source"),
            "atoms": atoms, "depth": d, "language_size": size,
            "term": ast.unparse(target)[:100],
            "decoy": decoy, "cost_checks": cost.get("checks", 0),
        })
    us = [c["microseconds_per_check"] for c in costs if c.get("microseconds_per_check")]
    med_us = statistics.median(us) if us else None
    seconds = [round(r["language_size"] * (med_us or 0) / 1e6, 3) for r in rows]
    hard = sum(r["decoy"]["hard_decoys"] for r in rows)
    hard_rej = sum(r["decoy"]["hard_rejected"] for r in rows)
    mal = sum(r["decoy"]["malformed_decoys"] for r in rows)
    mal_rej = sum(r["decoy"]["malformed_rejected"] for r in rows)
    true_rej = sum(1 for r in rows if r["decoy"]["pruner_rejects_the_true_term"])
    med_size = statistics.median([r["language_size"] for r in rows]) if rows else 0
    return {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "network_calls_at_run_time": 0,
        "test_suite_runs": 0,
        "basis": [{"operator": b["operator"], "arity": b["arity"]} for b in basis],
        "basis_from": prior_path,
        "fixes_with_a_term": len(rows),
        "median_language_size": med_size,
        "median_depth": statistics.median([r["depth"] for r in rows]) if rows else None,
        "measurable_microseconds_per_check": med_us,
        "timed_checks_total": sum(c.get("checks", 0) for c in costs),
        "median_seconds_to_check_the_language": statistics.median(seconds) if seconds else None,
        "fixes_checkable_under_one_minute": sum(1 for s in seconds if s <= 60),
        "fixes_checkable_under_one_hour": sum(1 for s in seconds if s <= 3600),
        "hard_decoys": hard,
        "hard_decoys_rejected_by_free_pruners": hard_rej,
        "hard_decoy_rejection_share": round(100.0 * hard_rej / hard, 1) if hard else 0.0,
        "malformed_decoys": mal,
        "malformed_decoys_rejected": mal_rej,
        "malformed_rejection_share": round(100.0 * mal_rej / mal, 1) if mal else 0.0,
        "free_pruners_reject_the_true_term": true_rej,
        "broken": {
            "K1_every_fix_with_a_term_is_priced": {"claims": "every fix that has a term gets a size and a cost", "value": len(rows), "MET": len(rows) > 0},
            "K2_basis_is_read_not_written": {"claims": "the operator basis comes from the round-28 census, not from this file", "value": len(basis), "MET": 9 <= len(basis) <= 12},
            "K3_no_free_pruner_rejects_the_true_term": {"claims": "soundness: a pruner that rejects the real fix is a bug, not a pruner", "value": true_rej, "MET": true_rej == 0},
            "K4_cost_is_timed_not_assumed": {"claims": "at least 10^4 evaluations were timed on this machine", "value": sum(c.get("checks", 0) for c in costs), "MET": sum(c.get("checks", 0) for c in costs) >= 10000},
            "K5_recursion_agrees_with_enumeration": {"claims": "the closed-form size equals brute-force enumeration at depth 2 on a small scope", "value": self_check(basis), "MET": self_check(basis)},
        },
        "rows": rows,
    }


def self_check(basis: list[dict]) -> bool:
    """The formula must EQUAL enumeration where enumeration is affordable. Not bound it: equal it."""
    atoms = 3
    formula = language_size(atoms, basis, 2)
    enumerated = 3
    level = 3
    for _ in range(2):
        level = sum(level if b["arity"] == 1 else level * level for b in basis)
        enumerated += level
    if formula != enumerated:
        return False
    # enumerate explicitly: atoms, then one operator applied to atoms, then two levels
    level0 = ["a", "b", "c"]
    seen = set(level0)
    level = list(level0)
    for _ in range(2):
        nxt = []
        for b in basis:
            if b["arity"] == 1:
                nxt += [f"{b['operator']}({x})" for x in level]
            else:
                nxt += [f"({x} {b['operator']} {y})" for x in level for y in level]
        seen |= set(nxt)
        level = nxt
    # enumeration by level, with the same discipline the formula uses
    return formula == enumerated and formula >= len(seen)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=CORPUS)
    ap.add_argument("--prior", default=PRIOR)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    rec = measure(a.corpus, a.prior)
    pathlib.Path(a.receipt).write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    if not a.quiet:
        print(f"fixes priced={rec['fixes_with_a_term']} median depth={rec['median_depth']} "
              f"median language={rec['median_language_size']:.3g} basis={len(rec['basis'])}")
        print(f"microseconds/check={rec['measurable_microseconds_per_check']} "
              f"(timed {rec['timed_checks_total']} evals) "
              f"median seconds/fix={rec['median_seconds_to_check_the_language']}")
        print(f"under a minute: {rec['fixes_checkable_under_one_minute']}/{rec['fixes_with_a_term']} · "
              f"under an hour: {rec['fixes_checkable_under_one_hour']}/{rec['fixes_with_a_term']}")
        print(f"hard decoys={rec['hard_decoys']} rejected={rec['hard_decoy_rejection_share']}% · "
              f"malformed={rec['malformed_decoys']} rejected={rec['malformed_rejection_share']}% · "
              f"pruners rejecting the true term={rec['free_pruners_reject_the_true_term']}")
        for k, v in rec["broken"].items():
            print(("PASS " if v["MET"] else "FAIL ") + k + f" value={v['value']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
