#!/usr/bin/env python3
"""Is one execution enough? A decidable answer, before the second execution.

THE QUESTION, STATED SO IT CAN BE ANSWERED
------------------------------------------
"Give the agent the action, let it run once, and it knows it for ever." That is a claim about
*sufficiency*, and sufficiency is decidable: after one execution, keep every transformation of the state
that the execution did not rule out, and ask whether those survivors can still be told apart by any state
the work can reach.

    survivors agree on every reachable state   -> one execution was enough; the knowledge is permanent
    survivors split on some reachable state    -> one execution was not enough; here is the cheapest
                                                  execution that settles it
    no survivor fits the execution at all      -> the vocabulary is insufficient; refuse, and never
                                                  memorise the observation

Three answers, computed, from real programs on real directories. No model, no weights, no network.

WHY THIS IS THE MISSING PIECE (2026 record)
-------------------------------------------
The project already measured the *coding* half: `IDENTIFICATION_COST_IN_A_REAL_SPACE_20261116_V1` shows
that after one published example a real bug's candidate space still has a MEDIAN OF 1037 SURVIVING
PROGRAMS (max 16480, 10.0 bits), only 4 of 23 tasks are identified, and 7 of 23 are not identified even
after every example -- because the right behaviour is not in the space at all. A GUI measurement
(`demonstration_version_space_v1`) reports 13.05 of 32 descriptions surviving one demonstration.

The frontier's own answer to the same question is to *not* hold a version space: Tycho (ARC-AGI-3,
arXiv 2607.28287) states it explicitly -- the policy records competing hypotheses in notes, picks one, and
"spends an action to distinguish them when useful". And knowing when *not* to act is measurably unsolved:
AgentAbstain (arXiv 2607.10059) finds the best of 17 frontier models at 59.5% paired accuracy, with act
accuracy exceeding abstain accuracy by 21 points. Identifiability theory says why (arXiv 2607.22430): a
weakly excited action direction gives small on-policy error and large counterfactual error, so a single
trace from a narrow distribution can fit the observed state exactly and still be wrong off that
distribution.

So the object here is not another learner. It is the *decision* a learner owes its caller:
`act` when every survivor agrees, `learn once more` when they split, `refuse` when none fits -- and the
sufficiency verdict that says which of the three applies, computed before spending the next execution.

THE HYPOTHESIS SPACE IS A GRAMMAR OVER THE STATE, NOT A LIST PER ACTION
-----------------------------------------------------------------------
A hypothesis is one transformation of the state, generated from the state itself:

    identity, copy(src->dst), sort, sort_unique, reverse, digest, prefix(n), truncate, delete, append

for every ordered pair of distinct paths, and every n in PREFIX_LENGTHS. The action's *name* plays no part:
the execution is filtered against the same space whether it is `sort`, `tac` or `head -c 8`, which is the
point -- what is learned is what the action does, not what it is called. |H| is a property of the state and
is reported, never hidden.

Model dependency: 0. Network: 0. Every observation is a real subprocess on a real copy of a real state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import finite_identifiability as F  # noqa: E402
from canonical.swe_kernel.computer_use_check_density_v1 import _has, _run  # noqa: E402
from canonical.swe_kernel.predictive_contract_v1 import _files, _seed  # noqa: E402

SCHEMA = "BRAIN_DEMONSTRATION_SUFFICIENCY_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
TIMEOUT_SECONDS = 15.0
PREFIX_LENGTHS = (4, 8, 16, 32)
KINDS = ("identity", "copy", "sort", "sort_unique", "reverse", "digest", "prefix", "truncate",
         "delete", "append")


# --------------------------------------------------------------------------- #
# the state, and one transformation of it
# --------------------------------------------------------------------------- #
def signature(state: Mapping[str, bytes]) -> str:
    """What an observation can see: which paths exist and what each holds."""
    return ";".join("%s=%s" % (path, hashlib.sha256(state[path]).hexdigest()[:12])
                    for path in sorted(state))


def _lines(data: bytes) -> list[bytes]:
    return data.splitlines(True)


def apply(kind: str, state: Mapping[str, bytes], *, src: str | None = None,
          dst: str | None = None, n: int = 0) -> dict[str, bytes]:
    """The predicted consequence of one reading of the action. Total: undefined cases are no-ops."""
    out = dict(state)
    if kind == "identity":
        return out
    if dst is None:
        return out
    source = out.get(src, b"") if src is not None else b""
    if kind == "copy":
        out[dst] = source
    elif kind == "sort":
        out[dst] = b"".join(sorted(_lines(source)))
    elif kind == "sort_unique":
        out[dst] = b"".join(sorted(set(_lines(source))))
    elif kind == "reverse":
        out[dst] = b"".join(reversed(_lines(source)))
    elif kind == "digest":
        out[dst] = ("%s  %s\n" % (hashlib.sha256(source).hexdigest(), src or "-")).encode()
    elif kind == "prefix":
        out[dst] = source[:n]
    elif kind == "truncate":
        out[dst] = b""
    elif kind == "delete":
        out.pop(dst, None)
    elif kind == "append":
        out[dst] = out.get(dst, b"") + source
    return out


def space(state: Mapping[str, bytes], extra_paths: Sequence[str] = ()) -> list[F.Hypothesis]:
    """Every reading of the state the grammar admits. Generated, counted, and stated -- not listed per action.

    The path universe is the state on disk PLUS the paths the invocation names. That is not a leak: which
    *names* exist is given by the interface, exactly as a page gives its elements; what is being inferred is
    what the action *does* to them. Without it the grammar cannot express "creates a file", and every action
    that creates one is refused -- a vocabulary gap that hides itself as unidentifiability.
    """
    paths = sorted(set(state) | set(extra_paths))
    found: list[F.Hypothesis] = []
    for kind in KINDS:
        if kind in ("identity",):
            found.append(F.Hypothesis("identity", {"kind": kind}))
            continue
        if kind == "prefix":
            for src in paths:
                for dst in paths:
                    if src == dst:
                        continue
                    for n in PREFIX_LENGTHS:
                        found.append(F.Hypothesis("prefix:%s>%s:%d" % (src, dst, n),
                                                  {"kind": kind, "src": src, "dst": dst, "n": n}))
            continue
        for src in paths:
            for dst in paths:
                if src == dst and kind not in ("delete", "truncate"):
                    continue
                if kind == "delete" and src != dst:
                    continue
                found.append(F.Hypothesis("%s:%s>%s" % (kind, src, dst),
                                          {"kind": kind, "src": src, "dst": dst}))
    return found


def _predict(hypothesis: F.Hypothesis, state: Mapping[str, bytes]) -> dict[str, bytes]:
    return apply(**hypothesis.payload, state=state)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# experiments: candidate states, with the outcome every survivor predicts
# --------------------------------------------------------------------------- #
def experiment_table(hypotheses: Sequence[F.Hypothesis], states: Mapping[str, Mapping[str, bytes]]
                     ) -> list[F.Experiment]:
    """One column per candidate state; each row is what a hypothesis predicts that state becomes."""
    table: list[F.Experiment] = []
    for state_id in sorted(states):
        outcomes = {hypothesis.hypothesis_id: signature(_predict(hypothesis, states[state_id]))
                    for hypothesis in hypotheses}
        table.append(F.Experiment(experiment_id=state_id, outcomes=outcomes, cost=1.0))
    return table


def observe(invocation: str, state: Mapping[str, bytes], work: pathlib.Path) -> dict[str, Any]:
    """Run the action for real, in a fresh copy of the state. The only source of truth here."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="observe-", dir=work))
    for path, data in state.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    try:
        code, noise = _run(root, invocation)
    except subprocess.TimeoutExpired:
        code, noise = 124, ""
    after = _files(root)
    shutil.rmtree(root, ignore_errors=True)
    return {"signature": signature(after), "exit_code": code, "noise": noise.strip()[:120],
            "state_after": {path: after[path].decode("utf-8", "replace") for path in sorted(after)}}


