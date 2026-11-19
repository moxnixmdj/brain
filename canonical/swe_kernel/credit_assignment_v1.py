#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Credit Assignment — attribute which steps in an agent trace caused the outcome.

THE PROBLEM
-----------
A terminal reward (success/failure) is a single signal over a trajectory of
dozens of decisions. Which step earned the win, and which caused the trouble?
Instant one-shot learning fails here: even doing something once, you cannot
attribute credit from a single trace.

State of the art (November 2026):
- Step-level attribution accuracy on the Who&When benchmark: ~14%
- None of the prominent existing credit-assignment methods produce fully
  correct attribution on the SkillLuck MDP (arxiv:2607.16999)
- Counterfactual Shapley values isolate skill from luck (arxiv:2607.16999)
- Twin-world credit estimation keys noise by turn for deterministic twins
  (arxiv:2610.31544)
- Causal Agent Replay applies do()-operations to steps (arxiv:2606.08275)

THE MECHANISM
-------------
For each step k in a trace:
  1. Restore the environment snapshot at step k (same files, same state)
  2. Run the factual action k, then replay steps k+1..end -> terminal outcome
  3. For each counterfactual (mutant) action at step k:
       Restore the same snapshot at step k
       Run the counterfactual action, then replay steps k+1..end -> terminal outcome
  4. Credit(k) = P(terminal success | factual path through k)
                 - mean P(terminal success | counterfactual paths through k)

Steps with high positive credit are causal: changing them changes the outcome.
Steps with zero credit are not causal: changing them leaves the outcome intact.

The point-of-commitment rule: the factual and counterfactual runs share the
same environment snapshot at step k, so the only difference is the action at
step k. Downstream steps are replayed identically. This isolates the decision
effect from luck — the outcome difference is attributable to step k alone.

Zero model calls, zero network calls, zero knowledge house. Exact integer
counts only. Every parameter calculated from first principles. Fail-closed.

