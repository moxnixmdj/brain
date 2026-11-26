"""Stochastic (random-search) SyGuS synthesizer over the OE grammar.

Companion to ``oe_sygus_synthesizer_v1``. Where the OE synthesizer does
bottom-up observational-equivalence enumeration (exhaustive up to a size
bound), this module does random/guided search over the SAME expression
grammar (``Expr`` / ``_eval_expr`` from the OE module). The point is ensemble
diversity: a stochastic search explores a different region of the candidate
space than exhaustive enumeration, so the two can find different solutions to
the same specification. This is the Angelix finding -- different synthesis
engines fix different bugs, and forging their results widens the candidate
space.

Zero-LLM, zero-weight, stdlib only. Deterministic given a seed.
"""
from __future__ import annotations

import math
import random
from typing import Any, Mapping, Sequence

from canonical.runtime import oe_sygus_synthesizer_v1 as OE

SCHEMA = "BRAIN_STOCHASTIC_SYNTHESIZER_V1"
AUTHORITY = "NONE"

# Unary ops available for random generation (subset of the OE grammar that
# takes a single sub-expression). Kept in sync with OE._eval_expr.
_UNARY_OPS = (
    "len", "neg", "abs", "trunc", "floor", "ceil", "int32_trunc",
    "strip", "lstrip", "rstrip", "lower", "upper", "not",
    "is_true", "is_false", "is_bool", "not_bool", "is_str", "not_str",
    "has_ctrl", "has_space", "has_ctrl_or_space", "has_non_ascii",
    "has_outer_ws", "has_newline", "has_null_byte", "has_digit",
    "has_upper",
)

# Binary ops (subset of the OE grammar that is BOTH evaluable by _eval_expr
# and emittable by emit_expr). Arity 2. Op names match OE exactly.
# "*" added 2026-11-25: micro_evolve_bench showed OE-side enumeration stops
# at depth 2, so shapes like (x*3)+3 were reachable by NEITHER engine; one
# sampled operator makes the stochastic side cover the whole 3-level class.
_BINARY_OPS = ("+", "-", "*", "and", "or", "==")


def _random_expr(rng: random.Random, var_names: list[str], consts: list[Any],
                 depth: int) -> OE.Expr:
    """Generate a random expression of bounded depth."""
    if depth <= 0 or rng.random() < 0.35:
        # Leaf: variable or constant.
        if var_names and rng.random() < 0.6:
            return OE.Expr("var", (rng.choice(var_names),), 1)
        return OE.Expr("const", (rng.choice(consts) if consts else 0,), 1)
    if rng.random() < 0.55:
        op = rng.choice(_UNARY_OPS)
        sub = _random_expr(rng, var_names, consts, depth - 1)
        return OE.Expr(op, (sub,), sub.size + 1)
    op = rng.choice(_BINARY_OPS)
    a = _random_expr(rng, var_names, consts, depth - 1)
    b = _random_expr(rng, var_names, consts, depth - 1)
    return OE.Expr(op, (a, b), a.size + b.size + 1)


def synthesize_value_expressions_stochastic(
    examples: Sequence[tuple[Mapping[str, Any], Any]],
    *,
    lang: str = "python",
    extra_consts: Sequence[Any] = (),
    max_results: int = 8,
    seed: int = 0,
    max_tries: int = 20000,
    max_depth: int = 4,
) -> list[dict[str, Any]]:
    """Random-search value-expression synthesis over the OE grammar.

    Same contract as ``OE.synthesize_value_expressions``: given
    ``(env, expected)`` pairs, return expressions matching ALL pairs. Uses
    random search instead of bottom-up enumeration, so it explores a
    different part of the space (and can find larger expressions that the
    OE size bound would miss).
    """
    if not examples:
        return []
    envs = [dict(e) for e, _ in examples]
    targets = [t for _, t in examples]
    var_names = sorted(set().union(*[set(e.keys()) for e in envs])) if envs else []
    # Candidate constants: from targets, env values, and small ints.
    consts: list[Any] = list(extra_consts)
    for t in targets:
        if isinstance(t, (int, float, str, bool)) and t not in consts:
            consts.append(t)
    for e in envs:
        for v in e.values():
            if isinstance(v, (int, float)) and v not in consts:
                consts.append(v)
    for c in (0, 1, 2, -1, "", " "):
        if c not in consts:
            consts.append(c)

    rng = random.Random(seed)
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _ in range(max_tries):
        if len(found) >= max_results:
            break
        expr = _random_expr(rng, var_names, consts, max_depth)
        code = OE.emit_expr(expr, lang)
        if code in seen:
            continue
        seen.add(code)
        ok = True
        for env, target in zip(envs, targets):
            try:
                val = OE._eval_expr(expr, env)
            except Exception:
                ok = False
                break
            if val is OE._SENTINEL_ERR or val != target:
                ok = False
                break
        if ok:
            found.append({"code": code, "expr": expr, "size": expr.size})
    return found


