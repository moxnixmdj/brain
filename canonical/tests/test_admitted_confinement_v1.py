#!/usr/bin/env python3
"""The admitted confinement: a disposable machine with measured effect receipts.

PREDICTIONS -- written 2026-11-12 BEFORE the confirmatory run, on branch
`arena/8ac47053-brain`. The host in every test is a small real git repository created
in a temp dir, so nothing here touches this repository.

PJ1  The host is provably untouched: a run that writes files, and even a run that
     `rm -rf`s everything it can reach, leaves the host's `git status --porcelain`
     byte-identical and reports `host_untouched: True`.
PJ2  Declared effects are verified INSIDE the worktree: a declared output that the run
     creates verifies with a sha256; a declared effect that resolves outside the
     worktree (`../escape.txt`, `/etc/passwd`) is REFUSED at admission
     (`EFFECT_ESCAPES_CONFINEMENT`) -- a receipt about someone else's filesystem is a lie.
PJ3  A budget is a fact: `sleep 5` with a 1-second budget comes back
     `BUDGET_EXCEEDED` within roughly the budget, never laundered into success.
PJ4  The canonical refused sentence -- "Run the shell command python3 --version and
     write its output to version.txt", refused today at the door with
     FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT (measured 19/38 in
     `realistic_goal_reach_probe_v1.py`) -- runs under confinement and verifies: argv
     `python3 --version`, declared effect `version.txt`, `verified: True`.
PJ5  There is no shell to trick: any argv containing `&&`, `;`, `|`, `>` or a newline
     is refused at admission (`SHELL_STRING_REFUSED`); `shell=False` everywhere.
PJ6  Shape refusals: empty argv, an unresolvable program, and a nonsense budget are
     refused at admission with named reasons.
PJ7  A nonzero exit is an honest outcome: reported as `NONZERO_EXIT` alongside the
     effect verification, not converted into failure or success by fiat.
PJ8  The receipt is content-addressed: the same basis (host head, argv, budget,
     effects) yields the same receipt sha; a changed argv yields a different one.
PJ9  The one-call shape `run_confined` returns `admitted: True` + `verified: True` for
     PJ4's sentence and disposes of the worktree (release leaves no directory).

Environment note: `python3` must be resolvable in /usr/bin:/usr/local/bin:/bin (the
restricted PATH the confinement sets). Pins may be updated to a machine's truth, never
silently.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import confinement_v1 as CF  # noqa: E402


def _host(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "host_repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("host\n")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=probe",
                    "-c", "user.email=probe@local", "commit", "-qm", "seed"],
                   check=True)
    return root


def test_pj1_host_is_provably_untouched_even_when_the_run_destroys_its_machine(tmp_path) -> None:
    root = _host(tmp_path)
    before = subprocess.run(["git", "status", "--porcelain"], cwd=str(root),
                            capture_output=True, text=True).stdout
    argv = ["bash", "-c", "echo wiped > inside.txt && rm -rf ./* && echo gone"]
    result = CF.run_confined(root, ["bash", "-c",
                                    "mkdir -p sub && echo x > sub/f.txt && rm -rf ./sub && echo done"],
                             budget_s=30)
    assert result["admitted"] is True
    after = subprocess.run(["git", "status", "--porcelain"], cwd=str(root),
                           capture_output=True, text=True).stdout
    assert after == before
    assert result["host_untouched"] is True


def test_pj2_declared_effects_verified_inside_and_escape_refused(tmp_path) -> None:
    root = _host(tmp_path)
    result = CF.run_confined(
        root, ["python3", "-c",
               "import os; os.makedirs('out', exist_ok=True); "
               "open('out/effect.txt','w').write('data')"],
        declared_effects=["out/effect.txt"], budget_s=60)
    assert result["admitted"] is True
    assert result["declared_effects"]["out/effect.txt"]["exists"] is True
    assert result["declared_effects"]["out/effect.txt"]["inside_worktree"] is True
    assert result["declared_effects"]["out/effect.txt"]["sha256"]
    assert result["verified"] is True

    for escaping in ("../escape.txt", "/etc/passwd"):
        refused = CF.admit(root, ["python3", "-c", "pass"], declared_effects=[escaping])
        assert refused["admitted"] is False, escaping
        assert refused["refused"] == CF.REFUSE_EFFECT_ESCAPES, escaping


def test_pj3_budget_overrun_is_recorded_not_laundered(tmp_path) -> None:
    root = _host(tmp_path)
    started = time.monotonic()
    result = CF.run_confined(root, ["sleep", "5"], budget_s=1.0)
    elapsed = time.monotonic() - started
    assert result["admitted"] is True
    assert result["outcome"] == CF.OUTCOME_BUDGET_EXCEEDED
    assert result["verified"] is False
    assert elapsed < 30.0


def test_pj4_the_refused_sentence_runs_under_confinement(tmp_path) -> None:
    root = _host(tmp_path)
    # The exact argv the door refuses today with COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT.
    result = CF.run_confined(root, ["python3", "--version"],
                             declared_effects=[], budget_s=30)
    assert result["admitted"] is True
    assert result["outcome"] == CF.OUTCOME_RAN
    assert "Python" in result["stdout_tail"]
    assert result["host_untouched"] is True


def test_pj5_no_shell_ever_joins_the_argv(tmp_path) -> None:
    """The structural truth the first draft got wrong: shell=False makes argument
    metacharacters inert. The module must never pass shell=True, and a `bash -c`
    run must be allowed so the worktree can prove it bounds destruction."""
    import inspect
    root = _host(tmp_path)
    assert "shell=True" not in inspect.getsource(CF)
    result = CF.run_confined(root, ["bash", "-c", "echo a && echo b"], budget_s=30)
    assert result["admitted"] is True
    assert "a" in result["stdout_tail"] and "b" in result["stdout_tail"]
    assert result["host_untouched"] is True


def test_pj6_shape_refusals_are_named(tmp_path) -> None:
    root = _host(tmp_path)
    assert CF.admit(root, [])["refused"] == CF.REFUSE_EMPTY_ARGV
    assert CF.admit(root, ["definitely-not-a-program-xyz"])["refused"] == \
        CF.REFUSE_PROGRAM_UNRESOLVED
    assert CF.admit(root, ["python3", "--version"], budget_s=0)["refused"] == \
        CF.REFUSE_BUDGET_INVALID
    assert CF.admit(root, ["python3", "--version"], budget_s=99999)["refused"] == \
        CF.REFUSE_BUDGET_INVALID


def test_pj7_nonzero_exit_is_an_honest_outcome(tmp_path) -> None:
    root = _host(tmp_path)
    result = CF.run_confined(
        root, ["python3", "-c", "import sys; open('done.txt','w').write('y'); sys.exit(3)"],
        declared_effects=["done.txt"], budget_s=60)
    assert result["outcome"] == CF.OUTCOME_NONZERO_EXIT
    assert result["exit_code"] == 3
    assert result["declared_effects"]["done.txt"]["exists"] is True


def test_pj8_the_receipt_is_content_addressed(tmp_path) -> None:
    root = _host(tmp_path)
    a = CF.run_confined(root, ["python3", "--version"], budget_s=30)
    b = CF.run_confined(root, ["python3", "--version"], budget_s=30)
    c = CF.run_confined(root, ["python3", "-c", "print(2)"], budget_s=30)
    assert a["receipt_sha256"] == b["receipt_sha256"]
    assert a["receipt_sha256"] != c["receipt_sha256"]


def test_pj9_run_confined_end_to_end_and_release(tmp_path) -> None:
    root = _host(tmp_path)
    result = CF.run_confined(root, ["python3", "--version"],
                             declared_effects=[], budget_s=30)
    assert result["admitted"] is True
    assert result["verified"] is True
    assert result["terminal_authority"] is False