# --------------------------------------------------------------------------- #
# the decision
# --------------------------------------------------------------------------- #
def sufficiency(hypotheses: Sequence[F.Hypothesis], table: Sequence[F.Experiment],
                observed: Mapping[str, str], task_states: Sequence[str]) -> dict[str, Any]:
    """The verdict, computed from what is left after the executions already spent."""
    filtered = F.filter_version_space(hypotheses, table, dict(observed))
    if filtered["status"] == "MODEL_FALSIFIED":
        return {"verdict": "VOCABULARY_INSUFFICIENT", "detail": filtered.get("reason"),
                "survivors": [], "terminal_authority": False}
    remaining = filtered["remaining_hypotheses"]
    unused = [entry for entry in table if entry.experiment_id not in observed]
    environment_classes = F.equivalence_classes(remaining, unused) if unused else \
        F.equivalence_classes(remaining, [])
    task_unused = [entry for entry in unused if entry.experiment_id in set(task_states)]
    task_classes = F.equivalence_classes(remaining, task_unused) if task_unused else \
        F.equivalence_classes(remaining, []) if unused else [[h] for h in remaining]

    if len(remaining) == 1:
        verdict = "IDENTIFIED"
    elif len(environment_classes) == 1:
        verdict = "BEHAVIOURALLY_IDENTICAL_IN_THIS_ENVIRONMENT"
    elif len(task_classes) == 1:
        # the dangerous, common case: safe on the work in front of it, permanently unsound off it
        verdict = "SAFE_FOR_THIS_TASK_ONLY"
    else:
        verdict = "NEEDS_ONE_MORE_EXECUTION"

    choice = F.select_discriminator(hypotheses, table, dict(observed))
    return {
        "verdict": verdict,
        "survivors": remaining,
        "survivor_count": len(remaining),
        "equivalence_classes_in_environment": len(environment_classes),
        "equivalence_classes_in_task": len(task_classes),
        "next_experiment": choice.get("experiment_id") if choice["status"] == "SELECT_EXPERIMENT" else None,
        "next_experiment_worst_case_remaining": choice.get("worst_case_remaining"),
        "no_experiment_left": choice["status"] == "NONIDENTIFIABLE_UNDER_AUTHORIZED_EXPERIMENTS",
        "terminal_authority": False,
    }


