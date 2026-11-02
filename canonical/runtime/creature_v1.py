#!/usr/bin/env python3
"""The three organs, connected: one subject that chooses its own work and is changed by it.

WHY THIS EXISTS
---------------
Measured 2026-11-02, on `19626c6`. Three modules each work, each passes its own tests, and
none of them is ever run:

  * `continuous_self_v1`       -- 10 tests. No `__main__`, so it cannot be started as a process.
                                  `ContinuousSelf(` appears in exactly two places, both inside
                                  `test_continuous_self_survives_a_kill_v1.py`.
  * `creature_stakes_and_initiative_v1` -- 16 tests. `work()` and `choose()` have zero non-test
                                  callers, and its `main()` prints a report; it is not a loop.
  * `ignorance_ledger_v1`       -- 13 tests. `open_gaps()` is classified ORPHAN by
                                  `census_orphan_capabilities_v1.py`.

So `continuous-self.yml` and `creature-stakes.yml` prove, on every pull request, that a creature
*would* survive being killed and *would* be changed by its history -- and no creature exists to
kill. `continuous_self_v1` names the state one step further along: *"a thread that persists and
is affected by nothing is a scheduler with a diary."* What the tree had was the diary, with no
thread.

This module is the missing switch, and it is deliberately small. `ContinuousSelf.run` was already
built as dependency injection -- *"`next_task(state)` returns the next thing to do... Both are
injected: this module owns continuity, not judgement."* The judgement was the only absent part,
and it was absent only in the sense of being unwired: `choose()` is written and measured at
**own 981.0 vs random 491.0** on the demonstration ledger.

WHAT IT CONNECTS
----------------
    next_task  <-  choose(standing, obligations)      its own criterion, gated by its own posture
    obligations<-  ignorance_ledger.rank(...)          what it does not know, ranked by what it is
                                                       worth -- REAL gaps, not `demonstration_ledger()`
    perform    ->  live_brain_route_admission.solve    the same live entry the heartbeat proves
                                                       alive daily
    outcome    ->  standing.record(...)                so its history changes what it does next
    outcome    ->  ignorance_ledger.resolve(...)       so the ledger learns which ignorance matters

The last two edges are the ones that make it a creature rather than a runner. Without
`standing.record` the posture is decoration; without `resolve` the ledger's own docstring applies
-- *"Without it, rank() is a guess dressed up as a calculation."*

WHAT IT REFUSES TO DO
---------------------
* **It never fabricates an obligation.** If the ledger is empty it idles. `demonstration_ledger()`
  is a test fixture and is not reachable from here.
* **It never records an environment failure as its own.** `environment_blocker` is consulted
  first, for the reason `live_learning_cycle_v1` already states: a missing apt package is a fact
  about THIS BOX, and recording it would teach the machine that a capability fails -- a memory
  that outlives the box it was made on.
* **It grades nothing itself.** The live entry's own `pass`/`status` is the verdict. There is no
  oracle in this module, so there is no second opinion to disagree with the first.
* **It claims no authority.** `terminal_authority` is false throughout and no receipt follows
  from a run. A creature that ran is not a creature that proved anything.

Nothing here calls a model. Nothing here spends.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import continuous_self_v1 as cs
from canonical.runtime import creature_stakes_and_initiative_v1 as stakes
from canonical.runtime import ignorance_ledger_v1 as ledger

SCHEMA = "PROJECT_BRAIN_CREATURE_V1"

# Where the durable self lives. Gitignored on purpose: a creature's continuity is carried as an
# artifact by the workflow that runs it, exactly as `live_learning_cycle_v1` already carries the
# durable learning store ("never committed"). Committing it would make two runners disagree about
# who the same creature is.
DEFAULT_STATE_DIR = "canonical/astra_runtime/state/creature_v1"

# Every open gap is an obligation. `rank()` defaults to 5, which would hide most of the ledger
# from the thing whose initiative is supposed to cover it.
ALL_OBLIGATIONS = 100_000

DEFAULT_MAX_STEPS = 25


class CreatureError(RuntimeError):
    """A refusal with a name. Nothing in this module fails silently."""


# --------------------------------------------------------------------- obligations


def obligations_from_ledger(path: str | None = None, *,
                            limit: int = ALL_OBLIGATIONS) -> list[stakes.Obligation]:
    """What the machine does not know, as the things it could work on next.

    The mapping is exact and is the reason these two modules belong together:

        gap id      -> Obligation.id
        ledger      -> Obligation.value   (expected value of closing it, per unit cost)
        value()       gap cost            -> Obligation.cost
        resolved    -> Obligation.closed

    `checkable` has no counterpart in a gap. It is set True, which means the CAUTIOUS posture does
    not yet filter on it -- stated here rather than left to be discovered, because a posture that
    cannot narrow anything is the decoration `test_stakes_are_real_not_decoration_v1` exists to
    catch. Making it real needs a per-gap notion of "success is checkable", which the ledger does
    not carry and this module will not invent.
    """
    rows = ledger.rank(limit=limit, include_resolved=True, path=path)
    out: list[stakes.Obligation] = []
    for gap in rows:
        out.append(stakes.Obligation(
            id=str(gap.get("id") or ""),
            value=float(gap.get("value") or ledger.value(gap)),
            cost=float(gap.get("cost") or 1.0),
            checkable=True,
            closed=bool(gap.get("resolved")),
        ))
    return [o for o in out if o.id]


# ------------------------------------------------------------------------ the creature


class Creature:
    """One subject: continuity from `continuous_self_v1`, judgement from the other two."""

    def __init__(self, *, state_dir: pathlib.Path | str = DEFAULT_STATE_DIR,
                 ledger_path: str | None = None, identity: str | None = None,
                 performer: Callable[[str, str], Mapping[str, Any]] | None = None,
                 clock: Callable[[], float] | None = None,
                 beat_seconds: float = cs.DEFAULT_BEAT_SECONDS):
        self.state_dir = pathlib.Path(state_dir)
        self.ledger_path = ledger_path
        self._performer = performer or _default_perform
        kwargs: dict[str, Any] = {"state_path": self.state_dir / "self_state.json",
                                  "journal_path": self.state_dir / "journal.jsonl",
                                  "beat_seconds": beat_seconds}
        if identity is not None:
            kwargs["identity"] = identity
        if clock is not None:
            kwargs["clock"] = clock
        self.self = cs.ContinuousSelf(**kwargs)
        self.standing: stakes.Standing | None = None
        self._store = stakes.StandingStore(self.state_dir / "standing.json")
        self._before: dict[str, Any] | None = None
        self._current: stakes.Obligation | None = None
        self._current_goal: str = ""
        self._pool: list[stakes.Obligation] = []
        self.steps: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ judgement

    def obligations(self) -> list[stakes.Obligation]:
        """Fresh each call, so a gap resolved mid-run is not offered again."""
        self._pool = obligations_from_ledger(self.ledger_path)
        return self._pool

    def _ensure_standing(self) -> None:
        """Load the standing once, after `resume()` has settled the identity.

        Called lazily from `next_task` (first step) and from `run`'s finally (so a zero-step run
        still has a standing to report and save). Loading it in `__init__` would read a stale
        identity: on resume, `ContinuousSelf` overwrites `self.identity` with the durable one, and
        the standing is keyed by identity. Loading before resume would therefore bind a fresh
        uuid's empty standing on top of the creature's real history -- silent amnesia.
        """
        if self.standing is None:
            self.standing = self._store.load(identity=self.self.identity)
            self._before = self.standing.as_row()

    def next_task(self, _state: Mapping[str, Any]) -> str | None:
        """`ContinuousSelf.run` calls this. None means idle, and idle is honest."""
        self._ensure_standing()
        if ledger.open_gaps(self.ledger_path) == 0:
            # Nothing it knows it does not know. No fabricated work: an empty ledger idles
            # rather than reaching for `demonstration_ledger()`, which is a test fixture.
            return None
        pool = self.obligations()
        open_pool = [o for o in pool if not o.closed]
        if not open_pool:
            return None
        chosen = stakes.choose(self.standing, open_pool)
        if chosen is None:
            return None
        self._current = chosen
        # Resolve the goal now, while the ledger row is in hand. Re-reading it inside `perform`
        # would rank the whole ledger a second time per step for one string.
        self._current_goal = _goal_of(chosen.id, self.ledger_path)
        return chosen.id

    # --------------------------------------------------------------------- action

    def perform(self, task: str, _self: Any) -> dict[str, Any]:
        """Do the chosen thing, then let the outcome change the creature.

        Two writes happen here and both are the point: `standing.record` makes the next choice a
        function of this one, and `ledger.resolve` teaches the ledger which ignorance mattered.
        """
        if self.standing is None:
            raise CreatureError("RESUME_NOT_CALLED")
        obligation = self._current
        goal = self._current_goal
        if obligation is not None and not goal:
            # The gap was resolved between ranking and selection. Say so instead of guessing.
            goal = _goal_of(obligation.id, self.ledger_path)
        try:
            result = self._performer(task, goal)
        except Exception as exc:  # a failing task must not end the thread
            # An exception is unverifiable, not wrong: nothing judged it. `record(verified=False)`
            # is the honest entry, and it is the one that drives `unverified_claims` -> CAUTIOUS.
            posture = self.standing.record(verified=False, correct=False)
            row = {"task": task, "goal": goal[:220], "ok": False,
                   "error": type(exc).__name__, "verified": False, "posture": posture}
            self.steps.append(row)
            return row
        if not isinstance(result, Mapping):
            raise CreatureError("PERFORMER_RETURNED_NON_OBJECT")

        blocker = _environment_blocker(result)
        passed = result.get("pass") is True
        status = str(result.get("status") or "")
        if blocker:
            # A fact about this box. Recorded in the step so it is visible, and deliberately NOT
            # written into standing or the ledger.
            row = {"task": task, "goal": goal[:220], "ok": False, "status": status,
                   "environment_blocked": blocker, "recorded": []}
            self.steps.append(row)
            return row

        posture = self.standing.record(verified=True, correct=passed)
        wrote = bool(ledger.resolve(task, helped=passed, close=passed, path=self.ledger_path))
        row = {"task": task, "goal": goal[:220], "ok": bool(passed), "status": status,
               "capability_id": str(result.get("compiled_capability_id") or ""),
               "verified": True, "posture": posture,
               "recorded": ["standing", "ledger"] if wrote else ["standing"]}
        self.steps.append(row)
        return row

    # ------------------------------------------------------------------------ run

    def run(self, *, max_steps: int = DEFAULT_MAX_STEPS) -> dict[str, Any]:
        """Start it.

        `ContinuousSelf.run` calls `resume()` itself, exactly once, and returns that result under
        `"resumed"`. This method must NOT resume first: doing so resumed twice, so a fresh birth
        reported `epoch 2` with a phantom RESUME journal row, and on a real restart the first
        resume consumed the interrupted-work record before the second could report it. The epoch
        is the one number a continuity module must not misreport, so the resume is left entirely to
        the module that owns it and is tested for it.
        """
        try:
            outcome = self.self.run(next_task=self.next_task, perform=self.perform,
                                    max_steps=max_steps)
        finally:
            # Saved even if the loop raised, and even on a zero-step run (where `next_task` never
            # fired to load it): what it learned about itself is the part that must not be lost,
            # and losing it is precisely the amnesia `continuous-self.yml` gates against.
            self._ensure_standing()
            self._store.save(self.standing)
        resumed = outcome.get("resumed") or {}
        before = self._before or (self.standing.as_row() if self.standing else {})
        after = self.standing.as_row() if self.standing else before
        return {
            "schema": SCHEMA,
            "identity": self.self.identity,
            "resumed": resumed.get("resumed"),
            "epoch": resumed.get("epoch"),
            "interrupted_on_resume": resumed.get("interrupted") or [],
            "steps": int(outcome.get("steps") or 0),
            "posture_before": before.get("posture"),
            "posture_after": after.get("posture"),
            "standing": after,
            "attempts": self.steps,
            "describe": self.self.describe(),
            "terminal_authority": False,
            "hard_nonclaims": [
                "A_CREATURE_THAT_RAN_IS_NOT_A_CREATURE_THAT_PROVED_ANYTHING",
                "NO_SENTIENCE_OR_EXPERIENCE_IS_MEASURED_OR_CLAIMED",
                "THE_LIVE_ENTRY_GRADES_ITSELF_THIS_MODULE_GRADES_NOTHING",
            ],
        }

    def selection_on_real_obligations(self, *, steps: int = stakes.SCARCE_STEPS,
                                      seed: int = 20261102) -> dict[str, Any]:
        """Its criterion against random, on the REAL ledger.

        The ~2.0x figure on record is measured on `demonstration_ledger()`, a fixture. This is the
        same comparison on what the machine actually does not know, which is the only version that
        says anything about the creature.
        """
        self._ensure_standing()
        pool = self.obligations()
        if not pool:
            return {"schema": SCHEMA + "_SELECTION", "obligations": 0,
                    "reason": "NO_OPEN_OBLIGATIONS_TO_CHOOSE_FROM"}
        return stakes.compare_selection(self.standing, pool, steps=steps, seed=seed)


# ---------------------------------------------------------------------- live entry


def _default_perform(task: str, goal: str) -> Mapping[str, Any]:
    """The same live entry the heartbeat proves alive every day. It grades itself."""
    from canonical.runtime import live_brain_route_admission_v1 as entry
    return entry.solve({"task_id": f"creature_v1_{task}", "goal": goal})


def _environment_blocker(result: Mapping[str, Any]) -> str | None:
    """Reuse the existing accessor rather than re-deriving what counts as this box's fault."""
    try:
        from execution_guard.live_solver_end_to_end_measurement_v1 import environment_blocker
    except Exception:
        return None
    try:
        return environment_blocker(result)
    except Exception:
        return None


