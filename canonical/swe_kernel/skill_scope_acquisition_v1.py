#!/usr/bin/env python3
"""A skill's condition of applicability is bought with observations, not declared with a count.

THE GAP THIS CLOSES
-------------------
Two modules in this tree already hold the law and the instrument:

  * `canonical/runtime/applicability_v1.learn(evidence)` identifies the requirement a set of
    observations supports, and refuses with a named reason when they do not support one. It needs
    `Sequence[(state, succeeded)]`, where a state is the set of facts observed TRUE.
  * `canonical/runtime/contrast_selection_v1.select_contrast(evidence, candidate_states)` names the
    observation that splits the surviving requirements most evenly. The caller owns realisability.

Neither has ever had anything to read. Measured across the last two rounds: the shipped skill records
carry `provenance {at, hits, origin}` and `verified_hits`, which are COUNTS; `crystallize_code_fix`
stores `training_baseline` (returncode 1, test_count 2) and `training_verification` (returncode 0) --
a real failure and a real success -- but in a shape the law cannot read, so the scope ledger reports
5 of 5 skills `EXACT_MATCH_ONLY` and every boundary `UNDETERMINED__NO_CONTRASTING_OUTCOME`. And no
module in the tree turns a source text into observable facts at all: a grep for `facts_of`,
`state_of`, `observable_facts`, `extract_facts`, `observe_state` across `canonical/` returns nothing.

`rule_scope_learning_v1.learn_scope` is adjacent and is NOT this. It narrows among three hypothesis
LEVELS -- SCOPE_STATEMENT, SCOPE_OPERATOR, SCOPE_SEMANTIC -- i.e. which rewriting machinery a lesson
needs, and returns `{"scope": hypothesis_id}`. It never calls `applicability_v1` or
`contrast_selection_v1`. Choosing the mechanism and identifying the domain are different questions.

WHAT THIS MEASURED, BEFORE IT WAS BUILT
---------------------------------------
One boundary lesson (`x <= hi` -> `x < hi`) was run against eight victims, each executed against its
OWN specification, facts computed from the AST:

    fired on 8 of 8    repaired 4 (the defect was present)    BROKE CORRECT CODE on 4 (it was not)

    4 observations, all successes  -> UNDETERMINED__NO_CONTRASTING_OUTCOME   required=None
    5 observations, first failure  -> IDENTIFIED__ONE_CONSISTENT_REQUIREMENT
                                      required=('baseline.violates_own_spec',)

So the boundary is bought with five executed observations, and the condition it buys is exactly the
precondition whose absence `skill_precondition_presence_v1` recorded on 2026-11-12: a rule learned
about a defect that was not there went on to introduce a bug in correct code. Offered a pool of
realisable states at four observations, `select_contrast` named the deciding one before it was made
(`SELECTED`, survivors 2 -> 1, discriminating fact `baseline.violates_own_spec`). Offered only the
states already observed, it correctly said no reachable state splits the survivors.

THE SEMANTICS TRAP, AND WHY IT IS THE LOAD-BEARING DETAIL
---------------------------------------------------------
A victim where the skill never fires is NOT a failure. It is `NOT_APPLICABLE` and it yields no
observation at all, because nothing was tried and nothing was learned. Counting a non-firing as a
failure would manufacture a boundary out of the tokenizer's reach rather than the skill's domain --
the same error as counting a `PASS` that only proved a process started. Every row here therefore
carries the verdict that produced it, and `FIRED` is a precondition for being evidence.

A fact must also be COMPUTED. The prototype this module came from used `"return " in source` for
`site.return`, which is true of a function that returns nowhere near the operator, and it produced a
requirement of `{baseline.violates_own_spec, site.return}` -- a plausible, wrong, narrower scope. On
the AST the same evidence yields `{baseline.violates_own_spec}` alone. A crude extractor does not
fail loudly; it reports a scope that looks identified.

WHAT THIS DOES NOT SAY
----------------------
That the acquired condition is TRUE in general. It is the one requirement consistent with the
observations made, and `learn` says so: with successes only it returns `NO_FAILURE__NECESSITY_IS_ONLY
_REFUTED_BY_FAILURE`, and with several consistent requirements it returns AMBIGUOUS rather than
picking. That a fact absent from a state was observed false. Absent means not observed true.
That `admits` accepts anything. It decides whether a skill may be PROPOSED against a target; the
caller's verifier still decides the outcome, and this module exposes no acceptance surface.
That the shipped corpus now has scopes. It does not: acquiring one needs victims and a specification
for each, and neither is stored with a skill. That gap is named, not papered over.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as _app  # noqa: E402
from canonical.runtime import contrast_selection_v1 as _cs  # noqa: E402

SCHEMA = "PROJECT_BRAIN_SKILL_SCOPE_ACQUISITION_V1"

# Observation verdicts. Only a firing is an observation; only a repair is a success.
NOT_APPLICABLE = "NOT_APPLICABLE__THE_SKILL_NEVER_FIRED"
REPAIRED = "REPAIRED"
BROKE_CORRECT = "BROKE_CORRECT_CODE"
NOOP_CORRECT = "NO_CHANGE_TO_AN_ALREADY_CORRECT_TARGET"
FIRED_STILL_WRONG = "FIRED_AND_STILL_WRONG"

#: Which verdicts count as evidence at all, and which of those count as success.
IS_EVIDENCE = frozenset({REPAIRED, BROKE_CORRECT, NOOP_CORRECT, FIRED_STILL_WRONG})
IS_SUCCESS = frozenset({REPAIRED})

#: The fact that says the target already fails the specification it is being judged by. This is the
#: requirement the boundary lesson above identified, and it is the observability the tree was missing.
BASELINE_VIOLATES = "baseline.violates_own_spec"
BASELINE_SATISFIES = "baseline.satisfies_own_spec"

MAX_OBSERVATIONS = 64


class ScopeAcquisitionError(RuntimeError):
    """A named refusal. Never widen quietly."""


# --------------------------------------------------------------------------- computed facts
def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    out: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            out[child] = node
    return out


def _encloses(hay: ast.AST | None, needle: ast.AST) -> bool:
    return hay is not None and any(n is needle for n in ast.walk(hay))


def observable_facts(source: str, *, baseline_ok: bool | None,
                     language: str = "python") -> frozenset[str]:
    """The facts a source text can be OBSERVED to have. Computed, never declared.

    `baseline_ok` is whether the target already satisfies its own specification. `None` means no
    specification was executed, and then no baseline fact is emitted at all -- an unexecuted claim is
    not a fact, which is the whole reason this module exists.
    """
    if language.lower() != "python":
        # Refusing is honest: the extractor below is an AST walker for Python, and a fact computed by
        # the wrong parser is worse than no fact. Other languages need their own extractor.
        raise ScopeAcquisitionError(f"NO_FACT_EXTRACTOR_FOR_LANGUAGE:{language}")
    facts: set[str] = set()
    if baseline_ok is None:
        facts.add("baseline.not_executed")
    else:
        facts.add(BASELINE_SATISFIES if baseline_ok else BASELINE_VIOLATES)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return frozenset(facts | {"source.unparseable"})

    parents = _parents(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        chain: list[ast.AST] = []
        cur = node
        while cur in parents:
            cur = parents[cur]
            chain.append(cur)
        # A substring test is not an observation: `"return " in src` is true of a function whose
        # return is nowhere near the operator, and that crudeness was measured to yield a plausible,
        # wrong, narrower scope. The site is where the comparison node actually sits.
        if any(isinstance(c, ast.Return) for c in chain):
            facts.add("site.return")
        if any(isinstance(c, ast.Assign) for c in chain):
            facts.add("site.assignment")
        if any(isinstance(c, ast.If) and _encloses(c.test, node) for c in chain):
            facts.add("site.if_guard")
        if any(isinstance(c, ast.While) and _encloses(c.test, node) for c in chain):
            facts.add("site.while_guard")
        if any(isinstance(c, ast.AugAssign) for c in chain):
            facts.add("site.augmented_assignment")
        if any(isinstance(c, ast.UnaryOp) and isinstance(c.op, ast.Not) for c in chain):
            facts.add("form.negated")
        if any(isinstance(c, ast.BoolOp) for c in chain):
            facts.add("form.compound_boolean")
        if any(isinstance(c, (ast.ListComp, ast.GeneratorExp, ast.SetComp, ast.DictComp))
               for c in chain):
            facts.add("site.comprehension")
        if isinstance(node.left, ast.Name):
            facts.add(f"left_operand.name.{node.left.id}")
        for op in node.ops:
            facts.add(f"operator.{type(op).__name__}")
    if not any(f.startswith("operator.") for f in facts):
        facts.add("operator.none_present")
    return frozenset(facts)


# --------------------------------------------------------------------------- one observation
def observe(rule: Mapping[str, Any], source: str, spec: str, *,
            propose: Callable[..., Iterable[str]] | None = None,
            language: str = "python",
            executor: Callable[[str, str], bool] | None = None) -> dict[str, Any]:
    """Run one victim against its OWN specification, before and after the skill is applied.

    Returns a dict carrying the verdict, the computed state, and -- only when the skill actually
    fired -- the `(state, succeeded)` row the law can read. The specification is the victim's own
    contract; nothing here is told what the victim is or what the right answer is.
    """
    from canonical.swe_kernel import operator_generalization_v1 as _gen

    proposer = propose or _gen.propose_operator_swaps
    run = executor or _default_executor

    baseline_ok = run(source, spec)
    candidates = [c for c in proposer(source, rule, language=language)]
    fired = bool(candidates)
    solved = any(run(c, spec) for c in candidates)

    if not fired:
        verdict = NOT_APPLICABLE
    elif solved and not baseline_ok:
        verdict = REPAIRED
    elif baseline_ok and not solved:
        verdict = BROKE_CORRECT
    elif solved:
        verdict = NOOP_CORRECT
    else:
        verdict = FIRED_STILL_WRONG

    state = observable_facts(source, baseline_ok=baseline_ok, language=language)
    return {"schema": SCHEMA, "verdict": verdict, "fired": fired,
            "baseline_ok": baseline_ok, "solved": solved,
            "candidates": len(candidates), "state": state,
            "row": (sorted(state), verdict in IS_SUCCESS) if verdict in IS_EVIDENCE else None}


def _default_executor(source: str, spec: str) -> bool:
    """Execute `source` then `spec`. The spec is assertions, so passing means they all held."""
    ns: dict[str, Any] = {}
    try:
        exec(compile(source, "<scope-victim>", "exec"), ns)
        exec(compile(spec, "<scope-spec>", "exec"), ns)
    except Exception:
        return False
    return True


# --------------------------------------------------------------------------- the law, applied
def scope_of(rows: Sequence[tuple[Iterable[str], bool]]) -> Any:
    """The boundary these observations support, by the tree's own law and no other."""
    return _app.learn(rows)