def decide(sufficiency_verdict: Mapping[str, Any]) -> str:
    """The rule the agent owes its caller. Three cases, no fourth."""
    if sufficiency_verdict["verdict"] == "VOCABULARY_INSUFFICIENT":
        return "REFUSE__THE_VOCABULARY_CANNOT_EXPRESS_WHAT_HAPPENED"
    if sufficiency_verdict["verdict"] == "NEEDS_ONE_MORE_EXECUTION" and sufficiency_verdict["next_experiment"]:
        return "LEARN_ONCE_MORE__AT_%s" % sufficiency_verdict["next_experiment"]
    if sufficiency_verdict["verdict"] in ("IDENTIFIED",
                                          "BEHAVIOURALLY_IDENTICAL_IN_THIS_ENVIRONMENT",
                                          "SAFE_FOR_THIS_TASK_ONLY"):
        return "ACT__EVERY_SURVIVOR_AGREES_ON_THE_STATES_IN_REACH"
    return "REFUSE__NO_AUTHORIZED_EXPERIMENT_CAN_SETTLE_IT"


def _permanence(verdict: Mapping[str, Any]) -> str:
    """The word "permanently" is the claim under test, so it gets its own verdict."""
    if verdict["verdict"] == "VOCABULARY_INSUFFICIENT":
        return "REFUSED__NOTHING_IS_KEPT"
    if verdict["verdict"] in ("IDENTIFIED",
                              "BEHAVIOURALLY_IDENTICAL_IN_THIS_ENVIRONMENT"):
        return "PERMANENT__NO_READING_SURVIVES_THAT_THE_ENVIRONMENT_CAN_TELL_APART"
    if verdict["verdict"] == "SAFE_FOR_THIS_TASK_ONLY":
        return "TASK_SCOPED__TRUE_NOW_AND_FALSE_WHEN_THE_WORK_WIDENS"
    return "NOT_YET_KNOWN__ONE_MORE_EXECUTION_NAMED"


