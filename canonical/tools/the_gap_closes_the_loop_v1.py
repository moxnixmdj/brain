#!/usr/bin/env python3
"""The gap closes the loop: an arbitrary environment, a guide, one verified experience, kept forever.

THE OWNER'S IDEA, EXECUTED, NOT DESCRIBED
------------------------------------------
An agent enters a computer environment it knows NOTHING about. The task data
lives in the instance. The only actions the caller offers are program
VOCABULARY (`statistics`, `math`) -- never the answer. The environment is not in
any training set; it exists on disk in a temporary directory that is created,
used, and deleted by this script.

The loop the owner asked for, and what this script measures:

  SCAN      the agent tries its actions, learns their dynamics, records state
  GAP       a first-class receipt names what the scan cannot explain
  RETRIEVE  the computer's own guide (a real file) answers the subject question
  EXECUTE   the guide's example is replayed (it matches the printed output),
            then GENERALIZED into a mechanism sketch (the data-dependent parts
            become holes) and BOUND to this instance by execution
  VERIFY    the goal is OBSERVED -- the stdlib recomputes the median, the trace
            is never the oracle
  ADMIT     the sketch replays on instances the agent never saw; both must
            reach the goal before anything is saved
  SAVE      the MECHANISM (templates with slots), never the data
  RECALL    a brand-new instance, one later run: no scan, no learning budget,
            goal observed, answer from memory -- then still re-verified

HONEST LIMITS (read before believing any of it)
-----------------------------------------------
This is a narrow environment that fits in one file. It proves the CIRCUIT, not
the world: no GUI, no browser, no SWE-bench Pro, no OSWorld. The guide excerpt
is written by this script (it is a faithful excerpt of the Python statistics
guide, not fetched at run time). The goal check recomputes the answer with the
stdlib, exactly as a held-out test does. Authority of the whole run:
NONE__PRODUCER_RUN_SANDBOX -- measurement, not a benchmark, not a capability
claim, not independent verification. Model calls: 0. Network: 0. Parameters: 0.

Exit code: 0 when every stage behaves as declared below, 1 otherwise.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import shutil
import statistics
import sys
import tempfile
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.swe_kernel import perfect_algorithm_v1 as pa  # noqa: E402

SCHEMA = "BRAIN_THE_GAP_CLOSES_THE_LOOP_20261124_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DATE = "2026-11-24"
RECEIPT_PATH = REPO / "canonical/verification/THE_GAP_CLOSES_THE_LOOP_20261124_V1.json"

GUIDE = """# statistics — mathematical statistics functions

This excerpt documents statistics.median, the part of the Python standard
library guide the task needs. It is a faithful excerpt: the transcript below is
the one the interpreter prints.

To compute the median of the numbers in a list, call statistics.median with the list. For example:

```
>>> statistics.median([3, 1, 4, 1, 5])
3
>>> statistics.median([10, 20, 30, 40, 50, 60])
35.0
```

statistics.median is robust against outliers, and it accepts any iterable of numbers.
"""

PROSE_ONLY_GUIDE = """# statistics — mathematical statistics functions

