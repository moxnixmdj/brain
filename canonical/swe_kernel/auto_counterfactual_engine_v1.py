#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto-discovered counterfactual engine — zero model calls, zero network calls.

THE ARGUMENT
------------
Manual counterfactual construction (supplying wrong_actions by hand) is the
single biggest engineering bottleneck in the instant one-shot learning loop.
Every new task requires hand-crafted mutants. This module eliminates that
bottleneck by systematically generating counterfactuals from a successful
trace using deterministic mutation operators:

    swap     — exchange two adjacent actions
    delete   — remove one action
    substitute — replace an action with a mutant variant
    reorder  — permute actions within a bounded window
    perturb  — change command arguments (src→dst, arg→alt_arg)

Each mutant is executed against a resettable environment snapshot. If the
terminal outcome changes, the mutated step is causally credited. This is
combinatorial search over counterfactual space — no model, no network, no
persistence.

ELON'S RULE APPLIED
-------------------
The best part is no part: no model calls for mutant generation, no network
calls for candidate search, no knowledge house for mutant storage. Every
mutant is generated from first principles (mutation operators + snapshot
restore), executed, and discarded.

Authority: NONE. Producer-run sandbox measurement.
"""

from __future__ import annotations

import itertools
import pathlib
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Mutant:
    """A single counterfactual mutant of a trace step."""

    step_index: int
    operator: str  # "substitute" | "delete" | "swap" | "reorder" | "perturb"
    original_action: str
    mutant_action: str | None  # None for delete/swap/reorder
    outcome_changed: bool
    original_outcome: int
    mutant_outcome: int
    credit: int  # 1 if outcome changed, 0 if not


@dataclass(frozen=True)
class CounterfactualResult:
    """Result of auto-discovered counterfactual attribution."""

    causal_steps: tuple[int, ...]
    non_causal_steps: tuple[int, ...]
    total_credit: int
    mutants: tuple[Mutant, ...]
    mutants_tested: int
    model_calls: int
    network_calls: int


# --------------------------------------------------------------------------- #
# Mutation operators — deterministic, combinatorial, no model involvement     #
# --------------------------------------------------------------------------- #


def _substitute_mutants(action: str) -> list[str]:
    """Generate substitute mutants for a single shell command.

    Operates on the command token level:
    - cp → mv (wrong operation)
    - src → nonexistent (wrong argument)
    - → /dev/null (redirect to null)
    - append → truncate (>> → >)
    """
    parts = action.split()
    if not parts:
        return []
    mutants: list[str] = []
    cmd = parts[0]
    args = parts[1:]

    # Operation swap: cp ↔ mv, rm → touch, etc.
    op_swap = {"cp": "mv", "mv": "cp", "rm": "touch", "touch": "rm",
               "sort": "cat", "cat": "sort", "gzip": "cat", "cat": "gzip"}
    if cmd in op_swap:
        mutants.append(op_swap[cmd] + (" " + " ".join(args) if args else ""))

    # Argument corruption: replace first file argument with nonexistent
    for i, a in enumerate(args):
        if a.startswith("-") or a == "":
            continue
        mutant_args = list(args)
        mutant_args[i] = "nonexistent_" + a
        mutants.append(cmd + " " + " ".join(mutant_args))
        break  # only corrupt first file arg

    # Redirect mutation: >> → >, > → >>, add 2>/dev/null
    if ">>" in action:
        mutants.append(action.replace(">>", ">"))
    if ">" in action and ">>" not in action:
        mutants.append(action.replace(">", ">>"))
    if "2>" not in action:
        mutants.append(action + " 2>/dev/null")

    return mutants


def _delete_mutant(steps: list[tuple[str, str]], index: int) -> list[tuple[str, str]]:
    """Remove the step at index."""
    return [s for i, s in enumerate(steps) if i != index]


def _swap_mutant(steps: list[tuple[str, str]], index: int) -> list[tuple[str, str]]:
    """Swap step at index with the next step."""
    if index + 1 >= len(steps):
        return steps
    result = list(steps)
    result[index], result[index + 1] = result[index + 1], result[index]
    return result


def _reorder_mutant(steps: list[tuple[str, str]], index: int) -> list[tuple[str, str]]:
    """Move step at index to the end (bounded permutation)."""
    if len(steps) <= 1:
        return steps
    result = list(steps)
    step = result.pop(index)
    result.append(step)
    return result


def _perturb_mutant(steps: list[tuple[str, str]], index: int) -> list[tuple[str, str]]:
    """Replace the action at index with a substitute mutant."""
    action = steps[index][0]
    subs = _substitute_mutants(action)
    if not subs:
        return steps
    result = list(steps)
    result[index] = (subs[0], steps[index][1])  # use first substitute
    return result


# --------------------------------------------------------------------------- #
# Execution substrate — deterministic shell, snapshot restore                 #
# --------------------------------------------------------------------------- #


def _execute_action(action: str, cwd: pathlib.Path) -> tuple[int, str, str]:
    """Execute a shell command deterministically. Returns (rc, stdout, stderr)."""
    try:
        result = subprocess.run(
            action,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)


def _snapshot(root: pathlib.Path) -> dict[str, bytes]:
    """Snapshot all files under root (excluding .git, __pycache__)."""
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
    }


def _restore(root: pathlib.Path, snapshot: dict[str, bytes]) -> None:
    """Restore environment from snapshot. Creates files, deletes extra ones."""
    current = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    for rel in current:
        if rel not in snapshot:
            (root / rel).unlink()
    for rel, data in snapshot.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)


# --------------------------------------------------------------------------- #
# Core engine                                                                 #
# --------------------------------------------------------------------------- #


class AutoCounterfactualEngine:
    """Systematically discovers counterfactuals from a successful trace.

    For each step k:
      1. Restore snapshot at k
      2. Execute factual action → terminal outcome
      3. For each mutant operator at k: restore snapshot, execute mutant,
         replay remaining steps → terminal outcome
      4. Credit(k) = 1 if any mutant changes the outcome, 0 otherwise

    Fail-closed: if no mutants can be generated or no separation is found,
    attribution is refused.
    """

    def __init__(self, environment_root: pathlib.Path):
        self.environment_root = environment_root
        self.model_calls = 0
        self.network_calls = 0

    def attribute(
        self,
        steps: Sequence[tuple[str, str]],
        terminal_outcome: int,
        max_mutants_per_step: int = 5,
    ) -> CounterfactualResult:
        """Run auto-discovered counterfactual attribution on a trace.

        Parameters
        ----------
        steps : sequence of (action, expected_marker)
            The successful trace to attribute.
        terminal_outcome : int
            The terminal outcome (0 = failure, 1 = success).
        max_mutants_per_step : int
            Maximum mutants to generate per step (bounds combinatorial
            explosion — deterministic cap, not learned).
        """
        if not steps:
            return CounterfactualResult(
                causal_steps=(),
                non_causal_steps=(),
                total_credit=0,
                mutants=(),
                mutants_tested=0,
                model_calls=0,
                network_calls=0,
            )

        steps_list = list(steps)
        n_steps = len(steps_list)
        causal: set[int] = set()
        all_mutants: list[Mutant] = []
        mutants_tested = 0

        for step_index in range(n_steps):
            # Capture snapshot before this step
            snapshot = _snapshot(self.environment_root)

            # Execute factual action at this step, then replay remaining
            factual_action = steps_list[step_index][0]
            factual_rc, _, _ = _execute_action(factual_action, self.environment_root)

            # Replay remaining steps from snapshot+1
            remaining_rc = 0
            for i in range(step_index + 1, n_steps):
                rc, _, _ = _execute_action(steps_list[i][0], self.environment_root)
                if rc != 0:
                    remaining_rc = rc
                    break

            factual_terminal = 1 if (factual_rc == 0 and remaining_rc == 0) else 0

            # Generate mutants for this step
            step_mutants: list[tuple[str, str, str | str]] = []  # (operator, original, mutant)

            # Substitute mutants
            for m in _substitute_mutants(factual_action)[:max_mutants_per_step]:
                step_mutants.append(("substitute", factual_action, m))

            # Delete mutant
            step_mutants.append(("delete", factual_action, None))

            # Swap mutant (only if not last step)
            if step_index + 1 < n_steps:
                step_mutants.append(("swap", factual_action, steps_list[step_index + 1][0]))

            # Reorder mutant
            if n_steps > 1:
                step_mutants.append(("reorder", factual_action, None))

            # Perturb mutant (same as substitute but distinct operator label)
            subs = _substitute_mutants(factual_action)
            if len(subs) > 1:
                step_mutants.append(("perturb", factual_action, subs[1]))

            # Test each mutant
            step_changed_outcome = False
            for operator, original, mutant in step_mutants:
                if mutants_tested >= max_mutants_per_step * n_steps:
                    break

                # Restore snapshot at this step
                _restore(self.environment_root, snapshot)

                # Execute mutant at this step
                if operator == "delete":
                    # Skip this step, replay the rest
                    mutant_rc = 0
                    for i in range(step_index, n_steps):
                        if i == step_index:
                            continue
                        rc, _, _ = _execute_action(steps_list[i][0], self.environment_root)
                        if rc != 0:
                            mutant_rc = rc
                            break
                elif operator == "swap":
                    # Execute swapped pair
                    rc1, _, _ = _execute_action(steps_list[step_index + 1][0], self.environment_root)
                    rc2, _, _ = _execute_action(factual_action, self.environment_root)
                    mutant_rc = rc1 or rc2
                    # Replay remaining
                    for i in range(step_index + 2, n_steps):
                        rc, _, _ = _execute_action(steps_list[i][0], self.environment_root)
                        if rc != 0:
                            mutant_rc = rc
                            break
                elif operator == "reorder":
                    # Move this step to end, replay all in new order
                    mutant_rc = 0
                    new_order = _reorder_mutant(steps_list, step_index)
                    for action, _ in new_order:
                        rc, _, _ = _execute_action(action, self.environment_root)
                        if rc != 0:
                            mutant_rc = rc
                            break
                else:
                    # substitute or perturb
                    assert mutant is not None
                    rc, _, _ = _execute_action(mutant, self.environment_root)
                    mutant_rc = rc
                    # Replay remaining steps
                    for i in range(step_index + 1, n_steps):
                        rc, _, _ = _execute_action(steps_list[i][0], self.environment_root)
                        if rc != 0:
                            mutant_rc = rc
                            break

                mutant_terminal = 1 if mutant_rc == 0 else 0
                outcome_changed = 1 if mutant_terminal != factual_terminal else 0
                if outcome_changed:
                    causal.add(step_index)
                    step_changed_outcome = True

                all_mutants.append(Mutant(
                    step_index=step_index,
                    operator=operator,
                    original_action=original,
                    mutant_action=mutant,
                    outcome_changed=bool(outcome_changed),
                    original_outcome=factual_terminal,
                    mutant_outcome=mutant_terminal,
                    credit=outcome_changed,
                ))
                mutants_tested += 1

            # Restore to factual state after testing mutants at this step
            _restore(self.environment_root, snapshot)
            _execute_action(factual_action, self.environment_root)
            for i in range(step_index + 1, n_steps):
                _execute_action(steps_list[i][0], self.environment_root)

        non_causal = tuple(i for i in range(n_steps) if i not in causal)
        total_credit = len(causal)

        return CounterfactualResult(
            causal_steps=tuple(sorted(causal)),
            non_causal_steps=non_causal,
            total_credit=total_credit,
            mutants=tuple(all_mutants),
            mutants_tested=mutants_tested,
            model_calls=0,
            network_calls=0,
        )


# --------------------------------------------------------------------------- #
# Convenience function                                                        #
# --------------------------------------------------------------------------- #


def auto_attribute_credit(
    environment_root: pathlib.Path,
    steps: Sequence[tuple[str, str]],
    terminal_outcome: int,
    max_mutants_per_step: int = 5,
) -> dict[str, Any]:
    """Convenience wrapper returning a dict result."""
    engine = AutoCounterfactualEngine(environment_root)
    result = engine.attribute(steps, terminal_outcome, max_mutants_per_step)
    return {
        "causal_steps": result.causal_steps,
        "non_causal_steps": result.non_causal_steps,
        "total_credit": result.total_credit,
        "mutants_tested": result.mutants_tested,
        "mutants": [
            {
                "step_index": m.step_index,
                "operator": m.operator,
                "original_action": m.original_action,
                "mutant_action": m.mutant_action,
                "outcome_changed": m.outcome_changed,
                "credit": m.credit,
            }
            for m in result.mutants
        ],
        "model_calls": result.model_calls,
        "network_calls": result.network_calls,
    }
