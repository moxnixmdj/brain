"""The long-horizon tasks, run by pytest and judged on final state alone.

This file is a thin runner: it executes `canonical/tests/programs/long_horizon_v1.py` in a fresh
temporary world and asserts that every task ends in the state the task named. The tasks themselves are
kept in `programs/` because they are a benchmark, not a unit test, and running them as a subprocess keeps
their environment isolated from this process's.

Why these tasks exist at all: OSWorld 2.0 (arXiv 2606.29537, June 2026) reports 20.6% strict completion
for the best agent and names the failures as long-horizon state, error repair, implicit-state inference
and *dynamic environment*. The suite here tests exactly those four, and none of the existing suites does.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PROGRAM = _ROOT / "canonical/tests/programs/long_horizon_v1.py"


def test_every_long_horizon_task_ends_in_the_state_it_named() -> None:
    result = subprocess.run([sys.executable, str(_PROGRAM)], capture_output=True, text=True,
                            cwd=str(_PROGRAM.parent), timeout=600)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "6/6 long-horizon tasks pass" in result.stdout, result.stdout


def test_a_refusal_that_names_the_fact_is_enough_to_repair() -> None:
    """THE JOIN A87 PROMISED AND DID NOT MAKE: a long-horizon task repaired from refusals alone.

    `ledgerctl` documents `--name` and `--amount` and documents none of the three rules it enforces. A
    planner reading only the pages produces `--amount 12.50`, which the page permits and the program
    refuses with `AMOUNT_MUST_BE_A_WHOLE_NUMBER:12.50`. The fix follows from the refusal, and nothing
    else does: no value is invented, and the same `CODE:detail` string a person reads is the string the
    loop parses.

    This is the point of the convention A87 made enforceable. An unlocated refusal (`AMOUNT_INVALID`)
    would say a rule was broken and not which value or what to do, and the loop would have to guess.
    """
    import json
    import os
    import tempfile

    bin_dir = _ROOT / "canonical/tests/programs/bin"
    world = pathlib.Path(tempfile.mkdtemp(prefix="refusal-repair-"))
    os.environ["LEDGER_STATE"] = str(world / "ledger.json")

    def call(args: list[str]) -> subprocess.CompletedProcess:
        env = dict(os.environ, LEDGER_STATE=str(world / "ledger.json"))
        return subprocess.run([sys.executable, str(bin_dir / "ledgerctl")] + args,
                              capture_output=True, text=True, env=env, cwd=str(bin_dir))

    # THE FIRST THING THE PROGRAM SAYS IS THE FIRST THING TO FIX, and it is not the thing a reader
    # would predict. The amount is checked before the nesting, so `--amount 12.50` is refused for
    # its decimal point and the nesting is not mentioned yet. A repair loop that assumed it knew
    # which rule would fire first would apply the wrong fix. Only the refusal decides that, which
    # is why the loop is driven by the string the program printed.
    first = call(["record", "add", "--name", "alpha.beta", "--amount", "12.50"])
    assert first.returncode != 0
    code, _, detail = first.stderr.strip().partition(":")
    assert code == "AMOUNT_MUST_BE_A_WHOLE_NUMBER", first.stderr
    assert detail == "12.50"

    # repair 1: a whole number, which is what the refusal asked for
    second = call(["record", "add", "--name", "alpha.beta", "--amount", "13"])
    code, _, detail = second.stderr.strip().partition(":")
    assert code == "NO_RECORDS_IN", second.stderr
    assert detail == "alpha", "the refusal did not name the parent: %r" % (second.stderr,)

    # repair 2: the parent the refusal named must exist first
    assert call(["record", "add", "--name", detail, "--amount", "1"]).returncode == 0

    # now the original command succeeds untouched -- the same argv, refused twice, accepted here
    final = call(["record", "add", "--name", "alpha.beta", "--amount", "13"])
    assert final.returncode == 0, final.stderr

    total = call(["report", "totals", "--prefix", "alpha"])
    assert total.returncode == 0, total.stderr
    assert json.loads(total.stdout)["total"] == 14


def test_an_unlocated_refusal_would_not_be_repairable() -> None:
    """The contrast that justifies the convention. Both programs refuse; only one says enough."""
    bin_dir = _ROOT / "canonical/tests/programs/bin"
    located = subprocess.run([sys.executable, str(bin_dir / "ledgerctl"), "record", "add",
                              "--name", "x.y", "--amount", "1"],
                             capture_output=True, text=True,
                             env=dict(__import__("os").environ, LEDGER_STATE="/tmp/none-" + "x.json"),
                             cwd=str(bin_dir))
    assert located.returncode != 0
    assert ":" in located.stderr.strip(), \
        "a refusal that does not locate its subject cannot be answered: %r" % (located.stderr,)
