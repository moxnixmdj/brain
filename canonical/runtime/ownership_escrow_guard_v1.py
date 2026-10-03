"""Fail-closed ownership escrow guard.

Acceptance may never create an unclassified ownership backlog. Every strict
Opus-5.5 acceptance PASS must be either fully owned in the same canonical state
or carry an exact ownership blocker with the missing proof obligations and next
action. Ownership may never outrun acceptance.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Mapping

OWNED="VERIFIED_OWNED_EQUAL_OR_BETTER"
BLOCKED="OWNERSHIP_BLOCKED_EXACT"

def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict):
        raise ValueError("JSON_OBJECT_REQUIRED:"+str(p))
    return x

def strict_acceptance(row:Mapping[str,Any])->bool:
    return (
        row.get("opus55_acceptance_state")=="PASS"
        and row.get("opus55_acceptance_calibrated") is True
        and row.get("unresolved")==[]
    )

def exact_blocker(row:Mapping[str,Any])->tuple[bool,list[str]]:
    e=[]
    escrow=row.get("ownership_escrow")
    if not isinstance(escrow,Mapping):
        return False,["OWNERSHIP_ESCROW_MISSING"]
    if escrow.get("state")!=BLOCKED:
        e.append("OWNERSHIP_ESCROW_STATE_INVALID")
    if not isinstance(escrow.get("blocker_class"),str) or not escrow.get("blocker_class"):
        e.append("OWNERSHIP_BLOCKER_CLASS_MISSING")
    missing=escrow.get("missing_proof_obligations")
    if not isinstance(missing,list) or not missing or any(not isinstance(x,str) or not x for x in missing):
        e.append("OWNERSHIP_MISSING_PROOF_OBLIGATIONS_INVALID")
    if not isinstance(escrow.get("next_action"),str) or not escrow.get("next_action"):
        e.append("OWNERSHIP_NEXT_ACTION_MISSING")
    if escrow.get("ownership_credit_delta")!=0:
        e.append("BLOCKED_ESCROW_OWNERSHIP_CREDIT_NONZERO")
    return not e,e

def evaluate(closure:Mapping[str,Any],matrix:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    crows={x.get("id"):x for x in closure.get("families",[]) if isinstance(x,Mapping) and isinstance(x.get("id"),str)}
    mrows={x.get("family"):x for x in matrix.get("rows",[]) if isinstance(x,Mapping) and isinstance(x.get("family"),str)}
    all_ids=sorted(set(crows)|set(mrows))
    results=[]
    for fam in all_ids:
        e=[]
        c=crows.get(fam); m=mrows.get(fam)
        if c is None:
            e.append("CLOSURE_ROW_MISSING")
            accepted=False
        else:
            accepted=strict_acceptance(c)
        if m is None:
            e.append("OWNERSHIP_MATRIX_ROW_MISSING")
            owned=False
        else:
            owned=m.get("status")==OWNED

        outcome="ACCEPTANCE_OPEN"
        if owned and not accepted:
            e.append("OWNERSHIP_WITHOUT_STRICT_ACCEPTANCE")
            outcome="INVALID"
        elif accepted and owned:
            if c.get("ownership_status")!=OWNED:
                e.append("CLOSURE_OWNERSHIP_STATUS_NOT_RECONCILED")
            outcome=OWNED
        elif accepted:
            ok,be=exact_blocker(c)
            e.extend(be)
            outcome=BLOCKED if ok else "UNCLASSIFIED_ACCEPTED_UNOWNED"

        e=sorted(set(e))
        if e:
            errors.extend(f"{fam}:{x}" for x in e)
        results.append({
            "family":fam,
            "strict_acceptance":accepted,
            "verified_owned":owned,
            "ownership_outcome":outcome,
            "errors":e,
        })

    accepted=sum(1 for x in results if x["strict_acceptance"])
    owned=sum(1 for x in results if x["verified_owned"])
    blocked=sum(1 for x in results if x["ownership_outcome"]==BLOCKED)
    unclassified=sum(1 for x in results if x["ownership_outcome"]=="UNCLASSIFIED_ACCEPTED_UNOWNED")
    passed=not errors
    return {
        "schema":"PROJECT_BRAIN_OWNERSHIP_ESCROW_GUARD_V1",
        "status":"PASS" if passed else "FAIL_CLOSED",
        "pass":passed,
        "counts":{
            "families":len(results),
            "strictly_accepted":accepted,
            "verified_owned":owned,
            "accepted_owned":sum(1 for x in results if x["strict_acceptance"] and x["verified_owned"]),
            "accepted_blocked_exact":blocked,
            "accepted_unclassified":unclassified,
        },
        "families":results,
        "errors":sorted(set(errors)),
        "invariant":"ACCEPTED_IMPLIES_VERIFIED_OWNED_OR_EXACT_OWNERSHIP_ESCROW_BLOCKER__OWNED_IMPLIES_ACCEPTED",
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "ownership_credit_delta":0,
        "incremental_spend_usd":0,
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=Path("."))
    ap.add_argument("--closure",default="canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json")
    ap.add_argument("--matrix",default="canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
    a=ap.parse_args(); root=a.root.resolve()
    out=evaluate(load(root/a.closure),load(root/a.matrix))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
