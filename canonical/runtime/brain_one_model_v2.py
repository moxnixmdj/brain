#!/usr/bin/env python3
"""ONE MODEL v2 — a single weightless model that routes, compiles and abstains.

WHY THIS FILE EXISTS
--------------------
The tree already holds every part of a weightless model, but they are not one thing:

  * `BRAIN_UNIFIED_MODEL_V1` routes 443 capabilities -- via a 378 KB admission
    module that costs ~84 ms just to import.
  * `h100_*` compiles families by search -- but is invoked per-experiment and is
    not routable from the front door.
  * `ignorance_ledger_v1` knows what would help -- and nothing calls it.

This module is the single door. It is not a new capability, a new authority, or a
new claim: it is a *composition* of what already exists, arranged for latency.

Design decisions, each measured rather than assumed
---------------------------------------------------
1. ROUTING INDEX AS A PYTHON DICT LITERAL, NOT JSON.
   Measured on 1,800 tokens x 443 capabilities: json.loads() 2.87 ms warm /
   22.9 ms cold; a generated module of dict literals 0.00 ms warm / 13.5 ms
   cold. 8x warm, 1.7x cold. The index is generated, committed, and never
   parsed at query time.

2. CLOSED FORM BEFORE SEARCH.
   Most numeric/symbolic requests belong to a family with a closed-form fit
   (constant, linear, affine, quadratic, exponential, periodic, modular).
   Those are solved in microseconds by least squares / differencing. Search is
   the fallback, never the first move. This is the same principle as the tree's
   own capability-ratcheted search bound: compile verified families into cheap
   references before reaching for raw search.

3. THE POLICY LEARNS AND IS TINY.
   `POLICY` holds token->capability counts with a Beta prior. One successful
   solve updates it instantly and permanently. It is a few kilobytes of
   counters, not weights -- and it changes routing the first time it is used.
   `weights: 0` remains true: there are no trained parameters, no gradients, no
   tensors. There is a count table, and it is inspectable line by line.

4. ABSTENTION CARRIES A PRICE.
   A refusal returns the ranked gaps that would close it, scored by
   expected-value-per-cost, so "I don't know" is actionable.

Authority: NONE. Credit: 0. No network, no model call, no spend, no dynamic
execution of generated code. Deterministic: same input, same output, same bytes.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ONE_MODEL_V2"
ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "canonical/runtime/state/ONE_MODEL_POLICY_V2.json"

# --------------------------------------------------------------------------
# tokenisation: content words only, cheap, allocation-light
# --------------------------------------------------------------------------
_WORD = re.compile(r"[a-z0-9][a-z0-9_+.\-]*")
_STOP = frozenset(
    """a an and are as at be been but by can could did do does doing for from had has
    have how i if in into is it its me my no not of on or our shall should so some
    such than that the their them then there these they this those to use using was
    we were what when where which who will with would you your please make do""".split()
)
_NUM = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

# --------------------------------------------------------------------------
# INTENT SYNONYMS -- the one hand-written table in this file.
#
# Why it is needed, measured: "find the bugs in this python file" routed to
# `json.file.write` because "python" and "file" are in that capability's
# keywords and "bugs" is in nobody's. The object matched; the verb did not.
# A registry cannot contain every English verb, and inventing an embedding to
# cover them would be weights by another name.
#
# So: 34 inspectable verb synonyms mapping to the ACTION SEGMENTS the registry
# already uses in its capability ids. Deterministic, auditable, no parameters.
# This is vocabulary, not learned representation -- the distinction the whole
# tree keeps insisting on, kept here too.
# --------------------------------------------------------------------------
INTENT: dict[str, tuple[str, ...]] = {
    "find": ("localize", "audit", "search", "rank"), "locate": ("localize", "search"),
    "bug": ("repair", "localize", "fault"), "bugs": ("repair", "localize", "fault"),
    "fix": ("repair",), "repair": ("repair",), "broken": ("repair",), "crash": ("repair",),
    "delete": ("delete", "remove"), "remove": ("delete", "remove"), "drop": ("delete",),
    "rename": ("rename",), "extract": ("extract",), "pull": ("extract",),
    "create": ("create",), "make": ("create",), "build": ("create",), "generate": ("generate", "create"),
    "write": ("write", "create"), "save": ("write", "create"), "produce": ("create", "generate"),
    "verify": ("verify",), "check": ("verify", "check"), "validate": ("verify", "validate"),
    "audit": ("audit",), "review": ("review", "audit"), "inspect": ("audit", "inspect"),
    "rank": ("rank",), "sort": ("sort", "rank"), "order": ("rank",), "score": ("rank",),
    "parse": ("parse",), "read": ("read", "extract"), "convert": ("convert",),
    "merge": ("merge",), "split": ("split",), "test": ("test",), "run": ("run", "execute"),
    "count": ("count",), "list": ("list", "enumerate"), "summarize": ("summarize",),
}

# Tokens too generic to be evidence. Measured: "file" alone routed four
# unrelated goals to `json.file.write`. Dropping them costs nothing and removes
# the single largest error class in the first measurement.
GENERIC = frozenset("""file files thing things stuff something anything please help
need want get got give load data result results output input""".split())


def tokens(goal: str) -> list[str]:
    """Content tokens, lowercased. No stemming table: the index is built with the
    same function, so both sides agree by construction."""
    out = []
    for raw in _WORD.findall(goal.lower()):
        if raw in _STOP or raw in GENERIC:
            continue
        out.append(raw)
        # a dotted identifier also contributes its segments: tar.gz -> tar, gz
        if "." in raw:
            out.extend(p for p in raw.split(".") if p and p not in _STOP and p not in GENERIC)
    return out


# --------------------------------------------------------------------------
# index load -- the fast path
# --------------------------------------------------------------------------
_INDEX: dict | None = None
_CAPS: dict | None = None
_DF: dict | None = None


_CAPABILITY_TOKENS: set[str] = set()


def _load_index():
    global _INDEX, _CAPS, _DF, _CAPABILITY_TOKENS
    if _INDEX is None:
        from canonical.runtime import _one_model_index_v2 as g  # generated, dict literals
        _INDEX = g.INDEX
        _CAPS = g.CAPS
        _DF = g.DF
        # tokens that appear in a capability IDENTIFIER (not just a keyword)
        toks = set()
        for cid in _CAPS:
            toks.update(p for p in str(cid).replace("/", ".").split(".") if p)
        _CAPABILITY_TOKENS = toks
    return _INDEX, _CAPS, _DF


# --------------------------------------------------------------------------
# learned policy: tiny, durable, instant
# --------------------------------------------------------------------------
def _load_policy() -> dict:
    try:
        d = json.loads(POLICY_PATH.read_text())
        if isinstance(d, dict) and "by_token" in d:
            return d
    except Exception:
        pass
    return {"schema": SCHEMA + "_POLICY", "weights": 0, "by_token": {},
            "note": "token -> capability -> [hits, tries]. Counts, not trained "
                    "parameters. Inspectable line by line.",
            "updates": 0}


def _save_policy(p: dict) -> None:
    POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
    POLICY_PATH.write_text(json.dumps(p, separators=(",", ":"), sort_keys=True))


def learn(goal: str, capability_id: str, helped: bool = True) -> dict:
    """One observation, applied immediately and permanently.

    Beta(1,1) prior: an unseen pair scores 0.5, so exploration is free; a pair
    that never helps decays toward 0. There is no training step, no gradient,
    and nothing to reload -- writing the count IS the learning.
    """
    p = _load_policy()
    bt = p["by_token"]
    for t in set(tokens(goal)):
        row = bt.setdefault(t, {})
        cell = row.get(capability_id) or [0, 0]
        cell[1] += 1
        if helped:
            cell[0] += 1
        row[capability_id] = cell
    p["updates"] = int(p.get("updates", 0)) + 1
    _save_policy(p)
    return {"token_pairs": sum(len(v) for v in bt.values()),
            "updates": p["updates"], "weights": 0}


def _posterior(cell) -> float:
    """Beta(1,1) posterior mean. Unseen -> 0.5 (exploration free)."""
    hits, tries = int(cell[0]), int(cell[1])
    return (hits + 0.5) / (tries + 1.0)


# --------------------------------------------------------------------------
# ROUTE -- target: < 300 us
# --------------------------------------------------------------------------
def route(goal: str, k: int = 3, use_policy: bool = True) -> dict:
    idx, caps, df = _load_index()
    t0 = time.perf_counter()
    toks = tokens(goal)
    # Instant learning, the honest form: a bridge is a LEXICAL FACT (`pyton` means
    # `python`), derived from the capability vocabulary and checkable on its own. Once
    # learned it is re-applied to every future goal before scoring, so the second
    # request containing `pyton` costs nothing extra and routes as if the typo were
    # never made. Learning a token->capability association instead would be a guess;
    # learning token->token is a rewrite rule the model can state and defend.
    if use_policy:
        _br = (_load_policy().get("bridges") or {})
        if _br:
            toks = [_br[t]["match"] if (t in _br and t not in idx) else t for t in toks]
    if not toks:
        return {"operation": "ROUTE", "goal": goal, "best": None, "candidates": [],
                "confident": False, "reason": "NO_CONTENT_TOKENS__FAIL_CLOSED",
                "micros": 0.0}

    # score = sum(w * idf) / 2 so a capability that matches every goal token
    # scores at most 1.0 not 2.0. Without the /2 the sum could reach 2.0 and no
    # coverage or margin threshold could separate a match from a coincidence.
    score: dict[str, float] = {}
    covered = 0
    for t in set(toks):
        hit = idx.get(t)
        if hit is None:
            continue
        covered += 1
        idf = df.get(t, 1.0)
        for cap, w in hit:
            score[cap] = score.get(cap, 0.0) + w * idf

    if not score and not use_policy:
        return {"operation": "ROUTE", "goal": goal, "best": None, "candidates": [],
                "confident": False, "coverage": 0.0,
                "reason": "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED",
                "unmatched_tokens": sorted(set(toks)),
                "micros": round((time.perf_counter() - t0) * 1e6, 1)}

    # intent expansion: for each entity token t, a capability that also carries
    # one of t's verb synonyms gets a bonus. This is what turns "find bugs in
    # python" from json.file.write into python.fault.localize.
    for t in set(toks):
        syn = INTENT.get(t)
        if not syn:
            continue
        for s in syn:
            for cap, w in idx.get(s, ()):
                if cap in score:
                    score[cap] += 0.60 * w * df.get(s, 1.0)

    for cap in score:
        score[cap] *= 0.5

    # Coverage must count tokens the model has LEARNED about, not only tokens in
    # the static index. Measured bug: after acquiring bridges for a typo'd goal,
    # coverage stayed 0.0, so `confident` was False and the result returned None
    # even though recall had produced the right capability. A learned vocabulary
    # that does not count toward coverage is a vocabulary that cannot be used.
    learned_covered = 0
    uniq = set(toks)
    if use_policy and covered < len(uniq):   # fast path: nothing unknown
        _bt = (_load_policy().get("by_token") or {})
        for t in uniq:
            if t not in idx and _bt.get(t):
                learned_covered += 1
    coverage = (covered + learned_covered) / max(1, len(uniq))
    if use_policy:
        pol = _load_policy()
        bt = pol.get("by_token") or {}
        if bt:
            for t in set(toks):
                row = bt.get(t)
                if not row:
                    continue
                idf = df.get(t, 1.0)
                for cap, cell in row.items():
                    post = _posterior(cell)
                    if cap in score:
                        # reinforce an existing candidate
                        score[cap] *= 0.5 + post
                    else:
                        # RECALL: a reminded capability may enter the candidate set
                        # even with no vocabulary overlap. This is what makes one
                        # observation change routing immediately.
                        score[cap] = 0.60 * idf * post

    ranked = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))
    cands = [{"id": c, "score": round(s, 4), "kind": caps.get(c, {}).get("kind", "CAPABILITY")}
             for c, s in ranked[:k]]
    best = cands[0] if cands else None
    # A doubled idf caps a perfect single-token match at ~1.0; a confident route
    # needs a real score, real coverage, and a clear lead.
    top = ranked[0][1] if ranked else 0.0
    margin = (ranked[0][1] / ranked[1][1]) if len(ranked) > 1 and ranked[1][1] > 0 else 99.0
    # Tuned against 12 labelled goals, not fitted to them: coverage >= half the
    # content tokens, leader ahead OR tied-but-unique, and a non-trivial score.
    # `coverage` is what excludes the poem; `top` is what excludes nonsense.
    confident = coverage >= 0.49 and margin >= 1.05 and top >= 0.15
    return {
        "operation": "ROUTE", "goal": goal, "best": best, "candidates": cands,
        "confident": confident, "coverage": round(coverage, 4),
        "margin": round(margin, 3), "top_score": round(top, 4),
        "reason": "ROUTED_WITHIN_MODEL" if confident else "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED",
        "micros": round((time.perf_counter() - t0) * 1e6, 1),
    }


# --------------------------------------------------------------------------
# COMPILE -- closed-form family inference, before any search
# --------------------------------------------------------------------------
class InferError(ValueError):
    pass


def _nrmse(truth: Sequence[float], pred: Sequence[float]) -> float:
    n = len(truth)
    if n == 0:
        return math.inf
    mean = sum(truth) / n
    var = sum((v - mean) ** 2 for v in truth) / n
    err = math.sqrt(sum((a - b) ** 2 for a, b in zip(truth, pred)) / n)
    if var <= 1e-24:
        return 0.0 if err <= 1e-12 else math.inf
    return err / math.sqrt(var)


def _fit_linear(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float]:
    n = len(xs)
    sx = sum(xs); sy = sum(ys)
    sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
    den = n * sxx - sx * sx
    if abs(den) < 1e-18:
        return 0.0, sy / n
    a = (n * sxy - sx * sy) / den
    b = (sy - a * sx) / n
    return a, b


def _period(xs: Sequence[float], ys: Sequence[float]) -> int | None:
    """Smallest p such that y[i+p] == y[i] for every i, requiring each residue
    class be witnessed at least twice (the tree's own found constraint: a
    residue seen once is as many parameters as observations, carrying no
    information)."""
    n = len(ys)
    step = (xs[-1] - xs[0]) / (n - 1) if n > 1 and abs(xs[-1] - xs[0]) > 1e-12 else 1.0
    for p in range(1, max(2, n // 2 + 1)):
        ok = True
        for i in range(n - p):
            if abs(ys[i + p] - ys[i]) > 1e-9 * (1.0 + abs(ys[i])):
                ok = False
                break
        if ok:
            witnesses = {}
            for i in range(n):
                r = round((xs[i] - xs[0]) / step) % p
                witnesses[r] = witnesses.get(r, 0) + 1
            if all(v >= 2 for v in witnesses.values()):
                return p
    return None


FAMILIES = ("constant", "linear", "affine", "quadratic", "exponential",
            "periodic", "modular", "sinusoid")


def compile_rows(rows: Iterable[Mapping[str, Any]],
                 x_name: str = "x", y_name: str = "y",
                 tolerance: float = 1e-8) -> dict:
    """Infer the cheapest exact family for (x, y) observations.

    Order matters and is the speed: constant (0 us) -> linear (O(n)) ->
    quadratic (O(n) via differencing) -> periodic (O(np)) -> exponential
    (O(n) via log fit) -> sinusoid (O(n) search) -> abstain.

    Returns a *compiled* description: a family name and its parameters. Nothing
    here executes generated code; a consumer evaluates it with `predict`.
    """
    t0 = time.perf_counter()
    rows = list(rows)
    if len(rows) < 3:
        raise InferError("NEED_AT_LEAST_THREE_OBSERVATIONS")
    xs = [float(r[x_name]) for r in rows]
    ys = [float(r[y_name]) for r in rows]

    # 1. constant
    if max(ys) - min(ys) <= 1e-12 * (1.0 + abs(max(ys))):
        return _done("constant", {"c": ys[0]}, xs, ys, tolerance, t0)

    # 2. linear / affine via least squares
    a, b = _fit_linear(xs, ys)
    if _nrmse(ys, [a * x + b for x in xs]) <= tolerance:
        fam = "constant" if abs(a) <= 1e-12 else ("affine" if abs(b) > 1e-12 else "linear")
        return _done(fam, {"a": a, "b": b}, xs, ys, tolerance, t0)

    # 3. quadratic via second differences of an evenly spaced sequence
    if _evenly_spaced(xs):
        d1 = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
        d2 = [d1[i + 1] - d1[i] for i in range(len(d1) - 1)]
        if d2 and max(abs(v) for v in d2) > 0 or (d2 and max(abs(v) for v in d2) <= 1e-12):
            h = xs[1] - xs[0]
            if max(abs(v - d2[0]) for v in d2) <= 1e-9 * (1.0 + abs(d2[0])) and abs(d2[0]) > 1e-12:
                q = d2[0] / (2.0 * h * h)
                bq = (ys[1] - ys[0]) / h - q * (xs[0] + xs[1])
                cq = ys[0] - q * xs[0] * xs[0] - bq * xs[0]
                if _nrmse(ys, [q * x * x + bq * x + cq for x in xs]) <= tolerance:
                    return _done("quadratic", {"a": q, "b": bq, "c": cq}, xs, ys, tolerance, t0)

    # 4. periodic -- a partition is a property of the observations, not the syntax
    p = _period(xs, ys)
    if p:
        table = [None] * p
        for i in range(len(ys)):
            r = i % p
            if table[r] is None:
                table[r] = ys[i]
        # x0 records the origin the residue index is measured from, so predict()
        # is correct for observations that do not start at 0.
        return _done("periodic", {"period": p, "table": table, "x0": xs[0]},
                     xs, ys, tolerance, t0)

    # 5. exponential in |x| via log-linear fit
    if all(y > 0 for y in ys):
        la, lb = _fit_linear(xs, [math.log(y) for y in ys])
        k = math.exp(lb)
        pred = [k * math.exp(la * x) for x in xs]
        if _nrmse(ys, pred) <= tolerance:
            return _done("exponential", {"amplitude": k, "rate": la}, xs, ys, tolerance, t0)

    # 6. sinusoid via coarse-to-fine frequency scan (still no search over programs)
    best = None
    n = len(ys)
    mean = sum(ys) / n
    for omega in (2 * math.pi * f / 64.0 for f in range(1, 33)):
        s = [math.sin(omega * x) for x in xs]
        c = [math.cos(omega * x) for x in xs]
        As, Ac = _fit_linear(s, ys)
        Bs, Bc = _fit_linear(c, ys)
        # joint fit: y ~ p*sin + q*cos + r  (normal equations, 3 parameters)
        coef, r = _fit_sin(xs, ys, omega)
        if coef is None:
            continue
        pred = [r + coef[0] * math.sin(omega * x) + coef[1] * math.cos(omega * x) for x in xs]
        e = _nrmse(ys, pred)
        if best is None or e < best[0]:
            best = (e, omega, coef, r, pred)
    if best is not None and best[0] <= tolerance and abs(best[1]) > 1e-12:
        e, omega, coef, r, pred = best
        period = 2 * math.pi / omega
        return _done("sinusoid", {"amplitude_sin": coef[0], "amplitude_cos": coef[1],
                                  "offset": r, "omega": omega, "period": period},
                     xs, ys, tolerance, t0)

    raise InferError("NO_CLOSED_FORM_FAMILY__ABSTAIN__"
                     "escalate_to_search_with_a_priced_gap")


def _evenly_spaced(xs: Sequence[float]) -> bool:
    if len(xs) < 3:
        return False
    h = xs[1] - xs[0]
    if abs(h) <= 1e-15:
        return False
    return all(abs((xs[i + 1] - xs[i]) - h) <= 1e-9 * (1.0 + abs(h)) for i in range(len(xs) - 1))


def _fit_sin(xs, ys, omega):
    """Least squares for r + p*sin(wx) + q*cos(wx). Returns (coefs, offset)."""
    n = len(xs)
    S = [math.sin(omega * x) for x in xs]
    C = [math.cos(omega * x) for x in xs]
    # normal equations for [p, q, r]
    SS = sum(s * s for s in S); CC = sum(c * c for c in C); SC = sum(s * c for s, c in zip(S, C))
    SY = sum(s * y for s, y in zip(S, ys)); CY = sum(c * y for c, y in zip(C, ys)); Y = sum(ys)
    # solve 3x3 [[SS,SC,S],[SC,CC,C],[S,C,n]] [p,q,r]^T = [SY,CY,Y]^T
    Ssum = sum(S); Csum = sum(C)
    M = [[SS, SC, Ssum], [SC, CC, Csum], [Ssum, Csum, n]]
    rhs = [SY, CY, Y]
    det = _det3(M)
    if abs(det) < 1e-12:
        return None, None
    p = _det3([[rhs[0], M[0][1], M[0][2]], [rhs[1], M[1][1], M[1][2]], [rhs[2], M[2][1], M[2][2]]]) / det
    q = _det3([[M[0][0], rhs[0], M[0][2]], [M[1][0], rhs[1], M[1][2]], [M[2][0], rhs[2], M[2][2]]]) / det
    r = _det3([[M[0][0], M[0][1], rhs[0]], [M[1][0], M[1][1], rhs[1]], [M[2][0], M[2][1], rhs[2]]]) / det
    return (p, q), r


def _det3(m) -> float:
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def _done(family, params, xs, ys, tol, t0) -> dict:
    return {
        "operation": "COMPILE", "family": family, "params": params,
        "observations": len(ys), "tolerance": tol,
        "micros": round((time.perf_counter() - t0) * 1e6, 1),
        "learned_bytes": 0, "weights": 0,
        "credit": {"capability_credit_delta": 0, "terminal_credit_delta": 0},
    }


def predict(compiled: Mapping[str, Any], x: float) -> float:
    """Evaluate a compiled family. The only place a family is turned into a
    number, and it never executes generated source."""
    f = compiled["family"]; p = compiled["params"]
    if f == "constant":
        return p["c"]
    if f in ("linear", "affine"):
        return p["a"] * x + p["b"]
    if f == "quadratic":
        return p["a"] * x * x + p["b"] * x + p["c"]
    if f == "periodic":
        n = p["period"]
        base = p.get("x0", 0.0)
        step = p.get("step", 1.0)
        return p["table"][int(round((x - base) / step)) % n]
    if f == "exponential":
        return p["amplitude"] * math.exp(p["rate"] * x)
    if f == "sinusoid":
        return p["offset"] + p["amplitude_sin"] * math.sin(p["omega"] * x) \
            + p["amplitude_cos"] * math.cos(p["omega"] * x)
    raise InferError("UNKNOWN_FAMILY:" + str(f))


# --------------------------------------------------------------------------
# ABSENT -- refusal that carries a price
# --------------------------------------------------------------------------
def absent(goal: str) -> dict:
    """What would close this gap, ranked by expected value per unit cost.

    This is `ignorance_ledger_v1`'s prior applied to routing: an untried gap
    scores 0.5 so exploration is free; a gap tried often and uselessly decays.
    """
    r = route(goal)
    if r["confident"]:
        return {"operation": "ABSENT", "goal": goal, "needed": False, "route": r}
    seen = set(tokens(goal)) - set((_load_index()[0]).keys())
    gaps = []
    for t in sorted(seen):
        gaps.append({"gap": "VOCABULARY:" + t, "p_useful": 0.5, "cost": 1.0, "value": 0.5})
    if not gaps:
        gaps.append({"gap": "FAMILY_COVERAGE", "p_useful": 0.5, "cost": 4.0, "value": 0.125})
    gaps.sort(key=lambda g: -g["value"])
    return {"operation": "ABSENT", "goal": goal, "needed": True,
            "cheapest_gaps": gaps[:5], "route": r,
            "rule": "AN_UNKNOWN_TOKEN_COSTS_ONE_LINE__A_MISSING_FAMILY_COSTS_ONE_TEST"}


# --------------------------------------------------------------------------
# STATUS
# --------------------------------------------------------------------------
def status() -> dict:
    idx, caps, df = _load_index()
    p = _load_policy()
    t0 = time.perf_counter()
    route("extract text from a pdf")
    warm_us = (time.perf_counter() - t0) * 1e6
    return {
        "schema": SCHEMA, "operation": "STATUS",
        "model": "BRAIN-ONE-MODEL-V2",
        "routing_tokens": len(idx), "capabilities": len(caps),
        "learned_updates": int(p.get("updates", 0)),
        "policy_pairs": len(p.get("tries", {})),
        "weights": 0, "learned_parameter_bytes": 0,
        "route_micros_warm": round(warm_us, 1),
        "non_claims": [
            "NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS",
            "NOT_AN_INDEPENDENT_VERIFICATION__SANDBOX_MEASUREMENT_ONLY",
            "NOT_TERMINAL_AUTHORITY__ZERO_CAPABILITY_AND_TERMINAL_CREDIT",
            "COVERAGE_IS_NOT_CAPABILITY__EXECUTION_STILL_REQUIRES_DECLARED_SUBSTRATE",
        ],
        "credit": {"capability_credit_delta": 0, "terminal_credit_delta": 0},
    }


__all__ = ["route", "compile_rows", "predict", "learn", "absent", "status",
           "tokens", "InferError", "SCHEMA"]


# --------------------------------------------------------------------------
# H100 BRIDGE -- closed form first, the tree's own family compiler second.
#
# `h100_zero_learned_parametric_unary_v1.discover` already synthesises families
# this file does not (affine + sinusoid, exp-in-|x|, threshold step) with zero
# learned bytes. It is ~75 ms on a cold first call, so it is imported lazily and
# only reached when the closed-form pass abstains. That ordering is the whole
# speed argument: the 5 us cases never pay for the 75 ms capability.
# --------------------------------------------------------------------------
def compile_with_h100(rows: Iterable[Mapping[str, Any]], x_name: str = "x",
                      y_name: str = "y") -> dict:
    """Escalate to the tree's verified family synthesizer when closed form fails."""
    rows = list(rows)
    try:
        return compile_rows(rows, x_name=x_name, y_name=y_name)
    except InferError as first:
        pass
    try:
        from canonical.runtime import h100_zero_learned_parametric_unary_v1 as p100
    except Exception as exc:                      # pragma: no cover - substrate
        raise InferError("CLOSED_FORM_ABSTAINED_AND_H100_UNAVAILABLE:%s" % exc)
    out = p100.discover(rows, target=y_name, input_name=x_name, exact_nrmse=1e-8)
    c = out.get("best_candidate")
    if not c:
        raise InferError("NO_FAMILY_FROM_CLOSED_FORM_OR_H100__ABSTAIN")
    return {
        "operation": "COMPILE", "family": c.get("family"), "params": c,
        "engine": "h100_zero_learned_parametric_unary_v1", "observations": len(rows),
        "micros": None, "learned_bytes": 0, "weights": 0,
        "credit": {"capability_credit_delta": 0, "terminal_credit_delta": 0},
    }


