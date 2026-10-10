"""Default-live R2 direct-route admission V2.

V2 preserves V1 selection but exposes one unique dynamic semantic-open state to
higher-level repair control when and only when no dynamic match/open competitor
and no legacy match/open state exists.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import r2_direct_live_admission_v1 as v1

SCHEMA="PROJECT_BRAIN_R2_DIRECT_LIVE_ADMISSION_WRAPPER_V2"
ROOT=Path(__file__).resolve().parents[2]
ROUTES=dict(v1.ROUTES)


def _base(status:str,passed:bool=False)->dict[str,Any]:
    out=v1._base(status,passed=passed); out["schema"]=SCHEMA; return out


def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    if not isinstance(request,Mapping):
        return {**_base("FAIL_CLOSED"),"matched":False,"reason":"REQUEST_NOT_OBJECT"}
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    try:
        dynamic=v1._dynamic_rows(root)
        if not dynamic:
            return v1.legacy.preflight(request,repo_root=root)
        matches=[]; opens=[]
        for row in dynamic:
            out=v1._dynamic_preflight(row,request,root)
            if out.get("matched") is True: matches.append((row,out))
            if out.get("direct_route_semantic_open") is True: opens.append((row,out))
        if len(matches)>1 or (matches and opens):
            return {
                **_base("FAIL_CLOSED__DIRECT_ROUTE_COLLISION"),"matched":bool(matches),
                "reason":"MULTIPLE_DYNAMIC_MATCH_OR_OPEN_STATES",
                "matching_route_ids":sorted(
                    {str(r["route_id"]) for r,_ in matches+opens}
                ),
            }
        if len(opens)>1:
            return {
                **_base("FAIL_CLOSED__DIRECT_ROUTE_COLLISION"),"matched":False,
                "reason":"MULTIPLE_DYNAMIC_SEMANTIC_OPEN_STATES",
                "matching_route_ids":sorted(str(r["route_id"]) for r,_ in opens),
            }
        legacy=v1.legacy.preflight(request,repo_root=root)
        legacy_engaged=(
            legacy.get("matched") is True
            or legacy.get("direct_route_semantic_open") is True
        )
        if matches:
            row,out=matches[0]
            if legacy_engaged:
                return {
                    **_base("FAIL_CLOSED__DIRECT_ROUTE_COLLISION"),"matched":True,
                    "reason":"DYNAMIC_ROUTE_OVERLAPS_LEGACY_V21",
                    "matching_route_ids":sorted([
                        str(row["route_id"]),str(legacy.get("route_id") or "LEGACY_V21")
                    ]),
                }
            return dict(out)
        if opens:
            row,out=opens[0]
            if legacy_engaged:
                return {
                    **_base("FAIL_CLOSED__DIRECT_ROUTE_COLLISION"),"matched":False,
                    "reason":"DYNAMIC_SEMANTIC_OPEN_OVERLAPS_LEGACY_V21",
                    "matching_route_ids":sorted([
                        str(row["route_id"]),str(legacy.get("route_id") or "LEGACY_V21")
                    ]),
                }
            exposed=dict(out)
            exposed["semantic_open_precedence_authority"]="UNIQUE_DYNAMIC_OPEN_AND_LEGACY_IDLE"
            exposed["semantic_open_observation_authority"]=True
            exposed["semantic_truth_authority"]=False
            exposed["execution_authority"]=False
            exposed["acceptance_authority"]=False
            exposed["terminal_authority"]=False
            return exposed
        return dict(legacy)
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),"matched":False,
            "reason":type(exc).__name__+":"+str(exc),
        }


def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    pf=preflight(request,repo_root=repo_root)
    if pf.get("matched") is not True:
        return pf
    return v1.run(request,repo_root=repo_root)
