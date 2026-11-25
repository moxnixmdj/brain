#!/usr/bin/env python3
"""Turn a committed benchmark report into a receipt that cannot overstate itself.

WHY THIS EXISTS
---------------
The first two measured runs of the SWE-bench Pro V2 harness produced a markdown table
reading `causal 0/3, nop 0/3, oracle 0/3` while every CI job was green. Two very
different things look like that: an agent that really failed every task, and a harness
that never read any trial. The raw report can be quoted as a resolve rate in the first
case and must never be quoted in the second — and the difference is not visible in the
`0` column.

So the number a reader is allowed to see is decided here, from fields the harness can
actually attest to, and everything else becomes an explicit `null` with a reason:

* ``run_produced_number`` — did any trial result get read at all.
* ``oracle_gate_pass`` / ``nop_gate_pass`` — the two controls that make the causal arm
  meaningful: the reference patch must resolve every task in the same job configuration,
  and doing nothing must resolve none of them. If either fails, the causal number is a
  number about the harness, not about the engine.
* ``model_calls_total`` / ``cost_usd_total`` — the standing claim under review is a
  zero-runtime-model-call house, so any nonzero value here voids the claim instead of
  being reported alongside it.

Nothing in this file measures a task or computes a score. It only reads the JSON the
eval job already committed, and refuses to launder a void run into a result.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

SCHEMA = "BRAIN_SWE_PRO_V2_RUN_RECEIPT_V1"
ARMS = ("causal", "nop", "oracle")

# Fields copied verbatim from the shard reports. A value that is absent upstream stays
# absent here — inventing a default would be inventing a measurement.
# Agent statuses that mean the harness, not the engine, decided the outcome. A trial
# in this set is a benchmark failure (it ran and scored 0) but is NOT evidence about the
# solver, so both readings are reported side by side.
HARNESS_SIDE = frozenset(
    {"HARNESS_ERROR", "NO_AGENT_REPORT", "UPLOAD_BLOCKED", "TREE_TOO_BIG", "EMPTY_TREE", "NOT_RUN"}
)

COPIED = (
    "resolved",
    "n_expected",
    "n_reported",
    "n_missing_trial",
    "resolve_rate_pct",
    "model_calls_total",
    "cost_usd_total",
    "wall_seconds_total",
    "wall_seconds_mean",
    "engine_statuses",
)


def _row_is_real(row: dict[str, Any]) -> bool:
    """A row read from a trial that actually ran, not a NOT_RUN placeholder.

    Recomputed here instead of trusting ``run_produced_number``: the first void run of
    this harness carried ``run_produced_number: true`` precisely because the collector
    counted its own placeholders. A receipt that inherits that flag inherits the bug.
    """
    return bool(row.get("trial_dir")) or row.get("agent_status") not in (None, "NOT_RUN")


def _n_real(rep: dict[str, Any]) -> int:
    return sum(1 for v in (rep.get("tasks") or {}).values() if _row_is_real(v))


def _attribution(rep: dict[str, Any]) -> dict[str, Any]:
    """Split a measured rate into what the engine decided and what the harness decided."""
    rows = [r for r in (rep.get("tasks") or {}).values() if _row_is_real(r)]
    engine_rows = [r for r in rows if str(r.get("agent_status")) not in HARNESS_SIDE]
    harness_rows = [r for r in rows if str(r.get("agent_status")) in HARNESS_SIDE]
    resolved_engine = sum(1 for r in engine_rows if r.get("resolved"))
    n_eng = int(rep.get("n_expected") or 0)
    return {
        "n_expected": n_eng,
        "rows_read": len(rows),
        "engine_attributable": len(engine_rows),
        "harness_side": len(harness_rows),
        "harness_side_statuses": sorted({str(r.get("agent_status")) for r in harness_rows}),
        "resolved_engine_attributable": resolved_engine,
        "resolve_rate_pct_engine_attributable": (
            round(100.0 * resolved_engine / len(engine_rows), 2) if engine_rows else None
        ),
        "measured_resolve_rate_pct": rep.get("resolve_rate_pct") if _n_real(rep) else None,
    }


def _gates(arms: dict[str, dict[str, Any]]) -> dict[str, bool]:
    """Recompute the two controls from the per-task truth, not from the harness's own flags."""
    out: dict[str, bool] = {}
    for arm in ("nop", "oracle"):
        rep = arms.get(arm) or {}
        rows = [r for r in (rep.get("tasks") or {}).values() if _row_is_real(r)]
        n = rep.get("n_expected") or 0
        out[f"{arm}_data_complete"] = bool(n) and len(rows) >= n
        resolved = sum(1 for r in rows if r.get("resolved"))
        if arm == "oracle":
            out["oracle_gate_pass"] = bool(n) and resolved == n and out["oracle_data_complete"]
        else:
            out["nop_gate_pass"] = out["nop_data_complete"] and resolved == 0
    return out