def _goal_of(gap_id: str, path: str | None = None) -> str:
    """The ledger's own phrasing of the gap is the goal. Nothing here rewrites it.

    An empty string means the gap vanished between ranking and selection. That is passed through
    rather than substituted: the live entry fails closed on a request with no goal, which is the
    correct outcome and is visible in the step row.
    """
    for gap in ledger.rank(limit=ALL_OBLIGATIONS, include_resolved=True, path=path):
        if str(gap.get("id")) == gap_id:
            return str(gap.get("what") or "")
    return ""


# --------------------------------------------------------------------------- report


def report(creature: Creature, *, steps: int = stakes.SCARCE_STEPS) -> dict[str, Any]:
    """What it is, what it does not know, and whether its criterion beats luck. No work performed.

    `resume()` runs first so the report reflects the durable creature's own identity rather than a
    fresh uuid, and so `describe()` is available. It touches only the state dir, never the ledger,
    so a report is read-only with respect to tracked state.
    """
    resumed = creature.self.resume()
    creature._ensure_standing()          # identity is settled by resume(); load standing once
    pool = creature.obligations()
    standing = creature.standing
    return {
        "schema": SCHEMA + "_REPORT",
        "identity": creature.self.identity,
        "epoch": resumed.get("epoch"),
        "describe": creature.self.describe(),
        "obligations_open": sum(1 for o in pool if not o.closed),
        "ledger": ledger.stats(creature.ledger_path),
        "standing": standing.as_row() if standing else {},
        "selection": creature.selection_on_real_obligations(steps=steps),
        "terminal_authority": False,
    }