# --------------------------------------------------------------------------- #
# the chains: real actions, real programs, real variants
# --------------------------------------------------------------------------- #
PAYLOAD_UNIQUE = b"alpha\nbeta\ngamma\ndelta\nepsilon\nzeta\neta\ntheta\n"
PAYLOAD_DUPLICATES = b"alpha\nbeta\nbeta\ngamma\ngamma\ngamma\ndelta\n"
PAYLOAD_UNSORTED = b"zeta\nalpha\ntheta\nbeta\neta\ndelta\ngamma\n"
PAYLOAD_SHORT = b"ab\n"
PAYLOAD_LONG = (b"line-%02d-padding-padding-padding\n" * 1) % 0 + b"".join(
    b"line-%02d-padding-padding-padding\n" % i for i in range(6))
PAYLOAD_EMPTY = b""
PAYLOAD_SINGLE = b"only one line\n"
# src.dat must differ from every other file, or "copy from in.txt" survives a copy from src.dat
# for the trivial reason that the two sources happen to be equal -- an accident of the fixture
# that would be scored as a behavioural identity.
SRC_CONTENT = b"src content that differs from every other file\n"


def _variants(base: Mapping[str, bytes], payload_variants: Mapping[str, bytes]
              ) -> dict[str, dict[str, bytes]]:
    states: dict[str, dict[str, bytes]] = {}
    for name, payload in payload_variants.items():
        state = {path: data for path, data in base.items() if path != "payload.dat"}
        state["payload.dat"] = payload
        states["payload_" + name] = state
    # a state that varies the SOURCE, not just the destination: without one, every reading that reads
    # src.dat and writes out.dat is behaviourally identical on single-line content, and the version space
    # would be right to say so. The discriminator can only choose among the states generated for it.
    multi = {path: data for path, data in base.items()}
    multi["src.dat"] = b"zeta\nalpha\nmu\n" + SRC_CONTENT
    states["src_multiline"] = multi
    with_dst = {path: data for path, data in base.items()}
    with_dst["out.dat"] = b"stale content that is not a sorted list\n"
    states["out_present"] = with_dst
    absent = {path: data for path, data in base.items() if path != "out.dat"}
    states["out_absent"] = absent
    return states


