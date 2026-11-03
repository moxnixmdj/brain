#!/usr/bin/env python3
"""One thread that does not stop when a task ends.

WHY THIS EXISTS
---------------
Every other module in this tree is invoked. A task arrives, work happens, a verdict is written,
the process exits. Whatever accumulates lives on disk, not in anything that is *running*.

That is the right design for a tool and the wrong one for the thing the owner keeps asking about:
one continuous subject, present while the work happens, which is the same subject tomorrow. This
module is the smallest honest attempt at that -- a long-lived loop that owns a durable self-state,
survives being killed at any moment, and can report accurately on what it was doing.

WHAT MAKES IT CHECKABLE
-----------------------
Three properties, each falsifiable by killing the process:

  * CONTINUITY   -- it resumes as the same identity with the same accumulated state.
  * HONESTY      -- on restart it reports the work that was in flight as INTERRUPTED, not as done
                    and not as never having started. A process that loses an attempt silently has
                    no continuity; it has amnesia dressed as a fresh start.
  * CAUSALITY    -- every transition is recorded before it is acted on, so an outside reader can
                    reconstruct what it was doing from the journal alone, at any moment.

WHAT THIS IS NOT
----------------
It is not a claim of experience or sentience, and nothing here tests for either. It is the
substrate those questions would have to be asked about: a continuous process with a durable self
and an accurate account of its own recent past. A coroutine in a loop is not a mind; it is the
smallest thing that could be one rather than a series of unrelated invocations.

Nothing here calls a model. Nothing here spends.
"""
from __future__ import annotations

import json
import os
import pathlib
import signal
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_CONTINUOUS_SELF_V1"
JOURNAL_SCHEMA = "PROJECT_BRAIN_CONTINUOUS_SELF_JOURNAL_V1"

STATES = ("RUNNING", "IDLE", "INTERRUPTED")

# A beat longer than this means the process was killed rather than merely busy.
DEFAULT_BEAT_SECONDS = 30.0


def _now() -> float:
    return time.time()


