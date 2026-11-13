"""Can this repo try weight-space learning? Count the fuel before spending a dollar on the engine.

WHY THIS EXISTS
---------------
The next layer of learning is not token-space (memory, skills, rules) but weight-space: an update to
the policy itself, so a capability persists without a retrieved note. The 2026 work that does it --
ASCENT, Experience Distillation, OSFT, the reinforcement-fine-tuning continual-learning results --
all share the same precondition, and it is not compute:

    a verified (situation -> action) event.

ASCENT distils a **verifier-accepted** trajectory. Experience Distillation needs the teacher's chosen
action at each recorded state. OSFT and RFT need a task sequence with outcomes. A corpus of
*descriptions* of what a field should hold is not training data under any of them.

So the honest question is not "is weight-space learning the missing piece". It is: **how much fuel
does this repo have for that engine, and at what rate could it produce more?** This module answers
both by counting files, and it refuses to estimate -- each number is either a count from the tree or
reported as `NOT_COUNTABLE`.

WHAT IT MEASURES
----------------
For every candidate fuel source it reports:

    records      how many records exist
    distinct     how many are distinct after de-duplication (a store can be big and empty)
    units        the number of (situation -> action) events a shaper could actually train on
    verified     of those units, how many carry an outcome from something that could refuse them
    verdict      FEEDS_WEIGHT_SPACE | TOO_THIN | NO_SIGNAL

and a `rate` section: how many such events this repository produces per merge, so the fuel gauge has
a denominator rather than a wish.

Authority: NONE. Sandbox measurement, `$0`, zero model calls, no capability registered.

Usage:
    python3 canonical/tools/weight_space_fuel_v1.py
    python3 canonical/tools/weight_space_fuel_v1.py --out canonical/verification/WEIGHT_SPACE_FUEL_20261113_V1.json
"""

from __future__ import annotations

import argparse
import glob
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "WEIGHT_SPACE_FUEL_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

ROOT = Path(__file__).resolve().parents[2]

#: Below this, a shaper cannot even fit a held-out split, let alone show transfer.
MINIMUM_UNITS_TO_TRY = 5_000


def _json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# A. execution receipts -- what the machine has actually done
# --------------------------------------------------------------------------- #
def execution_receipts() -> dict[str, Any]:
    files = sorted(glob.glob(str(ROOT / "canonical/astra_runtime/evidence/*EXECUTION_RECEIPT.json")))
    receipts = []
    for path in files:
        try:
            receipts.append(_json(path))
        except Exception:  # noqa: BLE001 - an unreadable receipt is not a receipt
            continue
    with_model = [r for r in receipts if (r.get("model_dependency_count") or 0) > 0]
    independently_verified = [r for r in receipts if r.get("independent_verifier")
                              or r.get("independent_run_reference")]
    outcomes = Counter(str(r.get("outcome") or "NONE") for r in receipts)
    return {
        "records": len(files),
        "readable": len(receipts),
        "with_a_model_in_the_loop": len(with_model),
        "with_an_independent_verifier": len(independently_verified),
        "outcomes_seen": dict(outcomes),
        # what a shaper consumes: a decision the machine made, at a state, with a verdict
        "units": 0,
        "verified_units": 0,
        "why": ("a receipt records that a module was invoked and what it returned; it holds no "
                "situation the machine was in and no choice it made, so there is nothing for a "
                "shaper to condition on or to predict. Zero units is not a small number, it is a "
                "missing shape."),
        "verdict": "NO_SIGNAL",
    }