# ---------------------------------------------------------------------------- CLI


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="One continuous subject: chooses its own work, is changed by it.")
    ap.add_argument("--state-dir", default=DEFAULT_STATE_DIR,
                    help="durable self, journal and standing (gitignored; carried as an artifact)")
    ap.add_argument("--ledger", default=None,
                    help="ignorance ledger path; defaults to the ledger's own tracked state")
    ap.add_argument("--identity", default=None,
                    help="reuse an identity explicitly; otherwise the durable state supplies it")
    ap.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    ap.add_argument("--report", action="store_true",
                    help="describe it and compare its criterion against random, without working")
    ap.add_argument("--steps", type=int, default=stakes.SCARCE_STEPS,
                    help="budget for the --report selection comparison")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    creature = Creature(state_dir=args.state_dir, ledger_path=args.ledger,
                        identity=args.identity)
    if args.report:
        row: dict[str, Any] = report(creature, steps=args.steps)
    else:
        # SIGTERM stops the loop between steps rather than mid-write. Only on the run path:
        # a report performs no work, and signal handlers belong to the main thread of a real
        # process, not to a library call under a test runner. This is the caller that makes
        # `install_signal_handlers` live rather than orphaned. It needs the object, not resumed
        # state -- request_stop only sets a flag.
        cs.install_signal_handlers(creature.self)
        # run() calls resume() itself, exactly once. Resuming here too was a double-resume:
        # on a fresh start it BIRTHed then immediately RESUMEd (epoch 2), and worse, it consumed
        # any interrupted-work record before run() could report it. Do not resume before run().
        row = creature.run(max_steps=args.max_steps)

    if args.json:
        print(json.dumps(row, indent=1, sort_keys=True, default=str))
    else:
        _print_human(row)
    return 0


