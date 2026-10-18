#!/usr/bin/env python3
"""Run the Brain's verified learning loop once, on fresh goals, and carry the store forward.

WHY THIS EXISTS.  The learning loop is complete and wired:

    live_brain_runtime_v1.run_decision(learn=True)
        -> autonomous_verified_self_improvement_v1.run_learning_episode
        -> integrate_solver_output          (episode not yet independently proved
                                             -> enqueued as VERIFY_EPISODE work)
        -> r3_improvement_queue_driver_v1.drain
        -> r3_independent_learning_verifier_v1.verify_episode_request
                                            (Brain-owned, executor cannot certify
                                             its own episode)
        -> promoted into the durable verified-episode / skill store
        -> read back next time as a planning compression overlay

...and nothing on a schedule ever runs it.  The only scheduled job in this
repository (live-brain-heartbeat.yml) is a liveness exam: it solves ~150 fresh
goals a day, judges them with stdlib oracles, proves the machine is alive, and
discards every outcome -- correctly, because it must not learn from its own
exam.  Every other workflow that touches this path only runs its unit tests.

So the machine's self-improvement loop executes exactly never in production.
This script is the switch that closes it.  It builds nothing new.

ONE CYCLE
    1. restore  durable R3 store from the previous run's artifact, if any
    2. promote  drain the queue with the Brain-owned independent verifier
    3. attempt  fresh cases through route_admission.solve -- the same entry the
                heartbeat proves alive -- and let each case's stdlib oracle judge
                the real artifact; only that verdict is written to memory, by
                experience_v1.observe (the recorder that will not suppress a
                capability on a run of bad luck alone)
    4. promote  drain again; whatever the independent verifier can re-derive
                becomes durable learned routes, the rest stays pending
    5. carry    write the durable store + experience store beside the receipt

The oracle is the Brain's own: V12 verifies execution, the independent verifier
recomputes the evidence.  This script grades nothing and asserts nothing about
the answers -- it only reports what the machine retained.

Authority: NONE.  Credit: 0.  It never pushes, never merges, never writes to main.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_LIVE_LEARNING_CYCLE_V1"

# gitignored on purpose: durable learning is carried as an artifact, never committed
STATE_NAME = "SELF_IMPROVEMENT_STATE_V1.json"
EXPERIENCE_REL = "canonical/runtime/state/experience_v1.json"
WORK = "canonical/astra_runtime/tmp/live_learning_cycle"


# --------------------------------------------------------------------------- store

def _learning():
    from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
    return learning


def _store_snapshot(state_path: Path) -> dict[str, Any]:
    """What the machine actually has.  No inference, no vibes."""
    learning = _learning()
    state = learning.load_state(state_path)
    queue = state.get("improvement_queue") or {}
    if not isinstance(queue, Mapping):
        queue = {}
    pending = parked = 0
    for row in queue.values():
        if not isinstance(row, Mapping):
            continue
        if row.get("status") == "PENDING":
            pending += 1
        elif row.get("status") == "PARKED":
            parked += 1
    return {
        "episodes_verified": len(state.get("episodes") or {}),
        "skills_verified": len(state.get("skills") or {}),
        "failure_classes": len(state.get("failures") or {}),
        "queue_pending": pending,
        "queue_parked": parked,
        "stats": dict(state.get("stats") or {}),
    }


def _experience_snapshot() -> dict[str, Any]:
    try:
        from canonical.runtime import experience_v1 as exp
        s = exp.summary()
        return {
            "cell_count": s.get("cell_count"),
            "credited": list(s.get("credited") or []),
            "suppressed": list(s.get("suppressed") or []),
            "resolution_count": s.get("resolution_count"),
        }
    except Exception as exc:
        return {"error": type(exc).__name__ + ":" + str(exc)}


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def restore(state_in: Path | None, state_path: Path, quarantine: Path) -> dict[str, Any]:
    """Put yesterday's durable store back where the machine expects it.

    An unattended loop must not die on a bad handoff.  The restored file is
    admitted only if the store's own loader accepts it; otherwise it is set
    aside and the cycle starts from empty rather than crashing or, worse,
    silently trusting a document it cannot read.
    """
    if state_in is None:
        return {"restored": False, "reason": "NO_STATE_IN"}
    src = state_in / STATE_NAME
    if not src.is_file():
        return {"restored": False, "reason": "STATE_ARTIFACT_ABSENT", "looked_at": str(src)}
    state_path.parent.mkdir(parents=True, exist_ok=True)
    probe = state_path.with_name(state_path.name + ".restore_probe")
    shutil.copyfile(src, probe)
    try:
        _learning().load_state(probe)
    except Exception as exc:
        quarantine.mkdir(parents=True, exist_ok=True)
        kept = quarantine / (STATE_NAME + ".rejected")
        shutil.copyfile(src, kept)
        probe.unlink(missing_ok=True)
        return {
            "restored": False,
            "reason": "STATE_ARTIFACT_REJECTED_BY_STORE_LOADER",
            "detail": type(exc).__name__ + ":" + str(exc)[:200],
            "quarantined_as": str(kept),
        }
    probe.replace(state_path)
    return {"restored": True, "sha256": _sha256(state_path), "bytes": src.stat().st_size}


def carry(out: Path, state_path: Path) -> dict[str, Any]:
    """Write the store out so the next run does not start from zero."""
    out.mkdir(parents=True, exist_ok=True)
    carried = {}
    if state_path.is_file():
        shutil.copyfile(state_path, out / STATE_NAME)
        carried[STATE_NAME] = _sha256(out / STATE_NAME)
    exp = ROOT / EXPERIENCE_REL
    if exp.is_file():
        shutil.copyfile(exp, out / "experience_v1.json")
        carried["experience_v1.json"] = _sha256(out / "experience_v1.json")
    return carried


# --------------------------------------------------------------------------- goals

def fresh_cases(rng: random.Random, work: Path, count: int) -> list[Any]:
    """Fresh cases this run has never seen: one plain sentence + one stdlib oracle.

    Reuses the heartbeat's own generator contract, so every input is built from
    os.urandom and no run can rehearse the next one's answers.  The oracle
    judges the real artifact -- it is the independent adjudicator, which is why
    its verdict may be written to memory at all.
    """
    from execution_guard import live_solver_families_v5 as fam

    gens = [
        fam.gen_math_numeric_sympy,
        fam.gen_json_query_jq,
        fam.gen_python_fault_localize,
        fam.gen_python_ast_patch_search,
    ]
    cases: list[Any] = []
    for i in range(max(0, count)):
        try:
            cases.append(gens[i % len(gens)](rng, work, i))
        except Exception:
            continue
    return cases


# --------------------------------------------------------------------------- steps

def promote(*, state_path: Path, max_rounds: int, max_actions: int) -> dict[str, Any]:
    """Drain queued work with the Brain-owned independent verifier."""
    from canonical.runtime import r3_verified_fixed_point_driver_v1 as fixed_point
    try:
        res = fixed_point.run(
            state_path=state_path,
            repo_root=ROOT,
            max_rounds=max_rounds,
            max_actions_per_round=max_actions,
        )
        return {
            "pass": res.get("pass") is True,
            "status": res.get("status"),
            "round_count": res.get("round_count"),
            "fixed_point": res.get("fixed_point") is True,
            "pending_work": res.get("pending_work") or [],
            "parked_work": res.get("parked_work") or [],
        }
    except Exception as exc:
        return {"pass": False, "status": "PROMOTION_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)}


def attempt(
    cases: list[Any],
    *,
    run_tag: str,
    observe: bool,
) -> list[dict[str, Any]]:
    """Run each fresh case through THE live entry, then let the oracle feed memory.

    The entry is route_admission.solve -- the one the heartbeat already proves
    alive every day.  Its result is not graded by us: the case's stdlib oracle
    judges the real artifact, exactly as the heartbeat does.  Only that verdict
    is written to memory, through experience_v1.observe -- the recorder that
    already refuses to suppress a capability on a run of bad luck alone.
    """
    from canonical.runtime import live_brain_route_admission_v1 as route_admission
    from canonical.runtime import experience_v1 as exp
    from execution_guard.live_solver_end_to_end_measurement_v1 import environment_blocker

    rows: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        started = time.perf_counter()
        family = str(getattr(case, "family", "?"))
        row: dict[str, Any] = {
            "index": index,
            "family": family,
            "goal": str(case.goal)[:220],
        }
        # task ids must be unique: the live controller checkpoints per task id
        task_id = f"{run_tag}_{family}_{index}"
        try:
            result = route_admission.solve({"task_id": task_id, "goal": case.goal})
            if not isinstance(result, Mapping):
                raise ValueError("LIVE_ENTRY_RETURNED_NON_OBJECT")
            row["status"] = result.get("status")
            try:
                good, why = case.oracle(dict(result))
            except Exception as exc:
                good, why = False, "ORACLE_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)[:200]
            row["oracle_pass"] = bool(good)
            row["oracle_reason"] = (why or "")[:200]
            row["capability_id"] = str(
                result.get("compiled_capability_id")
                or result.get("compiler_mode")
                or "-"
            )
            # A missing apt package is a fact about THIS BOX, not about the
            # capability.  Recording it would teach the machine that json.query.jq
            # fails, and that memory would outlive the box it was made on.  The
            # heartbeat already separates these; memory has to as well.
            blocker = environment_blocker(result)
            row["environment_blocked"] = blocker
            if blocker:
                row["recorded"] = []
            if observe and not blocker:
                # verified is the oracle's verdict, never the executor's own claim.
                learned = exp.observe(
                    str(case.goal),
                    {
                        "capability_id": row["capability_id"],
                        "verified": bool(good),
                        "error": "" if good else str(
                            result.get("failure_class")
                            or result.get("status")
                            or ""
                        ),
                    },
                )
                row["recorded"] = learned.get("recorded")
        except Exception as exc:
            row["oracle_pass"] = False
            row["status"] = "ATTEMPT_EXCEPTION"
            row["error"] = type(exc).__name__ + ":" + str(exc)[:200]
        row["elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- main

def run(
    *,
    out: Path,
    state_in: Path | None,
    goal_count: int,
    max_rounds: int,
    max_actions: int,
    seed: str | None,
    observe: bool,
) -> dict[str, Any]:
    learning = _learning()
    state_path = Path(learning.DEFAULT_STATE_PATH)
    work = ROOT / WORK
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    seeded = seed is not None
    rng = random.Random(int(seed) if seeded else int.from_bytes(os.urandom(8), "big"))

    started = time.perf_counter()

    restored = restore(state_in, state_path, out)
    before = _store_snapshot(state_path)
    exp_before = _experience_snapshot()

    promote_before = promote(state_path=state_path, max_rounds=max_rounds, max_actions=max_actions)
    after_restore_promotion = _store_snapshot(state_path)

    run_tag = "llc_" + (str(seed) if seeded else hashlib.sha256(os.urandom(16)).hexdigest()[:12])
    cases = fresh_cases(rng, work, goal_count)
    attempts = attempt(cases, run_tag=run_tag, observe=observe) if cases else []
    after_attempts = _store_snapshot(state_path)

    promote_after = promote(state_path=state_path, max_rounds=max_rounds, max_actions=max_actions)
    after = _store_snapshot(state_path)
    exp_after = _experience_snapshot()

    carried = carry(out, state_path)

    receipt = {
        "schema": SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seeded_run": seeded,
        "authority": "NONE",
        "terminal_credit_delta": 0,
        "state_restore": restored,
        "goals_requested": goal_count,
        "goals_generated": len(cases),
        "observe_enabled": observe,
        "attempts": attempts,
        "attempts_oracle_passed": sum(1 for r in attempts if r.get("oracle_pass") is True),
        "attempts_environment_blocked": sum(1 for r in attempts if r.get("environment_blocked")),
        "attempts_recorded_to_memory": sum(1 for r in attempts if r.get("recorded")),
        "promotion_before": promote_before,
        "promotion_after": promote_after,
        "store_before": before,
        "store_after_restore_promotion": after_restore_promotion,
        "store_after_attempts": after_attempts,
        "store_after": after,
        "deltas": {
            "episodes_verified": after["episodes_verified"] - before["episodes_verified"],
            "skills_verified": after["skills_verified"] - before["skills_verified"],
            "failure_classes": after["failure_classes"] - before["failure_classes"],
            "queue_pending": after["queue_pending"] - before["queue_pending"],
        },
        "experience_before": exp_before,
        "experience_after": exp_after,
        "carried": carried,
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="directory for the receipt and the carried store")
    ap.add_argument("--state-in", default=None, help="previous run's artifact dir holding " + STATE_NAME)
    ap.add_argument("--goals", type=int, default=8, help="fresh goals to attempt this cycle")
    ap.add_argument("--max-rounds", type=int, default=8)
    ap.add_argument("--max-actions", type=int, default=16)
    ap.add_argument("--seed", default=None, help="replay a seeded run; default is os.urandom")
    ap.add_argument("--no-observe", action="store_true",
                    help="run the cases without writing anything to memory (a control run)")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    receipt = run(
        out=out,
        state_in=Path(args.state_in) if args.state_in else None,
        goal_count=args.goals,
        max_rounds=args.max_rounds,
        max_actions=args.max_actions,
        seed=args.seed,
        observe=not args.no_observe,
    )
    (out / "LIVE_LEARNING_CYCLE_RECEIPT.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8"
    )
    (out / "SUMMARY.md").write_text(_summary(receipt), encoding="utf-8")
    print(_summary(receipt))
    return 0


def _summary(r: Mapping[str, Any]) -> str:
    d = r["deltas"]
    def n(key):
        return r["store_after"].get(key, 0)
    lines = [
        "# live learning cycle",
        "",
        f"- restored previous store: **{r['state_restore'].get('restored')}**"
        f" ({r['state_restore'].get('reason', '')})".rstrip(),
        f"- fresh cases generated: **{r['goals_generated']}** / requested {r['goals_requested']}",
        f"- oracle-judged passes: **{r['attempts_oracle_passed']}** / {len(r['attempts'])}",
        f"- memory writes enabled: **{r['observe_enabled']}**"
        f" (recorded {r['attempts_recorded_to_memory']},"
        f" environment-blocked {r['attempts_environment_blocked']} -- a missing"
        f" package is a fact about the box, not the capability)",
        "",
        "| store | before | after | delta |",
        "|---|---:|---:|---:|",
    ]
    for label, key in (
        ("verified episodes", "episodes_verified"),
        ("verified skills", "skills_verified"),
        ("failure classes", "failure_classes"),
        ("queue pending", "queue_pending"),
    ):
        lines.append(
            f"| {label} | {r['store_before'].get(key, 0)} | {n(key)} "
            f"| {'+' if d[key] >= 0 else ''}{d[key]} |"
        )
    lines += [
        "",
        f"- promotion (restored work): `{r['promotion_before'].get('status')}`",
        f"- promotion (new work): `{r['promotion_after'].get('status')}`",
        f"- carried: {', '.join(sorted(r['carried'])) or 'nothing'}",
        f"- elapsed: {r['elapsed_ms']} ms",
        "",
        "Authority: NONE. Credit: 0. Nothing here pushes, merges, or writes to main.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