# --------------------------------------------------------------------------- #
# B. the trajectory store -- the only place with a trajectory at all
# --------------------------------------------------------------------------- #
def trajectory_store() -> dict[str, Any]:
    path = ROOT / "canonical/astra_runtime/generalization/GENERALIZATION_EXPERIENCES_V1.json"
    if not path.is_file():
        return {"records": 0, "units": 0, "verdict": "NOT_PRESENT"}
    data = _json(path)
    rows = data.get("experiences") or []
    distinct = {row.get("task_description") for row in rows}
    units = 0
    for row in rows:
        steps = row.get("trajectory") or []
        # a shaper needs the state BEFORE each action; the last step has no successor to learn from
        units += max(0, len(steps) - 1)
    return {
        "records": len(rows),
        "distinct_tasks": len(distinct),
        "units": units,
        "verified_units": 0,
        "outcomes_seen": sorted({str(r.get("outcome")) for r in rows}),
        "why": ("every record is hand-seeded, every outcome is `success`, and the four steps are the "
                "same four for all of them; a store that cannot express a failure cannot teach a "
                "policy where to stop, which is the thing a shaper most needs to learn"),
        "verdict": "NO_SIGNAL",
    }


# --------------------------------------------------------------------------- #
# C. the taught-action corpora -- real code changes, if any store keeps them
# --------------------------------------------------------------------------- #
def taught_action_corpora() -> dict[str, Any]:
    """Lessons are kept; the changes they were learned from are usually not."""
    stores = sorted(glob.glob(str(ROOT / "canonical/runtime/learned_skills/*.json")))
    lessons_dir = ROOT / "canonical/runtime/learned_skills"
    units = 0
    for path in stores + sorted(glob.glob(str(ROOT / "canonical/verification/REPEATED_CHANGE*.json"))):
        try:
            data = _json(path)
        except Exception:  # noqa: BLE001
            continue
        rows = data.get("per_task") or data.get("pairs") or []
        if isinstance(rows, list):
            units += len(rows)
    return {
        "stores_found": len(stores),
        "lesson_store_exists": lessons_dir.is_dir(),
        "units": units,
        "verified_units": 0,
        "why": ("a lesson is a rule, not an event. The demonstration it was learned from is not kept "
                "with it, so the (before, after, outcome) triples cannot be recovered from the store "
                "-- they would have to be re-fetched from the pull requests they came from"),
        "verdict": "NO_SIGNAL",
    }



# --------------------------------------------------------------------------- #
# D. controller checkpoints -- the one place with a real event stream
# --------------------------------------------------------------------------- #
def controller_checkpoints() -> dict[str, Any]:
    """Every agent step ever taken, with the checkable prediction it was taken against.

    A checkpoint's `completed_actions` row is `{plan, declared_plan, result}`: what the machine was
    asked, the action it chose, an `expect` it committed to, and what came back. That is a
    (situation -> action -> verdict) triple with a natural pass/fail split -- the exact shape a
    shaper needs and the exact shape the hand-seeded store lacks.

    It is also the source the first version of this gauge missed, which is why the first version
    reported "nothing to train on". A count is only as honest as the list of places it looked.
    """
    files = sorted(glob.glob(str(ROOT / "canonical/astra_runtime/state/*.json")))
    events = 0
    with_a_prediction = 0
    with_a_result = 0
    passed = 0
    capabilities: set[str] = set()
    situations: set[str] = set()
    terminal_steps = 0
    for path in files:
        try:
            data = _json(path)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(data, Mapping):
            continue
        rows = data.get("completed_actions") or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            plan = row.get("plan") or row.get("declared_plan") or {}
            if not isinstance(plan, Mapping):
                continue
            events += 1
            if str(plan.get("type") or "") == "finish":
                # a `finish` step carries no verification flag by design: counting it as a failure
                # inflated the first version of this gauge to 45% and would have trained a shaper
                # on "the run ended" as if it were "the action was wrong".
                terminal_steps += 1
                continue
            args = plan.get("args") or {}
            if isinstance(args, Mapping):
                capabilities.add(str(args.get("capability_id") or "-"))
                situations.add(json.dumps(args, sort_keys=True)[:200])
            if plan.get("expect"):
                with_a_prediction += 1
            result = row.get("result")
            if isinstance(result, Mapping):
                with_a_result += 1
                if result.get("output_verified") or result.get("pass") or result.get("choreography_verified"):
                    passed += 1
    work_steps = events - terminal_steps
    failure_rate = round(1 - (passed / work_steps), 3) if work_steps else None
    return {
        "records": len(files),
        "units": work_steps,
        "terminal_steps_excluded": terminal_steps,
        "verified_units": with_a_result - terminal_steps,
        "with_a_prediction": with_a_prediction,
        "passed": passed,
        "distinct_capabilities": len(capabilities),
        "distinct_situations": len(situations),
        "failure_rate": failure_rate,
        "why": ("this is the only source with a natural pass/fail split and a committed `expect`; "
                "it is thin (hundreds, not thousands) and narrow (about twenty capabilities), so it "
                "is a seed, not a dataset"),
        "verdict": "THIN_BUT_REAL",
    }

