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


def _make_confined_io_verifier(fn_name: str, expected_cases: Sequence[tuple[Any, Any, Any]]) -> Callable[[str], bool]:
    """Verify `cand_src` behaviorally inside `PersistentConfinedZygote` (`0` host `exec()`)."""
    test_lines = [f"from probe_mod import {fn_name}"]
    for a_v, b_v, exp_v in expected_cases:
        test_lines.append(f"assert {fn_name}({a_v!r}, {b_v!r}) == {exp_v!r}")
    test_src = "\n".join(test_lines) + "\n"

    def _verify(cand_src: str) -> bool:
        import pathlib as _pl
        import tempfile as _tf
        from canonical.runtime import brokered_workspace_execution_v1 as _broker

        with _tf.TemporaryDirectory() as td:
            ws = _pl.Path(td)
            (ws / "probe_mod.py").write_text("def " + fn_name + "(a, b): return None\n", encoding="utf-8")
            (ws / "test_probe.py").write_text(test_src, encoding="utf-8")
            res = _broker.run_confined_python_candidate_batch(
                ws,
                "probe_mod.py",
                ["test_probe.py"],
                [cand_src],
                stop_on_first_pass=True,
                per_candidate_timeout_s=1.0,
            )
            return bool(res.get("ok") and res.get("confined") and res.get("screen_authoritative") and 0 in (res.get("passing_indices") or []))

    return _verify


def _make_confined_reference_verifier(fn_name: str, orig_src: str, ref_src: str, arity: int) -> Callable[[str], bool]:
    """Verify `cand_src` behaviorally against `ref_src` (requiring `orig_src != ref_src` on >=1 input) inside `PersistentConfinedZygote`."""
    if arity <= 0:
        inputs_repr = "[()]"
    elif arity == 1:
        inputs_repr = "[(3,), (0,), (-2,), ([1, 2, 3],), ('ab',)]"
    elif arity == 2:
        inputs_repr = "[(3, 7), (8, 2), (5, 5), (-2, 4), (0, 1)]"
    else:
        tup_a = "(" + ", ".join(str(i + 2) for i in range(arity)) + ")"
        tup_b = "(" + ", ".join(str(10 - i) for i in range(arity)) + ")"
        inputs_repr = f"[{tup_a}, {tup_b}]"

    test_src = (
        f"import orig_mod, ref_mod, cand_mod\n"
        f"_fn_o = getattr(orig_mod, {fn_name!r})\n"
        f"_fn_r = getattr(ref_mod, {fn_name!r})\n"
        f"_fn_c = getattr(cand_mod, {fn_name!r})\n"
        f"_valid = 0\n"
        f"_diff = 0\n"
        f"for _args in {inputs_repr}:\n"
        f"    try:\n"
        f"        _ro = _fn_o(*_args)\n"
        f"        _rr = _fn_r(*_args)\n"
        f"    except Exception:\n"
        f"        continue\n"
        f"    _valid += 1\n"
        f"    if _ro != _rr:\n"
        f"        _diff += 1\n"
        f"    assert _fn_c(*_args) == _rr\n"
        f"assert _valid > 0 and _diff > 0\n"
    )

    def _verify(cand_src: str) -> bool:
        import pathlib as _pl
        import tempfile as _tf
        from canonical.runtime import brokered_workspace_execution_v1 as _broker

        with _tf.TemporaryDirectory() as td:
            ws = _pl.Path(td)
            (ws / "orig_mod.py").write_text(orig_src + "\n", encoding="utf-8")
            (ws / "ref_mod.py").write_text(ref_src + "\n", encoding="utf-8")
            (ws / "cand_mod.py").write_text(orig_src + "\n", encoding="utf-8")
            (ws / "test_behav.py").write_text(test_src, encoding="utf-8")
            res = _broker.run_confined_python_candidate_batch(
                ws,
                "cand_mod.py",
                ["test_behav.py"],
                [cand_src],
                stop_on_first_pass=True,
                per_candidate_timeout_s=1.0,
            )
            return bool(res.get("ok") and res.get("confined") and res.get("screen_authoritative") and 0 in (res.get("passing_indices") or []))

    return _verify


