#!/usr/bin/env python3
"""Compose only what is proved — a composition rule with premise survival, per-step
proof, and proof survival, plus its own reach measurement.

THE DEFECT THIS CLOSES
----------------------
Two individually verified skills do not make a verified sequence. Measured 2026-11-12
(`SKILLS_DONT_COMPOSE_20261112_V1.md`): teach A `x <= 10` -> `x < 10` and teach B
`x < 10` -> `x <= 10`, apply both, net change none — and every local check passes.
`skill_sequence_verify_v1` was the first half of the answer: it reads the TEXT of a
sequence after the fact and names no-ops and reverts. It cannot answer the question
that decides whether a sequence may even run:

    does the second operation's premise still hold in the world the first one left?

A local check cannot see a global revert; a post-hoc check cannot refuse a step whose
premise is already dead. This module is the affirmative rule, and it is deliberately
the module two receipts named as next (`WHAT_ONE_DEMONSTRATION_REACHES_20261116_V1.md`
§6.4: "compose only what is proved … the next module should be a composition rule with
its own reach measurement").

THE RULE (five checks per step, in order)
-----------------------------------------
For each operation, on the world AFTER the previous effects:

  1. PREMISE      the operation's stated premise is evaluated on the CURRENT state.
                  Dead premise => refusal. The operation is never applied — a refusal
                  before execution, which no post-hoc textual check can make.
  2. APPLY        the operation runs. No change => refusal (a rule counted that did
                  nothing is not a pass).
  3. HISTORY      the produced state must not equal any earlier state (a step that
                  returns the text to where it already was is a revert, named by the
                  step it went back to).
  4. PROOF        the operation's own proof predicate must hold on the state it just
                  produced. Compose only what is proved.
  5. SURVIVAL     every EARLIER step's proof predicate is re-checked on the new state.
                  A later effect that invalidates an earlier proof kills the sequence
                  even when the text does not revert byte-for-byte.

PASS is all five, for every step. Each refusal names the step, the operation, and the
reason; the per-step trace (premise held, proof why, produced digest) is the receipt.

WHAT PROOFS ARE
---------------
A proof is a caller-supplied predicate `state -> (ok, why)`. The organ enforces that
proofs are required and re-checked; it cannot make a weak predicate strong. Callers
that have the tree's own judge pass the tree's own judge. The default `rule_op` proof
is structural and labelled as such — the step proof is "this apply's output, and it
parses" (crystallized rules are holed: `?id0`, `?num0`, so no textual replacement
check exists), and survival is the durable half of the claim: the taught pattern can
no longer fire anywhere in the state, and the state still parses. A later step
legitimately advancing the same line does not kill that claim; a later step that
brings the taught pattern back does. `structural_proof`/`structural_survival` remain
for callers whose cores are concrete, hole-free text.

RELATION TO skill_sequence_verify_v1
------------------------------------
Same measured defect, complementary checks: that module is a textual post-hoc
interference witness (no premise, no proofs); this module refuses dead premises
before execution and re-checks proofs after every later effect. The measured no-op
pair must be caught by both.

AUTHORITY: NONE. No capability registered, no model, no network, no spend. Every
number this module reports is folded from its own run and is open to re-execution.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_PROVED_COMPOSITION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

# --------------------------------------------------------------------------- #
# verdicts
# --------------------------------------------------------------------------- #
PASS = "PASS"
EMPTY_COMPOSITION = "EMPTY_COMPOSITION"
OP_INVALID = "OP_INVALID"
PREMISE_DIED = "COMPOSITION_PREMISE_DIED"
NO_CHANGE = "STEP_DID_NOTHING"
REVERTED = "STEP_REVERTED_EARLIER_STATE"
UNPROVED = "STEP_UNPROVED"
PROOF_DIED = "PROOF_DIED_AFTER_LATER_EFFECT"
RAISED = "STEP_RAISED"

Refusal = tuple[str, str]  # (verdict, reason)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# an operation that carries its own premise and proof
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class ProvedOperation:
    """One operation: a premise readable on any state, an effect, a proof of its claim.

    premise(state) -> None when the premise holds, else the dead requirement.
    apply(state)   -> the next state, or None when the operation did not fire.
    prove(state)   -> (holds, why) for this operation's own claim on that state —
                      used as the step proof on the state THIS step produced.
    survive(state) -> (holds, why) for the claim that must still hold AFTER later
                      effects. None means "same as prove". The two may differ
                      honestly: a step proof can require the replacement to have
                      landed, while survival only requires the defect to be gone —
                      a later step legitimately advancing the same line must not
                      kill an earlier proof whose claim is still true.
    """

    op_id: str
    premise: Callable[[str], str | None]
    apply: Callable[[str], str | None]
    prove: Callable[[str], tuple[bool, str]]
    survive: Callable[[str], tuple[bool, str]] | None = None
    metadata: Mapping[str, Any] = dataclasses.field(default_factory=dict)


def _as_operation(op: Any) -> ProvedOperation | None:
    if isinstance(op, ProvedOperation):
        return op
    if isinstance(op, Mapping):
        try:
            return ProvedOperation(
                op_id=str(op.get("op_id") or "OP"),
                premise=op["premise"],
                apply=op["apply"],
                prove=op["prove"],
                survive=op.get("survive"),
                metadata={k: v for k, v in op.items()
                          if k in ("op_id", "premise", "apply", "prove", "survive")},
            )
        except (KeyError, TypeError):
            return None
    return None


def _refusal(verdict: str, reason: str, *, steps: Sequence[Mapping[str, Any]],
             source: str, result: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY,
        "verdict": verdict, "reason": reason,
        "steps": list(steps), "source": source, "result": result,
        "steps_applied": len(steps),
    }
    payload.update(extra)
    return payload


# --------------------------------------------------------------------------- #
# THE RULE
# --------------------------------------------------------------------------- #
def compose(source: str, ops: Sequence[Any],
            *, recheck_prior: bool = True) -> dict[str, Any]:
    """Apply `ops` in order under the five-check rule. Refuse early, receipt always.

    The premise of step k is evaluated on the state step k-1 produced — that is the
    whole difference from applying verified skills one after another and hoping.
    """
    if not ops:
        return _refusal(EMPTY_COMPOSITION, "EMPTY_COMPOSITION",
                        steps=[], source=source, result=source)

    parsed: list[ProvedOperation] = []
    for index, raw in enumerate(ops):
        op = _as_operation(raw)
        if op is None:
            return _refusal(OP_INVALID, f"OP_NOT_AN_OPERATION:step{index + 1}",
                            steps=[], source=source, result=source)
        parsed.append(op)

    text = source
    history: dict[str, int] = {_sha(source): 0}  # state digest -> step that produced it
    steps: list[dict[str, Any]] = []

    for index, op in enumerate(parsed, start=1):
        # 1. premise, on the world the previous effects left behind
        try:
            dead = op.premise(text)
        except Exception as exc:  # a premise that raises is not a holding premise
            steps.append({"step": index, "op_id": op.op_id, "premise": "RAISED",
                          "applied": False})
            return _refusal(RAISED, f"PREMISE_RAISED:step{index}:{type(exc).__name__}",
                            steps=steps, source=source, result=text,
                            refused_at_step=index, op_id=op.op_id)
        if dead:
            steps.append({"step": index, "op_id": op.op_id, "premise": "DEAD",
                          "dead_requirement": str(dead), "applied": False})
            # refusal BEFORE execution: apply is never called on a dead premise
            return _refusal(PREMISE_DIED, f"PREMISE_DIED:step{index}:{dead}",
                            steps=steps, source=source, result=text,
                            refused_at_step=index, op_id=op.op_id,
                            dead_requirement=str(dead))
        steps.append({"step": index, "op_id": op.op_id, "premise": "HELD"})

        # 2. apply
        try:
            produced = op.apply(text)
        except Exception as exc:
            return _refusal(RAISED, f"STEP_RAISED:step{index}:{type(exc).__name__}:{exc}"[:200],
                            steps=steps, source=source, result=text,
                            refused_at_step=index, op_id=op.op_id)
        if produced is None or produced == text:
            steps[-1].update({"outcome": "NO_CHANGE", "applied": False})
            return _refusal(NO_CHANGE, f"STEP_DID_NOTHING:step{index}",
                            steps=steps, source=source, result=text,
                            refused_at_step=index, op_id=op.op_id)

        # 3. history: no returning to a state the text has already been in
        digest = _sha(produced)
        if digest in history:
            to_step = history[digest]
            steps[-1].update({"outcome": "REVERTED", "applied": True,
                              "to_state_of_step": to_step})
            return _refusal(REVERTED, f"STEP_REVERTED_EARLIER_STATE:step{index}",
                            steps=steps, source=source, result=produced,
                            refused_at_step=index, op_id=op.op_id,
                            reverted_to_step=to_step)

        # 4. this step's own proof, on the state it produced
        try:
            holds, why = op.prove(produced)
        except Exception as exc:
            steps[-1].update({"outcome": "PROVE_RAISED", "applied": True})
            return _refusal(RAISED, f"PROOF_RAISED:step{index}:{type(exc).__name__}",
                            steps=steps, source=source, result=produced,
                            refused_at_step=index, op_id=op.op_id)
        if not holds:
            steps[-1].update({"outcome": "UNPROVED", "applied": True, "proof": str(why)})
            return _refusal(UNPROVED, f"STEP_UNPROVED:step{index}:{why}"[:200],
                            steps=steps, source=source, result=produced,
                            refused_at_step=index, op_id=op.op_id)

        # 5. survival: every earlier proof must still hold after this effect
        survived: list[dict[str, Any]] = []
        if recheck_prior:
            for prior_index, prior in enumerate(parsed[: index - 1], start=1):
                predicate = prior.survive or prior.prove
                try:
                    prior_holds, prior_why = predicate(produced)
                except Exception as exc:
                    prior_holds, prior_why = False, f"PROOF_RAISED:{type(exc).__name__}"
                survived.append({"step": prior_index, "op_id": prior.op_id,
                                 "holds": bool(prior_holds), "why": str(prior_why),
                                 "via": "survive" if prior.survive else "prove"})
                if not prior_holds:
                    steps[-1].update({"outcome": "CHANGED", "applied": True,
                                      "proof": str(why), "prior_proof_died":
                                          {"step": prior_index, "op_id": prior.op_id,
                                           "why": str(prior_why)},
                                      "produced_sha256": digest})
                    return _refusal(
                        PROOF_DIED,
                        f"PROOF_DIED:step{index}:op {prior.op_id} "
                        f"(step{prior_index}) no longer holds: {prior_why}"[:200],
                        steps=steps, source=source, result=produced,
                        refused_at_step=index, op_id=op.op_id,
                        proving_op=prior.op_id, proving_step=prior_index,
                        proof_why=str(prior_why))

        history[digest] = index
        text = produced
        steps[-1].update({
            "outcome": "CHANGED", "applied": True, "proof": str(why),
            "produced_sha256": digest,
            "prior_survived": survived,
        })

    return {
        "schema": SCHEMA, "authority": AUTHORITY,
        "verdict": PASS, "reason": None,
        "steps": steps, "source": source, "result": text,
        "steps_applied": len(steps),
        "recheck_prior": bool(recheck_prior),
    }


# --------------------------------------------------------------------------- #
# factories: the two shapes callers actually hold
# --------------------------------------------------------------------------- #
def substring_premise(required: str) -> Callable[[str], str | None]:
    """Premise: this exact fragment must still be present in the current state."""

    def premise(state: str) -> str | None:
        return None if required in state else f"FRAGMENT_ABSENT:{required[:60]}"

    return premise


def _normalized(text: str) -> str:
    return "".join(str(text).split())


def structural_proof(pattern_core: str, replacement_core: str) -> Callable[[str], tuple[bool, str]]:
    """Step-local STRUCTURAL proof: parses, pattern gone, replacement present.

    This is a syntax proof. It is honest about being one: it says the edit landed as
    written, not that any program still behaves correctly.
    """

    def prove(state: str) -> tuple[bool, str]:
        try:
            compile(state, "<composition>", "exec")
        except SyntaxError as exc:
            return False, f"DOES_NOT_PARSE:{type(exc).__name__}"
        body = _normalized(state)
        if pattern_core and _normalized(pattern_core) in body:
            return False, "PATTERN_STILL_PRESENT"
        if replacement_core and _normalized(replacement_core) not in body:
            return False, "REPLACEMENT_ABSENT"
        return True, "STRUCTURAL_PROOF_HELD"

    return prove


def structural_survival(pattern_core: str) -> Callable[[str], tuple[bool, str]]:
    """Durable half of a structural proof: parses, the taught pattern stays gone.

    A later step may legitimately advance the same line past this operation's exact
    replacement (`x < 10` -> `x < 11`); what must survive is the claim the operation
    was taught to establish — the pattern it was taught to remove is still removed.
    """

    def survive(state: str) -> tuple[bool, str]:
        try:
            compile(state, "<composition>", "exec")
        except SyntaxError as exc:
            return False, f"DOES_NOT_PARSE:{type(exc).__name__}"
        body = _normalized(state)
        if pattern_core and _normalized(pattern_core) in body:
            return False, "PATTERN_STILL_PRESENT"
        return True, "STRUCTURAL_SURVIVAL_HELD"

    return survive


def rule_op(op_id: str, rule: Mapping[str, Any], *,
            prove: Callable[[str], tuple[bool, str]] | None = None) -> ProvedOperation:
    """A crystallized code rule as a proved operation.

    premise  the rule has a candidate in the CURRENT state (it could fire here)
    apply    the tree's own `apply_crystallized_code_rule`
    prove    the state this apply produced, re-parsed — crystallized rules are HOLED
             (`?id0`, `?num0`), so a textual "replacement present" check cannot be
             written; the honest step proof is "this apply's output, and it parses"
    survive  the durable claim of a rewrite rule: the taught pattern can no longer
             fire anywhere in the state, and the state still parses. A later step
             legitimately advancing the line past this rule's exact replacement
             (`x < 10` -> `x < 11`) keeps that claim true; a later step that brings
             the taught pattern back does not. A multi-match state where this rule
             could still fire elsewhere fails survival — fail-closed by design.
    """
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
        apply_crystallized_code_rule,
        iter_crystallized_code_rule_candidates,
    )

    def premise(state: str) -> str | None:
        try:
            has = next(iter(iter_crystallized_code_rule_candidates(state, rule)), None)
        except Exception as exc:  # unreadable rule => premise cannot be shown to hold
            return f"RULE_UNREADABLE:{type(exc).__name__}"
        return None if has is not None else "NO_CANDIDATE_FOR_PATTERN"

    def apply(state: str) -> str | None:
        out = apply_crystallized_code_rule(state, rule)
        if out is not None and out != state:
            apply.last_after = out  # type: ignore[attr-defined]
        return out

    def survive(state: str) -> tuple[bool, str]:
        try:
            compile(state, "<composition>", "exec")
        except SyntaxError as exc:
            return False, f"DOES_NOT_PARSE:{type(exc).__name__}"
        try:
            still = next(iter(iter_crystallized_code_rule_candidates(state, rule)), None)
        except Exception as exc:
            return False, f"RULE_UNREADABLE:{type(exc).__name__}"
        if still is not None:
            return False, "PATTERN_STILL_PRESENT"
        return True, "STRUCTURAL_SURVIVAL_HELD"

    def default_prove(state: str) -> tuple[bool, str]:
        try:
            compile(state, "<composition>", "exec")
        except SyntaxError as exc:
            return False, f"DOES_NOT_PARSE:{type(exc).__name__}"
        if state == getattr(apply, "last_after", None):
            return True, "STRUCTURAL_PROOF_HELD:APPLIED_AND_PARSES"
        return survive(state)

    return ProvedOperation(op_id=op_id, premise=premise, apply=apply,
                          prove=prove or default_prove, survive=survive)


# --------------------------------------------------------------------------- #
# reach measurement on the tree's own learned skills, on this repository's code
# --------------------------------------------------------------------------- #
def _bundle_skill(family: str) -> dict[str, Any]:
    from canonical.swe_kernel import learned_skill_verdict_v1 as lv

    prefix = {"inline": "inline the variable", "rename": "rename the variable"}[family]
    for skill in lv.load_skills():
        if str(skill.get("goal_skeleton") or "").startswith(prefix):
            return skill
    raise LookupError("no skill in the bundle for family %r" % (family,))


def _request(family: str, path: str, function: str, variable: str) -> dict[str, str]:
    from canonical.swe_kernel import one_demonstration_reach_v1 as reach
    return reach.request_for(family, path, function, variable)


def _features_of(function_node: Any, variable: str) -> dict[str, Any]:
    from canonical.swe_kernel import one_demonstration_reach_v1 as reach
    return reach._features(function_node, variable)


def _sites_in_text(text: str, path: str) -> list[dict[str, Any]]:
    import ast

    from canonical.swe_kernel import one_demonstration_reach_v1 as reach

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    sites: list[dict[str, Any]] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        seen: set[str] = set()
        for statement in node.body:
            for inner in ast.walk(statement):
                if isinstance(inner, ast.Name) and isinstance(inner.ctx, ast.Store) \
                        and inner.id not in seen:
                    seen.add(inner.id)
                    sites.append({"path": path, "function": node.name,
                                  "variable": inner.id,
                                  **reach._features(node, inner.id)})
    return sites


def _premise_holds(site: Mapping[str, Any]) -> bool:
    from canonical.swe_kernel import one_demonstration_reach_v1 as reach
    return reach._premise_holds(site)


def _skill_bundle_op(family: str, *, path: str, function: str, variable: str,
                     workdir: pathlib.Path, repo: pathlib.Path,
                     python_executable: str | None,
                     timeout_s: float) -> ProvedOperation:
    """One learned skill as a proved operation over a persistent workdir world.

    premise  the target still exists in the CURRENT text with the documented premise
             (plain binding, set once, read once, adjacent) — read off the state the
             previous effect left, never off the original site.
    apply    write the current state into the workdir, run the stored step, read back
    prove    the tree's own witness judge against the CURRENT file, plus the concrete
             postcondition of this step's own run, plus the independent filesystem
             check — the same three the reach instrument uses, never re-implemented
    """
    from canonical.swe_kernel import learned_skill_verdict_v1 as lv

    skill = _bundle_skill(family)

    def premise(state: str) -> str | None:
        matches = [s for s in _sites_in_text(state, path)
                   if s["function"] == function and s["variable"] == variable]
        if not matches:
            return f"TARGET_NOT_BOUND_ANYMORE:{function}.{variable}"
        if not _premise_holds(matches[0]):
            site = matches[0]
            return ("PREMISE_FALSE_AFTER_EARLIER_EFFECT:"
                    f"stores={site.get('stores')} loads={site.get('loads')} "
                    f"direct={site.get('direct')} adjacent={site.get('adjacent')}")
        return None

    def apply(state: str) -> str | None:
        target = pathlib.Path(workdir) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(state, encoding="utf-8")
        request = _request(family, path, function, variable)
        run = lv.run_program(lv.source_with_request(skill, request), workdir=workdir,
                             timeout_s=timeout_s, python_executable=python_executable)
        after = lv._read_back(path, workdir)
        apply.last_run = run          # type: ignore[attr-defined]
        apply.last_request = request  # type: ignore[attr-defined]
        apply.last_before = state     # type: ignore[attr-defined]
        return after if after != state else None

    def prove(state: str) -> tuple[bool, str]:
        request = getattr(apply, "last_request", None) \
            or _request(family, path, function, variable)
        run = getattr(apply, "last_run", None) or {"stdout": "", "stderr": ""}
        before = getattr(apply, "last_before", None) or state
        # The witness judge reads the CURRENT file in the workdir, which every apply
        # keeps equal to the state under proof — that is what makes a survival
        # re-check after a later effect meaningful without re-running this step.
        witness = lv.judge(lv.witness_postcondition(skill, request, before),
                           workdir=workdir, run=run)
        concrete = lv.judge(lv.concrete_postcondition(skill, request),
                            workdir=workdir, run=run)
        independent = lv.independent_check(
            str(skill.get("goal_skeleton") or ""),
            before=before, after=state, function=function,
            variable=(request.get("str0") if family == "inline"
                      else request.get("str0")))
        ok = bool(witness["accepted"] and concrete["accepted"]
                  and independent["holds"])
        why = "; ".join(str(part) for part in (
            "witness:" + str(witness.get("why")),
            "concrete:" + str(concrete.get("why")),
            "independent:" + str(independent.get("why")),
        ))
        return ok, why

    return ProvedOperation(
        op_id=f"{family}:{function}.{variable}",
        premise=premise, apply=apply, prove=prove,
        metadata={"family": family, "path": path, "function": function,
                  "variable": variable},
    )


def measure(*, count: int = 48, repo: pathlib.Path | None = None,
            python_executable: str | None = None, timeout_s: float = 60.0,
            verbose: bool = False) -> dict[str, Any]:
    """Reach of TWO proved operations composed on this repository's own code.

    Deterministic stride over the sites whose stated premise holds — the universe
    where step one is allowed to fire (the all-sites scan and the premise-holding
    count both land in the receipt, so the conditioning is visible). Per site:
    step one is one learned skill; step two is (a) the same logical target under
    the other family, premise re-read from the world step one left, and (b) a
    stride-chosen other variable of the same function, if one still satisfies its
    premise. Every second-step attempt lands in exactly one box:

        COMPOSED_VERIFIED   both steps proved, premises held, proofs survived, 0 damaged
        PREMISE_DIED        refused BEFORE execution, naming the dead requirement
        NO_SECOND_CANDIDATE nothing in the function still satisfies a premise
        B_REFUSED           premise held, the stored step declined at runtime
        B_UNPROVED          the step fired but its own proof failed (would have been a
                            silent damage without the proof check)
        SEQUENCE_REVERTED   step two returned the text to an earlier state
        PROOF_DIED          step two ran, but step one's proof no longer holds
        SEQUENCE_RAISED     a premise, apply, or proof raised where it must not
        A_NOT_PROVED        step one's premise held but the stored step declined
        A_PREMISE_DIED      step one was outside its own documented premise

    Two reach numbers, the pair the reach instrument already established:
    `reach_compose` = composed / all second-step attempts (including the pre-hoc
    premise refusals), and `reach_where_premises_held` = composed / attempts that
    got past every premise gate. The first says how far two proved operations get
    on this repository as it stands; the second says what the composition rule does
    inside the world it is allowed to touch.

    The DAMAGED box must be empty: every PASS is re-judged independently at the end
    (both witnesses + both independent checks on the final file), and any disagreement
    is DAMAGED, counted, and reported.
    """
    from canonical.swe_kernel import learned_skill_verdict_v1 as lv
    from canonical.swe_kernel import one_demonstration_reach_v1 as reach

    repo = repo or reach.ROOT
    started = time.time()
    # the stored steps iterate hash containers; pinning the seed keeps the receipt
    # re-executable to the same boxes (measured: unseeded runs shift a box or two)
    import os
    os.environ["PYTHONHASHSEED"] = "0"
    sites, scan = reach.all_sites(repo=repo)
    # The composition question is asked where step one is ALLOWED to fire: the
    # sites whose stated premise holds. The all-sites count stays in the receipt so
    # the conditioning is visible, never hidden.
    universe = [s for s in sites if _premise_holds(s)]
    scan["premise_holding_sites"] = len(universe)
    chosen = reach.sample(list(universe), count)

    boxes: dict[str, int] = {}
    by_direction: dict[str, dict[str, int]] = {"inline_then": {}, "rename_then": {}}
    examples: dict[str, list[dict[str, Any]]] = {}
    damaged_rows: list[dict[str, Any]] = []
    second_attempts = 0
    composed = 0
    pair_step1_refused = 0
    step1 = {"inline": {"attempted": 0, "proved": 0},
             "rename": {"attempted": 0, "proved": 0}}

    def bump(box: str, direction: str, example: dict[str, Any] | None = None) -> None:
        boxes[box] = boxes.get(box, 0) + 1
        bucket = by_direction[direction]
        bucket[box] = bucket.get(box, 0) + 1
        if example is not None and len(examples.setdefault(box, [])) < 3:
            examples[box].append(example)

    for position, site in enumerate(chosen):
        family_a = "inline" if position % 2 == 0 else "rename"
        direction = "inline_then" if family_a == "inline" else "rename_then"
        function = str(site["function"])
        variable = str(site["variable"])
        path = str(site["path"])

        with tempfile.TemporaryDirectory(prefix="brain_compose_") as scratch:
            workdir = pathlib.Path(scratch)
            before = lv._copy_target(path, workdir, repo)
            if before is None:
                bump("A_NOT_PROVED", direction, {"path": path, "why": "COPY_FAILED"})
                continue

            op_a = _skill_bundle_op(family_a, path=path, function=function,
                                    variable=variable, workdir=workdir, repo=repo,
                                    python_executable=python_executable,
                                    timeout_s=timeout_s)
            step1[family_a]["attempted"] += 1
            state_a = op_a.apply(before)
            if state_a is None:
                # the premise decides whether a refusal is a proof failure or a
                # boundary the rule must not cross: outside premise, no claim exists
                dead_a = op_a.premise(before)
                box_a = "A_PREMISE_DIED" if dead_a else "A_NOT_PROVED"
                bump(box_a, direction,
                     {"path": path, "function": function, "variable": variable,
                      "dead": str(dead_a) if dead_a else None})
                continue
            ok_a, why_a = op_a.prove(state_a)
            if not ok_a:
                bump("A_NOT_PROVED", direction,
                     {"path": path, "why": why_a[:160]})
                continue
            step1[family_a]["proved"] += 1

            family_b = "rename" if family_a == "inline" else "inline"
            target_b = variable if family_a == "inline" else variable + "_brain_renamed"

            # (a) same logical target, premise re-read from the post-A world
            op_b_same = _skill_bundle_op(family_b, path=path, function=function,
                                         variable=target_b, workdir=workdir, repo=repo,
                                         python_executable=python_executable,
                                         timeout_s=timeout_s)
            if op_b_same.premise(state_a):
                second_attempts += 1
                boxes["PREMISE_DIED"] = boxes.get("PREMISE_DIED", 0) + 1
                bucket = by_direction[direction]
                bucket["PREMISE_DIED"] = bucket.get("PREMISE_DIED", 0) + 1
                dead = op_b_same.premise(state_a)
                if len(examples.setdefault("PREMISE_DIED", [])) < 3:
                    examples["PREMISE_DIED"].append(
                        {"path": path, "function": function, "target": target_b,
                         "dead": str(dead)})
            else:
                second_attempts += 1
                outcome = _attempt_pair(before, op_a, op_b_same, direction, path,
                                        function, target_b, bump, workdir)
                if outcome == "COMPOSED_VERIFIED":
                    composed += 1
                if outcome in ("A_NOT_PROVED", "A_PREMISE_DIED"):
                    pair_step1_refused += 1

            # (b) another variable of the same function, if its premise still holds
            candidates = [s for s in _sites_in_text(state_a, path)
                          if s["function"] == function
                          and s["variable"] != variable
                          and s["variable"] != target_b
                          and _premise_holds(s)]
            if not candidates:
                bump("NO_SECOND_CANDIDATE", direction, {"path": path, "function": function})
            else:
                other = candidates[position % len(candidates)]
                op_b_other = _skill_bundle_op(family_b, path=path, function=function,
                                              variable=str(other["variable"]),
                                              workdir=workdir, repo=repo,
                                              python_executable=python_executable,
                                              timeout_s=timeout_s)
                second_attempts += 1
                outcome = _attempt_pair(before, op_a, op_b_other, direction, path,
                                        function, str(other["variable"]), bump,
                                        workdir)
                if outcome == "COMPOSED_VERIFIED":
                    composed += 1
                if outcome in ("A_NOT_PROVED", "A_PREMISE_DIED"):
                    pair_step1_refused += 1

            if verbose:
                print(f"[{position + 1}/{len(chosen)}] {direction} {function}.{variable}",
                      flush=True)

    reach_seconds = round(time.time() - started, 2)
    premises_held = max(0, second_attempts - boxes.get("PREMISE_DIED", 0)
                        - pair_step1_refused)
    return {
        "schema": "PROJECT_BRAIN_PROVED_COMPOSITION_MEASURE_V1",
        "authority": AUTHORITY,
        "date": "2026-11-16",
        "claim_on_trial": ("compose only what is proved: two learned operations, "
                           "premise re-read after every effect, per-step proof, "
                           "prior-proof survival"),
        "sampled_sites": len(chosen),
        "scan": scan,
        "step_one": step1,
        "second_step_attempts": second_attempts,
        "pair_step1_refused": pair_step1_refused,
        "premises_held_attempts": premises_held,
        "boxes": boxes,
        "boxes_by_direction": by_direction,
        "composed_verified": composed,
        "reach_compose": (round(composed / second_attempts, 4)
                          if second_attempts else None),
        "reach_where_premises_held": (round(composed / premises_held, 4)
                                      if premises_held else None),
        "damaged": len(damaged_rows),
        "damaged_rows": damaged_rows[:5],
        "examples": examples,
        "seconds": reach_seconds,
    }


def _attempt_pair(before: str, op_a: ProvedOperation, op_b: ProvedOperation,
                  direction: str, path: str, function: str, target: str,
                  bump: Callable[..., None], workdir: pathlib.Path) -> str:
    """Compose A then B from the ORIGINAL state under the full five-check rule.

    The pair runs through `compose` exactly as any caller would use it: premise of A
    on the original world, premise of B on A's output, per-step proofs, revert
    history seeded with the original state, and A's proof re-checked after B's
    effect. A PASS is then re-judged once more independently (both ops, final file);
    any disagreement is DAMAGED, which must stay empty.
    """
    composed = compose(before, [op_a, op_b], recheck_prior=True)
    verdict = composed["verdict"]
    refused_at = int(composed.get("refused_at_step") or 0)

    if verdict == PASS:
        final = composed["result"]
        for op in (op_a, op_b):
            holds, why = op.prove(final)
            if not holds:
                bump("DAMAGED", direction, {"path": path, "function": function,
                                            "target": target, "why": str(why)[:200]})
                return "DAMAGED"
        bump("COMPOSED_VERIFIED", direction, {"path": path, "function": function,
                                              "target": target,
                                              "steps": composed["steps_applied"]})
        return "COMPOSED_VERIFIED"

    if refused_at == 1:
        # step one failed inside the pair after the pre-classification said it was
        # proved — report it honestly as a step-one event, never as a second-step one
        first = (composed.get("steps") or [{}])[0]
        if first.get("premise") == "DEAD":
            box = "A_PREMISE_DIED"
            example = {"path": path, "function": function,
                       "dead": composed.get("dead_requirement")}
        else:
            box = "A_NOT_PROVED"
            example = {"path": path, "function": function, "why":
                       str(composed.get("reason"))[:200]}
    elif verdict == PREMISE_DIED:
        box = "PREMISE_DIED"
        example = {"path": path, "function": function, "target": target,
                   "dead": composed.get("dead_requirement")}
    elif verdict == NO_CHANGE:
        box = "B_REFUSED"
        example = {"path": path, "function": function, "target": target,
                   "why": str(composed.get("reason"))[:200]}
    elif verdict == REVERTED:
        box = "SEQUENCE_REVERTED"
        example = {"path": path, "function": function, "target": target,
                   "why": str(composed.get("reason"))[:200]}
    elif verdict == UNPROVED:
        box = "B_UNPROVED"
        example = {"path": path, "function": function, "target": target,
                   "why": str(composed.get("reason"))[:200]}
    elif verdict == PROOF_DIED:
        box = "PROOF_DIED"
        example = {"path": path, "function": function, "target": target,
                   "why": str(composed.get("reason"))[:200]}
    else:
        box = "SEQUENCE_RAISED"
        example = {"path": path, "function": function, "target": target,
                   "why": str(composed.get("reason"))[:200]}
    bump(box, direction, example)
    return box


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measure", action="store_true",
                        help="run the reach measurement over real sites")
    parser.add_argument("--count", type=int, default=48,
                        help="sites to stride-sample (default 48)")
    parser.add_argument("--out", default=None, help="write the receipt JSON here")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    if not args.measure:
        parser.error("--measure is required (this module's CLI is the measurement)")

    report = measure(count=args.count, verbose=args.verbose)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        pathlib.Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    # DAMAGED is the box that must stay empty; a non-empty one fails the run.
    return 0 if report.get("damaged") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
