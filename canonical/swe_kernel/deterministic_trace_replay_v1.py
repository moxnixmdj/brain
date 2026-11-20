#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic trace recording, bit-exact replay, and counterfactual forking — zero model calls.

THE ARGUMENT
------------
Agent debugging normally requires re-running live LLM loops, burning tokens
and hiding root causes. This module replaces live re-execution with:

1. TraceRecorder — records every shell execution as a content-addressed
   trace with filesystem snapshots before each step
2. BitExactReplayer — replays a trace bit-exactly by restoring snapshots
   and re-executing each step (zero model calls during replay)
3. CounterfactualForker — rewinds to any step k, mutates one action, and
   replays forward from k+1 to see how the outcome changes

This is the deterministic replay backbone: every run produces a trace that
can be replayed, forked, and counterfactually debugged without calling a
single model.

ELON'S RULE APPLIED
-------------------
The best part is no part: no model calls for replay, no network calls for
trace storage, no knowledge house for trace persistence. Traces are
recorded, replayed, forked, and discarded.

Authority: NONE. Producer-run deterministic calculation.
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TraceFrame:
    """One frame of a deterministic trace."""

    step_index: int
    action: str
    state_snapshot: dict  # relative_path -> file bytes (before action)
    return_code: int
    stdout: str
    stderr: str
    frame_hash: str = ""

    def compute_hash(self) -> str:
        """Content-addressed hash of this frame."""
        canonical = (
            str(self.step_index)
            + "|"
            + self.action
            + "|"
            + str(self.return_code)
            + "|"
            + self.stdout
            + "|"
            + self.stderr
            + "|"
            + str(sorted(self.state_snapshot.items()))
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class RecordedTrace:
    """A complete recorded trace — content-addressed and reproducible."""

    trace_id: str
    frames: tuple
    terminal_outcome: int
    total_steps: int
    model_calls: int
    network_calls: int


@dataclass(frozen=True)
class ForkResult:
    """Result of a counterfactual fork."""

    fork_step: int
    mutated_action: str
    original_outcome: int
    forked_outcome: int
    outcome_changed: bool
    frames_after_fork: tuple
    model_calls: int
    network_calls: int


class TraceRecorder:
    """Record shell executions as bit-exact traces with snapshots."""

    def __init__(self, environment_root: pathlib.Path):
        self.environment_root = environment_root
        self.model_calls = 0
        self.network_calls = 0

    def _snapshot(self, root: pathlib.Path) -> dict:
        """Snapshot all files under root (excluding .git, __pycache__)."""
        return {
            p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
        }

    def _execute(self, action: str) -> tuple:
        """Execute a shell command. Returns (rc, stdout, stderr)."""
        try:
            result = subprocess.run(
                action,
                shell=True,
                cwd=str(self.environment_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except Exception as exc:
            return 1, "", str(exc)

    def record(
        self,
        steps: list,
        trace_id: str | None = None,
    ) -> RecordedTrace:
        """Record a sequence of shell actions as a bit-exact trace.

        Before each step, the filesystem is snapshotted. After each step,
        the return code, stdout, and stderr are recorded. The result is a
        content-addressed trace that can be replayed bit-exactly.

        Zero model calls, zero network calls.
        """
        if trace_id is None:
            trace_id = "trace_" + str(abs(hash(str(steps))))[:8]

        frames = []
        terminal_outcome = 0

        for step_index, (action, _) in enumerate(steps):
            snapshot = self._snapshot(self.environment_root)
            rc, stdout, stderr = self._execute(action)

            frame = TraceFrame(
                step_index=step_index,
                action=action,
                state_snapshot=snapshot,
                return_code=rc,
                stdout=stdout,
                stderr=stderr,
            )
            frame = TraceFrame(
                step_index=frame.step_index,
                action=frame.action,
                state_snapshot=frame.state_snapshot,
                return_code=frame.return_code,
                stdout=frame.stdout,
                stderr=frame.stderr,
                frame_hash=frame.compute_hash(),
            )
            frames.append(frame)

            if rc != 0:
                terminal_outcome = 1
            else:
                terminal_outcome = 0

        return RecordedTrace(
            trace_id=trace_id,
            frames=tuple(frames),
            terminal_outcome=terminal_outcome,
            total_steps=len(frames),
            model_calls=0,
            network_calls=0,
        )


class BitExactReplayer:
    """Replay a recorded trace bit-exactly by restoring snapshots."""

    def __init__(self, environment_root: pathlib.Path):
        self.environment_root = environment_root
        self.model_calls = 0
        self.network_calls = 0

    def _restore(self, root: pathlib.Path, snapshot: dict) -> None:
        """Restore environment from snapshot."""
        current = {
            p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
        }
        for rel in current:
            if rel not in snapshot:
                (root / rel).unlink()
        for rel, data in snapshot.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(data)

    def _execute(self, action: str) -> tuple:
        try:
            result = subprocess.run(
                action,
                shell=True,
                cwd=str(self.environment_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except Exception as exc:
            return 1, "", str(exc)

    def replay(self, trace: RecordedTrace) -> dict:
        """Replay a trace bit-exactly.

        Restores each snapshot before executing its action. Verifies that
        the replayed return codes match the recorded ones.

        Returns a dict with replay status, step-by-step results, and
        whether the replay was bit-exact.
        """
        step_results = []
        bit_exact = True
        terminal_outcome = 0

        for frame in trace.frames:
            # Restore snapshot before this step
            self._restore(self.environment_root, frame.state_snapshot)

            # Re-execute the action
            rc, stdout, stderr = self._execute(frame.action)

            # Compare with recorded
            rc_match = rc == frame.return_code
            stdout_match = stdout == frame.stdout
            stderr_match = stderr == frame.stderr
            step_exact = rc_match and stdout_match and stderr_match

            if not step_exact:
                bit_exact = False

            if rc != 0:
                terminal_outcome = 1
            else:
                terminal_outcome = 0

            step_results.append(
                {
                    "step_index": frame.step_index,
                    "action": frame.action,
                    "recorded_rc": frame.return_code,
                    "replayed_rc": rc,
                    "rc_match": rc_match,
                    "stdout_match": stdout_match,
                    "stderr_match": stderr_match,
                    "step_exact": step_exact,
                }
            )

        return {
            "trace_id": trace.trace_id,
            "bit_exact": bit_exact,
            "terminal_outcome": terminal_outcome,
            "total_steps": len(trace.frames),
            "step_results": step_results,
            "model_calls": 0,
            "network_calls": 0,
        }


class CounterfactualForker:
    """Counterfactual forking: rewind to step k, mutate one action, replay forward.

    This is the core of counterfactual debugging: "What would happen if
    step k had been different?"

    Zero model calls, zero network calls.
    """

    def __init__(self, environment_root: pathlib.Path):
        self.environment_root = environment_root
        self.model_calls = 0
        self.network_calls = 0

    def _restore(self, root: pathlib.Path, snapshot: dict) -> None:
        current = {
            p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
        }
        for rel in current:
            if rel not in snapshot:
                (root / rel).unlink()
        for rel, data in snapshot.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(data)

    def _execute(self, action: str) -> tuple:
        try:
            result = subprocess.run(
                action,
                shell=True,
                cwd=str(self.environment_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except Exception as exc:
            return 1, "", str(exc)

    def fork_at(
        self,
        trace,
        fork_step: int,
        mutated_action: str,
    ) -> ForkResult:
        """Fork a trace at step k.

        1. Restore snapshot at step k (before the original action)
        2. Execute the mutated action instead of the original
        3. Replay all remaining steps (k+1 onward) from the mutated state
        4. Compare the terminal outcome with the original

        Returns whether the mutation changed the outcome.
        """
        if fork_step < 0 or fork_step >= len(trace.frames):
            return ForkResult(
                fork_step=fork_step,
                mutated_action=mutated_action,
                original_outcome=trace.terminal_outcome,
                forked_outcome=trace.terminal_outcome,
                outcome_changed=False,
                frames_after_fork=(),
                model_calls=0,
                network_calls=0,
            )

        # Restore snapshot at fork step
        self._restore(self.environment_root, trace.frames[fork_step].state_snapshot)

        # Record original outcome at this step
        original_rc = trace.frames[fork_step].return_code

        # Execute the mutated action
        mut_rc, mut_stdout, mut_stderr = self._execute(mutated_action)

        # Replay remaining steps from the mutated state
        frames_after_fork = []
        terminal_rc = mut_rc

        for i in range(fork_step + 1, len(trace.frames)):
            # Restore the snapshot that was recorded at step i
            # (this is the state after step i-1 in the original trace,
            # but we're continuing from the mutated state)
            # Instead, we continue executing from current state
            rc, stdout, stderr = self._execute(trace.frames[i].action)
            if rc != 0:
                terminal_rc = rc

            frames_after_fork.append(
                TraceFrame(
                    step_index=i,
                    action=trace.frames[i].action,
                    state_snapshot={},
                    return_code=rc,
                    stdout=stdout,
                    stderr=stderr,
                )
            )

        original_outcome = trace.terminal_outcome
        forked_outcome = 1 if terminal_rc != 0 else 0
        outcome_changed = original_outcome != forked_outcome

        return ForkResult(
            fork_step=fork_step,
            mutated_action=mutated_action,
            original_outcome=original_outcome,
            forked_outcome=forked_outcome,
            outcome_changed=outcome_changed,
            frames_after_fork=tuple(frames_after_fork),
            model_calls=0,
            network_calls=0,
        )


def record_trace(
    environment_root: pathlib.Path,
    steps: list,
    trace_id: str | None = None,
) -> dict:
    """Convenience: record a trace and return a dict."""
    recorder = TraceRecorder(environment_root)
    trace = recorder.record(steps, trace_id)
    return {
        "trace_id": trace.trace_id,
        "frames": [
            {
                "step_index": f.step_index,
                "action": f.action,
                "return_code": f.return_code,
                "stdout": f.stdout,
                "stderr": f.stderr,
                "frame_hash": f.frame_hash,
            }
            for f in trace.frames
        ],
        "terminal_outcome": trace.terminal_outcome,
        "total_steps": trace.total_steps,
        "model_calls": trace.model_calls,
        "network_calls": trace.network_calls,
    }


def replay_trace(
    environment_root: pathlib.Path,
    trace_dict: dict,
) -> dict:
    """Convenience: replay a trace dict and return results."""
    # Reconstruct RecordedTrace from dict
    from types import SimpleNamespace

    frames = []
    for f in trace_dict["frames"]:
        frames.append(
            TraceFrame(
                step_index=f["step_index"],
                action=f["action"],
                state_snapshot={},  # snapshots not serialized in dict
                return_code=f["return_code"],
                stdout=f["stdout"],
                stderr=f["stderr"],
                frame_hash=f.get("frame_hash", ""),
            )
        )

    trace = RecordedTrace(
        trace_id=trace_dict["trace_id"],
        frames=tuple(frames),
        terminal_outcome=trace_dict["terminal_outcome"],
        total_steps=trace_dict["total_steps"],
        model_calls=0,
        network_calls=0,
    )

    replayer = BitExactReplayer(environment_root)
    return replayer.replay(trace)
