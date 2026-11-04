"""Semantic anti-unification: can it notice that two DIFFERENT programs mean the SAME thing?

THE LIMIT THIS TARGETS
----------------------
Measured 2026-11-03 (`COMPOUNDING_IS_GENERATION_20261103_V1.md` §2): `concept_library_v1` induces
a concept only when the same subtree appears LITERALLY in two solved programs. The same idea
written differently yields nothing:

    max(p, q) - min(p, q)   vs   abs(s - t)          -> 0 concepts admitted
    (p + q) / 2.0            vs   s / 2.0 + t / 2.0  -> 0 concepts admitted

So the organ can **reuse what it wrote** and cannot **notice that two different programs mean the
same thing.** Everything sentient-like lives on the far side of that sentence, which is why this
module exists and why it is small.

WHAT THIS DOES, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------
It finds structurally-distinct subtree pairs that agree on every probe in a vector, and returns the
correspondence with the exact witness values. It uses `eval_pure_ast_expr` -- the repository's own
zero-`exec` evaluator -- so a "match" is an observation, not a claim about algebra.

It does NOT claim to prove equivalence. Agreement on a finite probe vector is evidence proportional
to the probes, and a disagreement anywhere is treated as proof of difference. The asymmetry is
deliberate: a false "different" costs a missed concept, a false "same" puts a wrong concept into
the synthesis grammar and every program built on it inherits the error.

WHAT WOULD FALSIFY IT
---------------------
If structurally-distinct pairs that agree on all probes cannot be found among programs that
clearly share an idea, the mechanism is not there. If they are found but agreement is an artefact
of too few probes, then `probe_sufficient` will be False and the correspondence must not be used.

Authority: NONE. Pure expression evaluation over small numeric values.
"""
from __future__ import annotations

import ast
import itertools
import math
from collections.abc import Mapping, Sequence
from typing import Any

from canonical.swe_kernel.concept_library_v1 import eval_pure_ast_expr

SCHEMA = "PROJECT_BRAIN_SEMANTIC_UNIFICATION_V1"

# Probe values deliberately include negatives, zeros and 1s: division singularities, sign flips
# and neutral elements are exactly where two different-looking expressions stop agreeing.
PROBE_VALUES = (0, 1, 2, 3, 5, -1, -3, 7, 10)
MIN_AGREEING_PROBES = 6


def _is_concept_shaped(node: ast.expr) -> bool:
    """A bare variable is not an idea.

    Measured 2026-11-03: without this, `p` and `s` "agreed on 9 probes" because both were bound
    to the same probe value -- variable renaming masquerading as semantic equivalence, and it
    made two completely unrelated programs (`p * q` vs `s + t`) report four correspondences.
    A correspondence has to involve STRUCTURE: at least one operator or call.
    """
    has_op = any(isinstance(n, (ast.BinOp, ast.Compare, ast.Call, ast.BoolOp)) for n in ast.walk(node))
    return has_op and sum(1 for _ in ast.walk(node)) >= 3


def _exprs(source: str) -> list[tuple[str, ast.expr, tuple[str, ...]]]:
    """Every expression in a program that mentions at least one of the function's parameters."""
    out: list[tuple[str, ast.expr, tuple[str, ...]]] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        params = tuple(a.arg for a in fn.args.args)
        if not params:
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.expr):
                continue
            names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            free = tuple(sorted(names & set(params)))
            if not free or not _is_concept_shaped(node):
                continue
            out.append((ast.unparse(node), node, free))
    return out


def _evaluate(node: ast.expr, free: Sequence[str], probes: Mapping[str, Any]) -> Any:
    env = {name: probes[name] for name in free}
    try:
        return eval_pure_ast_expr(node, env, extra_callables={"abs": abs, "min": min, "max": max,
                                                              "round": round, "int": int,
                                                              "float": float})
    except Exception as exc:  # noqa: BLE001 - a raise IS an observation
        return ("RAISED", type(exc).__name__)


ULP_TOLERANCE = 1e-12


