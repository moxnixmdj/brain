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
        )


class ContinuousSelf:
    """The loop, the durable state, and the journal of what it was doing."""

    def __init__(self, *, state_path: pathlib.Path | str, journal_path: pathlib.Path | str,
                 beat_seconds: float = DEFAULT_BEAT_SECONDS,
                 identity: str | None = None, clock: Callable[[], float] = _now):
        self.state_path = pathlib.Path(state_path)
        self.journal_path = pathlib.Path(journal_path)
        self.beat_seconds = beat_seconds
        self.clock = clock
        self.identity = identity or uuid.uuid4().hex
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

    def resume(self) -> dict[str, Any]:
        """Load the durable self, and account for whatever was in flight when it stopped."""
        prior = self._load()
        if prior is None:
            self.state = SelfState(identity=self.identity, started_at=self.clock(),
                                   last_beat_at=self.clock())
            self._append("BIRTH", beat=0)
            self._save()
            return {"schema": SCHEMA, "epoch": 1, "resumed": False, "identity": self.identity,
                    "interrupted": []}

        # Same identity, next epoch. The identity is the point: an epoch ends, the self does not.
        self.identity = prior.identity
        prior.epoch += 1
        prior.beat = 0
        prior.last_beat_at = self.clock()
        interrupted: list[dict[str, Any]] = []
        if prior.in_flight:
            row = dict(prior.in_flight)
            row["status"] = "INTERRUPTED"
            row["interrupted_at"] = self.clock()
            interrupted.append(row)
            prior.interrupted.append(row)
            prior.in_flight = None
            self._append("INTERRUPTED", task=row.get("task"), started_at=row.get("started_at"))
        self.state = prior
        self._append("RESUME", epoch=prior.epoch, interrupted=len(interrupted))
        self._save()
        return {"schema": SCHEMA, "epoch": prior.epoch, "resumed": True,
                "identity": self.identity, "interrupted": interrupted}

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
