"""Availability is a property of the LAYER: the same registry, probed at both doors.

Round 4 (A_PERFECT_ACTION_IS_NOT_AN_AVAILABLE_ACTION_20261112_V1.md) censused all 145
capabilities through `grounded_action_v1.act` and found the dominant failure mode to be
binding: 54 NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES vs 12 PRECONDITION and 59 SELECTED.
That number has been driving the ranked plan ever since.

But the tree has TWO binding surfaces:

  * `grounded_action_v1.act` -- the step executor used by chain_v1/macro_v1/completion
    battery.  It binds through `world_binding_v1.complete_inputs` alone.
  * `live_brain_route_admission_v1.solve` -- the door a sentence actually enters.  It
    compiles (typed plan / front compiler), runs `declared_input_derivation_v1` -- the
    module that drops adapter-defaulted slots and proves values the sentence states in
    another shape -- and merges proven inputs before execution.

Spot checks on this base already showed the gap is real: "read the git log" is
NOT_CALLABLE / PRECONDITION at act (7 of 8 slots missing, blind premise
`git.repository.available`) and pass=True at the door (op=log executed and verified).
The two SWE sentences round 4 showed failing at act fail at the door too -- but with
plan-level statuses (NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT,
FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED), not binding statuses.

This probe censuses the SAME goals at BOTH layers, inside a disposable clone so no
live state or file in this repository can be touched, and adjudicates the plan-driving
number.

PRE-REGISTERED PREDICTIONS (written before the first full run):

  P1  The door compiles a capability to itself for strictly more of the 145 goals than
      `act` selects it (round 4's act baseline: 59; re-measured live here).
  P2  More than half of the act-level NOT_CALLABLE rejections for the same goals do not
      appear at the door (derivation + typed plan exist only there).
  P3  The door's dominant NON-availability class is plan/selection level
      (no compiled capability, or routed elsewhere), not NOT_CALLABLE binding.
  P4  At least one capability that `act` rejects with PRECONDITION_NOT_TRUE_OF_WORLD
      still executes at the door -- `git.repository.operate.v1` is the known candidate.
  P5  No probe crash: adapter exceptions are recorded as fates, count <= 5.

Authority NONE.  One machine, $0, zero model dependency, disposable clone state.
Nothing here claims any capability's work is correct -- only whether it is reachable.

Run (from a clone of this branch, so writes cannot land here):
    git clone --quiet --no-local <repo> /tmp/census_clone
    cd /tmp/census_clone && python3 door_and_act_availability_census_20261112.py --out /tmp/census.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _keywords(entry: dict) -> list[str]:
    words = entry.get("keywords") or []
    return [str(w) for w in words if isinstance(w, (str, int, float)) and str(w).strip()]


def _goal_for(entry: dict) -> str | None:
    words = _keywords(entry)
    if not words:
        return None
    return " ".join(words[:10])


def _act_fate(result: dict, cid: str) -> dict:
    """Classify one GA.act verdict the way round 4's table did."""
    rejected = [r for r in (result.get("rejected") or []) if isinstance(r, dict)]
    mine = [r for r in rejected if str(r.get("capability_id")) == cid]
    selected = str(result.get("capability_id") or "")
    whys = [str(r.get("why") or "") for r in mine]
    out = {
        "selected": selected,
        "status": str(result.get("status") or ""),
        "executed": bool(result.get("executed")),
        "verified": bool(result.get("verified")),
        "reject_whys": whys,
    }
    if selected == cid:
        out["fate"] = "SELECTED"
    elif whys:
        # Round 4's collapse kept ONE row per capability; the kinds test shows the
        # dict-comprehension form, so the LAST reject row wins when several exist.
        out["fate"] = whys[-1]
    elif selected:
        out["fate"] = "ROUTED_ELSEWHERE"
    else:
        out["fate"] = "NOT_A_CANDIDATE_FOR_OWN_KEYWORDS"
    return out


def _door_fate(verdict: dict, cid: str) -> dict:
    compiled = str(verdict.get("compiled_capability_id") or "")
    admission = verdict.get("route_admission") or {}
    out = {
        "pass": bool(verdict.get("pass")),
        "status": str(verdict.get("status") or ""),
        "compiled": compiled,
        "route_selected": str(admission.get("selected_capability") or ""),
        "route_rule": str(admission.get("rule") or ""),
        "executed": bool(verdict.get("executed")),
    }
    if verdict.get("pass"):
        out["fate"] = "EXECUTED"
    elif compiled == cid:
        out["fate"] = "COMPILED_TO_SELF_BUT_FAILED"
    elif compiled:
        out["fate"] = "ROUTED_ELSEWHERE"
    else:
        out["fate"] = "NOT_COMPILED"
    return out


