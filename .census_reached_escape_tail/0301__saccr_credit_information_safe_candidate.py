"""Brain-owned terminal candidate adapter for the frozen SA-CCR credit contract.

Consumes only candidate-visible structured trade inputs. Hidden oracle outputs,
lineage, expected add-on, and applicability verdicts are never candidate-visible.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.saccr_credit_kernel import CreditTrade, trace_trade, credit_addon

_TRACE_FIELDS = (
    "supervisory_duration",
    "adjusted_notional",
    "delta",
    "maturity_factor",
    "effective_notional",
    "supervisory_factor",
    "supervisory_correlation",
    "directional_addon",
)

def _trade(row: Mapping[str, Any]) -> CreditTrade:
    required = {
        "notional","start","end","direction","reference",
        "credit_rating","is_index","margined_mpor",
    }
    if set(row) != required:
        raise ValueError("TRADE_SCHEMA_MISMATCH")
    return CreditTrade(
        notional=float(row["notional"]),
        start=float(row["start"]),
        end=float(row["end"]),
        direction=int(row["direction"]),
        reference=str(row["reference"]),
        credit_rating=str(row["credit_rating"]),
        is_index=bool(row["is_index"]),
        margined_mpor=None if row["margined_mpor"] is None else float(row["margined_mpor"]),
    )

def solve(public_case: Mapping[str, Any]) -> dict[str, Any]:
    task = public_case.get("task")
    if not isinstance(task, Mapping):
        return {"status":"FAIL_CLOSED","reason":"TASK_INVALID"}
    rows = task.get("trades")
    if not isinstance(rows, list) or not rows:
        return {"status":"FAIL_CLOSED","reason":"TRADES_INVALID"}
    try:
        trades = [_trade(x) for x in rows if isinstance(x, Mapping)]
        if len(trades) != len(rows):
            raise ValueError("TRADE_NOT_OBJECT")
        traces = []
        for trade in trades:
            raw = trace_trade(trade)
            traces.append({k: raw[k] for k in _TRACE_FIELDS})
        addon = credit_addon(trades)
    except Exception as exc:
        return {"status":"FAIL_CLOSED","reason":type(exc).__name__+":"+str(exc)}
    return {
        "status":"OK",
        "trade_traces":traces,
        "credit_addon":addon,
    }