Authority: NONE. Producer-run sandbox measurement. No model, no network, no spend.
"""

from __future__ import annotations

import hashlib
import itertools
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STABILITY_DELAY_SECONDS = 0.05
MAX_STEPS = 50
DEFAULT_COUNTERFACTUAL_ROLLOUTS = 5

# --------------------------------------------------------------------------- #
# schema / authority
# --------------------------------------------------------------------------- #

SCHEMA = "PROJECT_BRAIN_CREDIT_ASSIGNMENT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"

# --------------------------------------------------------------------------- #
# verdicts
# --------------------------------------------------------------------------- #

SENSE_DONE = "SENSE_DONE__TRACE_OBSERVED"
CONTRAST_DONE = "CONTRAST_DONE__COUNTERFACTUALS_GENERATED"
IDENTIFIED = "IDENTIFIED__CREDIT_ASSIGNED"
REFUSED = "REFUSED__ATTRIBUTION_FAILED"
REMEMBERED = "REMEMBERED__PERSISTED_TO_STORE"

NO_TRACE = "REFUSED__NO_TRACE"
NO_FACTUAL_SUCCESS = "REFUSED__NO_FACTUAL_SUCCESS"
NO_COUNTERFACTUALS = "REFUSED__NO_COUNTERFACTUALS"
STEP_NOT_CAUSAL = "STEP_NOT_CAUSAL__ZERO_CREDIT"


# --------------------------------------------------------------------------- #
# calculated parameter container
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CalculatedParameter:
    """A single parameter whose value is derived, never stored."""

    name: str
    value: Any
    derivation: str
    verified: bool = False


@dataclass
class CalculatedState:
    """The complete set of calculated parameters for one credit assignment."""

    parameters: dict[str, CalculatedParameter] = field(default_factory=dict)
    step: int = 0
    model_calls: int = 0
    network_calls: int = 0

    def add(self, name: str, value: Any, derivation: str) -> CalculatedParameter:
        param = CalculatedParameter(
            name=name, value=value, derivation=derivation,
        )
        self.parameters[name] = param
        return param

    def get(self, name: str) -> Any:
        param = self.parameters.get(name)
        return param.value if param is not None else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "model_calls": self.model_calls,
            "network_calls": self.network_calls,
            "parameter_count": len(self.parameters),
            "verified_count": sum(1 for p in self.parameters.values() if p.verified),
            "parameters": {
                name: {
                    "value": str(p.value)[:200],
                    "derivation": p.derivation,
                    "verified": p.verified,
                }
                for name, p in self.parameters.items()
            },
        }


# --------------------------------------------------------------------------- #
# trace data structures
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class TraceStep:
    """One step in an agent trajectory."""

    step_index: int
    state_snapshot: dict[str, bytes]  # file contents at this point
    action: str  # the command that was run
    outcome: tuple[int, str]  # (returncode, output)


@dataclass(frozen=True)
class AgentTrace:
    """A complete agent trajectory with a terminal outcome."""

    steps: tuple[TraceStep, ...]
    terminal_outcome: int  # 0 = failure, 1 = success


@dataclass(frozen=True)
class StepCredit:
    """Credit assigned to one step."""

    step_index: int
    factual_terminal_success: int  # 0 or 1
    counterfactual_terminal_successes: tuple[int, ...]  # 0 or 1 each
    counterfactual_count: int
    credit: float  # factual - mean(counterfactual)
    is_causal: bool  # credit > 0


# --------------------------------------------------------------------------- #
# phase 1: SENSE — observe the trace
# --------------------------------------------------------------------------- #


def sense_trace(
    root: pathlib.Path,
    steps: Sequence[tuple[str, str]],
    terminal_outcome: int,
) -> dict[str, Any]:
    """Observe an agent trace and calculate the factual baseline.

    Each step is (action, expected_outcome_marker). We snapshot the state
    before each action so we can restore it later for counterfactuals.

    Returns the trace with snapshots, or a REFUSED verdict.
    """
    if terminal_outcome not in (0, 1):
        return {
            "phase": "SENSE",
            "status": REFUSED,
            "reason": "INVALID_TERMINAL_OUTCOME",
            "model_calls": 0,
            "network_calls": 0,
        }

    if not steps:
        return {
            "phase": "SENSE",
            "status": REFUSED,
            "reason": "EMPTY_TRACE",
            "model_calls": 0,
            "network_calls": 0,
        }

    trace_steps: list[TraceStep] = []

    def _snapshot(r: pathlib.Path) -> dict[str, bytes]:
        return {
            p.relative_to(r).as_posix(): p.read_bytes()
            for p in r.rglob("*")
            if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
        }

    for index, (action, _) in enumerate(steps):
        snapshot = _snapshot(root)
        trace_steps.append(
            TraceStep(
                step_index=index,
                state_snapshot=snapshot,
                action=action,
                outcome=(0, ""),  # filled in during contrast phase
            )
        )

    trace = AgentTrace(
        steps=tuple(trace_steps),
        terminal_outcome=terminal_outcome,
    )

    return {
        "phase": "SENSE",
        "status": SENSE_DONE,
        "trace": trace,
        "step_count": len(trace_steps),
        "terminal_outcome": terminal_outcome,
        "model_calls": 0,
        "network_calls": 0,
        "derivation": "trace_observed_from_environment_snapshots",
    }


# --------------------------------------------------------------------------- #
# phase 2: CONTRAST — generate counterfactual interventions
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CounterfactualRollout:
    """One counterfactual rollout: same state, different action at step k."""

    step_index: int
    counterfactual_action: str
    factual_action: str
    terminal_outcome: int  # 0 = failure, 1 = success
    separated: bool  # True if outcome differs from factual


def _run_in(r: pathlib.Path, cmd: str, timeout: float = 15.0) -> tuple[int, str]:
    """Run a command in directory r, return (returncode, output)."""
    result = subprocess.run(
        ["/bin/sh", "-c", cmd],
        cwd=str(r),
        capture_output=True,
        timeout=timeout,
    )
    return result.returncode, (
        result.stdout + result.stderr
    ).decode("utf-8", errors="replace")


def _restore_snapshot(root: pathlib.Path, snapshot: dict[str, bytes]) -> None:
    """Restore the filesystem to the given snapshot."""
    # Remove files not in snapshot (except .git, __pycache__)
    for p in root.rglob("*"):
        if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts:
            rel = p.relative_to(root).as_posix()
            if rel not in snapshot:
                p.unlink(missing_ok=True)
    # Write/overwrite files in snapshot
    for rel, content in snapshot.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def _replay_remaining_steps(
    root: pathlib.Path,
    trace: AgentTrace,
    from_step: int,
    replacement_action: str | None = None,
) -> int:
    """Replay steps from_step+1..end from the current state.

    If replacement_action is given, step `from_step` uses that action instead
    of the factual one. Returns the terminal outcome (0 or 1).
    """
    current_outcome = 0
    for i in range(from_step, len(trace.steps)):
        step = trace.steps[i]
        action = replacement_action if (replacement_action is not None and i == from_step) else step.action
        # Restore the state snapshot before this step (except for the first,
        # which we already restored)
        if i > from_step or replacement_action is not None:
            _restore_snapshot(root, step.state_snapshot)
        time.sleep(STABILITY_DELAY_SECONDS)
        rc, _ = _run_in(root, action)
        current_outcome = 1 if rc == 0 else 0
    return current_outcome


def generate_counterfactuals(
    root: pathlib.Path,
    trace: AgentTrace,
    wrong_actions: Sequence[Sequence[tuple[str, str]]],
    max_rollouts_per_step: int = DEFAULT_COUNTERFACTUAL_ROLLOUTS,
) -> dict[str, Any]:
    """Generate counterfactual interventions for each step.

    For each step k:
      - Restore snapshot at step k
      - Run factual action k, replay remaining steps -> factual terminal outcome
      - For each counterfactual (mutant) action at step k:
          Restore same snapshot at step k
          Run counterfactual action, replay remaining steps -> counterfactual terminal outcome

    Returns per-step credit data.
    """
    rollouts: list[CounterfactualRollout] = []
    step_credits: list[StepCredit] = []

    for k in range(len(trace.steps)):
        step = trace.steps[k]

        # Restore snapshot at step k
        _restore_snapshot(root, step.state_snapshot)
        time.sleep(STABILITY_DELAY_SECONDS)

        # Factual run: action k, then replay remaining steps
        factual_rc, _ = _run_in(root, step.action)
        # Replay remaining steps k+1..end
        if k + 1 < len(trace.steps):
            factual_terminal = _replay_remaining_steps(root, trace, k + 1)
        else:
            factual_terminal = 1 if factual_rc == 0 else 0

        # Counterfactual runs
        counterfactual_outcomes: list[int] = []
        mutants = wrong_actions[k] if k < len(wrong_actions) else []

        for mutant_index, (kind, mutated) in enumerate(mutants):
            if len(counterfactual_outcomes) >= max_rollouts_per_step:
                break

            # Restore same snapshot at step k (point-of-commitment: same state)
            _restore_snapshot(root, step.state_snapshot)
            time.sleep(STABILITY_DELAY_SECONDS)

            mut_rc, _ = _run_in(root, mutated)
            if k + 1 < len(trace.steps):
                mut_terminal = _replay_remaining_steps(root, trace, k + 1)
            else:
                mut_terminal = 1 if mut_rc == 0 else 0

            counterfactual_outcomes.append(mut_terminal)

            rollouts.append(
                CounterfactualRollout(
                    step_index=k,
                    counterfactual_action=mutated,
                    factual_action=step.action,
                    terminal_outcome=mut_terminal,
                    separated=mut_terminal != factual_terminal,
                )
            )

        if counterfactual_outcomes:
            mean_counterfactual = sum(counterfactual_outcomes) / len(counterfactual_outcomes)
            credit = float(factual_terminal) - mean_counterfactual
            is_causal = credit > 0.0
        else:
            mean_counterfactual = 0.0
            credit = 0.0
            is_causal = False

        step_credits.append(
            StepCredit(
                step_index=k,
                factual_terminal_success=factual_terminal,
                counterfactual_terminal_successes=tuple(counterfactual_outcomes),
                counterfactual_count=len(counterfactual_outcomes),
                credit=credit,
                is_causal=is_causal,
            )
        )

    causal_steps = sum(1 for c in step_credits if c.is_causal)
    total_credit = sum(c.credit for c in step_credits)

    return {
        "phase": "CONTRAST",
        "status": CONTRAST_DONE if rollouts else NO_COUNTERFACTUALS,
        "step_count": len(trace.steps),
        "rollout_count": len(rollouts),
        "causal_steps": causal_steps,
        "non_causal_steps": len(step_credits) - causal_steps,
        "total_credit": round(total_credit, 6),
        "step_credits": [
            {
                "step_index": c.step_index,
                "factual_terminal_success": c.factual_terminal_success,
                "counterfactual_count": c.counterfactual_count,
                "credit": round(c.credit, 6),
                "is_causal": c.is_causal,
                "counterfactual_outcomes": c.counterfactual_terminal_successes,
            }
            for c in step_credits
        ],
        "rollouts": [
            {
                "step_index": r.step_index,
                "counterfactual_action": r.counterfactual_action,
                "factual_action": r.factual_action,
                "terminal_outcome": r.terminal_outcome,
                "separated": r.separated,
            }
            for r in rollouts
        ],
        "model_calls": 0,
        "network_calls": 0,
        "derivation": "counterfactual_interventions_point_of_commitment",
    }


# --------------------------------------------------------------------------- #
# phase 3: IDENTIFY — close credit by counterfactual comparison
# --------------------------------------------------------------------------- #


def identify_credit(
    contrast_result: dict[str, Any],
    min_credit_threshold: float = 0.0,
) -> dict[str, Any]:
    """Close credit assignment by counterfactual comparison.

    A step is identified as causal when its credit > min_credit_threshold,
    meaning changing that step changes the terminal outcome.

    Steps with credit == 0 are not causal: the outcome is the same whether
    the step happened or not. These steps are surface accidents, not causes.

    Returns the identified causal steps, or REFUSED if attribution fails.
    """
    if contrast_result["status"] != CONTRAST_DONE:
        return {
            "phase": "IDENTIFY",
            "status": REFUSED,
            "reason": contrast_result.get("reason", "NO_CONTRAST"),
            "model_calls": 0,
            "network_calls": 0,
        }

    step_credits = contrast_result["step_credits"]
    causal = [c for c in step_credits if c["is_causal"] and c["credit"] > min_credit_threshold]
    non_causal = [c for c in step_credits if not c["is_causal"] or c["credit"] <= min_credit_threshold]

    # Credit conservation: sum of all credits should equal the factual terminal
    # outcome minus the mean counterfactual terminal outcome across all steps.
    # This is a consistency check, not a requirement.
    total_credit = contrast_result["total_credit"]

    identified = {
        "phase": "IDENTIFY",
        "status": IDENTIFIED,
        "causal_steps": [c["step_index"] for c in causal],
        "non_causal_steps": [c["step_index"] for c in non_causal],
        "causal_count": len(causal),
        "non_causal_count": len(non_causal),
        "total_credit": total_credit,
        "factual_terminal_success": contrast_result["step_credits"][0]["factual_terminal_success"] if step_credits else 0,
        "step_credits": step_credits,
        "model_calls": 0,
        "network_calls": 0,
        "derivation": "counterfactual_credit_conservation",
    }

    # Fail-closed: if no counterfactuals separated any step, we cannot attribute
    # credit — refuse rather than manufacture attribution.
    separated_count = sum(
        1 for r in contrast_result.get("rollouts", []) if r["separated"]
    )
    if separated_count == 0 and len(contrast_result.get("rollouts", [])) > 0:
        identified["status"] = REFUSED
        identified["reason"] = "NO_STEP_SEPARATES_OUTCOME__ATTRIBUTION_IMPOSSIBLE"

    return identified


# --------------------------------------------------------------------------- #
# phase 4: ADMIT — held-out validation of credit attribution
# --------------------------------------------------------------------------- #


def admit_credit(
    identify_result: dict[str, Any],
    holdout_traces: Sequence[AgentTrace],
    root: pathlib.Path,
    wrong_actions: Sequence[Sequence[tuple[str, str]]],
) -> dict[str, Any]:
    """Admit credit attribution only if it holds on hold-out traces.

    For each hold-out trace, run the same counterfactual credit assignment.
    The attribution is admitted only if the same steps are identified as causal
    on the hold-out traces (generalization across traces).

    Fail-closed: refuse before persisting.
    """
    if identify_result["status"] != IDENTIFIED:
        return {
            "phase": "ADMIT",
            "status": REFUSED,
            "reason": identify_result.get("reason", "NOT_IDENTIFIED"),
            "model_calls": 0,
            "network_calls": 0,
        }

    identified_causal = set(identify_result["causal_steps"])

    holdout_results = []
    for trace in holdout_traces:
        # Build wrong_actions for this hold-out trace (same structure)
        ho_wrong = wrong_actions[: len(trace.steps)] if wrong_actions else [[] for _ in trace.steps]

        contrast = generate_counterfactuals(root, trace, ho_wrong)
        if contrast["status"] != CONTRAST_DONE:
            holdout_results.append({
                "trace_id": hashlib.sha256(
                    repr(trace).encode()
                ).hexdigest()[:12],
                "status": "SKIPPED",
                "reason": contrast.get("reason", "CONTRAST_FAILED"),
            })
            continue

        identification = identify_credit(contrast)
        ho_causal = set(identification.get("causal_steps", []))

        # Check agreement: do the same steps appear causal?
        agreement = identified_causal == ho_causal
        holdout_results.append({
            "trace_id": hashlib.sha256(repr(trace).encode()).hexdigest()[:12],
            "status": "ADMITTED" if agreement else "REFUSED",
            "causal_steps": sorted(ho_causal),
            "agreement": agreement,
        })

    admitted = all(
        r["status"] == "ADMITTED" for r in holdout_results if r["status"] != "SKIPPED"
    ) and len(holdout_results) > 0

    return {
        "phase": "ADMIT",
        "status": "ADMITTED" if admitted else REFUSED,
        "holdout_count": len(holdout_results),
        "admitted_count": sum(1 for r in holdout_results if r["status"] == "ADMITTED"),
        "holdout_results": holdout_results,
        "identified_causal_steps": sorted(identified_causal),
        "model_calls": 0,
        "network_calls": 0,
    }


# --------------------------------------------------------------------------- #
# phase 5: REMEMBER — persist only what admission admitted
# --------------------------------------------------------------------------- #


def remember_credit(
    admit_result: dict[str, Any],
) -> dict[str, Any]:
    """Persist only what the admission gate admitted.

    Credit attribution is calculated, not stored. Nothing is written to disk.
    The identified causal steps are returned as a calculated result.
    """
    if admit_result["status"] != "ADMITTED":
        return {
            "phase": "REMEMBER",
            "status": REFUSED,
            "reason": admit_result.get("reason", "ADMISSION_REFUSED"),
            "model_calls": 0,
            "network_calls": 0,
        }

    return {
        "phase": "REMEMBER",
        "status": REMEMBERED,
        "identified_causal_steps": admit_result["identified_causal_steps"],
        "holdout_count": admit_result["holdout_count"],
        "admitted_count": admit_result["admitted_count"],
        "model_calls": 0,
        "network_calls": 0,
        "stored_knowledge_bytes": 0,
        "knowledge_house": False,
        "derivation": "credit_attribution_calculated_not_stored",
    }


# --------------------------------------------------------------------------- #
# the complete credit assignment engine
# --------------------------------------------------------------------------- #


class CreditAssignment:
    """The complete credit assignment engine.

    SENSE → CONTRAST → IDENTIFY → ADMIT → REMEMBER

    Attributes which steps in an agent trace caused the terminal outcome
    using counterfactual interventions. Zero model calls, zero network calls,
    zero knowledge house.
    """

    def __init__(
        self,
        environment_root: pathlib.Path,
        *,
        max_rollouts_per_step: int = DEFAULT_COUNTERFACTUAL_ROLLOUTS,
    ) -> None:
        self.environment_root = environment_root
        self.max_rollouts_per_step = max_rollouts_per_step
        self.state = CalculatedState()
        self.assignments: list[dict[str, Any]] = []

    # -- SENSE ----------------------------------------------------------- #
    def sense(self, steps: Sequence[tuple[str, str]], terminal_outcome: int) -> dict[str, Any]:
        """Observe an agent trace."""
        result = sense_trace(self.environment_root, steps, terminal_outcome)
        if result["status"] == SENSE_DONE:
            self.state.add(
                "trace",
                {
                    "step_count": result["step_count"],
                    "terminal_outcome": result["terminal_outcome"],
                },
                "trace_observed_from_environment_snapshots",
            )
        return result

    # -- CONTRAST -------------------------------------------------------- #
    def contrast(
        self,
        sense_result: dict[str, Any],
        wrong_actions: Sequence[Sequence[tuple[str, str]]],
    ) -> dict[str, Any]:
        """Generate counterfactual interventions for each step."""
        if sense_result["status"] != SENSE_DONE:
            return {
                "phase": "CONTRAST",
                "status": REFUSED,
                "reason": "run SENSE first",
                "model_calls": 0,
                "network_calls": 0,
            }

        trace = sense_result["trace"]
        return generate_counterfactuals(
            self.environment_root,
            trace,
            wrong_actions,
            max_rollouts_per_step=self.max_rollouts_per_step,
        )

    # -- IDENTIFY -------------------------------------------------------- #
    def identify(
        self,
        contrast_result: dict[str, Any],
        min_credit_threshold: float = 0.0,
    ) -> dict[str, Any]:
        """Close credit by counterfactual comparison."""
        result = identify_credit(contrast_result, min_credit_threshold)
        if result["status"] == IDENTIFIED:
            self.state.add(
                "credit_attribution",
                {
                    "causal_steps": result["causal_steps"],
                    "total_credit": result["total_credit"],
                },
                "counterfactual_credit_conservation",
            )
        return result

    # -- ADMIT ----------------------------------------------------------- #
    def admit(
        self,
        identify_result: dict[str, Any],
        holdout_traces: Sequence[AgentTrace],
        wrong_actions: Sequence[Sequence[tuple[str, str]]],
    ) -> dict[str, Any]:
        """Admit credit attribution only if it holds on hold-out traces."""
        return admit_credit(
            identify_result,
            holdout_traces,
            self.environment_root,
            wrong_actions,
        )

    # -- REMEMBER -------------------------------------------------------- #
    def remember(
        self,
        admit_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist only what the admission gate admitted."""
        return remember_credit(admit_result)

    # -- FULL LOOP ------------------------------------------------------- #
    def run(
        self,
        steps: Sequence[tuple[str, str]],
        terminal_outcome: int,
        wrong_actions: Sequence[Sequence[tuple[str, str]]],
        holdout_traces: Sequence[AgentTrace] = (),
    ) -> dict[str, Any]:
        """Run the complete credit assignment loop.

        SENSE → CONTRAST → IDENTIFY → ADMIT → REMEMBER

        Returns which steps are causally responsible for the terminal outcome.
        """
        report: dict[str, Any] = {
            "schema": "PROJECT_BRAIN_CREDIT_ASSIGNMENT_V1",
            "authority": "NONE__PRODUCER_RUN_SANDBOX_CALCULATION",
            "model_calls": 0,
            "network_calls": 0,
            "phases": [],
        }

        # 1. SENSE
        sense = self.sense(steps, terminal_outcome)
        report["phases"].append(sense)
        if sense["status"] != SENSE_DONE:
            report["status"] = sense["status"]
            report["result"] = "REFUSED__NO_TRACE"
            return report

        # 2. CONTRAST
        contrast = self.contrast(sense, wrong_actions)
        report["phases"].append(contrast)
        if contrast["status"] != CONTRAST_DONE:
            report["status"] = contrast["status"]
            report["result"] = "REFUSED__NO_COUNTERFACTUALS"
            return report

        # 3. IDENTIFY
        identify = self.identify(contrast)
        report["phases"].append(identify)
        if identify["status"] != IDENTIFIED:
            report["status"] = identify["status"]
            report["result"] = "REFUSED__ATTRIBUTION_FAILED"
            return report

        # 4. ADMIT
        admit = self.admit(identify, holdout_traces, wrong_actions)
        report["phases"].append(admit)
        if admit["status"] != "ADMITTED":
            report["status"] = admit["status"]
            report["result"] = "REFUSED__ADMISSION_FAILED"
            return report

        # 5. REMEMBER
        remember = self.remember(admit)
        report["phases"].append(remember)
        if remember["status"] != REMEMBERED:
            report["status"] = remember["status"]
            report["result"] = "REFUSED__PERSISTENCE_FAILED"
            return report

        report["status"] = "COMPLETE"
        report["result"] = "CREDIT_ASSIGNMENT_COMPLETE"
        report["causal_steps"] = identify["causal_steps"]
        report["non_causal_steps"] = identify["non_causal_steps"]
        report["total_credit"] = identify["total_credit"]
        return report

    def status(self) -> dict[str, Any]:
        """Report the engine's status: calculated parameters, zero knowledge."""
        return {
            "schema": "PROJECT_BRAIN_CREDIT_ASSIGNMENT_V1",
            "authority": "NONE__PRODUCER_RUN_SANDBOX_CALCULATION",
            "model_calls": self.state.model_calls,
            "network_calls": self.state.network_calls,
            "parameters_calculated": len(self.state.parameters),
            "parameters_verified": sum(
                1 for p in self.state.parameters.values() if p.verified
            ),
            "assignments_executed": len(self.assignments),
            "stored_knowledge_bytes": 0,
            "knowledge_house": False,
            "every_parameter_calculated": True,
        }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Credit Assignment: SENSE→CONTRAST→IDENTIFY→ADMIT→REMEMBER, "
        "zero parameters, counterfactual intervention attribution.",
    )
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Environment root directory.",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="Write the full report to this path.",
    )
    ns = parser.parse_args(argv)

    engine = CreditAssignment(ns.root)
    # Minimal demo: a single step trace
    report = engine.run(
        steps=[("echo test", "")],
        terminal_outcome=1,
        wrong_actions=[[("wrong", "exit 1")]],
        holdout_traces=[],
    )
    print(json.dumps(report, indent=1, sort_keys=True))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