@dataclass
class SelfState:
    """The durable part: what this run is, not what it is doing."""

    identity: str
    started_at: float
    beat: int = 0
    last_beat_at: float = 0.0
    in_flight: dict[str, Any] | None = None
    completed: list[dict[str, Any]] = field(default_factory=list)
    interrupted: list[dict[str, Any]] = field(default_factory=list)
    epoch: int = 1
    last_absence_seconds: float = 0.0
    total_absence_seconds: float = 0.0
    world_snapshot: dict[str, Any] = field(default_factory=dict)
    last_world_drift: dict[str, Any] = field(default_factory=dict)
    behavioral_signature: str | None = None

    def as_row(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "started_at": self.started_at,
            "beat": self.beat,
            "last_beat_at": self.last_beat_at,
            "in_flight": self.in_flight,
            "completed": self.completed,
            "interrupted": self.interrupted,
            "epoch": self.epoch,
            "last_absence_seconds": round(self.last_absence_seconds, 6),
            "total_absence_seconds": round(self.total_absence_seconds, 6),
            "world_snapshot": dict(self.world_snapshot),
            "last_world_drift": dict(self.last_world_drift),
            "behavioral_signature": self.behavioral_signature,
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "SelfState":
        return cls(
            identity=str(row["identity"]),
            started_at=float(row["started_at"]),
            beat=int(row.get("beat") or 0),
            last_beat_at=float(row.get("last_beat_at") or 0.0),
            in_flight=row.get("in_flight"),
            completed=list(row.get("completed") or []),
            interrupted=list(row.get("interrupted") or []),
            epoch=int(row.get("epoch") or 1),
            last_absence_seconds=float(row.get("last_absence_seconds") or 0.0),
            total_absence_seconds=float(row.get("total_absence_seconds") or 0.0),
            world_snapshot=dict(row.get("world_snapshot") or {}),
            last_world_drift=dict(row.get("last_world_drift") or {}),
            behavioral_signature=(
                str(row["behavioral_signature"])
                if row.get("behavioral_signature") is not None
                else None
            ),
        )


def compute_world_drift(
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Compute exogenous changes in world state that occurred while the self was absent."""
    b = dict(before or {})
    a = dict(after or {})
    added = sorted(k for k in a if k not in b)
    removed = sorted(k for k in b if k not in a)
    changed = sorted(k for k in (set(a) & set(b)) if a[k] != b[k])
    return {
        "drifted": bool(added or removed or changed),
        "added": added,
        "removed": removed,
        "changed": changed,
        "drift_count": len(added) + len(removed) + len(changed),
    }


class ContinuousSelf:
    """The loop, the durable state, and the journal of what it was doing."""

    def __init__(self, *, state_path: pathlib.Path | str, journal_path: pathlib.Path | str,
                 beat_seconds: float = DEFAULT_BEAT_SECONDS,
                 identity: str | None = None, clock: Callable[[], float] = _now,
                 world_probe: Callable[[], Mapping[str, Any]] | None = None,
                 signature_fn: Callable[[], str] | None = None):
        self.state_path = pathlib.Path(state_path)
        self.journal_path = pathlib.Path(journal_path)
        self.beat_seconds = beat_seconds
        self.clock = clock
        self.identity = identity or uuid.uuid4().hex
        self.world_probe = world_probe
        self.signature_fn = signature_fn
        self.state: SelfState | None = None
        self._stopping = False

    # ---------------------------------------------------------------- journal

    def _append(self, kind: str, **fields: Any) -> None:
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        row = {"schema": JOURNAL_SCHEMA, "kind": kind, "at": self.clock(),
               "identity": self.identity, **fields}
        with self.journal_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    def journal(self) -> list[dict[str, Any]]:
        if not self.journal_path.is_file():
            return []
        rows = []
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    # ----------------------------------------------------------------- state

    def _load(self) -> SelfState | None:
        if not self.state_path.is_file():
            return None
        try:
            return SelfState.from_row(json.loads(self.state_path.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError):
            return None

    def _save(self) -> None:
        assert self.state is not None
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.state.as_row(), indent=1, sort_keys=True) + "\n",
                       encoding="utf-8")
        # Atomic replace: a kill during the write must not leave a half-written self behind.
        os.replace(tmp, self.state_path)

    def commit_world_and_signature(self) -> None:
        """Snapshot current world & behavioral competence signature before sleeping/continuing."""
        if self.state is None:
            return
        if self.world_probe is not None:
            try:
                self.state.world_snapshot = dict(self.world_probe())
            except Exception:
                pass
        if self.signature_fn is not None:
            try:
                self.state.behavioral_signature = str(self.signature_fn())
            except Exception:
                pass
        self._save()

    def resume(self) -> dict[str, Any]:
        """Load the durable self, perceive absence & world drift, and verify behavioral continuity."""
        now = self.clock()
        cur_world = {}
        if self.world_probe is not None:
            try:
                cur_world = dict(self.world_probe())
            except Exception:
                cur_world = {}
        cur_sig: str | None = None
        if self.signature_fn is not None:
            try:
                cur_sig = str(self.signature_fn())
            except Exception:
                cur_sig = None

        prior = self._load()
        if prior is None:
            self.state = SelfState(
                identity=self.identity,
                started_at=now,
                last_beat_at=now,
                world_snapshot=cur_world,
                behavioral_signature=cur_sig,
            )
            self._append("BIRTH", beat=0)
            self._save()
            return {
                "schema": SCHEMA,
                "epoch": 1,
                "resumed": False,
                "identity": self.identity,
                "interrupted": [],
                "absence_seconds": 0.0,
                "was_absent": False,
                "world_drift": {"drifted": False, "added": [], "removed": [], "changed": [], "drift_count": 0},
                "behavioral_continuity_verified": True,
            }

        # Measure real inter-epoch absence before overwriting last_beat_at!
        absence_sec = max(0.0, now - float(prior.last_beat_at or prior.started_at))
        was_absent = absence_sec >= self.beat_seconds
        world_drift = (
            compute_world_drift(prior.world_snapshot, cur_world)
            if self.world_probe is not None
            else {"drifted": False, "added": [], "removed": [], "changed": [], "drift_count": 0}
        )
        behavioral_verified = True
        if prior.behavioral_signature is not None and cur_sig is not None:
            behavioral_verified = (cur_sig == prior.behavioral_signature)

        # Same identity, next epoch. The identity is the point: an epoch ends, the self does not.
        self.identity = prior.identity
        prior.epoch += 1
        prior.beat = 0
        prior.last_beat_at = now
        prior.last_absence_seconds = absence_sec
        prior.total_absence_seconds += absence_sec
        prior.last_world_drift = world_drift
        if self.world_probe is not None:
            prior.world_snapshot = cur_world
        if prior.behavioral_signature is None and cur_sig is not None:
            prior.behavioral_signature = cur_sig

        interrupted: list[dict[str, Any]] = []
        if prior.in_flight:
            row = dict(prior.in_flight)
            row["status"] = "INTERRUPTED"
            row["interrupted_at"] = now
            row["absence_seconds"] = round(absence_sec, 6)
            interrupted.append(row)
            prior.interrupted.append(row)
            prior.in_flight = None
            self._append("INTERRUPTED", task=row.get("task"), started_at=row.get("started_at"))
        self.state = prior
        self._append(
            "RESUME",
            epoch=prior.epoch,
            interrupted=len(interrupted),
            absence_seconds=round(absence_sec, 6),
            world_drifted=world_drift["drifted"],
            behavioral_continuity_verified=behavioral_verified,
        )
        self._save()
        return {
            "schema": SCHEMA,
            "epoch": prior.epoch,
            "resumed": True,
            "identity": self.identity,
            "interrupted": interrupted,
            "absence_seconds": round(absence_sec, 6),
            "was_absent": was_absent,
            "world_drift": world_drift,
            "behavioral_continuity_verified": behavioral_verified,
        }

    # ------------------------------------------------------------------ work

    def begin(self, task: str, **detail: Any) -> dict[str, Any]:
        """Record the intention before doing anything. A reader can always see what it was doing."""
        if self.state is None:
            raise RuntimeError("RESUME_NOT_CALLED")
        if self.state.in_flight:
            raise RuntimeError("ALREADY_IN_FLIGHT:" + str(self.state.in_flight.get("task")))
        row = {"task": str(task), "started_at": self.clock(), **detail}
        self.state.in_flight = row
        self._append("BEGIN", task=row["task"], **detail)
        self._save()
        return row

    def finish(self, outcome: Mapping[str, Any]) -> dict[str, Any]:
        if self.state is None or not self.state.in_flight:
            raise RuntimeError("NOTHING_IN_FLIGHT")
        row = dict(self.state.in_flight)
        row.update({"status": "DONE", "ended_at": self.clock(), **dict(outcome)})
        self.state.completed.append(row)
        self.state.in_flight = None
        self._append("FINISH", task=row.get("task"), outcome=dict(outcome))
        self._save()
        return row

    def beat(self) -> dict[str, Any]:
        """A heartbeat. Its absence is how a later epoch knows it was killed rather than idle."""
        if self.state is None:
            raise RuntimeError("RESUME_NOT_CALLED")
        self.state.beat += 1
        self.state.last_beat_at = self.clock()
        self._append("BEAT", beat=self.state.beat)
        self._save()
        return {"beat": self.state.beat, "at": self.state.last_beat_at}

    def describe(self) -> dict[str, Any]:
        """What it was doing, for anyone outside, in plain terms."""
        if self.state is None:
            raise RuntimeError("RESUME_NOT_CALLED")
        current = self.state.in_flight
        return {
            "schema": SCHEMA,
            "identity": self.identity,
            "epoch": self.state.epoch,
            "beats": self.state.beat,
            "doing_now": current.get("task") if current else "IDLE",
            "in_flight_since": current.get("started_at") if current else None,
            "completed_count": len(self.state.completed),
            "interrupted_count": len(self.state.interrupted),
            "last_completed": (self.state.completed[-1]["task"]
                               if self.state.completed else None),
            "age_seconds": round(self.clock() - self.state.started_at, 3),
            "last_absence_seconds": round(self.state.last_absence_seconds, 6),
            "total_absence_seconds": round(self.state.total_absence_seconds, 6),
            "last_world_drift": dict(self.state.last_world_drift),
            "behavioral_signature": self.state.behavioral_signature,
        }

    # ------------------------------------------------------------------ loop

    def request_stop(self, *_args: Any) -> None:
        self._stopping = True

    def run(self, *, next_task: Callable[[dict[str, Any]], str | None],
            perform: Callable[[str, "ContinuousSelf"], Mapping[str, Any]],
            max_steps: int | None = None) -> dict[str, Any]:
        """One thread, until stopped.

        `next_task(state)` returns the next thing to do, or None for idle. `perform` does it and
        returns the outcome. Both are injected: this module owns continuity, not judgement.
        """
        started = self.resume()
        steps = 0
        while not self._stopping:
            if max_steps is not None and steps >= max_steps:
                break
            self.beat()
            task = next_task(self.state.as_row() if self.state else {})
            if task is None:
                self._append("IDLE")
                steps += 1
                continue
            self.begin(task)
            try:
                outcome = perform(task, self)
            except Exception as exc:  # a failing task must not end the thread
                self.finish({"ok": False, "error": type(exc).__name__})
            else:
                self.finish(dict(outcome or {}))
            steps += 1
        self._append("STOP", steps=steps, requested=self._stopping)
        return {"schema": SCHEMA, "resumed": started, "steps": steps,
                "describe": self.describe()}


def install_signal_handlers(self: ContinuousSelf) -> None:
    """SIGTERM stops the loop between steps rather than mid-write."""
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, self.request_stop)
        except (ValueError, OSError):
            continue
