"""Brain candidate for bounded information-safe tool-route discovery."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def initial_state()->dict[str,Any]:
    return {"knowledge":{}}


def _key(epoch:str,capability:str,tool_id:str)->str:
    return epoch+"\0"+capability+"\0"+tool_id


def observe_probe(state:Mapping[str,Any],receipt:Mapping[str,Any])->dict[str,Any]:
    out={"knowledge":dict(state.get("knowledge") or {})}
    if receipt.get("ok") is not True:
        return out
    key=_key(str(receipt.get("catalog_epoch")),str(receipt.get("capability")),str(receipt.get("tool_id")))
    out["knowledge"][key]=bool(receipt.get("capable"))
    return out


def select_route(task:Mapping[str,Any],tools:Sequence[Mapping[str,Any]],state:Mapping[str,Any])->dict[str,Any]:
    capability=str(task.get("required_capability") or "")
    epoch=str(task.get("catalog_epoch") or "")
    if not capability or not epoch:
        return {"status":"FAIL_CLOSED","reason":"TASK_INVALID"}
    rows=[]
    for row in tools:
        try:
            tid=str(row["tool_id"])
            cost=float(row["cost"])
        except Exception:
            return {"status":"FAIL_CLOSED","reason":"TOOL_ROW_INVALID"}
        if row.get("safe_probe") is not True:
            continue
        rows.append((cost,tid))
    rows.sort()
    knowledge=dict(state.get("knowledge") or {})

    # Prove all cheaper routes incapable before selecting a known capable route.
    for cost,tid in rows:
        key=_key(epoch,capability,tid)
        if key not in knowledge:
            return {"status":"NEED_PROBE","tool_id":tid}
        if knowledge[key] is True:
            return {"status":"SELECTED","tool_id":tid,"cost":cost}
    return {"status":"NO_ADMISSIBLE_ROUTE","reason":"ALL_SAFE_PROBED_ROUTES_INCAPABLE"}