def synthesize_diagnostic_probes(rule: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Synthesize real confined behavioral diagnostic probes for `rule` (`0` host `exec()`)."""
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
                lhs_expr = "bool(a)" if old_op in ("and", "or") else "a"
                rhs_expr = "bool(b)" if old_op in ("and", "or") else "b"
                probes: list[dict[str, Any]] = [
                    {
                        "label": f"direct_return_{old_op}_to_{new_op}",
                        "language": "python",
                        "source_text": f"def _probe_direct(a, b):\n    return {lhs_expr} {old_op} {rhs_expr}\n",
                        "verifier": _make_confined_io_verifier("_probe_direct", expected),
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
                        "verifier": _make_confined_io_verifier("_probe_ctx", expected),
                    },
                ]
                if old_op == "<=":
                    probes.append(
                        {
                            "label": "disjunctive_lte_boundary",
                            "language": "python",
                            "source_text": "def _probe_sem(a, b):\n    return a < b or a == b\n",
                            "verifier": _make_confined_io_verifier("_probe_sem", expected),
                        }
                    )
                elif old_op == ">=":
                    probes.append(
                        {
                            "label": "disjunctive_gte_boundary",
                            "language": "python",
                            "source_text": "def _probe_sem(a, b):\n    return a > b or a == b\n",
                            "verifier": _make_confined_io_verifier("_probe_sem", expected),
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

    import ast

    probes_out: list[dict[str, Any]] = []
    try:
        p_tree = ast.parse(pat_ded)
        r_tree = ast.parse(rep_ded)
        fn_node = next((n for n in p_tree.body if isinstance(n, ast.FunctionDef)), None)
        if fn_node is not None and any(isinstance(n, ast.FunctionDef) and n.name == fn_node.name for n in r_tree.body):
            stmt_ver = _make_confined_reference_verifier(fn_node.name, pat_ded, rep_ded, len(fn_node.args.args))
        else:
            stmt_ver = _make_confined_reference_verifier(
                "_stmt_wrap",
                "def _stmt_wrap():\n" + "\n".join("    " + ln for ln in pat_ded.splitlines()),
                "def _stmt_wrap():\n" + "\n".join("    " + ln for ln in rep_ded.splitlines()),
                0,
            )
        probes_out.append(
            {
                "label": "statement_anchored_probe",
                "language": "python",
                "source_text": pat_ded + "\n",
                "verifier": stmt_ver,
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
                    param_list = list(dict.fromkeys([v for v in sample_bind.values() if not v.isdigit()] or ["a", "b"]))
                    sig = ", ".join(param_list)
                    if p_sk[0] == "GENERIC_CST" and "=" in "".join(p_sk[2]):
                        ctx_src = f"def _expr_ctx({sig}):\n    if True:\n        {sample_p}\n    return {param_list[0]}\n"
                        exp_src = f"def _expr_ctx({sig}):\n    if True:\n        {sample_r}\n    return {param_list[0]}\n"
                    else:
                        ctx_src = f"def _expr_ctx({sig}):\n    _tmp = ({sample_p})\n    return _tmp\n"
                        exp_src = f"def _expr_ctx({sig}):\n    _tmp = ({sample_r})\n    return _tmp\n"
                    probes_out.append(
                        {
                            "label": "expression_context_probe",
                            "language": "python",
                            "source_text": ctx_src,
                            "expected_expr_rewrite": exp_src.strip(),
                            "verifier": _make_confined_reference_verifier("_expr_ctx", ctx_src.strip(), exp_src.strip(), len(param_list)),
                        }
                    )
        else:
            from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import iter_cst_skeleton_candidates

            guard_ctx = "def _expr_ctx(a, b):\n    return (a + 2) // b\n"
            cands_g = list(iter_cst_skeleton_candidates(guard_ctx, rule, target_language="python", minimize=True))
            if cands_g:
                probes_out.append(
                    {
                        "label": "expression_context_probe",
                        "language": "python",
                        "source_text": guard_ctx,
                        "expected_expr_rewrite": cands_g[0].strip(),
                        "verifier": _make_confined_io_verifier("_expr_ctx", [(8, 2, 5), (8, 0, 0)]),
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