def run_census(root: pathlib.Path) -> dict:
    # Imports happen here so the probe can only run as the process whose sys.path
    # points at `root` -- the caller's job to arrange (a clone).
    from canonical.runtime import grounded_action_v1 as GA
    from canonical.runtime import live_brain_route_admission_v1 as door

    registry = json.loads(
        (root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
    )["capabilities"]

    rows = []
    exceptions = []
    started = time.time()
    for index, cid in enumerate(sorted(registry), 1):
        entry = registry[cid]
        goal = _goal_for(entry)
        row = {"capability_id": cid, "keywords": len(_keywords(entry))}
        if goal is None:
            row["act"] = {"fate": "NO_KEYWORDS_DECLARED"}
            row["door"] = {"fate": "NO_KEYWORDS_DECLARED"}
            rows.append(row)
            continue
        row["goal"] = goal

        try:
            act = GA.act(
                goal, root=root, memory=False, bridge=False, computer_use=False
            )
            row["act"] = _act_fate(act or {}, cid)
        except Exception as exc:  # noqa: BLE001 - a raise is a fate, not a crash
            row["act"] = {"fate": "ADAPTER_RAISED", "error": repr(exc)[:300]}
            exceptions.append({"layer": "act", "capability_id": cid, "error": repr(exc)[:300]})

        try:
            verdict = door.solve({"task_id": f"census_{index}", "goal": goal})
            row["door"] = _door_fate(verdict or {}, cid)
        except Exception as exc:  # noqa: BLE001
            row["door"] = {"fate": "DOOR_RAISED", "error": repr(exc)[:300]}
            exceptions.append({"layer": "door", "capability_id": cid, "error": repr(exc)[:300]})

        rows.append(row)
        if index % 25 == 0:
            print(f"  ... {index}/{len(registry)} ({time.time() - started:.0f}s)", flush=True)

    return {
        "schema": "PROJECT_BRAIN_DOOR_AND_ACT_AVAILABILITY_CENSUS_V1",
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "root": str(root),
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_s": round(time.time() - started, 1),
        "capabilities": len(registry),
        "rows": rows,
        "exceptions": exceptions,
    }


def summarize(report: dict) -> dict:
    from collections import Counter

    act = Counter(r["act"]["fate"] for r in report["rows"])
    door = Counter(r["door"]["fate"] for r in report["rows"])
    act_selected = [r["capability_id"] for r in report["rows"] if r["act"]["fate"] == "SELECTED"]
    act_not_callable = [
        r["capability_id"] for r in report["rows"]
        if r["act"]["fate"] == "NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES"
    ]
    act_precondition = [
        r["capability_id"] for r in report["rows"]
        if r["act"]["fate"] == "PRECONDITION_NOT_TRUE_OF_WORLD"
    ]
    door_exec = [r["capability_id"] for r in report["rows"] if r["door"]["fate"] == "EXECUTED"]
    door_self_fail = [
        r["capability_id"] for r in report["rows"]
        if r["door"]["fate"] == "COMPILED_TO_SELF_BUT_FAILED"
    ]
    door_routed = [
        r["capability_id"] for r in report["rows"] if r["door"]["fate"] == "ROUTED_ELSEWHERE"
    ]
    door_not = [
        r["capability_id"] for r in report["rows"] if r["door"]["fate"] == "NOT_COMPILED"
    ]
    # P2: of the act NOT_CALLABLE set, how many do NOT carry that rejection at the door
    # (door reached them by any route: executed, self-fail, or routed elsewhere --
    # the door never emits NOT_CALLABLE, so "not rejected as binding" == reached past
    # the compile stage OR failed for another reason).
    not_callable_at_door = 0
    for r in report["rows"]:
        if r["capability_id"] in act_not_callable:
            if r["door"]["fate"] in ("EXECUTED", "COMPILED_TO_SELF_BUT_FAILED", "ROUTED_ELSEWHERE"):
                not_callable_at_door += 1
    # P4: act PRECONDITION set -- door executed?
    precondition_executed = sorted(set(act_precondition) & set(door_exec))
    return {
        "act_fates": dict(act.most_common()),
        "door_fates": dict(door.most_common()),
        "act_selected": len(act_selected),
        "act_not_callable": len(act_not_callable),
        "act_precondition": len(act_precondition),
        "door_executed": len(door_exec),
        "door_compiled_to_self_total": len(door_exec) + len(door_self_fail),
        "door_compiled_to_self_failed": len(door_self_fail),
        "door_routed_elsewhere": len(door_routed),
        "door_not_compiled": len(door_not),
        "not_callable_reached_past_compile_at_door": not_callable_at_door,
        "precondition_executed_at_door": precondition_executed,
        "exceptions": len(report["exceptions"]),
        "door_statuses": dict(
            Counter(
                r["door"].get("status", "")
                for r in report["rows"]
                if r["door"]["fate"] in ("NOT_COMPILED", "COMPILED_TO_SELF_BUT_FAILED", "ROUTED_ELSEWHERE")
            ).most_common(12)
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default="")
    ns = ap.parse_args()
    root = pathlib.Path(ns.root).resolve()
    report = run_census(root)
    report["summary"] = summarize(report)
    text = json.dumps(report, indent=1, sort_keys=True)
    if ns.out:
        pathlib.Path(ns.out).write_text(text, encoding="utf-8")
    print(json.dumps(report["summary"], indent=1, sort_keys=True))
    print("elapsed_s", report["elapsed_s"], "exceptions", len(report["exceptions"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