def ensemble_value_expressions(
    examples: Sequence[tuple[Mapping[str, Any], Any]],
    *,
    lang: str = "python",
    extra_consts: Sequence[Any] = (),
    max_results: int = 8,
    seed: int = 0,
) -> dict[str, list[dict[str, Any]]]:
    """Run OE + stochastic and return both candidate sets plus the union.

    The union is the ensemble candidate space. Comparing ``oe_only``,
    ``stochastic_only`` and ``union`` measures candidate diversity: if the
    union is larger than either alone, the engines explore different regions.
    """
    oe = OE.synthesize_value_expressions(
        examples, lang=lang, extra_consts=extra_consts, max_results=max_results
    )
    stoch = synthesize_value_expressions_stochastic(
        examples, lang=lang, extra_consts=extra_consts,
        max_results=max_results, seed=seed,
    )
    oe_codes = {e["code"] for e in oe}
    stoch_codes = {e["code"] for e in stoch}
    union = list(oe) + [e for e in stoch if e["code"] not in oe_codes]
    return {
        "oe_only": oe,
        "stochastic_only": stoch,
        "union": union,
        "oe_count": len(oe),
        "stochastic_count": len(stoch),
        "union_count": len(union),
        "overlap": len(oe_codes & stoch_codes),
        "stochastic_unique": len(stoch_codes - oe_codes),
    }


