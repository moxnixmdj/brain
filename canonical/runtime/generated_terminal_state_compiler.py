"""Generated current-state compiler for Project Brain terminal closure.

This compiler reconciles the registry, active proof basis, population protocol,
portfolio prequalification, and explicitly indexed progress artifacts. It does
not promote routes. Its job is to make stale/reconciliation lag visible and to
produce one deterministic read model from canonical inputs.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

REGISTRY="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
BASIS="canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json"
PROTOCOL="canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json"
PREQUAL="canonical/governance/EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json"
QUEUE="canonical/governance/TERMINAL_ROUTE_CLOSURE_QUEUE_RECEIPT_V1.json"
INDEX="canonical/governance/TERMINAL_PROGRESS_EVIDENCE_INDEX_V1.json"
OUT_SCHEMA="PROJECT_BRAIN_GENERATED_TERMINAL_STATE_V1"

def _read(root:Path, rel:str)->tuple[dict[str,Any],str]:
    raw=(root/rel).read_bytes()
    obj=json.loads(raw.decode("utf-8"))
    if not isinstance(obj,dict): raise ValueError(rel+":NOT_OBJECT")
    return obj,hashlib.sha256(raw).hexdigest()

def compile_state(root:Path)->dict[str,Any]:
    errors=[]
    try:
        registry,rh=_read(root,REGISTRY); basis,bh=_read(root,BASIS)
        protocol,ph=_read(root,PROTOCOL); prequal,qh=_read(root,PREQUAL)
        queue,qeh=_read(root,QUEUE); index,ih=_read(root,INDEX)
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        return {"schema":OUT_SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "errors":["INPUT_READ_FAILURE:"+type(exc).__name__],
                "execution_authority":False,"capability_credit_delta":0,"family_credit_delta":0}

    active_rows=registry.get("active_contracted_residuals")
    basis_rows=basis.get("contracts")
    protocol_ids=protocol.get("active_contracts")
    if not isinstance(active_rows,list) or not isinstance(basis_rows,list) or not isinstance(protocol_ids,list):
        errors.append("CONTRACT_SET_INPUT_INVALID")
        active_ids=[]; basis_ids=[]
    else:
        active_ids=[x.get("behavior_id") for x in active_rows if isinstance(x,dict)]
        basis_ids=[x.get("behavior_id") for x in basis_rows if isinstance(x,dict)]
        if any(not isinstance(x,str) or not x for x in active_ids+basis_ids+protocol_ids):
            errors.append("CONTRACT_ID_INVALID")
        if len(set(active_ids))!=len(active_ids) or len(set(basis_ids))!=len(basis_ids) or len(set(protocol_ids))!=len(protocol_ids):
            errors.append("CONTRACT_ID_DUPLICATE")
        if set(active_ids)!=set(basis_ids) or set(active_ids)!=set(protocol_ids):
            errors.append("CONTRACT_SET_MISMATCH")

    admitted=[]
    blocked={}
    if isinstance(basis_rows,list):
        for row in basis_rows:
            if not isinstance(row,dict): continue
            bid=row.get("behavior_id")
            blockers=row.get("blockers")
            if row.get("proof_state")=="TERMINAL_ROUTE_FROZEN_ADMISSIBLE" and blockers==[]:
                admitted.append(bid)
            else:
                blocked[str(bid)]=blockers if isinstance(blockers,list) else ["BLOCKERS_INVALID"]
    if basis.get("admissible_frozen_terminal_route_count")!=len(admitted):
        errors.append("BASIS_ADMISSIBLE_COUNT_MISMATCH")

    protocol_admitted=protocol.get("admissible_frozen_routes")
    if not isinstance(protocol_admitted,list) or any(not isinstance(x,str) or not x for x in protocol_admitted):
        errors.append("PROTOCOL_ADMISSIBLE_ROUTES_INVALID")
        protocol_admitted=[]
    else:
        if set(protocol_admitted)!=set(admitted):
            errors.append(
                "PROTOCOL_ADMISSION_MISMATCH:"
                +"missing="+",".join(sorted(set(admitted)-set(protocol_admitted)))
                +";extra="+",".join(sorted(set(protocol_admitted)-set(admitted)))
            )
        if protocol.get("admissible_frozen_route_count")!=len(protocol_admitted):
            errors.append("PROTOCOL_ADMISSIBLE_COUNT_MISMATCH")

    preq_count=prequal.get("admissible_frozen_terminal_route_count")
    if preq_count is not None and preq_count!=len(admitted):
        errors.append(f"PREQUAL_ADMISSIBLE_COUNT_MISMATCH:{preq_count}!={len(admitted)}")
    preq_basis_status=prequal.get("active_terminal_proof_basis_status")
    if preq_basis_status is not None and preq_basis_status!=basis.get("status"):
        errors.append("PREQUAL_BASIS_STATUS_MISMATCH")

    preq_progress=prequal.get("prequalification_progress")
    if isinstance(preq_progress,dict):
        nested_count=preq_progress.get("admissible_frozen_terminal_route_count")
        if nested_count is not None and nested_count!=len(admitted):
            errors.append(f"PREQUAL_NESTED_ADMISSIBLE_COUNT_MISMATCH:{nested_count}!={len(admitted)}")
        nested_routes=preq_progress.get("admissible_frozen_terminal_routes")
        if nested_routes is not None:
            if not isinstance(nested_routes,list) or any(not isinstance(x,str) or not x for x in nested_routes):
                errors.append("PREQUAL_NESTED_ADMISSIBLE_ROUTES_INVALID")
            elif set(nested_routes)!=set(admitted):
                errors.append(
                    "PREQUAL_NESTED_ADMISSION_MISMATCH:"
                    +"missing="+",".join(sorted(set(admitted)-set(nested_routes)))
                    +";extra="+",".join(sorted(set(nested_routes)-set(admitted)))
                )

    queue_closed=queue.get("closed_behavior_ids")
    queue_rows=queue.get("queue")
    queue_open_ids=[]
    if not isinstance(queue_closed,list) or any(not isinstance(x,str) or not x for x in queue_closed):
        errors.append("QUEUE_CLOSED_IDS_INVALID")
        queue_closed=[]
    if not isinstance(queue_rows,list):
        errors.append("QUEUE_ROWS_INVALID")
    else:
        for row in queue_rows:
            if not isinstance(row,dict) or not isinstance(row.get("behavior_id"),str) or not row.get("behavior_id"):
                errors.append("QUEUE_ROW_INVALID")
                continue
            queue_open_ids.append(row["behavior_id"])
    if set(queue_closed)!=set(admitted):
        errors.append(
            "QUEUE_CLOSED_ADMISSION_MISMATCH:"
            +"missing="+",".join(sorted(set(admitted)-set(queue_closed)))
            +";extra="+",".join(sorted(set(queue_closed)-set(admitted)))
        )
    if set(queue_open_ids)!=set(blocked):
        errors.append(
            "QUEUE_OPEN_SET_MISMATCH:"
            +"missing="+",".join(sorted(set(blocked)-set(queue_open_ids)))
            +";extra="+",".join(sorted(set(queue_open_ids)-set(blocked)))
        )
    if queue.get("closed_route_count")!=len(admitted):
        errors.append("QUEUE_CLOSED_COUNT_MISMATCH")
    if queue.get("open_route_count")!=len(blocked):
        errors.append("QUEUE_OPEN_COUNT_MISMATCH")
    if queue.get("source_basis_status")!=basis.get("status"):
        errors.append("QUEUE_BASIS_STATUS_MISMATCH")

    portfolios=prequal.get("portfolio_status")
    portfolio_blockers={}
    if isinstance(portfolios,dict):
        for pid,row in sorted(portfolios.items()):
            bs=row.get("blockers",[]) if isinstance(row,dict) else ["PORTFOLIO_ROW_INVALID"]
            portfolio_blockers[pid]=bs if isinstance(bs,list) else ["BLOCKERS_INVALID"]
    else:
        errors.append("PORTFOLIO_STATUS_INVALID")

    progress=[]
    entries=index.get("entries")
    if not isinstance(entries,list):
        errors.append("PROGRESS_INDEX_INVALID"); entries=[]
    for entry in entries:
        if not isinstance(entry,dict): errors.append("PROGRESS_ENTRY_INVALID"); continue
        rel=entry.get("path"); behavior=entry.get("behavior_id")
        if not isinstance(rel,str) or not rel:
            errors.append("PROGRESS_PATH_INVALID"); continue
        try:
            obj,h=_read(root,rel)
        except (OSError,ValueError,json.JSONDecodeError):
            errors.append("PROGRESS_ARTIFACT_UNREADABLE:"+rel); continue
        status=str(obj.get("status",""))
        progress.append({
            "behavior_id":behavior,
            "path":rel,
            "sha256":h,
            "status":status,
            "active_basis_admitted":behavior in admitted if isinstance(behavior,str) else None,
            "promotion_authority":False,
        })

    lag=[x for x in progress if x["active_basis_admitted"] is False and any(k in x["status"].upper() for k in ("FROZEN","PASS","VERIFIED","BOUND"))]
    passed=not errors
    return {
        "schema":OUT_SCHEMA,"status":"GENERATED" if passed else "FAIL_CLOSED","pass":passed,
        "source_sha256":{"registry":rh,"basis":bh,"protocol":ph,"prequalification":qh,"closure_queue":qeh,"progress_index":ih},
        "active_contract_count":len(set(active_ids)),
        "authoritative_admissible_route_count":len(admitted),
        "authoritative_admissible_routes":sorted(admitted),
        "protocol_admissible_routes":sorted(protocol_admitted),
        "derived_state_reconciliation_required": any(
            x.startswith(("PROTOCOL_ADMISSION_MISMATCH","PROTOCOL_ADMISSIBLE_COUNT_MISMATCH","PREQUAL_ADMISSIBLE_COUNT_MISMATCH","PREQUAL_NESTED_","PREQUAL_BASIS_STATUS_MISMATCH","QUEUE_"))
            for x in errors
        ),
        "blocked_contracts":blocked,
        "portfolio_blockers":portfolio_blockers,
        "progress_artifacts":progress,
        "reconciliation_candidates":lag,
        "reconciliation_candidate_count":len(lag),
        "execution_authority": bool(passed and basis.get("execution_authority") is True and protocol.get("execution_authority") is True and not blocked and all(not v for v in portfolio_blockers.values())),
        "rule":"PROGRESS_ARTIFACTS_NEVER_SELF_PROMOTE__ONLY_CANONICAL_ADMISSION_CRITERIA_MAY_CHANGE_AUTHORITY",
        "errors":sorted(set(errors)),"capability_credit_delta":0,"family_credit_delta":0,
    }

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("repo_root",type=Path); a=ap.parse_args()
    out=compile_state(a.repo_root); print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
