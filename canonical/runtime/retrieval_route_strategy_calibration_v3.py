#!/usr/bin/env python3
"""Expanded route-strategy calibration V3.

Extends V2 with the independently receipt-bound V11 30-case stratified live
event corpus. This expands provider/strategy calibration to multilingual,
behavior-only, provider-native enumeration, and additional public registries.

Later V12-V18 residual-recovery mechanisms are calibrated separately because
those stages are conditional fallback mechanisms, not ordinary first-pass
provider/query routes.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from canonical.runtime import retrieval_route_strategy_calibration_v2 as v2

SCHEMA="PROJECT_BRAIN_RETRIEVAL_ROUTE_STRATEGY_CALIBRATION_V3"
V11_FILE="canonical/governance/RETRIEVAL_V11_STRATIFIED_LIVE_EVENTS_20261004_V1.json"

def load_repository_events(root:Path)->list[dict[str,Any]]:
    rows=v2.load_repository_events(root)
    p=root/V11_FILE
    if not p.exists():
        raise ValueError("V11_STRATIFIED_LIVE_EVENTS_REQUIRED")
    obj=json.loads(p.read_text(encoding="utf-8"))
    obs=obj.get("observations")
    if not isinstance(obs,list) or len(obs)!=30:
        raise ValueError("V11_EXPECTED_30_OBSERVATIONS")
    for raw in obs:
        if not isinstance(raw,dict):
            raise ValueError("V11_OBSERVATION_MAPPING_REQUIRED")
        row=dict(raw)
        receipt=str(row.get("independent_receipt") or "").strip()
        authority=str(row.get("observation_authority") or "")
        if not receipt or "INDEPENDENT_PUBLIC_RUNNER_LIVE_NETWORK" not in authority:
            raise ValueError("V11_NON_INDEPENDENT_EVENT_REJECTED")
        row["_source_file"]=V11_FILE
        rows.append(row)
    return rows

def calibrate_repository(root:Path)->dict[str,Any]:
    out=v2.calibrate(load_repository_events(root))
    out=dict(out)
    out["schema"]=SCHEMA
    out["status"]="CALIBRATED_V10_PLUS_V11_PROVIDER_ROUTE_X_QUERY_STRATEGY_FROM_INDEPENDENT_LIVE_EVENTS"
    out["v11_stratified_events_included"]=True
    out["v11_event_count"]=30
    out["recovery_mechanism_calibration_separate"]=True
    out["hard_rules"]=list(out.get("hard_rules") or [])+[
        "V11_STRATIFIED_LIVE_EVENTS_ARE_MANDATORY",
        "V12_TO_V18_CONDITIONAL_RECOVERY_MECHANISMS_MUST_NOT_BE_COLLAPSED_INTO_FIRST_PASS_PROVIDER_STATS",
    ]
    return out

def main()->int:
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(calibrate_repository(root),indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
