"""THE CLAIM, END TO END: demonstrate once, then answer a NEW file instantly and permanently.

Measured 2026-11-09. Every step below is a real subprocess under the real carrier.

  demonstrate "how many unique lines in data.txt"  (16 rows, 8 distinct)
    -> answered 8, under admitted confinement
    -> crystallised PASS__WORKFLOW_SKILL_COMPILED_QUALIFIED_AND_OWNED
  then "how many unique lines in pods.txt"         (26 rows, 13 distinct)
    -> answered 13, from the learned skill

The three walls that stood in the way, each fixed and each with its own test here:

  1. execute_compiled_steps refused EVERY cli_exec step outright. It now routes a step
     to the carrier when the carrier would admit exactly that argv, and keeps the
     original refusal otherwise.
  2. the postcondition was {"kind": "stdout_integer"} for a program whose output is a
     SET. Added stdout_line_count, which is the right shape for "how many".
  3. the held-out and sabotage contracts were hard-coded to stdout_equals "11", so a
     correct set-printing skill was rejected on nine distinct rows.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
    _carried_step_is_admissible,
    execute_compiled_steps,
    verify_postcondition,
)
from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as ctrl

BASE = ROOT / "canonical" / "astra_runtime" / "tmp"


def _ws() -> Path:
    BASE.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="e2e_", dir=str(BASE)))


def _dupes(n: int, each: int = 2) -> str:
    return "\n".join(f"row-{i}" for i in range(n) for _ in range(each)) + "\n"


# ---- wall 1: the CLI step is routed, not refused -------------------------

def test_a_read_only_cli_step_runs_under_the_carrier():
    d = _ws()
    (d / "data.txt").write_text(_dupes(8))
    out = execute_compiled_steps([{"layer": "cli_exec", "argv": ["sort", "-u", "data.txt"]}], cwd=d)
    assert out["ok"] is True, out.get("status")
    receipt = out["step_receipts"][0]
    assert receipt["confined"] is True
    assert receipt["live_workspace_untouched"] is True
    assert len([l for l in (receipt["stdout"] or "").splitlines() if l.strip()]) == 8


def test_a_write_flag_is_still_refused_exactly_as_before():
    d = _ws()
    (d / "data.txt").write_text(_dupes(3))
    out = execute_compiled_steps([{"layer": "cli_exec", "argv": ["sed", "-i", "s/a/b/", "data.txt"]}], cwd=d)
    assert out["ok"] is False
    assert out["status"] == "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT"
    assert _carried_step_is_admissible({"argv": ["sed", "-i", "s/a/b/", "x"]}) is False


def test_a_pipeline_of_admitted_reads_is_carried_a_pipeline_of_anything_else_is_not():
    """UPDATED 2026-11-09 (r43). This test used to assert that NO pipeline runs, because
    the carrier took one argv and `cli_pipeline` was refused. That refusal was the
    ceiling: 23 verbs in parallel is 23 capabilities, 23 that sequence is thousands.

    The rule did not loosen -- it got precise. A pipe now runs when EVERY stage is a verb
    the carrier would admit on its own, and the command is built from structure rather
    than supplied as a string. `sh` is still refused, and so is any stage that is not
    read-only. See test_two_admitted_verbs_can_be_piped_v1.py for the 13 attacks.
    """
    d = _ws()
    (d / "data.txt").write_text(_dupes(3))
    out = execute_compiled_steps(
        [{"layer": "cli_pipeline", "stages": [["sort", "-u", "data.txt"], ["wc", "-l"]]}], cwd=d)
    assert out["ok"] is True, out.get("status")

    # and the safety half is unchanged: a shell stage is refused
    refused = execute_compiled_steps(
        [{"layer": "cli_pipeline", "stages": [["sh", "-c", "id"], ["wc", "-l"]]}], cwd=d)
    assert refused["ok"] is False


# ---- wall 2: the count postcondition has the right shape ----------------

def test_stdout_line_count_counts_distinct_rows():
    er = {"step_receipts": [{"stdout": "a\nb\nc\n"}]}
    ok, why = verify_postcondition({"kind": "stdout_line_count", "equals": 3}, execution_result=er)
    assert ok, why
    assert "3" in why


def test_stdout_line_count_refuses_the_wrong_number():
    er = {"step_receipts": [{"stdout": "a\nb\nc\n"}]}
    ok, why = verify_postcondition({"kind": "stdout_line_count", "equals": 9}, execution_result=er)
    assert not ok
    assert why.startswith("POSTCONDITION_STDOUT_LINE_COUNT_MISMATCH")


# ---- wall 3 + the whole claim: demonstrate once, then a NEW file --------

def test_demonstrate_once_then_answer_a_different_file_from_the_learned_skill():
    d = _ws()
    db = d / "skills.sqlite"
    (d / "data.txt").write_text(_dupes(8))

    first = ctrl.solve_or_learn({"goal": "how many unique lines in data.txt", "task_id": "e2e1"},
                                cwd=d, db_path=db)
    assert first.get("pass") is True, first
    assert str(first.get("answer")).strip() == "8", first
    assert first.get("confined") is True
    assert first.get("skill_crystallized") is True, first.get("qualification_receipt")
    assert str((first.get("qualification_receipt") or {}).get("status")).startswith("PASS__")

    (d / "pods.txt").write_text(_dupes(13))
    second = ctrl.solve_or_learn({"goal": "how many unique lines in pods.txt", "task_id": "e2e2"},
                                 cwd=d, db_path=db)
    assert second.get("pass") is True, second
    assert str(second.get("answer")).strip() == "13", second


def test_the_learned_answer_is_not_the_number_it_was_shown():
    """Permanence must not be the copy rule from the round-24 experiment."""
    d = _ws()
    db = d / "skills.sqlite"
    (d / "a.txt").write_text(_dupes(4))
    ctrl.solve_or_learn({"goal": "how many unique lines in a.txt", "task_id": "p1"}, cwd=d, db_path=db)
    (d / "b.txt").write_text(_dupes(21))
    out = ctrl.solve_or_learn({"goal": "how many unique lines in b.txt", "task_id": "p2"}, cwd=d, db_path=db)
    assert str(out.get("answer")).strip() == "21", out
