#!/usr/bin/env python3
"""Let a rule discover how general it actually is, instead of being told.

Why this exists
---------------
Three mechanisms in this repository each work and none of them talk to each other:

* `verified_skill_crystallizer_v1` stores a rule bound to the skeleton it was taught from.
  Measured 2026-11-01: one lesson reached **1 of 7** structurally novel instances.
* `operator_generalization_v1` proves that lesson was really an operator swap and reaches
  **6 of 7** — but only because a human noticed and wrote the generalization.
* `finite_capability_diagnosis` implements exact **version-space narrowing**: pick the probe
  that eliminates the most hypotheses. Measured: it had **no caller anywhere in the tree**.

So the missing ingredient was never a mechanism. It was the edge between them, and the edge is
this: *"how general is this lesson?"* is a finite question, an instance is a probe, and a
failure is an observation. That is precisely what a version space is for.

What this module does
---------------------
Given one crystallized rule and a handful of instances, it:

1. states a **finite, explicit** space of scope hypotheses (see `SCOPE_HYPOTHESES`) — no
   open-ended "it might generalize somehow";
2. predicts, per hypothesis, what would happen on each instance;
3. asks `select_probe` which instance is most informative, runs it, and folds the observation
   back with `update_version_space`;
4. reports the surviving scope, or `MODEL_FALSIFIED` if the observations contradict every
   hypothesis it was given.

It cannot widen its own claim. The surviving hypothesis is a statement about *this rule on
these instances*, and `terminal_authority` is false throughout.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Sequence

from canonical.runtime.finite_capability_diagnosis import (
    Hypothesis,
    Probe,
    select_probe,
    update_version_space,
)

SCHEMA = "PROJECT_BRAIN_RULE_SCOPE_LEARNING_V1"

# Outcomes an instance can produce. Ordered from weakest to strongest so a report reads.
SILENT = "SILENT"                      # the scope proposes nothing for this instance
PROPOSES_UNVERIFIED = "PROPOSES_UNVERIFIED"  # it proposes, and the caller's verifier says no
SOLVED = "SOLVED"                      # it proposes and the verifier accepts

OUTCOMES = (SILENT, PROPOSES_UNVERIFIED, SOLVED)

# The finite scope space. Each is a real, separately implemented capability -- nothing here is
# hypothetical machinery, and a hypothesis is only included if some module can actually realize
# it.
#
# `SCOPE_SEMANTIC` was absent for several rounds on exactly that rule: no module realized "same
# meaning, different shape", so offering it would have been a fabrication. It is present now
# because `boundary_disjunction_normalization_v1` realizes it for the boundary family -- and
# because it was measured to matter: the boundary lesson reaches 6 of 7 re-spellings without it
# and 7 of 7 with it. The space is nested, STATEMENT inside OPERATOR inside SEMANTIC, so a
# surviving SEMANTIC is a strictly wider claim than a surviving OPERATOR.
SCOPE_EXPRESSION = "SCOPE_EXPRESSION"

SCOPE_HYPOTHESES: tuple[Hypothesis, ...] = (
    Hypothesis("SCOPE_STATEMENT", frozenset({"crystallizer.recall"})),
    Hypothesis("SCOPE_OPERATOR", frozenset({"crystallizer.recall", "operator_generalization"})),
    Hypothesis(
        "SCOPE_SEMANTIC",
        frozenset({
            "crystallizer.recall",
            "operator_generalization",
            "boundary_disjunction_normalization",
        }),
    ),
)

MAX_ROUNDS = 64


class ScopeLearningError(RuntimeError):
    """A named refusal. Scope learning never guesses."""


def _hypotheses() -> list[Hypothesis]:
    return list(SCOPE_HYPOTHESES)


# --------------------------------------------------------------------------- prediction
def _first_verified(candidates: Iterable[str], source_text: str,
                    verifier: Callable[[str], bool]) -> str:
    """Fold a candidate stream into one outcome. Exceptions in a verifier are not a pass."""
    proposed = False
    for candidate in candidates:
        if not candidate or candidate == source_text:
            continue
        proposed = True
        try:
            if verifier(candidate):
                return SOLVED
        except Exception:
            continue
    return PROPOSES_UNVERIFIED if proposed else SILENT


def _verifier_for(instance: Mapping[str, Any],
                  verifier: Callable[[str], bool] | None) -> Callable[[str], bool]:
    """An instance may carry its own verifier; otherwise the caller's applies to all.

    Each instance usually has its own assertions, so a single global verifier is often wrong.
    Carrying it on the instance keeps the caller honest: one instance, one contract.
    """
    own = instance.get("verifier")
    if callable(own):
        return own
    if callable(verifier):
        return verifier
    raise ScopeLearningError("INSTANCE_HAS_NO_VERIFIER")


def predicted_outcome(hypothesis_id: str, rule: Mapping[str, Any], instance: Mapping[str, Any],
                      verifier: Callable[[str], bool] | None = None) -> str:
    """What this scope would do on this instance. Deterministic; runs the real mechanism."""
    verifier = _verifier_for(instance, verifier)
    from canonical.swe_kernel import operator_generalization_v1 as gen
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry

    source_text = str(instance.get("source_text") or "")
    language = str(instance.get("language") or rule.get("language") or "python")

    if hypothesis_id == "SCOPE_STATEMENT":
        if language != str(rule.get("language") or "python"):
            return SILENT  # the store keys rules by language; it is not even consulted
        return _first_verified(
            cry.iter_crystallized_code_rule_candidates(source_text, rule),
            source_text, verifier)

    if hypothesis_id == "SCOPE_OPERATOR":
        return _first_verified(
            gen.propose_operator_swaps(source_text, rule, language=language),
            source_text, verifier)

    if hypothesis_id == "SCOPE_SEMANTIC":
        # Same meaning, different shape: normalise the instance into the taught form first, then
        # apply the swap. Wider than SCOPE_OPERATOR, and it costs a real normalisation module.
        from canonical.swe_kernel import boundary_disjunction_normalization_v1 as normalise

        try:
            return _first_verified(
                normalise.propose_semantic_swaps(
                    source_text, rule, operator_swaps=gen.propose_operator_swaps),
                source_text, verifier)
        except normalise.NormalizationError:
            return SILENT

    raise ScopeLearningError(f"UNKNOWN_SCOPE_HYPOTHESIS:{hypothesis_id}")


def observed_outcome(rule: Mapping[str, Any], instance: Mapping[str, Any],
                     verifier: Callable[[str], bool] | None = None) -> str:
    """What actually happens when the machine tries this instance with every mechanism it has.

    This must be independent of the hypothesis under test, or the version space would be
    reasoning about its own predictions. So it runs the whole available repertoire -- statement
    recall first, then operator generalization, then semantic normalisation -- and reports the
    best outcome reached.
    """
    from canonical.swe_kernel import boundary_disjunction_normalization_v1 as normalise
    from canonical.swe_kernel import operator_generalization_v1 as gen
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry

    v = _verifier_for(instance, verifier)
    source_text = str(instance.get("source_text") or "")
    language = str(instance.get("language") or rule.get("language") or "python")

    # Run the mechanisms directly. Deriving the observation from the predictions would make the
    # version space reason about itself; this does not.
    statement = _first_verified(
        cry.iter_crystallized_code_rule_candidates(source_text, rule), source_text, v)
    if statement == SOLVED:
        return SOLVED
    operator = _first_verified(
        gen.propose_operator_swaps(source_text, rule, language=language), source_text, v)
    if operator == SOLVED:
        return SOLVED
    semantic = _first_verified(
        normalise.propose_semantic_swaps(
            source_text, rule, operator_swaps=gen.propose_operator_swaps),
        source_text, v)
    if semantic == SOLVED:
        return SOLVED
    if PROPOSES_UNVERIFIED in (statement, operator, semantic):
        return PROPOSES_UNVERIFIED
    return SILENT


# --------------------------------------------------------------------------- learning
def learn_scope(
    rule: Mapping[str, Any],
    instances: Sequence[Mapping[str, Any]],
    verifier: Callable[[str], bool] | None = None,
    *,
    observation_limit: int | None = None,
) -> dict[str, Any]:
    """Narrow the rule's scope by running the most informative instances first.

    `instances` each need ``source_text`` and may carry ``language`` and ``label``. The
    `verifier` takes a patched source and returns whether it is acceptable; it is the only
    thing that can turn a proposal into evidence.
    """
    if not instances:
        raise ScopeLearningError("SCOPE_LEARNING_REQUIRES_INSTANCES")

    hyp = _hypotheses()
    ids = [h.hypothesis_id for h in hyp]
    remaining = list(ids)
    tried: list[dict[str, Any]] = []
    untried = list(range(len(instances)))
    limit = MAX_ROUNDS if observation_limit is None else max(0, int(observation_limit))

    while len(remaining) > 1 and untried and len(tried) < limit:
        # Build one Probe per untried instance, predicting the outcome for every hypothesis
        # still in the space. A probe that cannot separate anything is not offered.
        probes: list[Probe] = []
        by_id: dict[str, int] = {}
        for idx in untried:
            instance = instances[idx]
            outcomes: dict[str, str] = {}
            for hid in remaining:
                outcomes[hid] = predicted_outcome(hid, rule, instance, verifier)
            if len(set(outcomes.values())) < 2:
                continue
            pid = f"INSTANCE_{idx}"
            probes.append(Probe(pid, outcomes, 1.0))
            by_id[pid] = idx

        if not probes:
            break

        # The version space is what SURVIVED, not the space we started with. Passing the full
        # hypothesis set with probes that omit already-eliminated hypotheses makes
        # `select_probe` escalate -- which is how a third scope hypothesis exposed this: the
        # loop stopped after one observation because the probe no longer covered `hyp`.
        space = [h for h in hyp if h.hypothesis_id in remaining]
        chosen = select_probe(space, probes)
        if chosen.get("status") != "SELECT":
            break
        pid = str(chosen["probe_id"])
        idx = by_id[pid]
        instance = instances[idx]

        # The prediction is not the observation: run the real mechanisms and trust only the
        # caller's verifier.
        observed = observed_outcome(rule, instance, verifier)

        chosen_probe = next(p for p in probes if p.probe_id == pid)
        step = update_version_space(space, chosen_probe, observed)
        tried.append({
            "instance": instance.get("label") or pid,
            "language": instance.get("language") or rule.get("language"),
            "observed": observed,
            "status": step.get("status"),
            "remaining": step.get("remaining_hypotheses"),
        })
        untried.remove(idx)

        if step.get("status") == "MODEL_FALSIFIED":
            return {
                "schema": SCHEMA, "rule_id": rule.get("skill_id"),
                "result": "MODEL_FALSIFIED", "remaining": [], "steps": tried,
                "reason": ("the observation contradicts every scope hypothesis offered; the "
                           "space is wrong, not the rule"),
                "terminal_authority": False,
            }
        remaining = list(step.get("remaining_hypotheses") or [])
        if not remaining:
            break

    return {
        "schema": SCHEMA,
        "rule_id": rule.get("skill_id"),
        "result": ("RESOLVED" if len(remaining) == 1
                   else "UNDERDETERMINED" if len(remaining) > 1 else "MODEL_FALSIFIED"),
        "scope": remaining[0] if len(remaining) == 1 else None,
        "remaining": remaining,
        "observations_used": len(tried),
        "instances_offered": len(instances),
        "steps": tried,
        "terminal_authority": False,
    }


def scope_is(learned: Mapping[str, Any], hypothesis_id: str) -> bool:
    """Did learning resolve to this scope?"""
    return learned.get("scope") == hypothesis_id


_BINARY_OP_EVAL: dict[str, Callable[[Any, Any], Any]] = {
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "//": lambda a, b: a // b,
    "%": lambda a, b: a % b,
    "and": lambda a, b: bool(a) and bool(b),
    "or": lambda a, b: bool(a) or bool(b),
}


def _render_rule_tokens_concrete(tokens: Sequence[Any], hole_bindings: Mapping[str, str]) -> str:
    parts: list[str] = []
    for item in tokens:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        k, v = str(item[0]), str(item[1])
        if k in ("hole_id", "hole_num", "hole_str"):
            parts.append(hole_bindings.get(v, "1" if k == "hole_num" else "x"))
        else:
            parts.append(v)
    return "".join(parts)


def synthesize_diagnostic_probes(rule: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Synthesize real executable diagnostic probes for `rule` across relational, arithmetic, boolean & statement scopes."""
    lang = str(rule.get("language") or "python").lower()
    if lang != "python":
        return []

    from canonical.swe_kernel.operator_generalization_v1 import derive_operator_swap

    delta = derive_operator_swap(rule)
    if delta is not None:
        old_op, new_op = delta["from"], delta["to"]
        fn_old = _BINARY_OP_EVAL.get(old_op)
        fn_new = _BINARY_OP_EVAL.get(new_op)
        if fn_old is not None and fn_new is not None:
            sample_points = (
                [(0, 0), (0, 1), (1, 0), (1, 1)]
                if old_op in ("and", "or") or new_op in ("and", "or")
                else [(2, 5), (5, 5), (7, 5), (6, 2), (1, 3)]
            )
            if any(fn_old(a, b) != fn_new(a, b) for a, b in sample_points):
                expected = [(a, b, fn_new(a, b)) for a, b in sample_points]

                def _make_verifier(fn_name: str) -> Callable[[str], bool]:
                    def _verify(cand_src: str) -> bool:
                        ns: dict[str, Any] = {}
                        exec(cand_src, ns)  # noqa: S102
                        fn = ns.get(fn_name)
                        if not callable(fn):
                            return False
                        return all(fn(a, b) == exp for a, b, exp in expected)

                    return _verify

                lhs_expr = "bool(a)" if old_op in ("and", "or") else "a"
                rhs_expr = "bool(b)" if old_op in ("and", "or") else "b"
                probes: list[dict[str, Any]] = [
                    {
                        "label": f"direct_return_{old_op}_to_{new_op}",
                        "language": "python",
                        "source_text": f"def _probe_direct(a, b):\n    return {lhs_expr} {old_op} {rhs_expr}\n",
                        "verifier": _make_verifier("_probe_direct"),
                    },
                    {
                        "label": f"novel_context_{old_op}_to_{new_op}",
                        "language": "python",
                        "source_text": (
                            f"def _probe_ctx(a, b):\n"
                            f"    out = ({lhs_expr} {old_op} {rhs_expr})\n"
                            f"    if True:\n"
                            f"        return out\n"
                        ),
                        "verifier": _make_verifier("_probe_ctx"),
                    },
                ]
                if old_op == "<=":
                    probes.append(
                        {
                            "label": "disjunctive_lte_boundary",
                            "language": "python",
                            "source_text": "def _probe_sem(a, b):\n    return a < b or a == b\n",
                            "verifier": _make_verifier("_probe_sem"),
                        }
                    )
                elif old_op == ">=":
                    probes.append(
                        {
                            "label": "disjunctive_gte_boundary",
                            "language": "python",
                            "source_text": "def _probe_sem(a, b):\n    return a > b or a == b\n",
                            "verifier": _make_verifier("_probe_sem"),
                        }
                    )
                return probes

    # Non-operator rule (e.g., constant/guard/call edit): synthesize a concrete statement probe from the rule's own tokens
    pat_toks = rule.get("pattern_tokens") or []
    rep_toks = rule.get("replacement_tokens") or []
    if not pat_toks or not rep_toks:
        return []
    holes: list[tuple[str, str]] = []
    seen_h: set[str] = set()
    for item in pat_toks:
        if isinstance(item, (list, tuple)) and len(item) >= 2 and str(item[0]) in ("hole_id", "hole_num"):
            hv = str(item[1])
            if hv not in seen_h:
                seen_h.add(hv)
                holes.append((str(item[0]), hv))
    bind: dict[str, str] = {}
    id_names = ["_fn_probe", "a", "b", "c", "d"]
    id_idx = 0
    for hk, hv in holes:
        if hk == "hole_num":
            bind[hv] = "2"
        else:
            bind[hv] = id_names[min(id_idx, len(id_names) - 1)]
            id_idx += 1
    pat_concrete = _render_rule_tokens_concrete(pat_toks, bind)
    rep_concrete = _render_rule_tokens_concrete(rep_toks, bind)
    if not pat_concrete.strip() or pat_concrete.strip() == rep_concrete.strip():
        return []
    import textwrap

    pat_ded = textwrap.dedent(pat_concrete).strip()
    rep_ded = textwrap.dedent(rep_concrete).strip()
    if not pat_ded.startswith("def "):
        param_names = [v for k, v in bind.items() if not v.isdigit() and v != "_fn_probe"]
        sig = ", ".join(dict.fromkeys(param_names or ["a", "b"]))
        first = pat_ded.splitlines()[0].strip()
        if len(pat_ded.splitlines()) == 1 and first.endswith(":"):
            if first.startswith(("elif ", "else:", "except", "finally:")):
                pat_ded = f"def _probe_fn({sig}):\n    if False:\n        return 0\n    {pat_ded}\n        return 1\n    return 0"
                rep_ded = f"def _probe_fn({sig}):\n    if False:\n        return 0\n    {rep_ded}\n        return 1\n    return 0"
            else:
                pat_ded = f"def _probe_fn({sig}):\n    {pat_ded}\n        return 1\n    return 0"
                rep_ded = f"def _probe_fn({sig}):\n    {rep_ded}\n        return 1\n    return 0"
        else:
            ind_p = "\n".join("    " + ln for ln in pat_ded.splitlines())
            ind_r = "\n".join("    " + ln for ln in rep_ded.splitlines())
            pat_ded = f"def _probe_fn({sig}):\n{ind_p}"
            rep_ded = f"def _probe_fn({sig}):\n{ind_r}"

    def _stmt_verifier(cand_src: str) -> bool:
        return cand_src.strip() == rep_ded.strip()

    import ast

    probes_out: list[dict[str, Any]] = []
    try:
        ast.parse(pat_ded)
        probes_out.append(
            {
                "label": "statement_anchored_probe",
                "language": "python",
                "source_text": pat_ded + "\n",
                "verifier": _stmt_verifier,
            }
        )
    except SyntaxError:
        pass
    try:
        from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import (
            compile_rule_to_cst_skeleton,
            minimize_cst_skeleton_pair,
            render_canonical_expr,
        )

        comp = compile_rule_to_cst_skeleton(rule)
        if comp is not None:
            min_pair = minimize_cst_skeleton_pair(comp["pattern_skeleton"], comp["replacement_skeleton"]) or (
                comp["pattern_skeleton"],
                comp["replacement_skeleton"],
            )
            p_sk, r_sk = min_pair
            if p_sk[0] not in ("ATOM", "NUM", "HOLE") and not (
                p_sk[0] == "ATOM" and p_sk[1] in ("True", "False", "None")
            ):
                sample_bind = {hv: bind[hv] for _, hv in holes if hv in bind}
                sample_p = render_canonical_expr(p_sk, "python", sample_bind)
                sample_r = render_canonical_expr(r_sk, "python", sample_bind)
                if sample_p and sample_r and sample_p != sample_r:
                    param_names = [v for v in sample_bind.values() if not v.isdigit()]
                    sig = ", ".join(dict.fromkeys(param_names or ["a", "b"]))
                    if p_sk[0] == "GENERIC_CST" and "=" in "".join(p_sk[2]):
                        ctx_src = f"def _expr_ctx({sig}):\n    if True:\n        {sample_p}\n    return {sig.split(',')[0].strip()}\n"
                        exp_src = f"def _expr_ctx({sig}):\n    if True:\n        {sample_r}\n    return {sig.split(',')[0].strip()}\n"
                    else:
                        ctx_src = f"def _expr_ctx({sig}):\n    _tmp = ({sample_p})\n    return _tmp\n"
                        exp_src = f"def _expr_ctx({sig}):\n    _tmp = ({sample_r})\n    return _tmp\n"
                    probes_out.append(
                        {
                            "label": "expression_context_probe",
                            "language": "python",
                            "source_text": ctx_src,
                            "expected_expr_rewrite": exp_src.strip(),
                            "verifier": lambda cs, _exp=exp_src.strip(): cs.strip() == _exp,
                        }
                    )
    except Exception:
        pass
    return probes_out


