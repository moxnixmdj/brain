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
_BINARY_OPS = ("+", "-", "and", "or", "==")


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
