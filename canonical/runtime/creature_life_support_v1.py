"""Creature life support: the resident, crash-resumable loop that keeps the creature alive.

WHY THIS EXISTS
---------------
Every organ the creature needs already exists and is tested: `ContinuousSelf`
(identity, epochs, kill detection), `mortality_and_triage_v1` (a life granted once,
never renewed), `creature_runtime_v1` (the sovereign board, stepping, triage) and
`autonomous_awake_loop_v1.AwakeAgencyDaemon.pulse` (sense -> study -> CoW experiment
-> repair -> crystallize, zero external LLM calls). What did not exist was the
*beating heart*: nothing in production ever called these organs on a clock. The
creature only lived inside test functions. This module is the missing switch --
the same relation `live-learning-cycle.yml` has to the learning path, applied to
the creature itself.

It is deliberately thin (INTEGRATE, not a new primitive):

  * one daemon instance is constructed ONCE per process, so warm caches, the
    ignorance ledger, the skill store and the R3 queue persist across pulses;
  * each pulse is followed by a durable heartbeat (append-only JSONL + atomic
    latest-state JSON), so an outside observer can audit liveness after a crash;
  * SIGTERM/SIGINT stop the loop BETWEEN pulses, never mid-write;
  * mortality is respected exactly as `mortality_and_triage_v1` defines it: life
    is a budget of *work*, not wall-clock. Idle pulses spend nothing (measured).
    When the budget is gone the loop reports LIFE_OVER and exits; restarting the
    process never re-grants life (`LifeStore.load` ignores the grant on resume).

It measures nothing about sentience, experience or selfhood. It measures pulses,
work closed and life spent. `k3_external_llm_calls` is 0 on every path.

CLI:
    python -m canonical.runtime.creature_life_support_v1 \
        --workspace . --state /path/to/state --seconds 600
    python -m canonical.runtime.creature_life_support_v1 \
        --workspace . --state /path/to/state --pulses 3 --json
    python -m canonical.runtime.creature_life_support_v1 \
        --workspace . --state /path/to/state --resident
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import signal
import sys
import threading
import time
from typing import Any

SCHEMA = "PROJECT_BRAIN_CREATURE_LIFE_SUPPORT_V1"
HEARTBEAT_SCHEMA = "PROJECT_BRAIN_CREATURE_HEARTBEAT_V1"
DOES_NOT_MEASURE = "sentience, experience, selfhood"


def _atomic_write_json(path: pathlib.Path, row: dict[str, Any]) -> None:
    """tmp + os.replace, the same durability discipline as LifeStore.save."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(row, indent=1, sort_keys=True, default=str) + "\n",
                   encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl_fsync(path: pathlib.Path, row: dict[str, Any]) -> None:
    """Append one heartbeat and fsync, so a SIGKILL cannot lose a recorded pulse."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def run_life_support(
    workspace_root: str | pathlib.Path,
    state_root: str | pathlib.Path,
    *,
    identity: str = "creature",
    life: float = 40.0,
    pulses: int | None = None,
    seconds: float | None = None,
    interval_s: float = 0.05,
    resident: bool = False,
    apply_verified_repairs: bool = False,
    max_curriculum_lessons: int = 2,
    max_steps: int | None = None,
    install_signals: bool = True,
    stop_event: threading.Event | None = None,
) -> dict[str, Any]:
    """Beat until stopped, budget-exhausted, or life over. Returns a full report.

    `workspace_root` is the world the creature senses and (only with
    `apply_verified_repairs=True`) repairs. `state_root` is its durable body:
    creature state, ignorance ledger, skill store, workflow db, R3 queue and
    heartbeats all live there and survive any kill.

    Budgets: `pulses` caps the number of pulses; `seconds` is a SOFT wall-clock
    bound checked between pulses (the current pulse always finishes -- killing
    mid-pulse is what SIGKILL is for, and continuity survives that too).
    `resident=True` means no budget: beat until SIGTERM/SIGINT or LIFE_OVER.
    At least one of pulses/seconds/resident is required: an accidental infinite
    loop must be an explicit choice.
    """
    if pulses is None and seconds is None and not resident:
        raise ValueError("NO_BUDGET: pass pulses=, seconds=, or resident=True")
    if pulses is not None and int(pulses) < 1:
        raise ValueError("PULSES_MUST_BE_POSITIVE")
    if seconds is not None and float(seconds) <= 0:
        raise ValueError("SECONDS_MUST_BE_POSITIVE")
    if interval_s < 0:
        raise ValueError("INTERVAL_MUST_BE_NON_NEGATIVE")

    ws = pathlib.Path(workspace_root).resolve()
    st = pathlib.Path(state_root).resolve()
    st.mkdir(parents=True, exist_ok=True)
    hb_jsonl = st / "heartbeats.jsonl"
    hb_latest = st / "heartbeat.json"

    from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon

    daemon = AwakeAgencyDaemon(
        ws,
        journal_dir=st,
        ledger_path=st / "ignorance_ledger.json",
        skill_store_path=st / "skills.sqlite",
        workflow_db_path=st / "workflow.sqlite",
        creature_identity=identity,
        creature_life=float(life),
        apply_verified_repairs=bool(apply_verified_repairs),
    )
    boot_epoch = daemon.creature.report().get("epoch")

    stop = stop_event if stop_event is not None else threading.Event()
    previous_handlers: dict[int, Any] = {}
    if install_signals:
        def _on_signal(signum: int, _frame: Any) -> None:
            stop.set()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                previous_handlers[sig] = signal.signal(sig, _on_signal)
            except (ValueError, OSError):
                # Not on the main thread (e.g. embedded in a test worker): the
                # caller owns stopping via stop_event instead.
                continue

    t0 = time.monotonic()
    n_pulses = 0
    stopped_by = "ERROR"
    last_error: str | None = None
    last_snap: dict[str, Any] | None = None
    try:
        while True:
            if stop.is_set():
                stopped_by = "SIGNAL"
                break
            if pulses is not None and n_pulses >= int(pulses):
                stopped_by = "MAX_PULSES"
                break
            if seconds is not None and (time.monotonic() - t0) >= float(seconds):
                stopped_by = "MAX_SECONDS"
                break
            if daemon.creature.report().get("ended"):
                stopped_by = "LIFE_OVER"
                break
            try:
                last_snap = daemon.pulse(
                    max_curriculum_lessons=int(max_curriculum_lessons),
                    max_steps=max_steps,
                )
            except Exception as exc:  # a failing pulse must not kill the heart
                last_error = f"{type(exc).__name__}: {exc}"
                _append_jsonl_fsync(hb_jsonl, {
                    "schema": HEARTBEAT_SCHEMA, "pulse": n_pulses + 1,
                    "identity": identity, "error": last_error,
                    "at_monotonic_s": round(time.monotonic() - t0, 3),
                })
                stopped_by = "ERROR"
                break
            n_pulses += 1
            creature_row = last_snap.get("creature") or {}
            hb = {
                "schema": HEARTBEAT_SCHEMA,
                "pulse": n_pulses,
                "identity": creature_row.get("identity", identity),
                "epoch": creature_row.get("epoch"),
                "cycle": last_snap.get("cycle"),
                "life_remaining": creature_row.get("life_remaining"),
                "life_spent": creature_row.get("life_spent"),
                "closed": creature_row.get("closed"),
                "open": creature_row.get("open"),
                "gaps_studied": last_snap.get("gaps_studied"),
                "gaps_closed": last_snap.get("gaps_closed"),
                "creature_steps": len(last_snap.get("creature_steps") or []),
                "k3_external_llm_calls": int(last_snap.get("k3_external_llm_calls") or 0),
                "elapsed_ms": last_snap.get("elapsed_ms"),
                "at_monotonic_s": round(time.monotonic() - t0, 3),
            }
            _append_jsonl_fsync(hb_jsonl, hb)
            _atomic_write_json(hb_latest, hb)
            if stop.is_set():
                stopped_by = "SIGNAL"
                break
            if interval_s > 0:
                stop.wait(float(interval_s))
    finally:
        for sig, handler in previous_handlers.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass

    report = daemon.creature.report()
    out = {
        "schema": SCHEMA,
        "identity": report.get("identity", identity),
        "workspace_root": str(ws),
        "state_root": str(st),
        "boot_epoch": boot_epoch,
        "epoch": report.get("epoch"),
        "pulses": n_pulses,
        "stopped_by": stopped_by,
        "ended": bool(report.get("ended")),
        "life_remaining": report.get("life_remaining"),
        "life_spent": report.get("life_spent"),
        "board": report.get("board"),
        "closed": report.get("closed"),
        "open": report.get("open"),
        "parked": report.get("parked"),
        "posture": report.get("posture"),
        "value_realised": report.get("value_realised"),
        "elapsed_s": round(time.monotonic() - t0, 3),
        "resident": bool(resident),
        "apply_verified_repairs": bool(apply_verified_repairs),
        "k3_external_llm_calls": 0,
        "does_not_measure": DOES_NOT_MEASURE,
        "last_pulse": ({
            "cycle": last_snap.get("cycle"),
            "gaps_studied": last_snap.get("gaps_studied"),
            "gaps_closed": last_snap.get("gaps_closed"),
            "creature_steps": len(last_snap.get("creature_steps") or []),
            "elapsed_ms": last_snap.get("elapsed_ms"),
        } if last_snap is not None else None),
    }
    if last_error is not None:
        out["error"] = last_error
    _atomic_write_json(st / "life_support_report.json", out)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="creature_life_support_v1",
        description="Resident, crash-resumable life loop for the Brain creature. "
                    "Zero external LLM calls; never re-grants life on restart.",
    )
    ap.add_argument("--workspace", required=True, help="world the creature senses/repairs")
    ap.add_argument("--state", required=True, help="durable body: creature state + heartbeats")
    ap.add_argument("--identity", default="creature")
    ap.add_argument("--life", type=float, default=40.0,
                    help="life granted AT BIRTH ONLY; ignored on resume (mortality law)")
    ap.add_argument("--pulses", type=int, default=None, help="stop after N pulses")
    ap.add_argument("--seconds", type=float, default=None,
                    help="soft wall-clock budget, checked between pulses")
    ap.add_argument("--resident", action="store_true",
                    help="no budget: beat until SIGTERM/SIGINT or life over")
    ap.add_argument("--interval-s", type=float, default=0.05,
                    help="idle wait between pulses")
    ap.add_argument("--max-curriculum-lessons", type=int, default=2)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--apply-verified-repairs", action="store_true",
                    help="write verified CoW repairs back into the workspace "
                         "(default off: experiment and learn without mutation)")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = ap.parse_args(argv)

    if args.pulses is None and args.seconds is None and not args.resident:
        ap.error("pass --pulses, --seconds, or --resident (an infinite loop must be explicit)")

    out = run_life_support(
        args.workspace, args.state,
        identity=args.identity, life=args.life,
        pulses=args.pulses, seconds=args.seconds, resident=args.resident,
        interval_s=args.interval_s,
        apply_verified_repairs=args.apply_verified_repairs,
        max_curriculum_lessons=args.max_curriculum_lessons,
        max_steps=args.max_steps,
    )
    if args.json:
        print(json.dumps(out, indent=1, sort_keys=True, default=str))
    else:
        print(f"[{out['schema']}] identity={out['identity']} epoch={out['epoch']} "
              f"pulses={out['pulses']} stopped_by={out['stopped_by']} "
              f"life_remaining={out['life_remaining']} closed={out['closed']} "
              f"open={out['open']} parked={out['parked']} posture={out['posture']} "
              f"elapsed_s={out['elapsed_s']} k3_external_llm_calls=0")
    return 0 if out["stopped_by"] != "ERROR" else 1


if __name__ == "__main__":
    sys.exit(main())