def _print_human(row: Mapping[str, Any]) -> None:
    if row.get("schema") == SCHEMA + "_REPORT":
        sel = row.get("selection") or {}
        led = row.get("ledger") or {}
        std = row.get("standing") or {}
        print(f"identity        {row.get('identity')}")
        print(f"obligations     {row.get('obligations_open')} open "
              f"({led.get('tried')} tried, {led.get('ever_helped')} ever helped)")
        print(f"posture         {std.get('posture')}  attempts={std.get('attempts')} "
              f"accuracy={std.get('accuracy')}")
        print(f"initiative      own {sel.get('own_criterion', {}).get('realised_value')} "
              f"vs random {sel.get('random', {}).get('realised_value')} "
              f"-> x{sel.get('ratio_vs_random')} "
              f"own_beats_random={sel.get('own_beats_random')}")
        return
    print(f"identity        {row.get('identity')}  epoch={row.get('epoch')} "
          f"resumed={row.get('resumed')}")
    interrupted = row.get("interrupted_on_resume") or []
    if interrupted:
        print(f"interrupted     {len(interrupted)} in-flight task(s) reported INTERRUPTED: "
              + ", ".join(str(r.get('task')) for r in interrupted))
    print(f"posture         {row.get('posture_before')} -> {row.get('posture_after')}")
    print(f"steps           {row.get('steps')}")
    for step in (row.get("attempts") or [])[-10:]:
        blocked = step.get("environment_blocked")
        verdict = f"BLOCKED:{blocked}" if blocked else ("ok" if step.get("ok") else "failed")
        print(f"  {str(step.get('task')):<18} {verdict:<28} {str(step.get('status'))[:52]}")


if __name__ == "__main__":
    raise SystemExit(main())