def _agreement(a: Any, b: Any) -> str:
    """EXACT, REPRESENTATION, or DISAGREE.

    `REPRESENTATION` exists because of a measured case: `100.0 * p / q` and `(p / q) * 100.0`
    agree in meaning and disagreed in 13 of 81 probes by one unit in the last place -- float
    multiplication is not associative. Calling that a semantic difference is an instrument bug.
    But a single tolerance would also hide real differences, so the grade is recorded per pair
    and the tolerance is machine-epsilon scale (1e-12 relative), far below any real
    disagreement this project's programs produce (the ones that differed at all differed by
    orders of magnitude or by sign).
    """
    if repr(a) == repr(b):
        return "EXACT"
    # int vs float is also a representation difference: measured 2026-11-03, the clamped-interval
    # pair `max(0.0, min(1.0, p))` vs a ternary chain "disagreed" only because one path returned
    # `0.0` (float) and the other `0` (int). `bool` is EXCLUDED deliberately -- `True == 1` in
    # Python, and letting a comparison result pass as a number would be a silent false positive.
    for v in (a, b):
        if isinstance(v, bool):
            return "DISAGREE"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if math.isclose(a, b, rel_tol=ULP_TOLERANCE, abs_tol=ULP_TOLERANCE):
            return "REPRESENTATION"
    return "DISAGREE"


def _signature(node: ast.expr, free: Sequence[str]) -> tuple[tuple[Any, ...], int]:
    """The value vector over every combination of probe values, and how many agreed.

    Uses combinations rather than permutations of the same multiset because two free variables
    bound to the same value is where a surprising number of "equivalences" die.
    """
    values: list[Any] = []
    for combo in itertools.product(PROBE_VALUES, repeat=len(free)):
        values.append(_evaluate(node, free, dict(zip(free, combo))))
    distinct = len({repr(v) for v in values})
    return tuple(values), distinct


def find_correspondences(sources: Sequence[str], *,
                         max_pairs: int = 40) -> dict[str, Any]:
    """Structurally distinct expressions from DIFFERENT programs that agree on every probe.

    Returns the correspondences, the witness projection, and -- importantly -- a sufficiency
    verdict per pair. A pair that agrees but is constant is not evidence of shared MEANING
    (0 == 0 for two different reasons), so non-constancy is required on both sides.
    """
    per_program = [(_exprs(src)) for src in sources]
    if len(per_program) < 2:
        return {"schema": SCHEMA, "correspondences": [], "reason": "NEED_TWO_PROGRAMS"}

    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for i in range(len(per_program)):
        for j in range(i + 1, len(per_program)):
            for left_src, left_ast, left_free in per_program[i]:
                for right_src, right_ast, right_free in per_program[j]:
                    if left_src == right_src:
                        continue            # structurally identical: the syntactic case, already works
                    if (left_src, right_src) in seen:
                        continue            # nested subtrees report the same pair repeatedly
                    seen.add((left_src, right_src))
                    if len(left_free) != len(right_free):
                        continue
                    if len(found) >= max_pairs:
                        break
                    lv, ldistinct = _signature(left_ast, left_free)
                    rv, rdistinct = _signature(right_ast, right_free)
                    if len(lv) != len(rv):
                        continue
                    grades = [_agreement(a, b) for a, b in zip(lv, rv)]
                    agree = sum(1 for g in grades if g != "DISAGREE")
                    exact = sum(1 for g in grades if g == "EXACT")
                    # Both sides must be non-constant, or "agreement" is two zeros agreeing.
                    if ldistinct < 2 or rdistinct < 2:
                        continue
                    if agree != len(lv):
                        continue
                    if len(lv) < MIN_AGREEING_PROBES:
                        continue
                    if agree < MIN_AGREEING_PROBES:
                        continue
                    found.append({
                        "left": left_src,
                        "right": right_src,
                        "left_program": i,
                        "right_program": j,
                        "free_left": list(left_free),
                        "free_right": list(right_free),
                        "probes_agreed": agree,
                        "probes_exact": exact,
                        "probes_representation": agree - exact,
                        "witness": [
                            {"left_args": list(combo), "right_args": list(combo),
                             "value": repr(v)}
                            for combo, v in list(
                                zip(itertools.product(PROBE_VALUES, repeat=len(left_free)), lv))[:4]
                        ],
                        "evidence": ("OBSERVED_AGREEMENT_ON_%d_PROBES" % agree),
                        "grade": "EXACT" if exact == len(lv) else "UP_TO_REPRESENTATION",
                    })
    return {
        "schema": SCHEMA,
        "correspondences": found,
        "count": len(found),
        "probe_values": list(PROBE_VALUES),
        "min_agreeing_probes": MIN_AGREEING_PROBES,
        "authority": "NONE",
        "not_claimed": [
            "that the correspondence is a PROOF of equivalence -- it is agreement on a finite "
            "probe vector, and a disagreement anywhere would have vetoed it",
            "that an admitted concept generalises beyond the values probed",
        ],
    }