def buy_scope(rule: Mapping[str, Any], victims: Sequence[Mapping[str, Any]], *,
              budget: int = MAX_OBSERVATIONS, language: str = "python") -> dict[str, Any]:
    """Spend observations until the scope is IDENTIFIED, or say exactly why it never was.

    Each victim needs `source` and `spec`. Order is chosen by `select_contrast` over the states the
    REMAINING victims would actually produce, so the caller owns realisability and nothing invents a
    state. A victim the skill never fires on costs an observation and yields no evidence, which is
    recorded rather than hidden.
    """
    if not victims:
        raise ScopeAcquisitionError("SCOPE_ACQUISITION_REQUIRES_VICTIMS")
    limit = max(0, min(int(budget), MAX_OBSERVATIONS))

    remaining = list(range(len(victims)))
    rows: list[tuple[list[str], bool]] = []
    trace: list[dict[str, Any]] = []
    states: dict[int, frozenset[str]] = {}
    boundary = _app.learn(rows)

    while remaining and len(trace) < limit:
        pool = []
        for idx in remaining:
            v = victims[idx]
            st = observable_facts(str(v.get("source", "")),
                                  baseline_ok=_default_executor(str(v.get("source", "")),
                                                                str(v.get("spec", ""))),
                                  language=language)
            states[idx] = st
            pool.append(st)
        choice = _cs.select_contrast(rows, pool) if rows else None
        if choice is not None and choice.informative and choice.state is not None:
            wanted = frozenset(choice.state)
            pick = next((i for i in remaining if states[i] == wanted), remaining[0])
        else:
            pick = remaining[0]
        remaining.remove(pick)

        obs = observe(rule, str(victims[pick].get("source", "")),
                      str(victims[pick].get("spec", "")), language=language)
        trace.append({"index": pick, "label": victims[pick].get("label"),
                      "verdict": obs["verdict"], "evidence": obs["row"] is not None,
                      "chosen_by": (choice.status if choice is not None else "FIRST__NO_EVIDENCE_YET"),
                      "gain_log_terms": (choice.gain_log_terms if choice is not None else None)})
        if obs["row"] is not None:
            rows.append((list(obs["row"][0]), bool(obs["row"][1])))
        boundary = _app.learn(rows)
        if boundary.status.startswith("IDENTIFIED"):
            break

    return {"schema": SCHEMA, "status": boundary.status, "required": boundary.required,
            "reason": boundary.reason, "survivors": boundary.survivor_count,
            "observations_spent": len(trace), "evidence_rows": len(rows),
            "successes": boundary.successes, "failures": boundary.failures,
            "not_applicable": sum(1 for t in trace if t["verdict"] == NOT_APPLICABLE),
            "broke_correct_code": sum(1 for t in trace
                                      if t["verdict"] == BROKE_CORRECT),
            "trace": trace, "boundary": boundary}


