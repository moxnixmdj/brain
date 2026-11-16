"""Can an instruction become a verifier? Measure it as a CLASSIFIER, in both directions.

The question
------------
Every result in this repository is judged by an oracle the deployment does not have: the page's
own `raw_reward`, the corpus's own test. Coverage was bought last session; TRUST was not. So the
one number that matters is: **when there is no reward, how often does the machine's own contract
agree with the verdict the page would have given?**

This is a classification problem with two costs, and they are not symmetric:

    FALSE ACCEPT   the contract says PASS on an attempt the page scored as a failure
                   -> this is how a learning loop bakes in a wrong lesson "at full confidence",
                      and it is the failure VerifierBench says generated verifiers have
    FALSE REJECT   the contract says FAIL on an attempt the page scored as a success
                   -> this wastes a correct answer; it makes the machine slower and more
                      conservative, but it cannot make it believe something false

Both are counted separately, per attempt, and never blended into one "accuracy".

How a labelled attempt is produced without ever handing the reward to the contract
-------------------------------------------------------------------------------
For each page: the machine searches for a plan (the page's reward judges the SEARCH, as before,
because that is how a first success is obtained), then RE-VERIFIES on a fresh page with the
page's reward re-read -- that is the ground-truth label. The contract is asked to judge exactly
the same trace, from the observations and the actions only. The contract module never imports,
receives or reads `raw_reward`/`done`; a test enforces that by scanning its source.

Two arms, so the label has to be earned twice:

    A  the plan that succeeded          (the page says PASS)
    B  a plan with ONE action replaced  (a decoy, so the page usually says FAIL)
       -- same length, same shape, one different action. The page says what it says; if the page
          says PASS too (a genuinely equivalent plan), the attempt is counted as a correct
          disagreement, never as an error.

Refusals are a third outcome and are reported as their own column: a contract that declines to
judge is honest, and its cost is only that the machine must fall back -- which is exactly the
condition the tree's fail-closed laws already require.

Usage
-----
    python3 canonical/tools/instruction_contract_measure_v1.py \
        --html-dir .../miniwob/html --node-modules-dir .../node_modules \
        --tasks click-button enter-text ... --budget 400 --out /tmp/contract.jsonl
    python3 canonical/tools/instruction_contract_measure_v1.py --consolidate ... --receipt ...
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time
from typing import Any, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import instruction_contract_v1 as contract_lib  # noqa: E402
from canonical.runtime import systematic_exploration_v1 as explorer  # noqa: E402
from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool  # noqa: E402

SCHEMA = "BRAIN_INSTRUCTION_CONTRACT_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

#: Pages where a plan exists for this hand: the ones the last two sessions solved or that the
#: pool of solvable pages covers. Extended per run with --tasks.
DEFAULT_TASKS = (
    "click-button", "click-test", "click-test-2", "click-link", "click-dialog",
    "click-checkboxes", "click-option", "enter-text", "enter-text-2", "enter-password",
    "enter-time", "enter-date", "search-engine", "simple-arithmetic", "simple-algebra",
    "text-transform", "scroll-text", "find-word", "click-tab", "choose-list",
    "click-collapsible", "focus-text", "unicode-test", "click-button-sequence",
)


def search_plan(bridge: Any, task: str, seed: int, *, budget: int) -> dict[str, Any]:
    """Find a plan with the page's reward, exactly as the shipped search does. The reward is
    used HERE and nowhere else: the contract never sees it."""
    loaded = bridge.load(task)
    if not loaded.get("ok"):
        raise RuntimeError(f"PAGE_DID_NOT_LOAD:{task}")
    env = tool.SeedEnv(bridge, seed, time_limit_ms=tool.EXPLORATION_TIME_LIMIT_MS)
    result = explorer.explore_to_goal(
        env, [], is_goal=tool.succeeded, is_dead=tool.failed,
        actions_of=lambda observation: tool.offered_actions(observation, tool.HAND_TIER),
        key_of=tool.state_key, order="cheapest", cost_of=tool.GuidedPrices(),
        action_budget=int(budget), reset_cost=1, include_model=False)
    return {"found": bool(result.get("pass")),
            "plan": [str(a) for a in (result.get("plan_cheapest") or [])],
            "budget_spent": int(result.get("budget_spent") or 0)}


def record_trace(bridge: Any, task: str, seed: int, plan: Sequence[str]) -> dict[str, Any]:
    """Replay a plan on a fresh page, recording (observation, action) pairs and the page's own
    verdict. The verdict is returned SEPARATELY from the trace: the contract is never handed it."""
    loaded = bridge.load(task)
    if not loaded.get("ok"):
        return {"played": False, "trace": [], "reward_verdict": None, "reason": "PAGE_DID_NOT_RELOAD"}
    observation = bridge.reset(seed, time_limit_ms=tool.EXPLORATION_TIME_LIMIT_MS)
    trace: list[tuple[dict[str, Any], str]] = []
    for action in plan:
        trace.append((observation, str(action)))
        try:
            observation = bridge.act(tool.parse_action(action))
        except Exception as error:  # noqa: BLE001
            return {"played": False, "trace": trace, "reward_verdict": None,
                    "reason": type(error).__name__}
        if observation.get("done"):
            break
    return {"played": True, "trace": trace,
            "reward_verdict": bool(tool.succeeded(observation)),
            "ended": bool(observation.get("done"))}


def decoy_plan(plan: Sequence[str], observation: Mapping[str, Any], *, seed: int) -> list[str]:
    """One action replaced by another that the page offers: same length, same shape.

    Deterministic given the seed. If the page offers nothing else the plan is returned unchanged
    and the attempt is skipped -- an unchanged plan is not a decoy and would silently inflate
    every "the page said FAIL" row.
    """
    if not plan:
        return []
    rng = random.Random(seed)
    position = rng.randrange(len(plan))
    offered = tool.offered_actions(observation, tool.HAND_TIER)
    alternatives = [a for a in offered if a != plan[position]]
    if not alternatives:
        return list(plan)
    replacement = alternatives[rng.randrange(len(alternatives))]
    out = list(plan)
    out[position] = replacement
    return out


def judge(trace: Sequence[tuple[Mapping[str, Any], str]], utterance: str,
          opening: Mapping[str, Any]) -> dict[str, Any]:
    """Compile from the OPENING observation (as a deployment would, before acting) and judge."""
    compiled = contract_lib.compile_contract(utterance, opening)
    verdict = contract_lib.check_contract(compiled, trace)
    return {"refusal": compiled.get("refusal"), "contract_verdict": verdict["verdict"],
            "contract_reason": verdict.get("reason"),
            "clauses": [{k: v for k, v in clause.items() if k in
                         ("operator", "name", "names", "value", "ordinal", "kind", "predicate",
                          "direction", "index")} for clause in compiled.get("clauses") or []],
            "clause_results": [{k: v for k, v in row.items() if k in ("operator", "verdict", "reason")}
                               for row in verdict.get("witness") or []]}


def measure_page(bridge: Any, task: str, *, seed: int, budget: int) -> dict[str, Any]:
    row: dict[str, Any] = {"kind": "page", "task": task, "seed": int(seed), "budget": int(budget)}
    started = time.time()
    found = search_plan(bridge, task, seed, budget=budget)
    row.update(found=found["found"], search_budget_spent=found["budget_spent"],
               plan_len=len(found["plan"]))
    if not found["found"]:
        row["attempts"] = []
        row["seconds"] = round(time.time() - started, 1)
        return row
    attempts: list[dict[str, Any]] = []
    for arm, plan in (("A_correct_plan", found["plan"]),
                      ("B_decoy_plan", decoy_plan(found["plan"], bridge.reset(seed), seed=seed))):
        played = record_trace(bridge, task, seed, plan)
        if not played["played"] or not played["trace"]:
            attempts.append({"arm": arm, "skipped": played.get("reason") or "NO_TRACE"})
            continue
        opening = played["trace"][0][0]
        judged = judge(played["trace"], str(opening.get("utterance") or ""), opening)
        attempts.append({
            "arm": arm, "plan": list(plan), "changed": plan != found["plan"],
            "reward_verdict": played["reward_verdict"], **judged})
    row["attempts"] = attempts
    row["seconds"] = round(time.time() - started, 1)
    return row


def summarise(pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Fold every attempt into the two costs, separately. No blended accuracy."""
    cells = {"false_accept": 0, "false_reject": 0, "agree_pass": 0, "agree_fail": 0,
             "uncheckable": 0, "skipped": 0}
    rows = []
    per_operator: dict[str, dict[str, int]] = {}
    for page in pages:
        for attempt in page.get("attempts") or []:
            if attempt.get("skipped"):
                cells["skipped"] += 1
                continue
            if attempt.get("contract_verdict") == contract_lib.UNCHECKABLE:
                cells["uncheckable"] += 1
                continue
            truth = bool(attempt.get("reward_verdict"))
            said = attempt.get("contract_verdict") == contract_lib.PASS
            if said and truth:
                cell = "agree_pass"
            elif not said and not truth:
                cell = "agree_fail"
            elif said and not truth:
                cell = "false_accept"
            else:
                cell = "false_reject"
            cells[cell] += 1
            for clause in attempt.get("clauses") or []:
                bucket = per_operator.setdefault(clause["operator"], {})
                bucket[cell] = bucket.get(cell, 0) + 1
            rows.append({"task": page["task"], "arm": attempt["arm"], "cell": cell,
                         "reward_verdict": truth, "contract_verdict": attempt.get("contract_verdict")})
    judged = cells["false_accept"] + cells["false_reject"] + cells["agree_pass"] + cells["agree_fail"]
    return {"pages": len(pages), "attempts": rows.__len__(),
            "pages_with_a_plan": sum(1 for p in pages if p.get("found")),
            "cells": cells, "judged": judged,
            "false_accept_rate": round(cells["false_accept"] / judged, 4) if judged else None,
            "false_reject_rate": round(cells["false_reject"] / judged, 4) if judged else None,
            "agreement": round((cells["agree_pass"] + cells["agree_fail"]) / judged, 4) if judged else None,
            "per_operator": per_operator}