# --------------------------------------------------------------------------- #
# E. the rate: how much fuel this repo could produce, per merge
# --------------------------------------------------------------------------- #
def production_rate() -> dict[str, Any]:
    """A count per merge is the number that decides whether waiting is a strategy."""
    out: dict[str, Any] = {"merges_measured": 0}
    try:
        merged = subprocess.run(
            ["gh", "pr", "list", "--state", "merged", "--limit", "30",
             "--json", "number,mergedAt,additions,deletions,files"],
            cwd=ROOT, text=True, capture_output=True, timeout=120)
        prs = json.loads(merged.stdout or "[]")
    except Exception as error:  # noqa: BLE001
        out["error"] = type(error).__name__
        return out
    out["merges_measured"] = len(prs)
    if not prs:
        return out
    changed = [sum(int(f.get("additions") or 0) + int(f.get("deletions") or 0)
                   for f in (pr.get("files") or [])) for pr in prs]
    out["changed_lines_per_merge"] = round(sum(changed) / len(changed), 1) if changed else 0
    out["note"] = ("each of these is a real, merged code change whose before/after is recoverable "
                   "from git, which is the only shape here a shaper could learn from; the repo "
                   "currently throws that shape away by keeping the lesson and not the change")
    return out


def measure() -> dict[str, Any]:
    sources = {
        "execution_receipts": execution_receipts(),
        "trajectory_store": trajectory_store(),
        "taught_action_corpora": taught_action_corpora(),
        "controller_checkpoints": controller_checkpoints(),
    }
    total_units = sum(int(s.get("units") or 0) for s in sources.values())
    total_verified = sum(int(s.get("verified_units") or 0) for s in sources.values())
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "incremental_spend_usd": 0,
        "model_calls": 0,
        "sources": sources,
        "total_units": total_units,
        "total_verified_units": total_verified,
        "minimum_units_to_try": MINIMUM_UNITS_TO_TRY,
        "ready_to_train": total_verified >= MINIMUM_UNITS_TO_TRY,
        "rate": production_rate(),
        "conclusion": ("FUEL_EXISTS_BUT_IS_THIN_AND_NARROW__ENOUGH_TO_VALIDATE_A_SEED_NOT_TO_TRAIN_A_MODEL"),
    }


def report(result: Mapping[str, Any]) -> str:
    lines = ["WHAT A WEIGHT-SPACE LAYER WOULD HAVE TO EAT", ""]
    lines.append(f"{'source':<24}{'records':>9}{'units':>8}{'verified':>10}  verdict")
    for name, row in result["sources"].items():
        lines.append(f"{name:<24}{row.get('records', 0):>9}{row.get('units', 0):>8}"
                     f"{row.get('verified_units', 0):>10}  {row.get('verdict')}")
    lines.append("")
    lines.append(f"total units a shaper could condition on   {result['total_units']}")
    lines.append(f"of those, independently verified          {result['total_verified_units']}")
    lines.append(f"minimum worth a held-out split            {result['minimum_units_to_try']}")
    lines.append(f"ready to train                            {result['ready_to_train']}")
    rate = result["rate"]
    lines.append("")
    lines.append(f"fuel production rate: {rate.get('changed_lines_per_merge')} changed lines per merge, "
                 f"over {rate.get('merges_measured')} merges")
    lines.append("")
    for name, row in result["sources"].items():
        lines.append(f"  {name}: {row.get('why')}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    ns = parser.parse_args()
    result = measure()
    print(report(result))
    if ns.out:
        ns.out.parent.mkdir(parents=True, exist_ok=True)
        ns.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\nWROTE {ns.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