def _level2c_exhaustive(
    examples: Sequence[tuple[Mapping[str, Any], Any]],
    *,
    extra_consts: Sequence[Any] = (),
    lang: str = "python",
    max_results: int = 8,
) -> list[dict[str, Any]]:
    """Enumerate the depth-3 class the OE levels miss: ((x|neg x|abs x) ∘ c) ∘ c.

    Same contract as the synthesizers: every returned expression matches ALL
    examples. Inner (level-2) nodes are de-duplicated by their observational
    signature over the example environments before composition, which is what
    keeps the outer product small.
    """
    if not examples:
        return []
    envs = [dict(e) for e, _ in examples]
    targets = [t for _, t in examples]

    def _sig(expr: OE.Expr) -> tuple[Any, ...] | None:
        out = []
        for env in envs:
            try:
                v = OE._eval_expr(expr, env)
            except Exception:
                return None
            if v is OE._SENTINEL_ERR or isinstance(v, (list, dict)):
                return None
            out.append((type(v).__name__, v))
        return tuple(out)

    target_sig = tuple((type(t).__name__, t) for t in targets)
    var_names = sorted(set().union(*[set(e) for e in envs])) if envs else []
    consts: list[Any] = [c for c in extra_consts]
    for t in targets:
        if isinstance(t, (int, float)) and not isinstance(t, bool) and t not in consts:
            consts.append(t)
    for c in (1, 2, 3, 4, -1):
        if c not in consts:
            consts.append(c)
    for e in envs:
        for v in e.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v not in consts:
                consts.append(v)
    consts = consts[:10]

    def _leaf(vname: str, cval: Any) -> OE.Expr:
        return OE.Expr("var", (vname,), 1) if vname else OE.Expr("const", (cval,), 1)

    # Level 1..2 with signature dedup. v6 section 10: bases include PAIRED
    # cross-variable atoms (x-y, abs(x-y), ...) so the 2-var class
    # ((x op c)*(y op c), u(x op y) op c) is completed the same deterministic
    # way the 1-var class was; caps keep the product honest (pool is deduped).
    inner: dict[tuple, OE.Expr] = {}
    pool: dict[tuple, OE.Expr] = {}
    bases: list = []
    for v in var_names:
        bases.append(_leaf(v, None))
        bases.extend(OE.Expr(u, (_leaf(v, None),), 2) for u in ("neg", "abs"))
    for i in range(len(var_names)):
        for j in range(len(var_names)):
            if i == j:
                continue
            for cop in ("+", "-", "*"):
                cross = OE.Expr(cop, (_leaf(var_names[i], None), _leaf(var_names[j], None)), 3)
                bases.append(cross)
                bases.extend(OE.Expr(u, (cross,), 4) for u in ("neg", "abs"))
    for b in bases:
        for op1 in _BINARY_OPS:
            for c in consts:
                for e in (OE.Expr(op1, (b, _leaf(None, c)), b.size + 2),
                          OE.Expr(op1, (_leaf(None, c), b), b.size + 2)):
                    s = _sig(e)
                    if s is None:
                        continue
                    if s == target_sig:
                        return [{"code": OE.emit_expr(e, lang), "expr": e, "size": e.size}]
                    pool.setdefault(s, e)
                    inner.setdefault(s, e)
    # Level 3 over deduplicated signatures
    for _s, l2 in inner.items():
        for op2 in _BINARY_OPS:
            for c in consts:
                for e in (OE.Expr(op2, (l2, _leaf(None, c)), l2.size + 2),
                          OE.Expr(op2, (_leaf(None, c), l2), l2.size + 2)):
                    s3 = _sig(e)
                    if s3 is None:
                        continue
                    if s3 == target_sig:
                        return [{"code": OE.emit_expr(e, lang), "expr": e, "size": e.size}]
                    # keep the whole 2c pool (signature-deduped) so the ITE
                    # composition can use DEEP branches, not only OE's level-2
                    # pool: the exact TACAS'17 / EUSolver pattern — terms and
                    # conditionals are separate grammars combined by if-then-else.
                    pool.setdefault(s3, e)
    # Composite pass (v6 section 10, levers 1+2 unified). (x+4)*(y-3) needs
    # TERM x TERM; a naive scan at real loop sizes was MEASURED at 429 atoms
    # / 5.3 s — over budget. But for ops *, +, - the second operand's value
    # vector is DETERMINED pointwise by target and first operand, so pairing
    # is O(atoms x points) dict lookups (inverse composition), ~30 ms at the
    # same size. Composite atoms join the POOL, so the ITE stage below can
    # compose product/sum BRANCHES (the compound-conditional class) for free.
    # Zero-divisor slots are skipped (rare sound loss: no candidate is ever
    # emitted unverified — every hit passes _sig over every example).
    if all(isinstance(t, (int, float)) and not isinstance(t, bool) for t in targets) \
            and len(inner) <= 2048:
        num_t = list(targets)
        by_vals: dict[tuple, list] = {}
        atoms_vals: list = []
        for e in inner.values():
            vs: list = []
            good = True
            for env in envs:
                try:
                    v = OE._eval_expr(e, env)
                except Exception:
                    good = False
                    break
                if v is OE._SENTINEL_ERR or isinstance(v, (bool, str, list, dict)) \
                        or not isinstance(v, (int, float)):
                    good = False
                    break
                vs.append(v)
            if good:
                atoms_vals.append((e, vs))
                by_vals.setdefault(tuple(vs), []).append(e)
        npts = len(envs)
        for ea, va in atoms_vals:
            plans = [
                ("+", tuple(num_t[i] - va[i] for i in range(npts))),
                ("-", tuple(va[i] - num_t[i] for i in range(npts))),
            ]
            mulk: list = []
            okm = True
            for i in range(npts):
                a, t = va[i], num_t[i]
                if a == 0:
                    okm = False
                    break
                if isinstance(t, int) and isinstance(a, int):
                    if t % a:
                        okm = False
                        break
                    mulk.append(t // a)
                else:
                    q = t / a
                    if q != int(q):
                        okm = False
                        break
                    mulk.append(float(q))
            if okm:
                plans.append(("*", tuple(mulk)))
            for op2, key in plans:
                for eb in by_vals.get(key, ()):
                    em = OE.Expr(op2, (ea, eb), ea.size + eb.size + 1)
                    s = _sig(em)
                    if s is None:
                        continue
                    if s == target_sig:
                        return [{"code": OE.emit_expr(em, lang), "expr": em, "size": em.size}]
                    pool.setdefault(s, em)
    # --- ITE composition over the 2c pool (same coverage+guard pattern OE
    # uses at its level 3, run on the deeper pool; miss-path only).
    n = len(envs)
    parts: list[tuple[int, Any, set]] = []
    for s, e in pool.items():
        cov = {i for i, (vv, tv) in enumerate(zip(s, target_sig)) if vv == tv}
        if 0 < len(cov) < n:
            parts.append((len(cov), e, cov))
    parts.sort(key=lambda x: (-x[0], x[1].size))
    for _c1, ex_then, cov_then in parts[:6]:
        rem = set(range(n)) - cov_then
        ex_else = next((e2 for _c2, e2, cov2 in parts if rem <= cov2), None)
        if ex_else is None:
            continue
        f_sub = [envs[i] for i in sorted(cov_then)]
        p_sub = [envs[i] for i in sorted(rem)]
        try:
            guards = OE.synthesize_separating_predicates(
                f_sub, p_sub, lang=lang, extra_consts=consts, max_results=2
            )
        except Exception:
            guards = []
        for g in guards:
            ite = OE.Expr("ite", (g["expr"], ex_then, ex_else),
                          g["expr"].size + ex_then.size + ex_else.size + 1, 0)
            if _sig(ite) == target_sig:
                return [{"code": OE.emit_expr(ite, lang), "expr": ite, "size": ite.size}]
    return []


def synthesize_body_from_examples(
    arg_names: Sequence[str],
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    extra_consts: Sequence[Any] = (),
    max_results: int = 8,
    seed: int = 7,
) -> str | None:
    """Ensemble fallback: an ``return <expr>`` body, or None.

    ``examples`` is the observational-synthesizer shape, ``((args...), expected)``
    per pair — the format the planner's H2 affordance extracts from test sources.
    Runs the OE + stochastic union over those pairs and re-VERIFIES every
    candidate against every example before returning it: a candidate is only
    ever returned if it already passes the complete visible spec, so the caller
    never pays for a wrong patch (the verify-at-generation property; the same
    gate the loop's own unittest run would apply later, applied earlier and
    free). Returns the shortest verified body.
    """
    if not examples or not arg_names:
        return None
    names = [str(a) for a in arg_names]
    pairs: list[tuple[dict[str, Any], Any]] = []
    for args, expected in examples:
        if len(tuple(args)) != len(names):
            return None
        pairs.append(({n: v for n, v in zip(names, tuple(args))}, expected))
    try:
        ens = ensemble_value_expressions(
            pairs, lang="python", extra_consts=extra_consts,
            max_results=max_results, seed=seed,
        )
        first = ens["union"]
    except Exception:
        return None
    # Escalation trigger is NO SHIPPABLE CANDIDATE, not merely an empty union:
    # a union whose candidates all need names the target module lacks (math.*)
    # is, for this path, equivalent to no candidates. micro_evolve_bench found
    # the exact-multi-point 3-level class (e.g. (x*3)+3) escapes OE's depth-2
    # levels AND the ~1/30k sampled hit rate of the random side; random
    # escalation over seeds is luck, so escalate instead by EXHAUSTIVELY
    # enumerating the class ((x|neg x|abs x) op c) op c, deduped by
    # observational signature. Deterministic; never runs when a pass exists.
    ns: dict[str, Any] = {}  # bare: eval adds __builtins__ (int/str/abs True); NO math —
    # the patched target module will not have imported it, so a candidate that
    # needs math is not shippable from this path. Verify under the target's env.

    def _scan(cands: list[dict[str, Any]]) -> str | None:
        found: str | None = None
        for cand in cands:
            code = str(cand.get("code") or "")
            if not code:
                continue
            try:
                fn = eval(f"lambda {', '.join(names)}: ({code})", dict(ns), {})  # noqa: S307
                if all(fn(*tuple(a)) == e for a, e in examples):
                    if found is None or len(code) < len(found):
                        found = code
            except Exception:
                continue
        return found

    best = _scan(first)
    if best is None:
        try:
            best = _scan(_level2c_exhaustive(
                pairs, extra_consts=extra_consts, lang="python",
                max_results=max_results,
            ))
        except Exception:
            best = None
    return None if best is None else f"return {best}"
