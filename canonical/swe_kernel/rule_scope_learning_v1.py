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
# it. `SCOPE_SEMANTIC` is deliberately absent: no module realizes "same meaning, different
# shape", so offering it as a hypothesis would be a fabrication.
SCOPE_HYPOTHESES: tuple[Hypothesis, ...] = (
    Hypothesis("SCOPE_STATEMENT", frozenset({"crystallizer.recall"})),
    Hypothesis("SCOPE_OPERATOR", frozenset({"crystallizer.recall", "operator_generalization"})),
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

    raise ScopeLearningError(f"UNKNOWN_SCOPE_HYPOTHESIS:{hypothesis_id}")


def observed_outcome(rule: Mapping[str, Any], instance: Mapping[str, Any],
                     verifier: Callable[[str], bool] | None = None) -> str:
    """What actually happens when the machine tries this instance with every mechanism it has.

    This must be independent of the hypothesis under test, or the version space would be
    reasoning about its own predictions. So it runs the whole available repertoire -- statement
    recall first, then operator generalization -- and reports the best outcome reached.
    """
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
    if PROPOSES_UNVERIFIED in (statement, operator):
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

        chosen = select_probe(hyp, probes)
        if chosen.get("status") != "SELECT":
            break
        pid = str(chosen["probe_id"])
        idx = by_id[pid]
        instance = instances[idx]

        # The prediction is not the observation: run the real mechanisms and trust only the
        # caller's verifier.
        observed = observed_outcome(rule, instance, verifier)

        chosen_probe = next(p for p in probes if p.probe_id == pid)
        step = update_version_space(hyp, chosen_probe, observed)
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
