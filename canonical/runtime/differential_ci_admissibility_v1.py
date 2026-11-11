#!/usr/bin/env python3
"""Fail-closed differential attribution for CI failures.

This module answers one narrow question:
    Did the branch introduce a verifier regression relative to its exact base?

It deliberately does NOT answer whether the branch is terminally valid, mergeable,
or entitled to acceptance/capability/family/ownership credit.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class Decision:
    classification: str
    patch_regression_proved: bool
    branch_absolute_validator_pass: bool
    baseline_validator_pass: bool
    inherited_failure_proved: bool
    differential_gate_pass: bool
    terminal_finality_authority: bool
    merge_authority: bool
    acceptance_credit_delta: int
    reason: str


def classify(
    base_exit_code: int,
    branch_exit_code: int,
    base_fingerprint: Optional[str] = None,
    branch_fingerprint: Optional[str] = None,
) -> Decision:
    base_ok = base_exit_code == 0
    branch_ok = branch_exit_code == 0

    if base_ok and branch_ok:
        return Decision(
            classification="BOTH_PASS",
            patch_regression_proved=False,
            branch_absolute_validator_pass=True,
            baseline_validator_pass=True,
            inherited_failure_proved=False,
            differential_gate_pass=True,
            terminal_finality_authority=False,
            merge_authority=False,
            acceptance_credit_delta=0,
            reason="The selected validator passes on both exact base and branch.",
        )

    if base_ok and not branch_ok:
        return Decision(
            classification="BRANCH_REGRESSION",
            patch_regression_proved=True,
            branch_absolute_validator_pass=False,
            baseline_validator_pass=True,
            inherited_failure_proved=False,
            differential_gate_pass=False,
            terminal_finality_authority=False,
            merge_authority=False,
            acceptance_credit_delta=0,
            reason="The validator passed on exact base and failed on branch.",
        )

    if not base_ok and branch_ok:
        return Decision(
            classification="BRANCH_IMPROVEMENT",
            patch_regression_proved=False,
            branch_absolute_validator_pass=True,
            baseline_validator_pass=False,
            inherited_failure_proved=False,
            differential_gate_pass=True,
            terminal_finality_authority=False,
            merge_authority=False,
            acceptance_credit_delta=0,
            reason="The branch repaired or bypassed a validator failure present on exact base.",
        )

    same_fingerprint = (
        bool(base_fingerprint)
        and bool(branch_fingerprint)
        and base_fingerprint == branch_fingerprint
    )
    if same_fingerprint:
        return Decision(
            classification="INHERITED_BASELINE_FAILURE",
            patch_regression_proved=False,
            branch_absolute_validator_pass=False,
            baseline_validator_pass=False,
            inherited_failure_proved=True,
            differential_gate_pass=True,
            terminal_finality_authority=False,
            merge_authority=False,
            acceptance_credit_delta=0,
            reason=(
                "Base and branch both fail with the same non-empty failure fingerprint. "
                "This proves inheritance for regression attribution only; absolute "
                "validation remains unavailable."
            ),
        )

    return Decision(
        classification="DUAL_FAILURE_UNRESOLVED_DELTA",
        patch_regression_proved=False,
        branch_absolute_validator_pass=False,
        baseline_validator_pass=False,
        inherited_failure_proved=False,
        differential_gate_pass=False,
        terminal_finality_authority=False,
        merge_authority=False,
        acceptance_credit_delta=0,
        reason=(
            "Base and branch both fail, but identical failure identity is not proved. "
            "Fail closed until a differential fingerprint or independent validator resolves it."
        ),
    )


def _self_test() -> None:
    cases = [
        ((0, 0, None, None), "BOTH_PASS", True),
        ((0, 1, "a", "b"), "BRANCH_REGRESSION", False),
        ((1, 0, "a", None), "BRANCH_IMPROVEMENT", True),
        ((1, 1, "same", "same"), "INHERITED_BASELINE_FAILURE", True),
        ((1, 1, "a", "b"), "DUAL_FAILURE_UNRESOLVED_DELTA", False),
        ((1, 1, None, None), "DUAL_FAILURE_UNRESOLVED_DELTA", False),
    ]
    for args, expected_class, expected_gate in cases:
        d = classify(*args)
        assert d.classification == expected_class, (args, d)
        assert d.differential_gate_pass is expected_gate, (args, d)
        assert d.terminal_finality_authority is False
        assert d.merge_authority is False
        assert d.acceptance_credit_delta == 0
    print(json.dumps({"self_test": "PASS", "cases": len(cases)}, sort_keys=True))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-exit", type=int)
    p.add_argument("--branch-exit", type=int)
    p.add_argument("--base-fingerprint")
    p.add_argument("--branch-fingerprint")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()

    if args.self_test:
        _self_test()
        return 0

    if args.base_exit is None or args.branch_exit is None:
        p.error("--base-exit and --branch-exit are required unless --self-test is used")

    decision = classify(
        args.base_exit,
        args.branch_exit,
        args.base_fingerprint,
        args.branch_fingerprint,
    )
    print(json.dumps(asdict(decision), sort_keys=True))

    # This exit code represents the *differential regression-attribution gate* only.
    # Terminal-finality and merge authority remain false in the emitted decision.
    return 0 if decision.differential_gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