def calibrate_rule_scope(rule: Mapping[str, Any], *, store: Any = None) -> dict[str, Any]:
    """Synthesize diagnostic probes, narrow `rule`'s version space via `select_probe`, and persist `learned_scope`."""
    probes = synthesize_diagnostic_probes(rule)
    if not probes:
        return {
            "schema": SCHEMA,
            "rule_id": rule.get("skill_id"),
            "result": "NO_PROBES_APPLICABLE",
            "scope": None,
            "persisted": False,
            "terminal_authority": False,
        }
    stmt_probes = [p for p in probes if p.get("label") != "expression_context_probe"]
    expr_probes = [p for p in probes if p.get("label") == "expression_context_probe"]
    report = dict(learn_scope(rule, stmt_probes or probes))
    remaining = list(report.get("remaining") or [])
    effective_scope = str(report.get("scope") or (remaining[0] if remaining else "")) or None
    if effective_scope == "SCOPE_STATEMENT" and expr_probes:
        try:
            from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import iter_cst_skeleton_candidates

            ep = expr_probes[0]
            v_fn = ep["verifier"]
            if any(
                v_fn(cand)
                for cand in iter_cst_skeleton_candidates(
                    ep["source_text"], rule, target_language="python", minimize=True
                )
            ):
                effective_scope = SCOPE_EXPRESSION
                report["scope"] = SCOPE_EXPRESSION
                report["result"] = "RESOLVED"
        except Exception:
            pass
    report["effective_scope"] = effective_scope
    persisted = False
    sid = str(rule.get("skill_id") or "")
    if store is not None and sid and effective_scope and hasattr(store, "update_learned_scope"):
        persisted = bool(store.update_learned_scope(sid, effective_scope, audit=report))
    report["persisted"] = persisted
    return report