def build_receipt(report: dict[str, Any], *, date: str) -> dict[str, Any]:
    arms_in = report.get("arms") or {}
    produced = bool(arms_in) and any(_n_real(rep) for rep in arms_in.values())
    gates = _gates(arms_in)

    arms_out: dict[str, dict[str, Any]] = {}
    for arm, rep in arms_in.items():
        row = {k: rep[k] for k in COPIED if k in rep}
        if not produced:
            # A void run has no resolve rate. Drop the two fields that could be read as
            # one and keep the counts that explain why.
            row["resolved"] = None
            row["resolve_rate_pct"] = None
            row["void_reason"] = "NO_TRIAL_RESULTS_READ"
        arms_out[arm] = row

    counts = {
        arm: {
            "rows_read": _n_real(rep),
            "rows_expected": int(rep.get("n_expected") or 0),
            "resolved": sum(1 for r in (rep.get("tasks") or {}).values() if _row_is_real(r) and r.get("resolved")),
        }
        for arm, rep in arms_in.items()
    }
    reasons: list[str] = []
    if not produced:
        # Say only this. Accusing the nop/oracle controls of being broken when no trial
        # was read at all would replace one overstatement with another.
        reasons.append(
            "NO_TRIAL_DATA: no trial row was read for any expected task, so this run "
            "produced no benchmark number. The 0 columns in the raw report are a harness "
            "failure, not a score, and the controls were never exercised."
        )
    else:
        for arm, gate in (("oracle", "ORACLE_GATE"), ("nop", "NOP_GATE")):
            c = counts.get(arm, {})
            read, n, resolved = c.get("rows_read", 0), c.get("rows_expected", 0), c.get("resolved", 0)
            if gates.get(f"{arm}_gate_pass"):
                continue
            if not n or read < n:
                reasons.append(
                    f"{gate}: only {read}/{n} trials of the {arm} control were read, so the "
                    "control is unproven and the causal number is not interpretable."
                )
            elif arm == "oracle":
                reasons.append(
                    f"ORACLE_GATE: the reference patch resolved {resolved}/{n}, not N/N, in this "
                    "job configuration — a task's own test is then not the constraint it claims "
                    "to be, and no causal resolve rate can be attributed to the engine."
                )
            else:
                reasons.append(
                    f"NOP_GATE: doing nothing resolved {resolved}/{n}, so the tests accept an "
                    "unmodified tree and a 0/N causal score would be meaningless anyway."
                )
    attribution = {arm: _attribution(rep) for arm, rep in arms_in.items()}
    if produced:
        # A control arm whose own trial died in the harness is not clean evidence, and a
        # causal arm with no engine-attributable trial measured nothing about the solver.
        c = attribution.get("causal") or {}
        if c.get("rows_read") and not c.get("engine_attributable"):
            reasons.append(
                f"ATTRIBUTION: all {c['rows_read']} causal trials ended in harness-side "
                f"statuses {c.get('harness_side_statuses')}, so this run measured nothing about "
                "the engine even though the verifier did score them."
            )
        for arm in ("nop", "oracle"):
            a = attribution.get(arm) or {}
            if a.get("harness_side"):
                reasons.append(
                    f"{arm.upper()}_CONTROL_DIRTIED: {a['harness_side']} of its trials carry "
                    f"harness-side statuses {a.get('harness_side_statuses')}, so the {arm} gate "
                    "is not clean evidence that the tests discriminate."
                )
    for arm, rep in arms_in.items():
        if int(rep.get("model_calls_total") or 0) != 0:
            reasons.append(f"MODEL_CALLS: {arm} recorded {rep.get('model_calls_total')} model calls.")
        if float(rep.get("cost_usd_total") or 0.0) != 0.0:
            reasons.append(f"COST: {arm} recorded cost {rep.get('cost_usd_total')} USD.")
    if report.get("run_failed"):
        reasons.append("RUN_FAILED: the eval job reported failure; no shard report was committed.")

    # One rule, so the verdict and the explanation can never drift apart: a number is
    # quotable exactly when the run produced rows and nothing on this list is true.
    claimable = produced and not reasons

    what_it_did_prove: list[str] = []
    if produced:
        what_it_did_prove.append(
            "each task's own verifier ran inside the pinned official container image, and its "
            "reward is the only source of the resolved flag"
        )
        what_it_did_prove.append("the engine ran with no network and no hosted model call")
    what_it_did_prove.append(
        "the harness distinguishes a failed run from an unmeasured one, and says which it got"
    )

    return {
        "schema": SCHEMA,
        "authority": (
            "OFFICIAL_TASK_VERDICTS__GATES_PASSED" if claimable
            else "OFFICIAL_TASK_VERDICTS__GATES_NOT_PASSED" if produced
            else "NO_MEASUREMENT__HARNESS_ONLY"
        ),
        "date": date,
        "benchmark": report.get("benchmark") or "SWE-bench Pro V2",
        "eval_commit": report.get("commit") or "unknown",
        "task_set_label": report.get("benchmark_label"),
        "run_produced_number": produced,
        "run_produced_number_as_reported_by_harness": report.get("run_produced_number"),
        "n_real_trial_rows_per_arm": {arm: _n_real(rep) for arm, rep in arms_in.items()},
        "claimable_as_a_benchmark_number": claimable,
        "why_not_claimable": reasons,
        "gates_recomputed_here": gates,
        "control_rows": counts,
        "attribution": attribution,
        "gates_reported_by_harness": report.get("gates") or {},
        "arms": arms_out,
        "n_shard_reports_read": report.get("n_reports_read"),
        "what_this_run_did_prove": what_it_did_prove,
        "note": (
            "A resolve rate is quotable only when the oracle and nop controls pass in the same job "
            "configuration that produced it. This receipt is derived from the committed report by "
            "copying fields; it adds no measurement and rounds nothing."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog=__name__)
    ap.add_argument("--report", required=True, help="committed aggregate report JSON")
    ap.add_argument("--out", required=True, help="where to write the receipt")
    ap.add_argument("--date", default="unknown")
    args = ap.parse_args(argv)

    report = json.loads(pathlib.Path(args.report).read_text(encoding="utf-8"))
    receipt = build_receipt(report, date=args.date)
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "claimable": receipt["claimable_as_a_benchmark_number"],
        "authority": receipt["authority"],
        "reasons": receipt["why_not_claimable"],
    }, indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
