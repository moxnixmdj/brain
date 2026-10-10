"""Brain candidate adapter for the active SA-CCR credit contract."""
from __future__ import annotations
from canonical.runtime.saccr_credit_kernel import CreditTrade, trace_trade, credit_addon

def solve(public):
    rows=public.get("task",{}).get("trades")
    if not isinstance(rows,list) or not rows:
        return {"status":"FAIL_CLOSED","reason":"TRADES_REQUIRED"}
    trades=[]
    for r in rows:
        trades.append(CreditTrade(
            notional=float(r["notional"]),start=float(r["start"]),end=float(r["end"]),
            direction=int(r["direction"]),reference=str(r["reference"]),
            credit_rating=str(r["credit_rating"]),is_index=bool(r["is_index"]),
            margined_mpor=None if r.get("margined_mpor") is None else float(r["margined_mpor"])))
    traces=[]
    for t in trades:
        tr=trace_trade(t); tr.pop("trade",None); traces.append(tr)
    return {"status":"RESOLVED","traces":traces,"credit_addon":credit_addon(trades)}