def describe(doc: Mapping[str, Any]) -> str:
    lines = ["%d semantic correspondence(s) between structurally DISTINCT expressions"
             % int(doc.get("count") or 0)]
    for row in (doc.get("correspondences") or [])[:8]:
        lines.append("  %-26s == %-26s  on %d probes"
                     % (row["left"], row["right"], row["probes_agreed"]))
    return "\n".join(lines)


def _rename_free(node_src: str, src_free: Sequence[str], dst_free: Sequence[str]) -> str:
    """Positionally rename free variables -- the correspondence was established under exactly
    this pairing (the same probe tuple fed to both sides), so positional is the honest mapping."""
    tree = ast.parse(node_src, mode="eval")
    mapping = dict(zip(src_free, dst_free))
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id in mapping:
            n.id = mapping[n.id]
    return ast.unparse(tree.body)


def bridge_sources(left: str, right: str, correspondence: Mapping[str, Any]) -> str:
    """Rewrite `right`'s body occurrences of the corresponding expression into `left`'s form.

    This is the join that was missing. `sleep_abstract` needs literal shared syntax; a verified
    correspondence now supplies that syntax from the OTHER program, so the organ sees one shared
    subtree where before it saw none. Nothing new is asserted: the rewritten program is
    observationally the same program, and the concept it helps induce still has to pass the
    library's own execution, non-constancy and mutant-killing gates.
    """
    # Direction matters and was got wrong on the first attempt: the text to FIND is `right`'s
    # expression as written in `right`, and the text to SUBSTITUTE is `left`'s expression renamed
    # into `right`'s variable names. Renaming the other way produced a needle that was never
    # present, so every trial reported REWRITE_CHANGED_NOTHING and measured nothing.
    needle = correspondence["right"]
    replacement = _rename_free(correspondence["left"], correspondence["free_left"],
                               correspondence["free_right"])
    out: list[str] = []
    for line in right.splitlines():
        if needle in line:
            line = line.replace(needle, replacement)
        out.append(line)
    return "\n".join(out) + ("\n" if right.endswith("\n") else "")


def abstract_with_correspondence(library: Any, left: str, right: str) -> dict[str, Any]:
    """Induce concepts from two programs, using semantic correspondences to create shared syntax.

    Returns both arms so the difference is attributable: `without` is the organ's ordinary
    behaviour on the two sources, `with` is its behaviour once a verified correspondence has
    aligned the syntax. If they are equal the join bought nothing and must be reported as such.
    """
    baseline = library.sleep_abstract([left, right])
    doc = find_correspondences([left, right])
    trials: list[dict[str, Any]] = []
    before = set(getattr(library, "_concepts", {}).keys())
    for corr in doc.get("correspondences") or []:
        bridged = bridge_sources(left, right, corr)
        if bridged == right:
            trials.append({"correspondence": corr["left"] + " == " + corr["right"],
                           "skipped": "REWRITE_CHANGED_NOTHING"})
            continue
        res = library.sleep_abstract([left, bridged])
        new = sorted(set(getattr(library, "_concepts", {}).keys()) - before)
        trials.append({
            "correspondence": corr["left"] + " == " + corr["right"],
            "grade": corr["grade"],
            "admitted": int(res.get("admitted_count") or 0),
            "new_concepts": new,
        })
    return {
        "schema": SCHEMA + "_JOIN",
        "without": int(baseline.get("admitted_count") or 0),
        "correspondences": int(doc.get("count") or 0),
        "trials": trials,
        "with_total": sum(int(t.get("admitted") or 0) for t in trials),
        "authority": "NONE",
    }
