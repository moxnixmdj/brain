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
import re
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

# Learned-grammar (concept-template) pass budget -- v6 section 14. Caps, not
# knobs: they bound a path that only runs when nothing verified exists yet.
_TPL_MAX_ATOMS = 160   # hole fillings per concept (shortest atoms first)
_TPL_MAX_BODY = 120    # reject concepts too big to be a micro-grammar atom
_TPL_MAX_CODE = 200    # reject instantiated candidates past this length
_TPL_NAME_COST = 8     # a library concept call costs a node, not its body
_TPL_MAX_CANDS = 1200  # hard budget on variants handed to the verifier
_TPL_MAX_LIFT_ATOMS = 24  # atoms a lifted-literal variant is tried against
_TPL_MAX_FAST = 16     # concept-on-variable candidates tried on the common path
_TPL_LIT = re.compile(r"(?<![\d.])\d+(?![\d.])")


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
    concepts: Sequence[Any] = (),
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
    num_t: list = [t for t in targets
                   if isinstance(t, (int, float)) and not isinstance(t, bool)]
    ok_num = len(num_t) == len(targets)

    def _atom_vals() -> list:
        out: list = []
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
                out.append((e, vs))
        return out

    atoms_vals_c: list = _atom_vals() if ok_num and len(inner) <= 2048 else []
    if ok_num and len(inner) <= 2048:
        by_vals: dict[tuple, list] = {}
        atoms_vals = atoms_vals_c
        for e, vs in atoms_vals:
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
    va_by_id = {id(e): vs for e, vs in atoms_vals_c}
    for _c1, ex_then, cov_then in parts[:6]:
        rem = set(range(n)) - cov_then
        ex_else = next((e2 for _c2, e2, cov2 in parts if rem <= cov2), None)
        if ex_else is None and ok_num:
            # Restricted composition (plan v6 section 11 lever): the else
            # branch only has to match the targets ON THE POINTS WHERE IT
            # RUNS. Composing then inverting on the remainder set builds
            # branches like -(x*3)-y that are (irrelevantly) wrong on the
            # then-side and so were unreachable for a global inversion.
            # Correctness is untouched: the final _sig check still requires
            # the WHOLE composed ITE to match every example.
            ridx = sorted(rem)
            need = [num_t[i] for i in ridx]
            va = va_by_id.get(id(ex_then))
            rem_by: dict[tuple, Any] = {}
            for e2, v2 in atoms_vals_c:
                rem_by.setdefault(tuple(v2[i] for i in ridx), e2)
            for a, vav in atoms_vals_c:
                k1 = tuple(need[j] - vav[ridx[j]] for j in range(len(ridx)))
                k2 = tuple(vav[ridx[j]] - need[j] for j in range(len(ridx)))
                mulk: list | None = []
                for j in range(len(ridx)):
                    x_ = vav[ridx[j]]
                    t_ = need[j]
                    if x_ == 0 or isinstance(t_, int) and isinstance(x_, int) and t_ % x_ != 0 \
                            or not (isinstance(t_, int) and isinstance(x_, int)) and (t_ / x_) != int(t_ / x_):
                        mulk = None
                        break
                    mulk.append(t_ // x_ if isinstance(t_, int) and isinstance(x_, int) else float(t_ / x_))
                for op3, kk in (("+", k1), ("-", k2), ("*", tuple(mulk) if mulk is not None else None)):
                    if kk is None:
                        continue
                    b = rem_by.get(kk)
                    if b is None:
                        continue
                    cand = OE.Expr(op3, (a, b), a.size + b.size + 1)
                    sc = _sig(cand)
                    if sc is not None and all(sc[i] == target_sig[i] for i in ridx):
                        ex_else = cand
                        break
                if ex_else is not None:
                    break
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
    # Learned-grammar pass (v6 section 14). The compounding concept library's
    # admitted concepts are TEMPLATE ATOMS: a `body_expr` with `_v0..` holes,
    # admitted upstream only if they compress corpus description length,
    # evaluate deterministically on probes, and kill a syntactic mutant. The
    # hand-written grammar above has no min/max/clamp class at ANY depth, so a
    # concept hit here is reach the enumerator cannot produce in principle --
    # measured: the primary observational stage ships a learned clamp concept
    # verbatim and reaches 7/10 on the clamp family, while this fallback used to
    # answer the same spec with an overfit ITE that passes the visible points and
    # is wrong everywhere else. Holes are filled from the level-1/2 atom sources
    # already deduped in `inner`, so cost is |concepts| x |inner| string builds,
    # capped, on a path that only runs when no verified candidate exists.
    # Soundness unchanged: the caller re-verifies every candidate against every
    # example before shipping.
    if concepts:
        try:
            # Fill from `pool` (levels 1-3 + composites), not `inner` (levels
            # 1-2 only): `(x*4)+3`-class atoms are level-3, and a clamp around
            # a level-2-only hole cannot express `min(max(x*4+3, 0), 100)`.
            atom_srcs = sorted({str(OE.emit_expr(e, lang)) for e in pool.values()},
                               key=len)[:_TPL_MAX_ATOMS]
        except Exception:
            atom_srcs = []
        got = _concept_candidates(concepts, var_names, atom_srcs, consts,
                                  lift=True, max_cands=_TPL_MAX_CANDS)
        if got:
            # All of them, not `max_results`: the caller's verifier selects, and
            # truncating here was MEASURED to lose solves (7/10 -> 5/10).
            return got
    return []


def numeric_concept_templates(library: Any) -> list[dict[str, Any]]:
    """Read-view of the concept library, shaped for the micro grammar.

    Only first-order NUMERIC expression templates: the micro synthesizer
    evaluates over int/float example envs, so a statement-level or string-domain
    concept (the repo's own corpus is full of those, e.g. whitespace
    normalization mined from 6 sites) is not instantiable here -- and pretending
    otherwise would cost time and buy nothing. `retired` entries are dropped,
    matching the library's own outcome-based retirement (the Library-Drift
    remedy: contribution log + retirement + cap, all three already on entries).
    Never raises: a missing, unloaded or malformed library yields [].
    """
    if library is None:
        return []
    try:
        raw = library.concepts()
        items = list(raw.values()) if isinstance(raw, dict) else list(raw)
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for e in items:
        get = e.get if isinstance(e, dict) else (lambda k, d=None: getattr(e, k, d))
        try:
            if get("retired"):
                continue
            body = str(get("body_expr") or "")
            params = [str(p) for p in (get("param_names") or ())]
            kind = str(get("domain_kind") or "any")
        except Exception:
            continue
        if not body or kind not in ("numeric", "any"):
            continue
        if len(params) != 1 or not all(
                p.startswith("_v") and p[2:].isdigit() for p in params):
            # first-order only: `_concept_candidates` re-checks this, but
            # filtering here keeps a higher-order concept (a concept whose hole
            # is a FUNCTION, which the micro grammar has no way to apply) out of
            # the candidate budget instead of paying to reject it per call.
            continue
        out.append({"body_expr": body, "param_names": params,
                    "retired": False, "domain_kind": kind})
    return out


def _concept_candidates(
    concepts: Sequence[Any],
    var_names: Sequence[str],
    atom_srcs: Sequence[str],
    consts: Sequence[Any],
    *,
    lift: bool,
    max_cands: int,
) -> list[dict[str, Any]]:
    """Instantiate learned concept templates against a synthesizer's atom set.

    A concept in the compounding library is stored as `body_expr` with `_v0..`
    holes -- a TEMPLATE, not an expression, which is why the hand-written
    micro grammar cannot reach its shapes at any depth (no min/max atoms exist
    there at all). Two families of instantiation:

      * base: fill the hole with a variable, or with an atom the enumerator
        already produced. With `atom_srcs=()` this is |concepts| x |vars|
        candidates -- microseconds, cheap enough for the COMMON path, where a
        shorter overfit would otherwise pre-empt the exact hit.
      * lifted (`lift=True`): also re-fill the template's own numeric literals
        from the example's constants, because a stored concept carries the
        literals it was mined with (`min(max(2 * _v0, 0), 100)` reproduces
        exactly THAT coefficient otherwise). Turning one concept into a
        parameterized family is enumeration, so it stays on the miss path.

    The min/max DUAL is generated for free (half of a real corpus writes a
    clamp as `max(min(...))`). Every candidate here is a HYPOTHESIS: the
    caller's `_scan` re-verifies against every example and selects by `rank`,
    so nothing can ship unverified, same as everywhere else in this module.
    """
    cands: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _push(code: str, cost: int) -> None:
        if code in seen or len(code) > _TPL_MAX_CODE or len(cands) >= max_cands:
            return
        seen.add(code)
        # `rank`, not length: a library concept is a NAMED abstraction with
        # independent support (it compressed a real corpus, evaluated
        # deterministically on probes, killed a syntactic mutant), so calling it
        # costs a node -- not its body. Ranked by raw length, the shortest-first
        # rule prefers a shorter ad-hoc ITE that fits the visible points and is
        # wrong off-spec: the learned grammar is paid for and then thrown away
        # by the tiebreak (measured: generalizes 1/10 vs 2/10 on the clamp
        # family, and 4/10 -> 7/10 spec-pass once ranked by grammar cost).
        cands.append({"code": code, "size": cost, "rank": cost})

    for cpt in concepts:
        get = cpt.get if isinstance(cpt, dict) else (lambda k, d=None: getattr(cpt, k, d))
        try:
            body = str(get("body_expr") or "")
            params = [str(x) for x in (get("param_names") or ())]
            retired = bool(get("retired"))
        except Exception:
            continue
        holes = [q for q in params if q.startswith("_v") and q[2:].isdigit()]
        if retired or not body or len(body) > _TPL_MAX_BODY:
            continue
        if len(holes) != len(params) or len(holes) != 1:
            continue  # only first-order templates instantiate in this grammar
        hole = holes[0]
        shapes = [body]
        if "\x00" not in body and "min" in body and "max" in body:
            shapes.append(body.replace("min", "\x00").replace("max", "min")
                          .replace("\x00", "max"))
        for shape in shapes:
            for fv in [*var_names, *atom_srcs]:
                _push(shape.replace(hole, f"({fv})"), _TPL_NAME_COST + len(fv))
            if not lift:
                continue
            lift_fills = list(dict.fromkeys([*var_names, *atom_srcs]))[:_TPL_MAX_LIFT_ATOMS]
            for m in list(_TPL_LIT.finditer(shape))[:3]:
                for c in consts:
                    cv = f"({c})" if c < 0 else str(c)
                    lifted = shape[:m.start()] + cv + shape[m.end():]
                    for fv in lift_fills:
                        _push(lifted.replace(hole, f"({fv})"),
                              _TPL_NAME_COST + len(fv) + 2)
                    if len(cands) >= max_cands:
                        break
                if len(cands) >= max_cands:
                    break
    return cands


def synthesize_body_from_examples(
    arg_names: Sequence[str],
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    extra_consts: Sequence[Any] = (),
    max_results: int = 8,
    seed: int = 7,
    concepts: Sequence[Any] = (),
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
    consts_fast: list[Any] = [t for _, t in examples
                              if isinstance(t, (int, float)) and not isinstance(t, bool)][:10]
    ns: dict[str, Any] = {}  # bare: eval adds __builtins__ (int/str/abs True); NO math —
    # the patched target module will not have imported it, so a candidate that
    # needs math is not shippable from this path. Verify under the target's env.

    def _scan(cands: list[dict[str, Any]]) -> str | None:
        found: str | None = None
        found_cost: int | None = None
        for cand in cands:
            code = str(cand.get("code") or "")
            if not code:
                continue
            try:
                fn = eval(f"lambda {', '.join(names)}: ({code})", dict(ns), {})  # noqa: S307
                if all(fn(*tuple(a)) == e for a, e in examples):
                    # shortest under the CURRENT grammar: candidates may carry a
                    # `rank` key (learned-grammar cost) that overrides raw
                    # length; everything else keeps the old behavior exactly.
                    cost = cand.get("rank", len(code))
                    if found_cost is None or cost < found_cost:
                        found, found_cost = code, cost
            except Exception:
                continue
        return found

    # Learned grammar on the COMMON path too, but only the free part: a
    # concept applied to a bare variable is |concepts| x |vars| evaluations, and
    # it is the one class that can beat an already-found overfit on rank
    # (min/max clamp reuse). The enumerative part (literal lifting over the atom
    # pool) stays below, on the miss path, where its ~300 ms is free.
    if concepts:
        try:
            fast = _concept_candidates(concepts, names, (), consts_fast,
                                       lift=False, max_cands=_TPL_MAX_FAST)
        except Exception:
            fast = []
        if fast:
            first = [*first, *fast]
    best = _scan(first)
    if best is None:
        try:
            best = _scan(_level2c_exhaustive(
                pairs, extra_consts=extra_consts, lang="python",
                max_results=max_results, concepts=concepts,
            ))
        except Exception:
            best = None
    return None if best is None else f"return {best}"
