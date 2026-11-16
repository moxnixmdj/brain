#!/usr/bin/env python3
"""Which repair? Ask the one question the tests did not.

THE DEFECT THIS CLOSES
----------------------
`closed_loop_trace_abduction_repair_v1` returns *the first candidate that passes
the tests*. Measured on 19 scored HumanEvalFix bugs (2026-11-16, this tree):

    candidates that pass the same tests, partitioned by behaviour on 8-120
    unlabelled inputs:
      reference behaviour present among them ..................... 11/16
      tests leave >= 2 distinct behaviours ........................ 4/16
      of those, the reference behaviour is present ................ 4/4
      returned candidate already equals the reference ............ 9/16
      wrong for a reason NO question can fix ...................... 5/16
        (the generator never proposed the right behaviour)

and, decisively, when a first-passing candidate disagreed with the reference,
MAJORITY VOTE AMONG THE CANDIDATES PICKED THE WRONG ONE **3 times in 5**
(Python/3 4/5 majority wrong; Python/101 5/6 majority wrong).

So "just show it once and it is solved" fails in two separable ways, and they
need different cures:

  SELECTION  the tests do not identify the repair, but the right behaviour is
             already in the candidate set. A question with a *known answer*
             settles it. Majority/self-consistency cannot: it is measured to be
             worse than random here.
  SYNTHESIS  the right behaviour is not in the set at all. No question helps;
             the hypothesis space itself is insufficient.

This module implements only SELECTION, because that is the part that is a real
mechanism rather than more search. It never guesses and never votes.

WHAT IT DOES
------------
  partition(candidates, probes)      behaviour equivalence classes over
                                     UNLABELLED inputs (inputs are data;
                                     no label is used to build the partition)
  diagnose                          one of:
        IDENTIFIED_BY_TESTS            1 class
        UNDETERMINED__A_QUESTION_DECIDES  >=2 classes
        (the third outcome -- right behaviour absent -- is not visible from
         inside and must never be asserted; the caller compares against an
         oracle, or does not know)
  decide(classes, observations)      filter the version space with each labelled
                                     answer; ACCEPT only when one class remains;
                                     ASK naming the cheapest discriminating
                                     input when several do; REFUSE otherwise.

It reuses `canonical.runtime.finite_identifiability` -- the tree's existing
exact finite version-space kernel -- so the "which question to ask" rule is the
one the project already proved for finite hypothesis spaces, not a new one.

AUTHORITY: NONE. This grants no capability and no benchmark credit. Bounded by
the probe library it is given: a class that no supplied probe splits is not
proved equal, only unsplit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime.finite_identifiability import (
    Experiment,
    Hypothesis,
    equivalence_classes,
    filter_version_space,
    select_discriminator,
)

SCHEMA = "PROJECT_BRAIN_REPAIR_VERSION_SPACE_SELECTION_V1"

ACCEPT = "ACCEPT"
ASK = "ASK"
REFUSE = "REFUSE"

# Dispositions of a selection attempt. The distinction is the whole point: a
# single behaviour class is NOT evidence that the behaviour is right -- it is
# equally consistent with every candidate being wrong the same way (measured:
# Python/3 and Python/101 both had one class and a wrong majority). Only a class
# that SURVIVED a question has been chosen by evidence.
SETTLED = "SETTLED_BY_QUESTION"          # an answer eliminated the alternatives, one left
SETTLED_TO_A_CLASS = "SETTLED_TO_A_BEHAVIOUR_CLASS"  # an answer picked a class; its >1 members
                                                     # are identical on every probe supplied
UNSEPARATED = "UNSEPARATED__NO_INPUT_TOLD_THEM_APART"   # nothing we could construct split them


def _outcome_key(outcome: Any) -> str:
    """A behaviour observation as a stable string. `("value", repr)` and
    `("raised", Name)` are already strings; anything else is refused rather
    than guessed at. An already-normalised key passes through, so a caller can
    hand back keys it received from this function."""
    if isinstance(outcome, str) and outcome:
        return outcome
    if not isinstance(outcome, Sequence) or isinstance(outcome, (str, bytes)) or not outcome:
        raise ValueError("OUTCOME_INVALID")
    kind = str(outcome[0])
    if kind in ("value", "raised", "late"):
        return kind if len(outcome) == 1 else f"{kind}:{outcome[1]}"
    raise ValueError(f"OUTCOME_KIND_INVALID:{kind}")


def partition(candidate_ids: Sequence[str],
              behaviours: Mapping[str, Sequence[Any]]) -> dict[str, Any]:
    """Behaviour equivalence classes over the candidate set.

    `behaviours[candidate_id]` is the outcome vector on the probe library, in a
    fixed order. Two candidates are in the same class exactly when every supplied
    probe gives them the same outcome. Classes are keyed by representative id.

    Returns {classes: [[ids...]...], class_of: {id: index}, distinct: int,
             split: bool, schema}. A failure to supply every vector is refused --
    a partially observed candidate cannot be placed, and placing it by default
    would be the same guess this module exists to remove.
    """
    ids = [str(c) for c in candidate_ids]
    if not ids:
        return {"schema": SCHEMA, "status": "REFUSED", "reason": "NO_CANDIDATES",
                "classes": [], "class_of": {}, "distinct": 0, "split": False}
    missing = [i for i in ids if i not in behaviours]
    if missing:
        return {"schema": SCHEMA, "status": "REFUSED", "reason": "BEHAVIOUR_MISSING",
                "missing": missing[:5], "classes": [], "class_of": {},
                "distinct": 0, "split": False}
    lengths = {len(behaviours[i]) for i in ids}
    if len(lengths) != 1:
        return {"schema": SCHEMA, "status": "REFUSED", "reason": "PROBE_VECTORS_UNEQUAL_LENGTH",
                "lengths": sorted(lengths), "classes": [], "class_of": {},
                "distinct": 0, "split": False}
    if lengths == {0}:
        return {"schema": SCHEMA, "status": "REFUSED", "reason": "NO_PROBES",
                "classes": [], "class_of": {}, "distinct": 0, "split": False}

    signatures: dict[tuple[str, ...], list[str]] = {}
    for cid in ids:
        try:
            sig = tuple(_outcome_key(o) for o in behaviours[cid])
        except ValueError as exc:
            return {"schema": SCHEMA, "status": "REFUSED", "reason": str(exc),
                    "classes": [], "class_of": {}, "distinct": 0, "split": False}
        signatures.setdefault(sig, []).append(cid)

    classes = sorted(signatures.values(), key=lambda c: (-len(c), c[0]))
    class_of: dict[str, int] = {}
    for index, members in enumerate(classes):
        for cid in members:
            class_of[cid] = index
    return {
        "schema": SCHEMA,
        "status": "OK",
        "classes": classes,
        "class_of": class_of,
        "distinct": len(classes),
        "split": len(classes) > 1,
        "members": {cid: len(members) for cid, members in
                    ((c[0], c) for c in classes)},
        "probes": lengths.pop(),
    }


def diagnose(part: Mapping[str, Any]) -> dict[str, Any]:
    """What the tests + probe library have established so far."""
    if part.get("status") != "OK":
        return {"schema": SCHEMA, "verdict": "REFUSED",
                "reason": part.get("reason", "PARTITION_NOT_OK")}
    if not part["split"]:
        return {"schema": SCHEMA, "verdict": "IDENTIFIED_BY_TESTS",
                "distinct": 1, "candidates": sum(len(c) for c in part["classes"]),
                # one class over the probes supplied -- NOT proved equal in general
                "bounded_by": "THE_PROBE_LIBRARY_SUPPLIED"}
    return {"schema": SCHEMA, "verdict": "UNDETERMINED__A_QUESTION_DECIDES",
            "distinct": part["distinct"],
            "largest_class": max(len(c) for c in part["classes"]),
            "candidates": sum(len(c) for c in part["classes"])}


# --------------------------------------------------------------------------- #
# One labelled question: reuse the project's exact finite kernel
# --------------------------------------------------------------------------- #

def _experiments(part: Mapping[str, Any], probe_outcomes: Mapping[str, Sequence[str]],
                 probe_ids: Sequence[str]) -> tuple[list[Hypothesis], list[Experiment]]:
    """Each surviving behaviour class is one hypothesis; each probe that splits it
    is one experiment whose outcome model is the class's observed outcome."""
    hypotheses = [Hypothesis(hypothesis_id=f"class:{i}")
                  for i in range(len(part["classes"]))]
    experiments: list[Experiment] = []
    for probe in probe_ids:
        if probe not in probe_outcomes:
            continue
        outcomes = {f"class:{i}": _outcome_key(probe_outcomes[probe][i])
                    for i in range(len(part["classes"]))}
        experiments.append(Experiment(experiment_id=str(probe), outcomes=outcomes))
    return hypotheses, experiments


