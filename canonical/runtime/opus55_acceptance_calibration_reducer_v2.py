"""Fail-closed Opus 5.5 acceptance calibration with stronger-proof transmutation.

Frozen protocol definitions never change here. A family is calibrated only when:
1) its terminal behavioral adjudication passed; and
2) the unchanged frozen protocol is effectively PASS, either directly or through
   an independently admissible full-protocol witness accepted by the existing
   acceptance proof transmuter.

This reducer creates no new reality and grants no authority by itself.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime.acceptance_proof_transmuter_v1 import evaluate as transmute

EXPECTED_FAMILY_COUNT=19
PASS="PASS"

def _family_ids(envelope:Mapping[str,Any])->list[str]:
    rows=envelope.get("families")
    if not isinstance(rows,list): return []
    return [r["id"] for r in rows if isinstance(r,Mapping) and isinstance(r.get("id"),str)]

def _protocol_map(protocols:Mapping[str,Any])->dict[str,Mapping[str,Any]]:
    rows=protocols.get("protocols")
    if not isinstance(rows,list): return {}
    out={}
    for row in rows:
        if isinstance(row,Mapping) and isinstance(row.get("family"),str):
            if row["family"] in out:
                return {}
            out[row["family"]]=row
    return out

def evaluate(
    envelope:Mapping[str,Any],
    protocols_doc:Mapping[str,Any],
    reduction:Mapping[str,Any],
    transmutation_input:Mapping[str,Any],
)->dict[str,Any]:
    errors:list[str]=[]
    families=_family_ids(envelope)
    if len(families)!=EXPECTED_FAMILY_COUNT or len(set(families))!=EXPECTED_FAMILY_COUNT:
        errors.append("TARGET_ENVELOPE_FAMILY_ACCOUNTING_INVALID")
    protocols=_protocol_map(protocols_doc)
    if set(protocols)!=set(families):
        errors.append("PROTOCOL_FAMILY_SET_MISMATCH")

    fv=reduction.get("family_verdict")
    behavioral:set[str]=set()
    if not isinstance(fv,Mapping) or fv.get("valid") is not True:
        errors.append("POSTWAVE_FAMILY_VERDICT_INVALID")
    else:
        passed=fv.get("passed_families")
        if not isinstance(passed,list) or any(not isinstance(x,str) for x in passed):
            errors.append("POSTWAVE_PASSED_FAMILIES_INVALID")
        else:
            behavioral=set(passed)
            if not behavioral.issubset(set(families)):
                errors.append("POSTWAVE_UNKNOWN_FAMILY")

    t=transmute(protocols_doc,transmutation_input)
    if t.get("status")!="PASS" or t.get("errors")!=[]:
        errors.append("TRANSMUTATION_FAIL_CLOSED")
    trows=t.get("families")
    if not isinstance(trows,list):
        errors.append("TRANSMUTATION_FAMILIES_INVALID")
        trows=[]
    tmap={}
    for row in trows:
        if not isinstance(row,Mapping) or not isinstance(row.get("family"),str):
            errors.append("TRANSMUTATION_ROW_INVALID")
            continue
        fid=row["family"]
        if fid in tmap:
            errors.append(f"TRANSMUTATION_DUPLICATE_FAMILY:{fid}")
            continue
        tmap[fid]=row
    if set(tmap)!=set(families):
        errors.append("TRANSMUTATION_FAMILY_SET_MISMATCH")

    rows=[]
    calibrated=[]
    pending=[]
    behavioral_missing=[]
    for family in families:
        behavior_pass=family in behavioral
        tr=tmap.get(family,{})
        effective=tr.get("result_status")==PASS
        if not behavior_pass:
            behavioral_missing.append(family)
        closed=bool(behavior_pass and effective)
        if closed: calibrated.append(family)
        else: pending.append(family)
        closure_mode=tr.get("closure_mode")
        if closed and closure_mode=="ALREADY_PASS":
            proof_source="FROZEN_PROTOCOL_DIRECT_PASS"
            reason="BEHAVIORAL_PASS_AND_FROZEN_PROTOCOL_DIRECT_PASS"
        elif closed:
            proof_source="VERIFIED_FULL_PROTOCOL_STRONGER_WITNESS"
            reason="BEHAVIORAL_PASS_AND_EFFECTIVE_FROZEN_PROTOCOL_PASS_VIA_STRONGER_WITNESS"
        elif not behavior_pass:
            proof_source=None
            reason="TERMINAL_BEHAVIORAL_PASS_MISSING"
        else:
            proof_source=None
            reason="EFFECTIVE_FROZEN_OPUS55_PROTOCOL_RESULT_NOT_CLOSED"
        rows.append({
            "family":family,
            "behavioral_contract_pass":behavior_pass,
            "frozen_protocol_status":protocols.get(family,{}).get("status"),
            "effective_protocol_status":tr.get("result_status"),
            "effective_closure_mode":closure_mode,
            "effective_witness_id":tr.get("witness_id"),
            "proof_source":proof_source,
            "opus_acceptance_calibrated":closed,
            "reason":reason,
        })

    calibrated=sorted(calibrated)
    pending=sorted(pending)
    behavioral_missing=sorted(behavioral_missing)
    errors=sorted(set(errors))
    pass_all=not errors and not behavioral_missing and len(calibrated)==EXPECTED_FAMILY_COUNT
    return {
        "schema":"PROJECT_BRAIN_OPUS55_ACCEPTANCE_CALIBRATION_VERDICT_V2",
        "status":"PASS" if pass_all else "FAIL_CLOSED",
        "pass":pass_all,
        "errors":errors,
        "target_family_count":len(families),
        "behavioral_pass_family_count":len(behavioral & set(families)),
        "acceptance_calibrated_family_count":len(calibrated),
        "acceptance_pending_family_count":len(pending),
        "acceptance_calibrated_families":calibrated,
        "acceptance_pending_families":pending,
        "behavioral_missing_families":behavioral_missing,
        "families":rows,
        "terminal_goal_acceptance_closed":bool(pass_all),
        "transmutation_summary":{
            "closed_family_count":t.get("closed_family_count"),
            "open_family_count":t.get("open_family_count"),
            "execution_authority":t.get("execution_authority"),
            "promotion_authority":t.get("promotion_authority"),
        },
        "rule":"BEHAVIORAL_PASS_AND_EFFECTIVE_UNCHANGED_FROZEN_PROTOCOL_PASS_REQUIRED__FULL_SCOPE_VERIFIED_STRONGER_WITNESS_MAY_DISCHARGE_PROTOCOL_WITHOUT_REWRITING_IT",
        "new_terminal_evidence_required_by_this_reducer":False,
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }

def _load(path:Path)->dict[str,Any]:
    v=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError(str(path))
    return v

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("envelope",type=Path)
    ap.add_argument("protocols",type=Path)
    ap.add_argument("reduction",type=Path)
    ap.add_argument("transmutation_input",type=Path)
    a=ap.parse_args()
    out=evaluate(*map(_load,(a.envelope,a.protocols,a.reduction,a.transmutation_input)))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not out["errors"] else 2

if __name__=="__main__":
    raise SystemExit(main())