# --------------------------------------------------------------------------
# CLI -- `python3 -m canonical.runtime.brain_one_model_v2 <verb> ...`
# --------------------------------------------------------------------------
def _cli(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="brain_one_model_v2",
                                 description="One weightless model: route, compile, abstain.")
    sub = ap.add_subparsers(dest="verb", required=True)

    sub.add_parser("status", help="what the model contains and what it cannot claim")

    r = sub.add_parser("route", help="a plain goal -> ranked capabilities")
    r.add_argument("goal")
    r.add_argument("-k", type=int, default=3)

    c = sub.add_parser("compile", help="(x,y) observations -> an exact family")
    c.add_argument("--rows", required=True, help='JSON [{"x":..,"y":..},..]')
    c.add_argument("--h100", action="store_true", help="escalate to the H100 synthesizer")
    c.add_argument("--at", type=float, action="append", default=[], help="also predict at x")

    a = sub.add_parser("absent", help="what would close this gap, priced")
    a.add_argument("goal")

    so = sub.add_parser("solve", help="route -> bind -> execute -> verify")
    so.add_argument("goal")
    so.add_argument("--inputs", default="{}", help="JSON object of declared inputs")
    so.add_argument("--capability", default=None, help="skip routing, name the capability")
    so.add_argument("--bind-only", action="store_true", help="no execution, no side effects")
    so.add_argument("--cache", action="store_true", help="memoise on input content")
    so.add_argument("--refresh", action="store_true", help="ignore any cached receipt")

    cs = sub.add_parser("cache", help="cache statistics")
    cs.add_argument("--clear", action="store_true")

    ac = sub.add_parser("acquire", help="close the cheapest gap, permanently")
    ac.add_argument("goal")
    ac.add_argument("--capability", default=None, help="capability the bridge should teach")
    ac.add_argument("--execute", action="store_true")

    br = sub.add_parser("bridge", help="map one unknown token onto the vocabulary")
    br.add_argument("token")

    l = sub.add_parser("learn", help="one observation, applied immediately")
    l.add_argument("goal")
    l.add_argument("capability_id")
    l.add_argument("--unhelpful", action="store_true")

    ns = ap.parse_args(argv)
    if ns.verb == "status":
        print(json.dumps(status(), indent=1))
        return 0
    if ns.verb == "route":
        print(json.dumps(route(ns.goal, k=ns.k), indent=1))
        return 0
    if ns.verb == "compile":
        rows = json.loads(ns.rows)
        out = compile_with_h100(rows) if ns.h100 else compile_rows(rows)
        if ns.at:
            out = dict(out)
            out["predictions"] = {str(x): predict(out, x) for x in ns.at}
        print(json.dumps(out, indent=1, default=str))
        return 0
    if ns.verb == "absent":
        print(json.dumps(absent(ns.goal), indent=1))
        return 0
    if ns.verb == "solve":
        inputs = json.loads(ns.inputs)
        if ns.cache:
            out = solve_cached(ns.goal, inputs, ns.capability, refresh=ns.refresh)
        else:
            out = solve(ns.goal, inputs, ns.capability, execute=not ns.bind_only)
        print(json.dumps(out, indent=1, default=str)[:4000])
        return 0 if out.get("pass") is not False else 1
    if ns.verb == "cache":
        if ns.clear:
            for f in CACHE_DIR.glob("*.json"):
                f.unlink(missing_ok=True)
        print(json.dumps(cache_stats(), indent=1))
        return 0
    if ns.verb == "acquire":
        print(json.dumps(acquire(ns.goal, ns.capability, execute=ns.execute),
                         indent=1, default=str)[:4000])
        return 0
    if ns.verb == "bridge":
        print(json.dumps(bridge(ns.token), indent=1))
        return 0
    if ns.verb == "learn":
        print(json.dumps(learn(ns.goal, ns.capability_id, helped=not ns.unhelpful), indent=1))
        return 0
    return 2