def decide(part: Mapping[str, Any], *,
           probe_ids: Sequence[str] | None = None,
           probe_outcomes: Mapping[str, Sequence[str]] | None = None,
           observations: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Filter the version space with the labelled answers received so far.

    * one class left            -> ACCEPT that class's representative (the caller
                                  must still verify in a fresh process)
    * several, a probe splits   -> ASK, naming a probe whose answer must eliminate
                                  something (never a probe that cannot)
    * several, nothing splits   -> REFUSE, naming the unsplittable classes. This is
                                  the honest "the tests plus every input I can
                                  think of cannot tell these apart" answer.

    `observations` maps a probe id to the outcome key the ORACLE returned. Nothing
    here invents a label; an observation for an unknown probe fails closed inside
    the kernel.
    """
    if part.get("status") != "OK":
        return {"schema": SCHEMA, "decision": REFUSE, "reason": part.get("reason")}
    if not part["split"]:
        return {"schema": SCHEMA, "decision": ACCEPT, "class": part["classes"][0],
                "reason": "ONE_BEHAVIOUR_OVER_THE_PROBE_LIBRARY",
                "bounded_by": "THE_PROBE_LIBRARY_SUPPLIED"}
    if probe_outcomes is None or probe_ids is None:
        return {"schema": SCHEMA, "decision": REFUSE,
                "reason": "NO_PROBE_OUTCOMES_TO_ASK_WITH",
                "classes": part["classes"]}

    hypotheses, experiments = _experiments(part, probe_outcomes, probe_ids)
    answer = select_discriminator(hypotheses, experiments, observations or {})
    status = answer.get("status")

    if status == "RESOLVED":
        remaining = answer["remaining_hypotheses"]
        index = int(remaining[0].split(":", 1)[1])
        return {"schema": SCHEMA, "decision": ACCEPT, "class": part["classes"][index],
                "reason": "THE_OBSERVATIONS_LEFT_ONE_BEHAVIOUR",
                "kernel": status, "terminal_authority": False}
    if status == "SELECT_EXPERIMENT":
        index = int(answer["experiment_id"]) if answer["experiment_id"].isdigit() else None
        return {"schema": SCHEMA, "decision": ASK,
                "probe": index,
                "probe_id": answer["experiment_id"],
                "classes_left": len(answer["remaining_hypotheses"]),
                "worst_case_remaining": answer["worst_case_remaining"],
                "objective": answer["objective"],
                "kernel": status, "terminal_authority": False}
    if status in ("NONIDENTIFIABLE_UNDER_AUTHORIZED_EXPERIMENTS", "REDUCED"):
        return {"schema": SCHEMA, "decision": REFUSE,
                "reason": status,
                "classes": answer.get("equivalence_classes") or answer.get("remaining_hypotheses"),
                "note": "no supplied input separates the survivors; this is a "
                        "witness relative to the probes given, not a proof of equality",
                "kernel": status, "terminal_authority": False}
    return {"schema": SCHEMA, "decision": REFUSE,
            "reason": str(answer.get("status") or status),
            "errors": answer.get("errors"), "kernel": status}


# --------------------------------------------------------------------------- #
# End to end: candidates that pass the tests -> one admissible answer, or a
# refusal that names what is missing.
# --------------------------------------------------------------------------- #

@dataclass
class Selection:
    """The result of asking. `accepted` is a candidate id or None; `candidate` is
    the source the caller should verify, and is None exactly when we refuse.

    `disposition` is the part that must not be flattened:
      SETTLED_BY_QUESTION                     an oracle answer eliminated the rest
      UNSEPARATED__NO_INPUT_TOLD_THEM_APART    one class: no input we could build
                                              split the candidates, and that says
                                              nothing about whether they are right
    """
    decision: str
    accepted: str | None = None
    candidate: str | None = None
    question: dict[str, Any] | None = None
    refused_because: str | None = None
    disposition: str = ""
    class_size: int = 0
    rounds: int = 0
    trace: list[dict[str, Any]] = field(default_factory=list)

    def as_record(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "decision": self.decision,
                "disposition": self.disposition,
                "accepted_id": self.accepted,
                "class_size": self.class_size,
                "question": self.question,
                "refused_because": self.refused_because,
                "rounds": self.rounds,
                "trace": self.trace,
                "terminal_authority": False}


def ask_until_settled(sources: Mapping[str, str],
                      probe_ids: Sequence[str],
                      behaviour_of: "Any",
                      oracle: "Any",
                      *,
                      max_questions: int = 3) -> Selection:
    """Ask the fewest labelled questions that settle which repair to ship.

    sources        candidate id -> source text
    probe_ids      the FREE library; ordering is fixed
    behaviour_of   (source, probe_id) -> outcome tuple, from an unlabelled run
    oracle         (probe_id) -> outcome tuple for the REFERENCE behaviour. This is
                   the only place information from outside the candidate set enters,
                   and it is the single thing the "learn it once, permanently" plan
                   silently assumes it already has.

    Returns ACCEPT with the candidate, or REFUSE naming why. Never guesses, never
    votes, never reports a class it did not observe.
    """
    ids = list(sources)
    vectors = {cid: [behaviour_of(sources[cid], p) for p in probe_ids] for cid in ids}
    part = partition(ids, vectors)
    if part.get("status") != "OK":
        return Selection(REFUSE, refused_because=f"PARTITION:{part.get('reason')}",
                         disposition=UNSEPARATED)

    observations: dict[str, str] = {}
    trace: list[dict[str, Any]] = [diagnose(part)]
    probe_outcomes = {str(i): [vectors[part["classes"][k][0]][i] for k in range(part["distinct"])]
                      for i in range(len(probe_ids))}
    # re-partition progressively: each answer can only merge observations, never
    # move a candidate between classes, so the class table stays valid.
    for round_index in range(max_questions):
        step = decide(part, probe_ids=[str(i) for i in range(len(probe_ids))],
                      probe_outcomes=probe_outcomes,
                      observations=observations)
        trace.append(step)
        if step["decision"] == ACCEPT:
            members = step.get("class") or []
            chosen = members[0] if members else None
            # A single class is only evidence when a question was paid for. With
            # no observation at all it is the "they all agree" case, which is
            # equally the "they all agree and are all wrong" case.
            if not observations:
                disposition = UNSEPARATED
            elif len(members) == 1:
                disposition = SETTLED
            else:
                disposition = SETTLED_TO_A_CLASS
            return Selection(ACCEPT, accepted=chosen,
                             candidate=sources.get(chosen) if chosen else None,
                             disposition=disposition, class_size=len(members),
                             rounds=round_index, trace=trace)
        if step["decision"] != ASK:
            return Selection(REFUSE, refused_because=str(step.get("reason")),
                             disposition=UNSEPARATED,
                             rounds=round_index, trace=trace)
        index = step["probe_id"]
        local = int(index)
        observations[index] = _outcome_key(oracle(probe_ids[local]))
    return Selection(REFUSE, refused_because="QUESTIONS_EXHAUSTED",
                     disposition=UNSEPARATED,
                     rounds=max_questions, trace=trace)
