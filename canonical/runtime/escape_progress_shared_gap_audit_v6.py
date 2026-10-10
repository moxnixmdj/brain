"""Current causal-projection audit for Escape-Progress row proofs.

V6 preserves the exact frozen 13-obligation universe while projecting only
independently verified current causal route changes before authenticating row
proofs:
- GDPVal and Chartography: historical Gap B -> current Gap A;
- TB Science: remains structural Gap B but parked, not active work.

No row receives credit from reclassification. CC_R3 still requires authenticated
canonical row proofs for all 13 projected rows.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import escape_progress_shared_gap_audit_v4 as v4
from canonical.runtime import escape_progress_shared_gap_audit_v5 as v5
from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)

SCHEMA="PROJECT_BRAIN_ESCAPE_PROGRESS_SHARED_GAP_EXECUTABLE_AUDIT_V6"
ROOT=Path(__file__).resolve().parents[2]
MANIFEST_PATH=ROOT/"canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
BINDING_PATH=ROOT/"canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V7.json"
RECLASS_PATH=ROOT/"canonical/governance/ESCAPE_ACTIVE_GAP_B_CAUSAL_RECLASSIFICATION_20261010_V1.json"
RECLASS_VERIFY_PATH=ROOT/"canonical/verification/ESCAPE_ACTIVE_GAP_B_CAUSAL_RECLASSIFICATION_PUBLIC_VERIFY_20261010_V1.json"
EXPECTED_RECLASS_BLOB="c793b7f57b13a936646a2825cd67f26c28bf3744"
EXPECTED_RECLASS_VERIFY_BLOB="1be936fc211b06baa480f2b747cb933ca2cd6dcf"
GAP_A="GAP_A_ACQUISITION_TOTALITY"
GAP_B="GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"


def _blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


def _load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError("JSON_OBJECT_REQUIRED:"+str(path))
    return value


def _project(manifest:Mapping[str,Any],binding:Mapping[str,Any])->dict[str,Any]:
    raw_reclass=RECLASS_PATH.read_bytes()
    raw_verify=RECLASS_VERIFY_PATH.read_bytes()
    if _blob(raw_reclass)!=EXPECTED_RECLASS_BLOB:
        raise ValueError("RECLASSIFICATION_BLOB_DRIFT")
    if _blob(raw_verify)!=EXPECTED_RECLASS_VERIFY_BLOB:
        raise ValueError("RECLASSIFICATION_VERIFY_BLOB_DRIFT")
    rc=json.loads(raw_reclass)
    rv=json.loads(raw_verify)
    if rv.get("subject",{}).get("git_blob_sha")!=EXPECTED_RECLASS_BLOB:
        raise ValueError("RECLASSIFICATION_VERIFY_SUBJECT_MISMATCH")
    if rv.get("independent_carrier",{}).get("conclusion")!="success":
        raise ValueError("RECLASSIFICATION_INDEPENDENT_VERIFY_NOT_PASS")

    projection=binding.get("current_effective_projection")
    if not isinstance(projection,Mapping):
        raise ValueError("CURRENT_EFFECTIVE_PROJECTION_REQUIRED")
    overrides=projection.get("route_group_overrides")
    if overrides!={
        "PROWORK_GDPVAL_GE_1846":GAP_A,
        "CHARTOGRAPHY_TOOLS_GE_89":GAP_A,
    }:
        raise ValueError("ROUTE_GROUP_OVERRIDES_INVALID")
    if projection.get("parked_rows")!=["TB_SCIENCE_GE_58_7"]:
        raise ValueError("PARKED_ROWS_INVALID")

    rows=manifest.get("rows")
    if not isinstance(rows,list) or len(rows)!=13:
        raise ValueError("FROZEN_MANIFEST_ROWS_INVALID")
    out=deepcopy(dict(manifest))
    projected=[]
    seen=set()
    for row in rows:
        if not isinstance(row,Mapping):
            raise ValueError("FROZEN_MANIFEST_ROW_INVALID")
        r=deepcopy(dict(row))
        oid=r.get("obligation_id")
        if not isinstance(oid,str) or not oid or oid in seen:
            raise ValueError("FROZEN_MANIFEST_ID_INVALID")
        seen.add(oid)
        if oid in overrides:
            if r.get("route_group")!=GAP_B:
                raise ValueError("OVERRIDE_PREDECESSOR_GROUP_DRIFT:"+oid)
            r["historical_route_group"]=GAP_B
            r["route_group"]=GAP_A
            r["current_route_projection_source"]=str(RECLASS_PATH.relative_to(ROOT))
        projected.append(r)
    out["rows"]=projected
    out["schema"]="PROJECT_BRAIN_ESCAPE_PROGRESS_13_CURRENT_CAUSAL_PROJECTION_V1"
    out["projection_authority"]=False
    out["acceptance_credit_delta"]=0
    return out


def audit_repo(
    root:Path=ROOT,
    row_proof_bindings:Mapping[str,Mapping[str,Any]]|None=None,
)->dict[str,Any]:
    try:
        manifest=_load(root/MANIFEST_PATH.relative_to(ROOT))
        binding=_load(root/BINDING_PATH.relative_to(ROOT))
        projected=_project(manifest,binding)
        supplied=row_proof_bindings if isinstance(row_proof_bindings,Mapping) else {}

        current_by_oid={}
        currentness_errors=[]
        currentness_rows=[]
        for row in manifest["rows"]:
            oid=str(row.get("obligation_id") or "")
            current=v5._resolve_row_current_evidence(row,repo_root=root)
            current_by_oid[oid]=current
            currentness_rows.append({
                "obligation_id":oid,
                "pass":current.get("pass") is True,
                "path":current.get("path"),
                "git_blob_sha":current.get("git_blob_sha"),
                "byte_sha256":current.get("byte_sha256"),
                "errors":list(current.get("errors") or []),
            })
            for err in current.get("errors") or []:
                currentness_errors.append(oid+":"+str(err))

        filtered={}
        proof_currentness_errors=[]
        for oid,ref in supplied.items():
            current=current_by_oid.get(str(oid))
            if not isinstance(current,Mapping) or current.get("pass") is not True:
                proof_currentness_errors.append(str(oid)+":ROW_CURRENT_EVIDENCE_NOT_VALID")
                continue
            if not isinstance(ref,Mapping):
                proof_currentness_errors.append(str(oid)+":ROW_PROOF_BINDING_NOT_OBJECT")
                continue
            verify_ref=ref.get("independent_verification")
            if not isinstance(verify_ref,Mapping):
                proof_currentness_errors.append(str(oid)+":ROW_PROOF_VERIFICATION_REFERENCE_REQUIRED")
                continue
            try:
                bound=resolve_receipt_bytes(verify_ref,repo_root=root)
            except ReceiptResolutionError as exc:
                proof_currentness_errors.append(str(oid)+":ROW_PROOF_VERIFICATION_BYTE_BINDING_INVALID:"+str(exc))
                continue
            errors=v5._current_evidence_verification_errors(bound["document"],current)
            if errors:
                proof_currentness_errors.extend(str(oid)+":"+x for x in errors)
                continue
            filtered[str(oid)]=ref

        structural=v4.audit(
            projected,binding,row_proof_bindings=filtered,repo_root=root
        )
        all_currentness=sorted(set(currentness_errors+proof_currentness_errors))
        projection=binding["current_effective_projection"]
        projection_ok=(
            structural.get("pass") is True
            and structural.get("structural_audit",{}).get("gap_a_count")==12
            and structural.get("structural_audit",{}).get("gap_b_count")==1
            and projection.get("active_gap_b_count")==0
            and projection.get("parked_gap_b_count")==1
        )
        cc=structural.get("cc_r3_proved") is True and not all_currentness
        return {
            "schema":SCHEMA,
            "status":(
                "PASS__CURRENT_PROJECTED_CC_R3_PROVED__13_OF_13"
                if cc else
                "PASS__CURRENT_CAUSAL_PROJECTION_AUDIT__CC_R3_OPEN"
                if projection_ok and not currentness_errors else
                "FAIL_CLOSED__CURRENT_CAUSAL_PROJECTION_INVALID"
            ),
            "pass":projection_ok and not currentness_errors,
            "cc_r3_proved":cc,
            "projected_gap_a_count":12,
            "projected_gap_b_structural_count":1,
            "active_gap_b_count":0,
            "parked_gap_b_count":1,
            "parked_rows":["TB_SCIENCE_GE_58_7"],
            "authenticated_current_row_proof_count":len(filtered),
            "currentness_errors":all_currentness,
            "currentness_rows":currentness_rows,
            "authenticated_projected_audit":structural,
            "terminal_authority":False,
            "acceptance_credit_delta":0,
            "terminal_credit_delta":0,
            "boundary":"CAUSAL_ROUTE_PROJECTION_ONLY__PARKED_TB_REMAINS_OPEN__ALL_13_AUTHENTICATED_ROW_PROOFS_REQUIRED_FOR_CC_R3",
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "cc_r3_proved":False,"reason":type(exc).__name__+":"+str(exc),
            "terminal_authority":False,"acceptance_credit_delta":0,
            "terminal_credit_delta":0,
        }


if __name__=="__main__":
    print(json.dumps(audit_repo(),sort_keys=True))