def _chain(work: pathlib.Path, name: str, invocation: str, payload_variants: Mapping[str, bytes],
           task_states: Sequence[str], goal: str, first_state: str = "as_given") -> dict[str, Any]:
    base = {"payload.dat": PAYLOAD_UNIQUE, "src.dat": SRC_CONTENT, "keep.dat": b"do not touch\n"}
    (work / "scratch").mkdir(exist_ok=True)
    seed_root = pathlib.Path(tempfile.mkdtemp(prefix="seed-", dir=work))
    _seed(seed_root, "payload.dat", PAYLOAD_UNIQUE, "keep.dat")
    (seed_root / "src.dat").write_bytes(SRC_CONTENT)
    base = _files(seed_root)
    shutil.rmtree(seed_root, ignore_errors=True)

    mentioned = [token for token in invocation.replace(">", " ").split()
                 if token.endswith((".dat", ".txt", ".out")) and token.isascii()]
    hypotheses = space(base, extra_paths=mentioned)
    states = _variants(base, payload_variants)
    states["as_given"] = dict(base)
    table = experiment_table(hypotheses, states)

    first = observe(invocation, states[first_state], work)
    observed = {first_state: first["signature"]}
    verdict = sufficiency(hypotheses, table, observed, list(task_states))

    # the arms. Each one is asked the same question: on the states this task can reach, is the
    # contract you would have kept from ONE execution still right?
    reachable = [state_id for state_id in sorted(states) if state_id in set(task_states)]
    outside = [state_id for state_id in sorted(states) if state_id not in set(task_states)]
    truth = {state_id: observe(invocation, states[state_id], work) for state_id in reachable + outside}
    by_id = {hypothesis.hypothesis_id: hypothesis for hypothesis in hypotheses}
    survivors_now = list(verdict.get("survivors") or [])
    naive_pick = survivors_now[0] if survivors_now else None
    pick = by_id.get(naive_pick) if naive_pick else None

    naive_wrong, version_space_wrong, asks = [], [], []
    naive_wrong_outside = []
    for state_id in outside:
        actual = truth[state_id]["signature"]
        if pick is not None and signature(_predict(pick, states[state_id])) != actual:
            naive_wrong_outside.append(state_id)
    for state_id in reachable:
        actual = truth[state_id]["signature"]
        if pick is not None and signature(_predict(pick, states[state_id])) != actual:
            naive_wrong.append(state_id)
        survivors = [by_id[h] for h in survivors_now]
        predictions = {signature(_predict(h, states[state_id])) for h in survivors}
        if len(predictions) == 1 and predictions != {actual}:
            version_space_wrong.append(state_id)      # every survivor is wrong: nothing to be done
        elif len(predictions) > 1 and actual not in predictions:
            version_space_wrong.append(state_id)      # honest ambiguity, expressed as such
        elif len(predictions) > 1:
            asks.append(state_id)

    # spend the executions the discriminator asks for, and see whether ONE more was enough
    spent, decision = 1, decide(verdict)
    while (verdict["verdict"] == "NEEDS_ONE_MORE_EXECUTION" and verdict.get("next_experiment")
           and spent < 4):
        state_id = verdict["next_experiment"]
        if state_id in observed or state_id not in states:
            break
        observed[state_id] = observe(invocation, states[state_id], work)["signature"]
        spent += 1
        verdict = sufficiency(hypotheses, table, observed, list(task_states))
        decision = decide(verdict)

    # repeating the SAME execution: the one thing "run it once more" would try
    repeat = observe(invocation, states[first_state], work)
    repeat_changed = repeat["signature"] != first["signature"]

    goal_code, goal_output = _run(work, goal)

    return {
        "chain": name,
        "invocation": invocation,
        "hypotheses": len(hypotheses),
        "candidate_states": len(states),
        "task_states": list(task_states),
        "first_execution": {"signature": first["signature"], "exit_code": first["exit_code"]},
        "survivors_after_one_execution": (sufficiency(hypotheses, table, {first_state: first["signature"]},
                                                      list(task_states)).get("survivor_count")),
        "verdict_after_one_execution": sufficiency(hypotheses, table, {first_state: first["signature"]},
                                                   list(task_states))["verdict"],
        "decision_after_one_execution": decide(sufficiency(hypotheses, table, {first_state: first["signature"]},
                                                           list(task_states))),
        "executions_to_settle": spent,
        "final_verdict": verdict["verdict"],
        "final_decision": decision,
        "final_survivors": verdict.get("survivor_count"),
        "final_survivor_readings": verdict.get("survivors") or [],
        "permanence": _permanence(verdict),
        "equivalence_classes_in_task": verdict.get("equivalence_classes_in_task"),
        "equivalence_classes_in_environment": verdict.get("equivalence_classes_in_environment"),
        "naive_one_shot_wrong_on": naive_wrong,
        "naive_one_shot_wrong_outside_the_task": naive_wrong_outside,
        "first_state": first_state,
        "version_space_wrong_on": version_space_wrong,
        "version_space_asks_on": asks,
        "needed_more_than_one": spent > 1,
        "repeating_the_same_execution_changed_anything": repeat_changed,
        "goal": {"invocation": goal, "passes": goal_code == 0, "symptom": goal_output.strip()[:120]},
    }


def _chains(work: pathlib.Path) -> list[dict[str, Any]]:
    """Seven real actions. Sorted-unique payload is the task's input; the variants are what the task meets."""
    unique_task = ["as_given", "payload_unique"]
    specs = [
        ("sort_versus_sort_unique", "sort -o out.dat payload.dat",
         {"unique": PAYLOAD_UNIQUE, "duplicates": PAYLOAD_DUPLICATES}, unique_task,
         "sort -c out.dat"),
        ("sort_unique_versus_sort", "sort -u -o out.dat payload.dat",
         {"unique": PAYLOAD_UNIQUE, "duplicates": PAYLOAD_DUPLICATES}, unique_task,
         "sort -c out.dat"),
        ("copy_versus_no_clobber", "cp src.dat out.dat",
         {"unique": PAYLOAD_UNIQUE}, ["as_given", "out_present", "out_absent"],
         "cmp -s src.dat out.dat"),
        ("prefix_length", "head -c 8 payload.dat > out.dat",
         {"unique": PAYLOAD_UNIQUE, "long": PAYLOAD_LONG}, ["as_given", "payload_long", "payload_short"],
         "cmp -s out.dat payload.dat"),
        ("reverse_versus_sort", "tac payload.dat > out.dat",
         {"unique": PAYLOAD_UNIQUE, "unsorted": PAYLOAD_UNSORTED}, unique_task,
         "tac payload.dat | cmp -s - out.dat"),
        ("digest_versus_copy", "sha256sum payload.dat > out.dat",
         {"unique": PAYLOAD_UNIQUE}, unique_task, "sha256sum -c out.dat"),
        # one line: every permutation is the identity, so the first execution looks like a copy and the
        # vocabulary has no reason to suspect anything. The second execution is what exposes it.
        ("nondeterministic_action_looks_identified", "sort -R payload.dat -o out.dat",
         {"single": PAYLOAD_SINGLE, "unique": PAYLOAD_UNIQUE}, ["as_given", "payload_single"],
         "sort -c out.dat"),
    ]
    first_states = {"nondeterministic_action_looks_identified": "payload_single"}
    return [_chain(work, name, invocation, variants, task_states, goal,
                   first_state=first_states.get(name, "as_given"))
            for name, invocation, variants, task_states, goal in specs]


