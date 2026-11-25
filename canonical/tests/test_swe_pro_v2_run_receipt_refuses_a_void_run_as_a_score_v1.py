"""Tests for the benchmark-run receipt: when may a number be quoted, and when must it vanish.

These tests drive `build_receipt` directly. The property under test is a negative one:
a report that contains a table of zeros must NOT come out of the receipt as a resolve
rate, because in this project's history such a table has meant "the harness read no
trials" more often than it has meant "the engine failed".
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parents[1]))

import swe_pro_v2_run_receipt_v1 as rc  # noqa: E402


def row(*, reward, agent_status, resolved, trial_dir=None):
    r = {
        "reward": reward,
        "resolved": resolved,
        "agent_status": agent_status,
        "n_files_changed": 1 if agent_status == "EDITS_UPLOADED" else 0,
    }
    if trial_dir:
        r["trial_dir"] = trial_dir
    return r


VOID = {
    "schema": "brain.bench_eval_report.v1",
    "run_produced_number": True,  # the harness flag was WRONG here; the receipt must not inherit it
    "benchmark": "SWE-bench Pro V2 (smoke: 3 qutebrowser HARD-51 tasks)",
    "commit": "003e43df",
    "arms": {
        arm: {
            "arm": arm,
            "n_expected": 3,
            "n_reported": 3,  # placeholders counted as reported
            "n_missing_trial": 3,
            "resolved": 0,
            "resolve_rate_pct": 0.0,
            "model_calls_total": 0,
            "cost_usd_total": 0.0,
            "tasks": {f"t{i}": row(reward=None, agent_status="NOT_RUN", resolved=False) for i in range(3)},
        }
        for arm in ("causal", "nop", "oracle")
    },
}

MEASURED = {
    "schema": "brain.bench_eval_report.v1",
    "run_produced_number": True,
    "benchmark": "SWE-bench Pro V2 (HARD-51, 51 tasks)",
    "commit": "abcdef01",
    "arms": {
        "causal": {
            "arm": "causal",
            "n_expected": 2,
            "n_reported": 2,
            "n_missing_trial": 0,
            "resolved": 1,
            "resolve_rate_pct": 50.0,
            "model_calls_total": 0,
            "cost_usd_total": 0.0,
            "wall_seconds_total": 12.0,
            "wall_seconds_mean": 6.0,
            "engine_statuses": {"EDITS_UPLOADED": 1, "NO_EDITS": 1},
            "tasks": {
                "t0": row(reward=1.0, agent_status="EDITS_UPLOADED", resolved=True, trial_dir="t0__a"),
                "t1": row(reward=0.0, agent_status="NO_EDITS", resolved=False, trial_dir="t1__b"),
            },
        },
        "nop": {
            "arm": "nop",
            "n_expected": 2,
            "n_reported": 2,
            "n_missing_trial": 0,
            "resolved": 0,
            "resolve_rate_pct": 0.0,
            "model_calls_total": 0,
            "cost_usd_total": 0.0,
            "tasks": {
                f"t{i}": row(reward=0.0, agent_status="nop", resolved=False, trial_dir=f"t{i}__n") for i in (0, 1)
            },
        },
        "oracle": {
            "arm": "oracle",
            "n_expected": 2,
            "n_reported": 2,
            "n_missing_trial": 0,
            "resolved": 2,
            "resolve_rate_pct": 100.0,
            "model_calls_total": 0,
            "cost_usd_total": 0.0,
            "tasks": {
                f"t{i}": row(reward=1.0, agent_status="oracle", resolved=True, trial_dir=f"t{i}__o") for i in (0, 1)
            },
        },
    },
}


def test_a_run_with_no_real_trial_row_is_never_a_resolve_rate() -> None:
    rec = rc.build_receipt(VOID, date="2026-11-25")
    assert rec["claimable_as_a_benchmark_number"] is False
    assert rec["authority"] == "NO_MEASUREMENT__HARNESS_ONLY"
    assert rec["run_produced_number"] is False
    assert rec["run_produced_number_as_reported_by_harness"] is True, "the disagreement must be visible"
    for arm in ("causal", "nop", "oracle"):
        assert rec["arms"][arm]["resolved"] is None
        assert rec["arms"][arm]["resolve_rate_pct"] is None
        assert rec["arms"][arm]["void_reason"] == "NO_TRIAL_RESULTS_READ"
        assert rec["arms"][arm]["n_reported"] == 3, "the placeholder count is kept as the explanation"
    assert rec["n_real_trial_rows_per_arm"] == {"causal": 0, "nop": 0, "oracle": 0}
    assert any(r.startswith("NO_TRIAL_DATA") for r in rec["why_not_claimable"])
    assert rec["why_not_claimable"] == [r for r in rec["why_not_claimable"] if r.startswith("NO_TRIAL_DATA")], (
        "a void run must not also accuse the nop/oracle controls of being broken — they were never run"
    )
    assert rec["control_rows"]["nop"] == {"rows_read": 0, "rows_expected": 3, "resolved": 0}


def test_a_gated_measured_run_carries_the_numbers_verbatim() -> None:
    rec = rc.build_receipt(MEASURED, date="2026-11-25")
    assert rec["claimable_as_a_benchmark_number"] is True
    assert rec["authority"] == "OFFICIAL_TASK_VERDICTS__GATES_PASSED"
    assert rec["why_not_claimable"] == []
    # copied, never recomputed or rounded
    assert rec["arms"]["causal"]["resolved"] == MEASURED["arms"]["causal"]["resolved"]
    assert rec["arms"]["causal"]["resolve_rate_pct"] == 50.0
    assert rec["arms"]["causal"]["engine_statuses"] == {"EDITS_UPLOADED": 1, "NO_EDITS": 1}
    assert rec["arms"]["causal"]["wall_seconds_mean"] == 6.0
    assert rec["gates_recomputed_here"] == {"nop_data_complete": True, "nop_gate_pass": True,
                                           "oracle_data_complete": True, "oracle_gate_pass": True}
    assert "each task's own verifier ran inside the pinned official container image" in " ".join(
        rec["what_this_run_did_prove"]
    )


def test_failing_control_or_any_spending_voids_the_claim_even_with_data() -> None:
    # nop resolved a task: the tests are not the constraint they claim to be.
    bad_nop = json.loads(json.dumps(MEASURED))
    bad_nop["arms"]["nop"]["tasks"]["t1"]["resolved"] = True
    bad_nop["arms"]["nop"]["tasks"]["t1"]["reward"] = 1.0
    rec = rc.build_receipt(bad_nop, date="x")
    assert rec["claimable_as_a_benchmark_number"] is False
    assert any("doing nothing resolved 1/2" in r for r in rec["why_not_claimable"])
    assert rec["arms"]["causal"]["resolve_rate_pct"] == 50.0, "the number exists, it just is not quotable"

    # oracle short of N/N: the causal number is not attributable to the engine.
    bad_oracle = json.loads(json.dumps(MEASURED))
    bad_oracle["arms"]["oracle"]["tasks"]["t1"]["resolved"] = False
    bad_oracle["arms"]["oracle"]["tasks"]["t1"]["reward"] = 0.0
    bad_oracle["arms"]["oracle"]["resolved"] = 1
    rec2 = rc.build_receipt(bad_oracle, date="x")
    assert rec2["claimable_as_a_benchmark_number"] is False
    assert any(r.startswith("ORACLE_GATE") for r in rec2["why_not_claimable"])

    # one hosted model call anywhere destroys the zero-cost claim, so it is reported
    # as a violation rather than as a footnote.
    spent = json.loads(json.dumps(MEASURED))
    spent["arms"]["causal"]["model_calls_total"] = 1
    spent["arms"]["causal"]["cost_usd_total"] = 0.42
    rec3 = rc.build_receipt(spent, date="x")
    assert rec3["claimable_as_a_benchmark_number"] is False
    assert any(r.startswith("MODEL_CALLS") for r in rec3["why_not_claimable"])
    assert any(r.startswith("COST") for r in rec3["why_not_claimable"])


def test_cli_writes_the_receipt_and_reads_only_the_committed_report(tmp_path) -> None:
    rep = tmp_path / "report.json"
    rep.write_text(json.dumps(MEASURED), encoding="utf-8")
    out = tmp_path / "verification" / "RECEIPT.json"
    proc = subprocess.run(
        [sys.executable, str(TOOLS / "swe_pro_v2_run_receipt_v1.py"),
         "--report", str(rep), "--out", str(out), "--date", "2026-11-25"],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["schema"] == rc.SCHEMA
    assert written["claimable_as_a_benchmark_number"] is True
    # the tool must not mutate the input report
    assert json.loads(rep.read_text(encoding="utf-8")) == MEASURED


def test_a_harness_error_trial_is_counted_as_measured_but_not_as_an_engine_verdict() -> None:
    """0/3 and 0/2 are both true statements, and the receipt must carry both."""
    m = json.loads(json.dumps(MEASURED))
    m["arms"]["causal"]["tasks"]["t1"]["agent_status"] = "HARNESS_ERROR"
    m["arms"]["causal"]["tasks"]["t1"]["error"] = "RuntimeError: exec refused"
    rec = rc.build_receipt(m, date="x")
    att = rec["attribution"]["causal"]
    assert att["harness_side"] == 1 and att["engine_attributable"] == 1
    assert att["harness_side_statuses"] == ["HARNESS_ERROR"]
    assert att["measured_resolve_rate_pct"] == 50.0, "the benchmark counts what ran"
    assert att["resolve_rate_pct_engine_attributable"] == 100.0, "the engine's own record is 1 of 1"
    assert rec["claimable_as_a_benchmark_number"] is True
    assert rec["attribution"]["nop"]["harness_side"] == 0, (
        "harbor's factory control agents write no engine report; that is expected, not dirt"
    )
    # and a run whose every trial died in the harness has no engine number at all
    all_bad = json.loads(json.dumps(MEASURED))
    for tid in ("t0", "t1"):
        all_bad["arms"]["causal"]["tasks"][tid]["agent_status"] = "UPLOAD_BLOCKED"
        all_bad["arms"]["causal"]["tasks"][tid]["resolved"] = False
    all_bad["arms"]["causal"]["resolved"] = 0
    all_bad["arms"]["oracle"]["tasks"]["t0"]["agent_status"] = "HARNESS_ERROR"
    rec2 = rc.build_receipt(all_bad, date="x")
    assert rec2["attribution"]["causal"]["resolve_rate_pct_engine_attributable"] is None
    assert rec2["claimable_as_a_benchmark_number"] is False