def census(html_dir: str, node_modules_dir: str, *, substrate: str = "chromium") -> dict[str, Any]:
    """Compile a contract for EVERY page and count what can and cannot be judged.

    This is the censused answer to "how much of computer use has an oracle", page by page, with
    the refusals named. It costs one reset per page and no search at all.
    """
    bridge = tool.Bridge(html_dir, node_modules_dir, substrate=substrate)
    pages = sorted(path.stem for path in pathlib.Path(html_dir).rglob("*.html"))
    rows: list[dict[str, Any]] = []
    for task in pages:
        try:
            loaded = bridge.load(task)
            if not loaded.get("ok"):
                rows.append({"task": task, "refusal": "PAGE_DID_NOT_LOAD"})
                continue
            observation = bridge.reset(0)
        except Exception as error:  # noqa: BLE001
            bridge.restart()
            rows.append({"task": task, "refusal": f"ERROR_{type(error).__name__}"})
            continue
        utterance = str(observation.get("utterance") or "")
        if not utterance:
            rows.append({"task": task, "refusal": "NO_INSTRUCTION", "utterance": ""})
            continue
        compiled = contract_lib.compile_contract(utterance, observation)
        row = {"task": task, "utterance": utterance, "refusal": compiled.get("refusal"),
               "operators": [clause["operator"] for clause in compiled.get("clauses") or []]}
        if not compiled.get("refusal"):
            # FALSIFIABILITY, measured on the page itself. A contract that accepts the empty
            # plan -- the agent does nothing at all -- cannot ever reject a wrong trace, so it
            # is not a verifier no matter how many clauses it lists. This is checked against the
            # real page (one reset, no search, no reward read), not against a synthetic trace.
            verdict = contract_lib.check_contract(compiled, [(observation, "")])
            row["accepts_doing_nothing"] = verdict["verdict"] == contract_lib.PASS
        rows.append(row)
    bridge.close()
    compiled_rows = [row for row in rows if not row.get("refusal")]
    vacuous = sorted(row["task"] for row in compiled_rows if row.get("accepts_doing_nothing"))
    by_refusal: dict[str, list[str]] = {}
    for row in rows:
        key = row.get("refusal") or "COMPILED"
        by_refusal.setdefault(key, []).append(row["task"])
    return {"pages": len(rows),
            "compiled": len(by_refusal.get("COMPILED", [])),
            "share_compiled": round(len(by_refusal.get("COMPILED", [])) / len(rows), 4) if rows else None,
            # a compiled contract that accepts doing nothing is an always-pass grader; it is
            # reported separately instead of being counted as capability
            "falsifiable": len(compiled_rows) - len(vacuous),
            "accepts_doing_nothing": {"count": len(vacuous), "tasks": vacuous},
            "by_refusal": {key: {"count": len(tasks), "tasks": sorted(tasks)}
                           for key, tasks in sorted(by_refusal.items())},
            "rows": rows}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html-dir")
    parser.add_argument("--node-modules-dir")
    parser.add_argument("--substrate", default="chromium", choices=("chromium", "jsdom"))
    parser.add_argument("--tasks", nargs="+", default=None)
    parser.add_argument("--budget", type=int, default=400)
    parser.add_argument("--seed", type=int, default=1060)
    parser.add_argument("--census", action="store_true", help="compile a contract for every page")
    parser.add_argument("--out", required=False)
    parser.add_argument("--consolidate", nargs="+", default=None)
    parser.add_argument("--receipt", default=None)
    args = parser.parse_args(argv)

    if args.consolidate:
        return _consolidate(args.consolidate, args.receipt)
    if args.census:
        report = census(args.html_dir, args.node_modules_dir, substrate=args.substrate)
        text = json.dumps(report, indent=1, sort_keys=True)
        if args.receipt:
            pathlib.Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
            pathlib.Path(args.receipt).write_text(text + "\n")
            print(f"written {args.receipt}")
        else:
            print(text)
        print(f"\nCOMPILED {report['compiled']}/{report['pages']} "
              f"({report['share_compiled']}) of the instruction corpus")
        for key, value in report["by_refusal"].items():
            print(f"  {key:44s} {value['count']:3d}")
        return 0
    if not (args.html_dir and args.out):
        parser.error("--html-dir and --out are required to measure")
    tasks = args.tasks or list(DEFAULT_TASKS)
    bridge = tool.Bridge(args.html_dir, args.node_modules_dir, substrate=args.substrate)
    versions = bridge.versions()
    with open(args.out, "w") as handle:
        for task in tasks:
            row = measure_page(bridge, task, seed=args.seed, budget=args.budget)
            row["environment"] = versions
            handle.write(json.dumps(row) + "\n")
            cells = []
            for attempt in row.get("attempts") or []:
                if attempt.get("skipped"):
                    cells.append(f"{attempt['arm'][0]}:skip")
                else:
                    cells.append(f"{attempt['arm'][0]}:truth={attempt['reward_verdict']}"
                                 f"/contract={attempt['contract_verdict']}")
            print(f"{task:26s} found={row['found']} plan={row['plan_len']:2d} " + "  ".join(cells),
                  flush=True)
    bridge.close()
    return 0


def _consolidate(paths: Sequence[str], receipt: str | None) -> int:
    pages: list[dict[str, Any]] = []
    for path in paths:
        pages += [json.loads(line) for line in pathlib.Path(path).read_text().splitlines() if line.strip()]
    out = {"schema": SCHEMA, "authority": AUTHORITY, "kind": "receipt",
           "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "incremental_spend_usd": 0, "producer_cognition_model_dependency_count": 0,
           "summary": summarise(pages), "pages": pages}
    text = json.dumps(out, indent=1, sort_keys=True)
    if receipt:
        pathlib.Path(receipt).write_text(text + "\n")
        print(f"written {receipt}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