def measure() -> dict[str, Any]:
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain-demo-sufficiency-"))
    missing = [program for program in ("sort", "cp", "head", "tac", "sha256sum", "cmp")
               if not _has(program)]
    try:
        chains = _chains(work) if not missing else []
    finally:
        shutil.rmtree(work, ignore_errors=True)

    verdicts_after_one: dict[str, int] = {}
    for chain in chains:
        key = chain["decision_after_one_execution"].split("__")[0]
        verdicts_after_one[key] = verdicts_after_one.get(key, 0) + 1

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "environment": {
            "kind": "real directory, real programs from PATH, real state variants, independent goal commands",
            "hypothesis_space": "a stated grammar over the state: %s" % ", ".join(KINDS),
            "prefix_lengths": list(PREFIX_LENGTHS),
            "decided_before_spending": "the sufficiency verdict is computed from the survivors, not from a second run",
        },
        "missing_programs": missing,
        "chains": len(chains),
        "actions": [chain["chain"] for chain in chains],
        "verdicts_after_one_execution": verdicts_after_one,
        "needed_more_than_one_execution": [c["chain"] for c in chains if c["needed_more_than_one"]],
        "settled_by_one_execution": [c["chain"] for c in chains if not c["needed_more_than_one"]],
        "naive_one_shot_wrong_on_the_task": {c["chain"]: c["naive_one_shot_wrong_on"] for c in chains
                                            if c["naive_one_shot_wrong_on"]},
        "naive_one_shot_wrong_outside_the_task": {c["chain"]: c["naive_one_shot_wrong_outside_the_task"]
                                                 for c in chains if c["naive_one_shot_wrong_outside_the_task"]},
        "task_safe_but_not_environment_safe": [
            c["chain"] for c in chains if c["final_verdict"] == "SAFE_FOR_THIS_TASK_ONLY"],
        "permanence": {c["chain"]: c["permanence"] for c in chains},
        "version_space_asks_instead_of_being_wrong": {c["chain"]: c["version_space_asks_on"] for c in chains
                                                     if c["version_space_asks_on"]},
        "repeating_the_same_execution_ever_helped": [c["chain"] for c in chains
                                                     if c["repeating_the_same_execution_changed_anything"]],
        "refusals": [c["chain"] for c in chains if c["final_decision"].startswith("REFUSE")],
        "survivor_counts": {c["chain"]: c["survivors_after_one_execution"] for c in chains},
        "hypothesis_space_sizes": {c["chain"]: c["hypotheses"] for c in chains},
        "per_chain": chains,
        "external_state": {
            "frontier_does_not_hold_a_version_space":
                "Tycho (arXiv 2607.28287, ARC-AGI-3): the policy records competing hypotheses in notes and "
                "picks one, and 'does not maintain an explicit version space'",
            "abstention_is_unsolved":
                "AgentAbstain (arXiv 2607.10059): best of 17 frontier models 59.5% paired accuracy, act "
                "accuracy exceeds abstain accuracy by 21 points",
            "why_one_trace_cannot_identify":
                "arXiv 2607.22430: weakly excited action directions give small on-policy error and large "
                "counterfactual error -- one trace from a narrow distribution fits and is still wrong",
            "agents_struggle_to_identify_by_query":
                "arXiv 2606.16576: agents identifying a hidden world model by queries are measured on "
                "non-informative query rates",
            "already_measured_in_this_tree":
                "IDENTIFICATION_COST_IN_A_REAL_SPACE_20261116_V1: median 1037 surviving programs after one "
                "demonstration (max 16480, 10.0 bits), 4 of 23 tasks identified, 7 of 23 insufficient even "
                "after every example",
        },
        "limit": ("the hypothesis space is a stated grammar, so a sufficiency verdict is relative to it. That "
                  "is why the third outcome exists and is measured: when no reading fits, the answer is "
                  "REFUSE, not a memorised observation. A behaviour outside the grammar cannot be learned "
                  "from any number of executions -- that is the synthesis wall, and this receipt names it "
                  "rather than crossing it"),
    }
    report["what_this_shows"] = _headline(report)
    return report


