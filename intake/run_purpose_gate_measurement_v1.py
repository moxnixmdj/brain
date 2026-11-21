#!/usr/bin/env python3
"""Measure the composed purpose gate on real executed contrasts.

Criteria are declared before any trace is executed. Authority NONE.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "canonical" / "tools"
for path in (str(ROOT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402

from intake import bulk_copy_environment_v1 as bulk  # noqa: E402
from intake import purpose_gate_v1 as P  # noqa: E402
from intake import residual_question_gate_v1 as G  # noqa: E402

SCHEMA = "BRAIN_PURPOSE_GATE_MEASUREMENT_V1"
ARGS = {"content": env.PROBE_NEW, "old": env.PROBE_OLD,
        "name": "seed", "target": "copy"}
CREATED = "created_once[probe_new_content]"
MONOTONE = "monotone[probe_new_content] and final:count[probe_new_content]==1"

DECLARED: dict[str, str] = {
    "P1": "a residual with no real separating run produces NO_QUESTION",
    "P2": "one real run in a new action vocabulary separates the residual and gives 0/1 goal mismatches",
    "P3": "untrusted author, stale digest, wrong kind and unknown candidate are all refused",
    "P4": "an accepted selection is stored externally, reloads, and deletion restores the question",
    "P5": "zero model calls, zero stored parameters, zero network calls; every trace executed",
}


def _candidates() -> list[G.Candidate]:
    def created(trace: G.Trace) -> bool:
        return runs._increased_once(trace, env.PROBE_NEW)

    def monotone(trace: G.Trace) -> bool:
        return (runs._count(trace[-1], env.PROBE_NEW) == 1
                and all(runs._count(trace[i + 1], env.PROBE_NEW)
                        >= runs._count(trace[i], env.PROBE_NEW)
                        for i in range(len(trace) - 1)))

    return G.from_predicates([(CREATED, created), (MONOTONE, monotone)])


def _traces(root: pathlib.Path, kind: str) -> list[G.Trace]:
    machine = env.build_git(root) if kind == "GIT" else bulk.build(root)
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    return runs.traces_for(machine, ARGS, depth=2 if kind == "GIT" else 1)


def measure(receipt_path: pathlib.Path) -> dict[str, Any]:
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-purpose-gate-"))
    candidates = _candidates()
    git_traces = _traces(where / "git", "GIT")
    bulk_traces = _traces(where / "bulk", "BULK_COPY")
    instruction = "probe_new_content must arrive once and stay"
    digest = P.answers.instruction_sha256(instruction)

    quiet = P.decide({"instruction": instruction, "authorized_users": ["owner"]},
                     candidates, git_traces, goal_judge=quotient.portable_judge)
    contrast = P.decide({"instruction": instruction, "authorized_users": ["owner"]},
                        candidates, bulk_traces, goal_judge=quotient.portable_judge)

    def typed(candidate_id: str, author: str = "owner", **overrides: Any) -> dict[str, Any]:
        row = {"author": author, "instruction_sha256": digest,
               "question_fingerprint": contrast["question_fingerprint"],
               "kind": P.ANSWER_KIND, "candidate_id": candidate_id}
        row.update(overrides)
        return row

    mismatches = contrast["gate"]["mismatches_with_goal_judge"]
    correct_id = next(cid for cid, count in mismatches.items() if count == 0)
    correct_text = next(option["text"] for option in contrast["payload"]["options"]
                        if option["candidate_id"] == correct_id)
    refusals = {
        "untrusted": P.decide({"instruction": instruction, "authorized_users": ["owner"],
                               "purpose_answer": typed(correct_id, "stranger")},
                              candidates, bulk_traces)["reason"],
        "stale_digest": P.decide({"instruction": instruction, "authorized_users": ["owner"],
                                  "purpose_answer": typed(correct_id, instruction_sha256="0" * 64)},
                                 candidates, bulk_traces)["reason"],
        "wrong_kind": P.decide({"instruction": instruction, "authorized_users": ["owner"],
                                "purpose_answer": typed(correct_id, kind="FREE_PROSE")},
                               candidates, bulk_traces)["reason"],
        "invented_candidate": P.decide({"instruction": instruction, "authorized_users": ["owner"],
                                        "purpose_answer": typed("not-in-residual")},
                                       candidates, bulk_traces)["reason"],
    }
    accepted = P.decide({"instruction": instruction, "authorized_users": ["owner"],
                         "purpose_answer": typed(correct_id)}, candidates, bulk_traces)
    store = where / "purpose_store.json"
    answer_state = {"instruction": instruction, "authorized_users": ["owner"],
                    "purpose_answer": typed(correct_id)}
    P.persist(answer_state, accepted, store)
    reloaded = P.stored_answer(store, contrast["question_fingerprint"])
    restore = P.decide({"instruction": instruction, "authorized_users": ["owner"],
                        "purpose_answer": P.as_state_answer(reloaded)} if reloaded else
                       {"instruction": instruction, "authorized_users": ["owner"]},
                       candidates, bulk_traces)
    store.unlink()
    after_delete = P.decide({"instruction": instruction, "authorized_users": ["owner"]},
                            candidates, bulk_traces)

    p1 = quiet["action"] == P.NO_QUESTION and quiet["gate"]["distinguishing_runs"] == 0
    p2 = (contrast["action"] == P.ASK_USER
          and contrast["gate"]["distinguishing_runs"] == 1
          and sorted(mismatches.values()) == [0, 1])
    p3 = all(reason != P.ACCEPTED for reason in refusals.values())
    p4 = (restore["action"] == P.ACCEPTED
          and after_delete["action"] == P.ASK_USER)
    p5 = bool(git_traces and bulk_traces)
    verdict = {
        "P1_no_zero_information_question": {"action": quiet["action"],
                                            "runs": len(git_traces),
                                            "distinguishing": quiet["gate"]["distinguishing_runs"],
                                            "MET": p1},
        "P2_one_real_contrast_pays_the_question": {
            "runs": len(bulk_traces), "distinguishing": contrast["gate"]["distinguishing_runs"],
            "mismatches": mismatches, "correct_text": correct_text,
            "MET": bool(p2)},
        "P3_refusals": {**refusals, "MET": p3},
        "P4_external_deletable_store": {
            "reloaded_action": restore["action"], "after_delete_action": after_delete["action"],
            "MET": p4},
        "P5_zeros_and_real_execution": {
            "git_runs": len(git_traces), "bulk_runs": len(bulk_traces),
            "model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
            "MET": p5},
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-21",
        "mode": "COMPOSED_PURPOSE_GATE_TESTED_ON_REAL_EXECUTED_CONTRASTS",
        "declared_before_the_runs": DECLARED,
        "verdict": verdict,
        "all_criteria_met": all(row["MET"] for row in verdict.values()),
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "non_claims": [
            "no benchmark score, no OSWorld or SWE-bench run",
            "no user answered; the selection was typed by this producer",
            "no claim of live runtime wiring or general natural-language understanding",
            "independent verification is not claimed; authority is NONE",
        ],
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args()
    receipt = measure(options.receipt)
    print(json.dumps({"all_criteria_met": receipt["all_criteria_met"],
                      "seconds": receipt["cost"]["seconds"]}, indent=1))
    return 0 if receipt["all_criteria_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