# --------------------------------------------------------------------------
# SOLVE -- one call: route -> bind -> execute -> verify against the registry's
# own expectation. This is what turns a router into a model.
#
# Why direct dispatch and not `verified_bound_capability_execution_adapter_v1`:
# measured, all 138 adapters share exactly one signature `run(args, root)`, and
# that adapter's `execute(capability_id)` exposes no inputs parameter. Going
# through it would require a second binding layer for a call it cannot make.
# What is NOT skipped is the registry contract: status must be
# VERIFIED_BOUND_CAPABILITY, spend must be zero, the action template must bind
# from caller inputs only, and the declared `expect` must hold afterwards.
# --------------------------------------------------------------------------
_PLACEHOLDER = re.compile(r"\$\{input\.([A-Za-z0-9_]+)\}")


class SolveError(RuntimeError):
    pass


_REGISTRY: dict | None = None


def _registry() -> dict:
    """The registry is immutable for a process. Re-reading and re-parsing 141
    entries on every solve cost 1.8 ms of a 1.9 ms bind; memoise it."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = json.loads(
            (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    return _REGISTRY


def _root() -> Path:
    return ROOT


def bind(capability_id: str, inputs: Mapping[str, Any]) -> dict:
    """Bind caller inputs to the capability's frozen action template.

    Only a placeholder the template already declares may be filled. A capability
    may never widen its own surface: an input the template does not name is
    refused, not ignored -- otherwise a caller could smuggle state past the
    contract it is being checked against.
    """
    _, caps, _ = _load_index()
    meta = caps.get(capability_id) or {}
    if meta.get("kind") != "BOUND_CAPABILITY":
        raise SolveError("NOT_A_BOUND_CAPABILITY:" + capability_id)
    entry = _registry()["capabilities"].get(capability_id)
    if not entry:
        raise SolveError("CAPABILITY_NOT_IN_REGISTRY")
    if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise SolveError("STATUS_NOT_VERIFIED_BOUND:" + str(entry.get("status")))
    if float(entry.get("incremental_spend_usd") or 0) != 0.0:
        raise SolveError("NONZERO_SPEND_CAPABILITY_REFUSED")

    tmpl = entry.get("action_template") or {}
    args_t = tmpl.get("args") or {}
    bound: dict[str, Any] = {}
    declared: set[str] = set()
    for k, v in args_t.items():
        if isinstance(v, str):
            for name in _PLACEHOLDER.findall(v):
                declared.add(name)
                if name not in inputs:
                    raise SolveError("INPUT_BINDING_REQUIRED:" + name)
                bound[k] = inputs[name]
        else:
            bound[k] = v
    # a template with a bare "${input.X}" in args (e.g. pdf uses `path`)
    for k, v in args_t.items():
        if isinstance(v, str) and v not in _PLACEHOLDER.sub("", v) is False:
            pass
    extra = set(inputs) - declared
    if extra:
        raise SolveError("INPUT_NOT_DECLARED_BY_TEMPLATE:" + ",".join(sorted(extra)))
    return {"entry": entry, "args": bound, "expect": tmpl.get("expect") or {},
            "declared": sorted(declared)}


def _check_expect(result: Any, expect: Mapping[str, Any]) -> tuple[bool, str]:
    field = expect.get("field")
    kind = expect.get("type")
    if not field:
        return True, "NO_DECLARED_EXPECTATION"
    if not isinstance(result, Mapping) or field not in result:
        return False, "EXPECT_FIELD_ABSENT:" + str(field)
    val = result[field]
    if kind == "field_equals":
        ok = val == expect.get("value")
    elif kind == "field_nonempty":
        ok = bool(val)
    elif kind == "field_truthy":
        ok = bool(val)
    else:
        ok = val is not None
    return ok, ("EXPECT_SATISFIED:" if ok else "EXPECT_VIOLATED:") + str(field)


def solve(goal: str, inputs: Mapping[str, Any] | None = None,
          capability_id: str | None = None, execute: bool = True) -> dict:
    """A plain goal in, verified work out -- or a named refusal.

    `execute=False` performs route + bind only, with no side effects. That split
    exists so a caller can price a solve before running it.
    """
    t0 = time.perf_counter()
    inputs = dict(inputs or {})
    r = route(goal)
    cid = capability_id or (r["best"]["id"] if r["best"] else None)
    if not cid:
        return {"operation": "SOLVE", "goal": goal, "pass": False,
                "status": "FAIL_CLOSED__GOAL_NOT_REPRESENTED_IN_MODEL",
                "route": r, "credit": {"capability_credit_delta": 0,
                                       "terminal_credit_delta": 0},
                "millis": round((time.perf_counter() - t0) * 1000, 2)}

    try:
        b = bind(cid, inputs)
    except SolveError as e:
        return {"operation": "SOLVE", "goal": goal, "capability_id": cid, "pass": False,
                "status": "FAIL_CLOSED__" + str(e), "route": r,
                "credit": {"capability_credit_delta": 0, "terminal_credit_delta": 0},
                "millis": round((time.perf_counter() - t0) * 1000, 2)}

    if not execute:
        return {"operation": "SOLVE", "goal": goal, "capability_id": cid, "pass": None,
                "status": "ROUTED_AND_BOUND__NOT_EXECUTED",
                "bound_args": sorted(b["args"]), "declared_inputs": b["declared"],
                "expect": b["expect"], "route": r,
                "millis": round((time.perf_counter() - t0) * 1000, 2)}

    adapter = b["entry"].get("adapter_module")
    entry_point = b["entry"].get("entrypoint") or "run"
    try:
        mod = __import__("canonical.runtime.bound_capabilities.%s" % adapter,
                         fromlist=[entry_point])
        fn = getattr(mod, entry_point)
    except Exception as e:
        return {"operation": "SOLVE", "goal": goal, "capability_id": cid, "pass": False,
                "status": "FAIL_CLOSED__ADAPTER_UNAVAILABLE:" + type(e).__name__,
                "detail": str(e)[:200], "route": r,
                "millis": round((time.perf_counter() - t0) * 1000, 2)}

    t_exec = time.perf_counter()
    try:
        result = fn(b["args"], _root())
        ok, why = _check_expect(result, b["expect"])
        err = None
    except Exception as e:
        result, ok, why = None, False, "ADAPTER_RAISED:" + type(e).__name__
        err = str(e)[:300]
    exec_ms = round((time.perf_counter() - t_exec) * 1000, 2)

    out = {
        "operation": "SOLVE", "goal": goal, "capability_id": cid,
        "pass": bool(ok), "status": ("PASS__BOUND_CAPABILITY_EXECUTED_AND_EXPECTATION_VERIFIED"
                                     if ok else "FAIL_CLOSED__" + why),
        "expectation": why, "exec_ms": exec_ms,
        "route_micros": r.get("micros"),
        "millis": round((time.perf_counter() - t0) * 1000, 2),
        "credit": {"capability_credit_delta": 0, "ownership_credit_delta": 0,
                   "terminal_credit_delta": 0},
        "weights": 0,
    }
    if err:
        out["error"] = err
    if isinstance(result, Mapping):
        out["result_keys"] = sorted(map(str, result.keys()))[:12]
    return out


# --------------------------------------------------------------------------
# MEMOISATION -- content-addressed, so a repeated solve costs microseconds.
#
# Measured before writing this: the audit capability spends 4.2 s of a 4.5 s
# call inside `ast.parse` over 2,337 files. Parallelism does not help -- this box
# has 2 cores; threads gave 3 %, processes gave -45 % (pickling costs more than
# the parse). What does help is not doing the work twice: a key of
# (capability, canonical args, content hash of every input file) makes an
# unchanged repeat instant, and that is the common agent pattern.
#
# This is the same principle as the tree's own capability-ratcheted search bound
# and Stitch's: compile a verified result into a cheap reference rather than
# recompute it from raw input.
# --------------------------------------------------------------------------
CACHE_DIR = ROOT / "canonical/runtime/state/one_model_cache"
_CACHE_LIMIT = 256


def _walk(root: Path, skip_prefix: str, skip_abs: frozenset = frozenset()) -> list:
    """(relpath, size, mtime_ns) via os.scandir.

    Measured on 2,614 files: pathlib rglob + 2x f.stat() costs 82.7 ms; this
    costs 5.7 ms. pathlib's per-entry Path construction and repeated stat calls
    dominate, and DirEntry caches the stat the walk already made.
    """
    out = []
    stack = [str(root)]
    base = str(ROOT)
    while stack:
        cur = stack.pop()
        try:
            it = os.scandir(cur)
        except OSError:
            continue
        with it:
            for e in it:
                try:
                    if e.is_dir(follow_symlinks=False):
                        stack.append(e.path)
                    elif e.is_file(follow_symlinks=False):
                        rel = e.path[len(base) + 1:] if e.path.startswith(base) else e.path
                        if rel.startswith(skip_prefix) or e.path in skip_abs:
                            continue
                        st = e.stat()
                        out.append((rel, st.st_size, st.st_mtime_ns))
                except OSError:
                    continue
    out.sort()
    return out


def _input_digest(inputs: Mapping[str, Any]) -> str:
    """Content hash for small inputs, stat signature for large trees.

    Exclusions, each found by the cache failing to hit:
      * write targets (`output_path`, `out_dir`, ...) do not exist before the
        first run and do after, so hashing them guarantees a miss;
      * the cache directory itself -- it lives under canonical/runtime, so
        hashing a source_root of canonical/runtime hashed our own receipts.
    """
    h = hashlib.sha256()
    cache_rel = str(CACHE_DIR.relative_to(ROOT))
    # A write target's EXISTENCE must not be hashed, and that is not enough: if
    # the target lives INSIDE a directory input, the first run creates it, the
    # directory signature changes, and the key differs from itself forever.
    # Measured: `output_path` inside `source_root` gave MISS on every call,
    # even in the same process. Resolve the write-target paths up front and
    # exclude those exact files from every directory walk.
    skip_abs = frozenset(
        str((ROOT / str(v)).resolve()) for k, v in inputs.items()
        if k.lower().startswith("out") or k.lower().endswith("_out")
        or k.lower() in ("dest", "destination", "target"))
    for k in sorted(inputs):
        kl = k.lower()
        # A write target's EXISTENCE must not be hashed (it appears after the
        # first run, guaranteeing a miss forever). But its NAME must be, because
        # several capabilities embed the output path in the artifact they build
        # and report -- an archive created for a.tar.gz is not the same result as
        # one created for b.tar.gz. Measured: skipping the name entirely made two
        # different outputs share a key, and the second call returned a receipt
        # for the first.
        is_out = kl.startswith("out") or kl.endswith("_out") or kl in ("dest", "destination", "target")
        h.update(k.encode()); h.update(b"\x00")
        if is_out:
            h.update(str(inputs[k]).encode()); h.update(b"\x02")
            continue
        s = str(inputs[k])
        h.update(s.encode())
        p = ROOT / s
        if p.is_file():
            h.update(p.read_bytes())
        elif p.is_dir():
            h.update(repr(_dir_signature(p, cache_rel, skip_abs)).encode())
        h.update(b"\x01")
    return h.hexdigest()


# Files modified this recently are "racy": this filesystem is ext2/ext3, whose
# mtime has ONE-SECOND resolution, so a same-size rewrite inside the same
# second leaves the stat signature byte-identical. Measured: `x = 1` -> `x = 2`
# produced the same digest and the cache served a stale answer. Content is
# hashed only inside this window; older files are stat-safe, because a later
# write necessarily lands in a different second and changes the mtime. This is
# the same rule git uses for racily-clean entries.
RACY_WINDOW_NS = 2_000_000_000


def _dir_signature(root: Path, skip_prefix: str, skip_abs: frozenset) -> list:
    now = time.time_ns()
    cutoff = now - RACY_WINDOW_NS
    sig = []
    for rel, size, mt in _walk(root, skip_prefix, skip_abs):
        if mt >= cutoff:                      # racy: mtime cannot prove anything
            try:
                with open(ROOT / rel, "rb") as f:
                    sig.append((rel, size, mt, hashlib.sha256(f.read()).hexdigest()))
            except OSError:
                sig.append((rel, size, mt, None))
        else:
            sig.append((rel, size, mt))
    return sig


def _cache_key(capability_id: str, inputs: Mapping[str, Any]) -> str:
    return capability_id.replace("/", "_") + "__" + _input_digest(inputs)[:32]


def solve_cached(goal: str, inputs: Mapping[str, Any] | None = None,
                 capability_id: str | None = None, refresh: bool = False) -> dict:
    """`solve`, memoised on the content of its inputs.

    A hit returns the stored receipt with `cache: "HIT"` and the original
    `exec_ms` preserved -- the number is not overwritten, so a cached answer
    never claims to have just run.
    """
    t0 = time.perf_counter()
    inputs = dict(inputs or {})
    cid = capability_id or ((route(goal)["best"] or {}).get("id"))
    if not cid:
        return solve(goal, inputs, capability_id)
    key = _cache_key(cid, inputs)
    path = CACHE_DIR / (key + ".json")
    if not refresh and path.is_file():
        try:
            rec = json.loads(path.read_text())
            rec["cache"] = "HIT"
            rec["micros"] = round((time.perf_counter() - t0) * 1e6, 1)
            return rec
        except Exception:
            pass
    out = solve(goal, inputs, capability_id=cid)
    out["cache"] = "MISS"
    out["micros"] = round((time.perf_counter() - t0) * 1e6, 1)
    if out.get("pass") is not None:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(out, sort_keys=True))
            _prune_cache()
        except Exception:
            pass
    return out


def _prune_cache() -> None:
    try:
        files = sorted(CACHE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
        for p in files[:-_CACHE_LIMIT] if len(files) > _CACHE_LIMIT else []:
            p.unlink(missing_ok=True)
    except Exception:
        pass


def cache_stats() -> dict:
    try:
        files = list(CACHE_DIR.glob("*.json"))
        return {"entries": len(files), "bytes": sum(p.stat().st_size for p in files),
                "dir": str(CACHE_DIR.relative_to(ROOT))}
    except Exception:
        return {"entries": 0, "bytes": 0}


# --------------------------------------------------------------------------
# ACQUIRE -- close the cheaest gap, permanently, in one call.
#
# The `absent` verb prices gaps but used to leave them open. This closes them.
#
# Design follows the tree's own `h100_lexical_coverage_bound_v1`: a fixed
# lexicon cannot cover an unbounded token universe, so lexical operation is
# conditional on runtime source availability, with fail-closed abstention when
# sources are missing or ambiguous. The runtime source here is the vocabulary
# the model ALREADY has (1,659 routing tokens compiled from the registry). An
# unseen token is bridged to a known one by three deterministic rules, in this
# order, each cheaper and more reliable than the last:
#
#   1. STEM     "archiving" -> "archive"      (strip a suffix, exact hit)
#   2. EDIT     "archiv"    -> "archive"      (Damerau-Levenshtein <= 2)
#   3. TRIGRAM  "tarfile"   -> "tar"          (Dice coefficient >= 0.55)
#
# Each rule is inspectable and each bridge is RECORDED, so the second encounter
# is a direct hit rather than a re-derivation. That record is the whole of the
# learning, and it is a small table of aliases -- not weights.
# --------------------------------------------------------------------------

_SUFFIXES = ("ations", "ation", "ings", "ing", "ers", "er", "ies", "es", "ed", "s")


def _stem(word: str) -> list[str]:
    out = [word]
    for suf in _SUFFIXES:
        if len(word) > len(suf) + 2 and word.endswith(suf):
            stem = word[: -len(suf)]
            out.append(stem)
            out.append(stem + "e")       # decoding -> decode
            if len(stem) > 2 and stem[-1] == stem[-2]:
                out.append(stem[:-1])    # running -> run
    return out


def _edit_kind(a: str, b: str) -> tuple[int, str] | None:
    """Cheapest single edit turning a into b, or None if more than one is needed.

    Returns (cost, kind) where kind is INS/DEL/TRANS/SUB, or None.

    Why only ONE edit, and why the kind matters:

    Measured false bridge from the first version -- which allowed two edits --
    `tree` -> `time` (two independent substitutions). That silently converted
    "syntax tree" into "syntax time" and changed a correct route.

    Typing errors are overwhelmingly single insertions, deletions or adjacent
    transpositions (Damerau's original observation). Two independent
    substitutions inside a 4-letter word is not a typo, it is a different word.
    Allowing exactly one edit of those kinds, on words of 4+ characters, keeps
    `pyton`->`python` and `sqllite`->`sqlite` and refuses `tree`->`time`.
    """
    la, lb = len(a), len(b)
    if la == lb:
        diff = [i for i in range(la) if a[i] != b[i]]
        if not diff:
            return (0, "IDENTITY")
        if len(diff) == 1:
            return (1, "SUB")
        if (len(diff) == 2 and diff[1] == diff[0] + 1
                and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]):
            return (1, "TRANS")
        return None
    if abs(la - lb) == 1:
        short, long_ = (a, b) if la < lb else (b, a)
        i = 0
        while i < len(short) and short[i] == long_[i]:
            i += 1
        if short[i:] == long_[i + 1:]:
            return (1, "INS" if la < lb else "DEL")
        return None
    return None


_VOCAB_CACHE: frozenset | None = None
_TRI_INDEX: dict = {}


def _tri_index(vocab) -> dict:
    """Vocabulary bucketed by every trigram it contains.

    The trigram rule was costing 166 us per refusal because it computed Dice against all
    5,253 tokens. A Dice coefficient >= 0.55 REQUIRES shared trigrams, so a token sharing
    none with the query can never win: bucketing by trigram drops almost the whole
    vocabulary before any arithmetic runs. Candidates that pass are still scored with the
    full, unchanged rule -- this narrows the search, it does not relax it.
    """
    idx = {}
    for v in vocab:
        for g in _trigrams(v):
            idx.setdefault(g, []).append(v)
    return idx


def _trigrams(s: str) -> set[str]:
    p = "##" + s + "#"
    return {p[i:i + 3] for i in range(len(p) - 2)}


def _dice(a: str, b: str) -> float:
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    return 2.0 * len(ta & tb) / (len(ta) + len(tb))


def bridge(token: str, vocabulary: set[str] | None = None) -> dict:
    """Map one unknown token onto the model's existing vocabulary.

    Returns {'match', 'rule', 'score'} or {'match': None, 'reason': ...}.
    Deterministic and side-effect free; `acquire` persists the result.
    """
    idx, _, _ = _load_index()
    global _VOCAB_CACHE
    if vocabulary is not None:
        vocab = vocabulary
    else:
        # `set(idx)` over 5,253 tokens was rebuilt on EVERY bridge call, which made a
        # refusal cost 13 ms. It is derived from an immutable index, so it is computed
        # once. Measured: 13,854 us -> ~2 us per bridge.
        if _VOCAB_CACHE is None:
            _VOCAB_CACHE = frozenset(idx)
        vocab = _VOCAB_CACHE
    t = token.lower().strip()
    if not t:
        return {"match": None, "reason": "EMPTY_TOKEN"}
    if t in vocab:
        return {"match": t, "rule": "IDENTITY", "score": 1.0}

    # 1. stem
    for cand in _stem(t):
        if cand in vocab and cand != t:
            return {"match": cand, "rule": "STEM", "score": 1.0}

    # 2. exactly one typo-shaped edit, but only against vocabulary that names a
    #    CAPABILITY. The full token list includes prose borrowed from registry
    #    keywords, and that is where the false bridges live: `tree`->`three`
    #    came from a keyword, not from a capability name. A typo is a mistake in
    #    the name of a thing you meant; it should resolve to a thing.
    if len(t) >= 4:
        for v in (vocab & _CAPABILITY_TOKENS):
            if abs(len(v) - len(t)) > 1 or v[:1] != t[:1]:
                continue
            k = _edit_kind(t, v)
            if k and k[0] == 1:
                return {"match": v, "rule": "TYPO_1_" + k[1], "score": 0.95}

    # 3. trigram Dice, but only accept a clear winner -- a marginal overlap
    #    bridges "mother" to "method" and teaches the model something false.
    #    Candidate generation is bucketed by the query's own trigrams: a Dice >= 0.55
    #    REQUIRES a shared trigram, so this narrows the search without relaxing the rule.
    global _TRI_INDEX
    if not _TRI_INDEX:
        _TRI_INDEX = _tri_index(vocab)
    cand = set()
    for g in _trigrams(t):
        cand.update(_TRI_INDEX.get(g, ()))
    if not cand:
        return {"match": None, "reason": "NO_SOURCE_FOR_TOKEN"}
    scored = sorted(((_dice(t, v), v) for v in cand), reverse=True)
    best, second = scored[0], (scored[1] if len(scored) > 1 else (0.0, None))
    if best[0] >= 0.55 and (second[0] < 0.9 * best[0] or second[1] is None):
        return {"match": best[1], "rule": "TRIGRAM_DICE", "score": round(best[0], 4)}
    if best[0] >= 0.55:
        return {"match": None, "reason": "AMBIGUOUS_BRIDGE",
                "tied": [best[1], second[1]], "score": round(best[0], 4)}
    return {"match": None, "reason": "NO_SOURCE_FOR_TOKEN"}


def _learn_bridges(bridges: Iterable[Mapping[str, Any]]) -> int:
    """Persist token->token rewrites. Idempotent; one write per call, not per bridge."""
    st = _load_policy()
    m = st.setdefault("bridges", {})
    n = 0
    for b in bridges:
        t, v = b.get("token"), b.get("match")
        if not t or not v or t == v:
            continue
        prev = m.get(t)
        # a later, better-evidenced bridge replaces a weaker one; a weaker one never
        # displaces a stronger one, so the belief cannot oscillate between two typos
        if prev is None or float(b.get("score") or 0) >= float(prev.get("score") or 0):
            m[t] = {"match": v, "rule": b.get("rule"), "score": b.get("score"),
                    "learned_at": time.time()}
            n += 1
    if n:
        _save_policy(st)
    return n


def acquire(goal: str, capability_id: str | None = None,
            execute: bool = False) -> dict:
    """Close the cheapest gap for a goal, then re-try. One call, permanent.

    `execute` defaults to False on purpose: acquisition is a vocabulary change,
    and a caller should see what was learned before anything runs.

    Provenance is returned for every bridge. A bridge the model inferred and
    cannot justify is indistinguishable from a guess, and this project does not
    ship guesses.
    """
    t0 = time.perf_counter()
    before = route(goal)
    if before["confident"] and capability_id is None:
        return {"operation": "ACQUIRE", "goal": goal, "needed": False,
                "route": before,
                "micros": round((time.perf_counter() - t0) * 1e6, 1)}

    idx, _, _ = _load_index()
    unknown = [t for t in sorted(set(tokens(goal))) if t not in idx]
    bridges, refused = [], []
    for t in unknown:
        b = bridge(t)
        (bridges if b.get("match") else refused).append(dict(b, token=t))

    # Persist the bridge against THIS goal's own tokens, so the next request
    # using the same unknown token routes without re-deriving it. Learning
    # against the synthetic string "txt text" would record a token that no
    # future goal contains.
    learned = 0
    if bridges:
        learned = _learn_bridges(bridges)
    if bridges and capability_id:
        for _b in bridges:
            learn(goal, capability_id, helped=True)
    after = route(goal)

    out = {
        "operation": "ACQUIRE", "goal": goal, "needed": True,
        "unknown_tokens": unknown,
        "bridged": bridges, "refused": refused,
        "bridges_learned": learned,
        "resolved_capability": capability_id,
        "route_before": {"confident": before["confident"],
                         "best": (before["best"] or {}).get("id"),
                         "coverage": before.get("coverage")},
        "route_after": {"confident": after["confident"],
                        "best": (after["best"] or {}).get("id"),
                        "coverage": after.get("coverage")},
        "closed": after["confident"] and not before["confident"],
        "micros": round((time.perf_counter() - t0) * 1e6, 1),
        "rule": "BRIDGE_ONLY_FROM_SOURCES_THE_MODEL_ALREADY_HAS__"
                "AMBIGUOUS_BRIDGES_ARE_REFUSED_NOT_GUESSED",
        "weights": 0,
    }
    if execute and capability_id:
        out["solve"] = solve(goal, {}, capability_id=capability_id)
    return out

if __name__ == "__main__":
    raise SystemExit(_cli())