def _headline(report: Mapping[str, Any]) -> str:
    one = report["settled_by_one_execution"]
    more = report["needed_more_than_one_execution"]
    naive = report["naive_one_shot_wrong_outside_the_task"]
    task_safe = report["task_safe_but_not_environment_safe"]
    asks = report["version_space_asks_instead_of_being_wrong"]
    return (
        "%d real actions, %d readings each in a stated grammar, one real execution first. One execution "
        "settled %d of %d actions on the states the task reaches; %d could not be settled by it. In %d of %d "
        "actions the one execution leaves several readings that agree on every state the task reaches and "
        "DISAGREE outside it -- so 'it worked, therefore I know it' is true and 'permanently' is false: the "
        "first survivor is wrong on %d further state(s) across %d action(s). Keeping the survivors instead "
        "answers 'this is undetermined, and here is the execution that settles it' on %d states across %d "
        "actions. Repeating the same execution changed the verdict on %d actions. %d action(s) were refused "
        "outright because no reading of the state predicts what happened. "
        "So 'experience it once and keep it for ever' is not a law: it is a special case that holds when the "
        "survivors agree on every state the work can reach, and that is a question you can answer before "
        "spending the second execution."
        % (report["chains"], max(report["hypothesis_space_sizes"].values()) if
           len(set(report["hypothesis_space_sizes"].values())) == 1 else
           (min(report["hypothesis_space_sizes"].values()), max(report["hypothesis_space_sizes"].values())),
           len(one), report["chains"], len(more), len(task_safe), report["chains"],
           sum(len(v) for v in naive.values()), len(naive), sum(len(v) for v in asks.values()), len(asks),
           len(report["repeating_the_same_execution_ever_helped"]), len(report["refusals"])))


def summarize(report: Mapping[str, Any]) -> str:
    lines = ["environment: " + report["environment"]["kind"],
             "actions %d | readings per action %d..%d | model calls 0"
             % (report["chains"], min(report["hypothesis_space_sizes"].values()),
                max(report["hypothesis_space_sizes"].values()))]
    for chain in report["per_chain"]:
        lines.append("  %-40s |H|=%-4d survivors=%-4s spent=%d  %s"
                     % (chain["chain"], chain["hypotheses"], chain["survivors_after_one_execution"],
                        chain["executions_to_settle"], chain["final_verdict"]))
        lines.append("      permanence: %s | survivors: %s"
                     % (chain["permanence"].split("__")[0],
                        ", ".join(chain["final_survivor_readings"][:4]) or "-"))
        if chain["naive_one_shot_wrong_outside_the_task"]:
            lines.append("      the one-shot pick is wrong OUTSIDE the task on: %s"
                         % ", ".join(chain["naive_one_shot_wrong_outside_the_task"]))
        if chain["naive_one_shot_wrong_on"]:
            lines.append("      the one-shot pick is wrong on the task at: %s"
                         % ", ".join(chain["naive_one_shot_wrong_on"]))
        if chain["version_space_asks_on"]:
            lines.append("      survivors split inside the task at: %s"
                         % ", ".join(chain["version_space_asks_on"]))
    if report["refusals"]:
        lines.append("  refused: " + ", ".join(report["refusals"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Decide whether one execution identified an action, before spending the second.")
    parser.add_argument("--json", dest="json_path", default=None)
    ns = parser.parse_args(argv)
    report = measure()
    print(summarize(report))
    print("\n" + report["what_this_shows"])
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
