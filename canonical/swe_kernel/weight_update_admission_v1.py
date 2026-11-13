#!/usr/bin/env python3
"""A weight update is admitted by what it does to inputs it was not trained on.

THE HOLE THIS CLOSES, MEASURED FIRST
------------------------------------
This tree has exactly one weight-space learner: `OnlineParametricPolicyModel` in
`semantic_generalization_engine_v1` -- three linear heads over hashed text features, one gradient
step per verified experience. `solve_task` calls it after a verified answer and keeps the receipt.

The receipt measures `pre_loss` and `post_loss` **on the goal it just trained on**. Measured on
this machine, 2026-11-13, a stream of 32 verified goals whose labels come from the independent
typed parser (`parse_task`), one step each, exactly as the engine calls it:

    every one of the 32 receipts reported loss_delta > 0 and a non-zero ||dW||
    agreement with the parser at the end: 5 of 32
    goals that were predicted CORRECTLY and became WRONG during the stream: 3

So thirty-two updates each certified themselves successful, and the layer ended up agreeing with
the tree's own symbolic parser on 16% of the stream while breaking three predictions it already
had right. Nothing in the receipt can see that, because nothing in the receipt looks at a second
input. This is the weight-space twin of the token-space hole closed in
`lesson_admission_gate_v1`: permanence granted by a check that only ever saw the demonstration.

WHAT THIS DOES
--------------
The candidate step is applied to a **copy** of the heads. Agreement with the typed parser is
measured before and after on goals that are NOT the training goal, split into goals already
trained on (archive) and goals not yet seen (transfer). The live weights are touched only if the
candidate gained somewhere and lost nothing.

    ADMIT    gained >= 1, lost == 0            the caller may keep the step
    REFINE   gained == 0, lost == 0            nothing measured; do not keep it
    REJECT   lost >= 1                         it broke a prediction that was already right
    REFUSED  no probes / label outside the head's vocabulary / probe is the training goal

WHY THE PARSER IS THE JUDGE
---------------------------
The heads are a corroborator, not the answerer: `solve_task` answers from the typed AST and the
executed program. So the honest question for a weight step is whether the parametric layer moved
toward or away from the symbolic layer on inputs it was not trained on. The label is re-derived
with `parse_task` here, never taken from the head, and never taken from a stored claim.

WHAT THIS IS NOT
----------------
Not LLM fine-tuning. These are three small linear heads; the finding is about the **gate**, not
about how a 70B model behaves under LoRA. Not a capability, not a receipt with authority, and not
a proof: `whole_capability_proved` stays False and agreement is bounded by the probes supplied.
It also does not make the head useful faster -- refusing steps trades reach for precision, and the
measurement tool reports both arms so the trade is visible instead of implied.

Authority: NONE. Sandbox measurement, zero model calls, $0.
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SCHEMA = "PROJECT_BRAIN_WEIGHT_UPDATE_ADMISSION_V1"

ADMIT = "ADMIT"
REFINE = "REFINE"
REJECT = "REJECT"
REFUSED = "REFUSED"

ARCHIVE = "ARCHIVE"
TRANSFER = "TRANSFER"


@dataclass(frozen=True)
class Probe:
    """A goal with the label the SYMBOLIC parser gives it, and where it came from."""

    goal: str
    operation: str
    concept: str
    domain: str
    role: str = TRANSFER


def _vocab():
    from canonical.swe_kernel.semantic_generalization_engine_v1 import (
        ALL_CONCEPTS, DOMAINS, OPERATIONS,
    )

    return OPERATIONS, ALL_CONCEPTS, DOMAINS


def label_is_in_vocabulary(operation: str, concept: str, domain: str) -> bool:
    ops, concepts, domains = _vocab()
    return operation in ops and concept in concepts and domain in domains


def probes_from_goals(
    goals: Iterable[str],
    *,
    exclude: str = "",
    archive_goals: Iterable[str] = (),
) -> dict[str, Any]:
    """Re-derive each label with the parser. Goals it cannot type are named, not guessed."""
    from canonical.swe_kernel.semantic_generalization_engine_v1 import parse_task

    archive = set(archive_goals)
    kept: list[Probe] = []
    refused: list[dict[str, str]] = []
    seen: set[str] = set()
    for goal in goals:
        text = str(goal).strip()
        if not text or text == exclude.strip() or text in seen:
            continue
        seen.add(text)
        task = parse_task(text)
        if not label_is_in_vocabulary(task.operation, task.concept, task.domain):
            refused.append({"goal": text, "reason": "PARSER_LABEL_OUTSIDE_HEAD_VOCABULARY",
                            "operation": task.operation, "concept": task.concept,
                            "domain": task.domain})
            continue
        kept.append(Probe(text, task.operation, task.concept, task.domain,
                          ARCHIVE if text in archive else TRANSFER))
    return {"probes": kept, "refused": refused}


def _shadow(model: Any) -> Any:
    """A copy whose weight matrices are private, and which cannot write a state file."""
    shadow = copy.copy(model)
    shadow.W_op = [list(row) for row in model.W_op]
    shadow.W_concept = [list(row) for row in model.W_concept]
    shadow.W_domain = [list(row) for row in model.W_domain]
    shadow.state_path = None
    return shadow


def _correct(model: Any, probes: Sequence[Probe]) -> set[str]:
    right: set[str] = set()
    for probe in probes:
        pred = model.predict(probe.goal)
        if (pred["best_operation"], pred["best_concept"], pred["best_domain"]) == (
            probe.operation, probe.concept, probe.domain
        ):
            right.add(probe.goal)
    return right


def fingerprint(model: Any) -> str:
    import hashlib

    blob = json.dumps([model.W_op, model.W_concept, model.W_domain], sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def evaluate_update(
    model: Any,
    goal: str,
    operation: str,
    concept: str,
    domain: str,
    *,
    probes: Sequence[Probe],
    learning_rate: float = 0.05,
    weight_decay: float = 1e-4,
) -> dict[str, Any]:
    """Apply one candidate step to a COPY and report what it did to other inputs."""
    base: dict[str, Any] = {"schema": SCHEMA, "authority": "NONE",
                            "whole_capability_proved": False, "trained_goal": goal}
    if not label_is_in_vocabulary(operation, concept, domain):
        return {**base, "verdict": REFUSED, "reason": "TRAINED_LABEL_OUTSIDE_HEAD_VOCABULARY"}
    usable = [p for p in probes if p.goal.strip() != goal.strip()]
    if not probes:
        return {**base, "verdict": REFUSED, "reason": "NO_PROBES_OFFERED"}
    if not usable:
        return {**base, "verdict": REFUSED, "reason": "EVERY_PROBE_IS_THE_TRAINED_GOAL"}
    for probe in usable:
        if not label_is_in_vocabulary(probe.operation, probe.concept, probe.domain):
            return {**base, "verdict": REFUSED, "reason": f"PROBE_LABEL_OUTSIDE_VOCABULARY:{probe.goal}"}

    before = _correct(model, usable)
    shadow = _shadow(model)
    receipt = shadow.update_from_experience(goal, operation, concept, domain,
                                           learning_rate=learning_rate, weight_decay=weight_decay,
                                           persist=False)
    after = _correct(shadow, usable)
    gained, lost = after - before, before - after
    roles = {p.goal: p.role for p in usable}
    counts = {
        "probes": len(usable),
        "correct_before": len(before),
        "correct_after": len(after),
        "gained": len(gained),
        "lost": len(lost),
        "gained_transfer": sum(1 for g in gained if roles[g] == TRANSFER),
        "gained_archive": sum(1 for g in gained if roles[g] == ARCHIVE),
        "lost_archive": sum(1 for g in lost if roles[g] == ARCHIVE),
        "lost_transfer": sum(1 for g in lost if roles[g] == TRANSFER),
    }
    report = {**base, "counts": counts, "naive_receipt": receipt,
              "gained_goals": sorted(gained), "lost_goals": sorted(lost)}
    if lost:
        return {**report, "verdict": REJECT, "reason": "BROKE_A_PREDICTION_THAT_WAS_RIGHT"}
    if not gained:
        return {**report, "verdict": REFINE, "reason": "NO_MEASURED_GAIN_ON_ANY_OTHER_INPUT"}
    return {**report, "verdict": ADMIT, "reason": None}


def apply_if_admitted(
    model: Any,
    goal: str,
    operation: str,
    concept: str,
    domain: str,
    *,
    probes: Sequence[Probe],
    learning_rate: float = 0.05,
    weight_decay: float = 1e-4,
    persist: bool = True,
) -> dict[str, Any]:
    """Keep the step only on ADMIT. On any other verdict the live weights are untouched."""
    before_fp = fingerprint(model)
    report = evaluate_update(model, goal, operation, concept, domain, probes=probes,
                             learning_rate=learning_rate, weight_decay=weight_decay)
    if report.get("verdict") != ADMIT:
        return {**report, "applied": False, "weights_unchanged": fingerprint(model) == before_fp}
    receipt = model.update_from_experience(goal, operation, concept, domain,
                                          learning_rate=learning_rate, weight_decay=weight_decay,
                                          persist=persist)
    return {**report, "applied": True, "applied_receipt": receipt,
            "weights_unchanged": False, "weights_before_sha256": before_fp,
            "weights_after_sha256": fingerprint(model)}


# ---------------------------------------------------------------------------
# the concrete stream used by the CLI and the measurement tool
# ---------------------------------------------------------------------------
FILES = {"python_ast": "mod.py", "markdown": "doc.md", "json": "data.json",
         "csv": "table.csv", "text": "notes.txt"}
WORDS = {"python_ast": ["functions", "methods", "classes", "if statements", "async functions",
                        "decorators"],
         "markdown": ["headings", "links", "code blocks"],
         "json": ["keys", "objects", "arrays"],
         "csv": ["rows", "columns"],
         "text": ["lines", "words"]}


def stream_goals() -> list[str]:
    return [f"{op} the {word} in {FILES[domain]}"
            for domain, words in WORDS.items() for word in words for op in ("count", "list")]


def fresh_model(tmp_dir: pathlib.Path | None = None) -> Any:
    from canonical.swe_kernel.semantic_generalization_engine_v1 import OnlineParametricPolicyModel

    path = (tmp_dir or pathlib.Path(".")) / "WEIGHT_ADMISSION_PROBE_POLICY_V1.json"
    if path.is_file():
        path.unlink()
    return OnlineParametricPolicyModel(state_path=path)


def main(argv: list[str] | None = None) -> int:
    import tempfile

    parser = argparse.ArgumentParser(description="One weight step, measured on inputs it did not train on.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    built = probes_from_goals(stream_goals())
    probes = built["probes"]
    with tempfile.TemporaryDirectory() as tmp:
        model = fresh_model(pathlib.Path(tmp))
        first = probes[0]
        report = evaluate_update(model, first.goal, first.operation, first.concept, first.domain,
                                 probes=[p for p in probes if p.goal != first.goal])
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"probes={len(probes)} parser_refused={len(built['refused'])}")
        print(f"first step: {report['verdict']} ({report['reason']})")
        print(f"    naive receipt loss_delta={report['naive_receipt']['loss_delta']} "
              f"counts={report['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