# --------------------------------------------------------------------------- enforcement
def admits(scope_required: Iterable[str] | None, target_facts: Iterable[str]) -> dict[str, Any]:
    """May a skill with this identified requirement be PROPOSED against this target?

    A refusal, not an acceptance: this decides whether to try, and the caller's verifier still
    decides the outcome. With no identified requirement there is nothing to withhold on, and the
    answer says so rather than pretending to a check that never happened.
    """
    required = frozenset(str(x) for x in (scope_required or ()))
    have = frozenset(str(x) for x in (target_facts or ()))
    if not required:
        return {"admitted": True, "basis": "NO_IDENTIFIED_REQUIREMENT__NOTHING_TO_WITHHOLD_ON",
                "missing": []}
    missing = sorted(required - have)
    return {"admitted": not missing, "basis": ("REQUIREMENT_SATISFIED" if not missing
                                              else "IDENTIFIED_REQUIREMENT_ABSENT"),
            "missing": missing}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    from canonical.tools.skill_scope_acquisition_probe_v1 import demonstration
    doc = demonstration()
    if args.json:
        print(json.dumps(doc, indent=1, sort_keys=True, default=sorted))
        return 0
    print("skill scope acquisition: what a skill learns about WHERE it applies\n")
    print(f"  victims offered            {doc['victims_offered']}")
    print(f"  skill fired on             {doc['fired_on']}")
    print(f"  repaired (defect present)  {doc['repaired']}")
    print(f"  broke correct code         {doc['broke_correct_code_before_scope']}")
    print(f"\n  observations to IDENTIFY   {doc['observations_to_identify']}")
    print(f"  required                   {doc['required']}")
    print(f"  status                     {doc['status']}")
    print(f"\n  with the scope enforced: breakages {doc['broke_correct_code_before_scope']}"
          f" -> {doc['broke_correct_code_after_scope']}, repairs {doc['repaired']}"
          f" -> {doc['repairs_after_scope']}")
    print(f"  refusals now named         {doc['refusals_named']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