To compute the median of the numbers in a list, use statistics.median with the list.
It is robust against outliers and accepts any iterable of numbers. This page has
no example and no transcript: nothing here can be replayed or executed.
"""

TRAIN = (7, 2, 9, 4, 11)          # deliberately NOT the guide's printed example
ADMIT_A = (9, 7, 11, 3, 8, 10)    # admission instance 1 (never seen in training)
ADMIT_B = (100, 1, 50)            # admission instance 2
RECALL = (42, 8, 15, 16, 23, 4)   # recall instance, used one run later


def goal_predicate(obs) -> bool:
    return (isinstance(obs, tuple) and len(obs) == 3 and obs[0] == "result"
            and obs[2] == statistics.median(obs[1]))


class StatisticsRepl:
    """A real, arbitrary environment: data in, Python expressions in, result out."""

    kind = "statistics"

    def __init__(self, data):
        self.data = tuple(data)
        self.last = None

    def reset(self) -> None:
        self.last = None

    def state(self):
        if self.last is None:
            return ("input", self.data)
        return ("result", self.data, self.last)

    def act(self, statement):
        import math as _math
        import statistics as _statistics

        tree = ast.parse(str(statement), mode="eval")
        root = tree.body
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name) and root.id not in ("statistics", "math"):
            raise ValueError("PROGRAM_NOT_IN_VOCABULARY: " + root.id)
        ns = {"statistics": _statistics, "math": _math}
        self.last = eval(compile(tree, "<guide>", "eval"), ns)  # the ENV evaluates, not the caller
        return self.last

    def snapshot(self):
        return self.last

    def restore(self, saved) -> None:
        self.last = saved


def fresh(data):
    return StatisticsRepl(data)


def run_stage(label, memory_path, guide_root, env, unseen, started_total):
    out = pa.run(env, "compute the median of the numbers in the list",
                 ["statistics.median"],  # program VOCABULARY, not the answer
                 goal_predicate=goal_predicate,
                 goal_family="statistics_median", env_kind="statistics",
                 memory_path_=memory_path, budget=2, max_depth=2, seed=0,
                 unseen_instances=unseen,
                 fresh_reset=lambda e: e.reset(),
                 fresh_act=lambda e, a: e.act(a),
                 fresh_state=lambda e: e.state(),
                 local_root=guide_root)
    out["stage"] = label
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, default=RECEIPT_PATH)
    options = parser.parse_args(argv)

    work = pathlib.Path(tempfile.mkdtemp(prefix="gap-closes-the-loop-"))
    try:
        guide_root = work / "guides"
        guide_root.mkdir()
        memory_path = work / "memory.json"
        (guide_root / "statistics.md").write_text(GUIDE, encoding="utf-8")

        started = time.time()
        stages: dict[str, object] = {}

        # ---- stage 1: learn from nothing but the environment and its guide
        env_a = fresh(TRAIN)
        out_a = run_stage("learn", memory_path, guide_root, env_a,
                          [fresh(ADMIT_A), fresh(ADMIT_B)], started)
        stages["learn"] = out_a

        # ---- stage 2: recall on a brand-new instance, one run later
        env_d = fresh(RECALL)
        out_d = run_stage("recall", memory_path, guide_root, env_d, None, started)
        stages["recall"] = out_d

        # ---- stage 3 (negative control): a prose-only guide closes nothing
        (guide_root / "statistics.md").write_text(PROSE_ONLY_GUIDE, encoding="utf-8")
        memory_neg = work / "memory_negative.json"
        env_n = fresh(TRAIN)
        out_n = run_stage("prose_only_negative_control", memory_neg, guide_root,
                          env_n, [fresh(ADMIT_A)], started)
        stages["prose_only_negative_control"] = out_n

        stored_rule = None
        try:
            stored_rule = pa.load_memory(memory_path).get("rules") or []
        except Exception as e:  # noqa: BLE001
            stored_rule = [{"error": str(e)}]

        claims = {
            "learn_reaches_goal_and_observes_it": out_a.get("status") == "PASS__DOCUMENT_PLAN_EXECUTED_AND_VERIFIED",
            "goal_value_matches_stdlib": env_a.last == statistics.median(TRAIN),
            "admitted_on_two_unseen_instances": (out_a.get("steps", {}).get("admit", {}) or {}).get("verdict") == "ADMIT",
            "mechanism_saved_not_data": (
                bool(stored_rule)
                and all("7, 2, 9" not in json.dumps(r) and "9, 7, 11" not in json.dumps(r) for r in stored_rule)),
            "recall_needs_no_scan_and_still_verifies": (
                out_d.get("status") == "PASS__REPLAY_FROM_MEMORY"
                and "scan" not in out_d.get("steps", {})
                and env_d.last == statistics.median(RECALL)),
            "prose_only_guide_refused": out_n.get("status") == "OPEN__NO_PLAN_AFTER_SCAN",
        }
        receipt = {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "date": DATE,
            "stages": stages,
            "stored_rule_count": len(stored_rule or []),
            "stored_rule": stored_rule,
            "claims": claims,
            "all_claims_hold": all(claims.values()),
            "cost": {"model_calls": 0, "network_calls_at_run_time": 0, "parameters_stored": 0},
            "what_this_is_not": [
                "not a benchmark result: one machine, one narrow environment",
                "not independent verification: producer sandbox measurement only",
                "not OSWorld, not SWE-bench Pro, not Terminal-Bench",
                "not a capability claim and not terminal truth",
                "the guide excerpt was written by this script; no network was used",
            ],
        }
        options.receipt.parent.mkdir(parents=True, exist_ok=True)
        options.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str),
                                   encoding="utf-8")

        print("THE GAP CLOSES THE LOOP -- 2026-11-24")
        print("stage learn     :", out_a.get("status"), "| outcome:", out_a.get("outcome"))
        print("  goal observed :", env_a.last, "(stdlib median:", statistics.median(TRAIN), ")")
        print("  admit         :", (out_a.get("steps", {}).get("admit") or {}).get("verdict"),
              "| reached", (out_a.get("steps", {}).get("admit") or {}).get("reached"),
              "of", (out_a.get("steps", {}).get("admit") or {}).get("instance_count"))
        print("stage recall    :", out_d.get("status"), "| outcome:", out_d.get("outcome"))
        print("  recalled      :", env_d.last, "(stdlib median:", statistics.median(RECALL), ")")
        print("  scan was run  :", "scan" in out_d.get("steps", {}))
        print("negative control:", out_n.get("status"))
        print("stored rule ids :", [r.get("rule_id") for r in (stored_rule or []) if isinstance(r, dict)])
        print("claims          :", json.dumps(claims, sort_keys=True))
        print("receipt         :", options.receipt)
        print("authority       :", AUTHORITY)
        return 0 if receipt["all_claims_hold"] else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
