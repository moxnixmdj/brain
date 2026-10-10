"""Verify TB-Science is parked outside active Gap-B after retired Rank20 V3."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_ESCAPE_TB_SCIENCE_CURRENT_ROUTE_RECLASSIFICATION_V2_VERIFY"
TB_PATH="canonical/governance/CURRENT_TB_SCIENCE_EXECUTION.json"
TB_BLOB="7678d9a56461b121ffd52dd4c9c8df464fda08d2"
REPAIR_PATH="canonical/verification/TB_SCIENCE_BOUND_START_CAS_CALLER_REPAIR_VERIFY_20261010_V1.json"
REPAIR_BLOB="bf5aa5cddf6c1272a9664320273d39725470b2e5"
RECLASS_PATH="canonical/governance/ESCAPE_TB_SCIENCE_CURRENT_ROUTE_RECLASSIFICATION_20261010_V2.json"

def blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def read_bound(root:Path,rel:str,expected:str)->dict[str,Any]:
    p=(root/rel).resolve()
    p.relative_to(root.resolve())
    if not p.is_file() or p.is_symlink():
        raise RuntimeError("BOUND_FILE_INVALID:"+rel)
    actual=blob(p)
    if actual!=expected:
        raise RuntimeError("BOUND_BLOB_MISMATCH:"+rel+":"+actual)
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict):
        raise RuntimeError("BOUND_JSON_OBJECT_REQUIRED:"+rel)
    return v

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        tb=read_bound(root,TB_PATH,TB_BLOB)
        repair=read_bound(root,REPAIR_PATH,REPAIR_BLOB)
        reclass_path=root/RECLASS_PATH
        reclass=json.loads(reclass_path.read_text(encoding="utf-8"))
        if reclass.get("schema")!="PROJECT_BRAIN_ESCAPE_TB_SCIENCE_CURRENT_ROUTE_RECLASSIFICATION_20261010_V2":
            raise RuntimeError("RECLASS_SCHEMA_INVALID")
        if reclass.get("obligation_id")!="TB_SCIENCE_GE_58_7":
            raise RuntimeError("OBLIGATION_ID_INVALID")
        if reclass.get("current_scheduler_class")!="PARKED_AUTHORITY_LIMITED__UNRESOLVED_TARGET__NO_CURRENT_EXECUTABLE_INTERNAL_ROUTE":
            raise RuntimeError("SCHEDULER_CLASS_INVALID")
        fin=tb.get("finalized_rank20_v3_nonconsuming") or {}
        if fin.get("task_started") is not False or fin.get("durable_start_cas_acquired") is not False:
            raise RuntimeError("RETIRED_ATTEMPT_STARTED")
        if fin.get("benchmark_trials_consumed")!=0:
            raise RuntimeError("RANK20_V3_TRIAL_CONSUMED")
        for key in ("retry_authority","replacement_authority","activation_authority"):
            if fin.get(key) is not False:
                raise RuntimeError("RETIRED_AUTHORITY_STILL_TRUE:"+key)
        aa=tb.get("rank20_activation_authority") or {}
        if aa.get("authorized") is not False or aa.get("retired_after_nonconsuming_abort") is not True:
            raise RuntimeError("ACTIVATION_AUTHORITY_NOT_RETIRED")
        rv=tb.get("rank20_bound_start_cas_repair_verified") or {}
        if not str(rv.get("status") or "").startswith("PASS__"):
            raise RuntimeError("REPAIR_NOT_VERIFIED_IN_CURRENT_TB")
        if rv.get("verification_git_blob_sha")!=REPAIR_BLOB:
            raise RuntimeError("REPAIR_BINDING_MISMATCH")
        if rv.get("rank20_v3_retry_authority") is not False or rv.get("rank20_v3_replacement_authority") is not False:
            raise RuntimeError("REPAIR_REAUTHORIZED_RETIRED_ATTEMPT")
        if rv.get("activation_present") is not False:
            raise RuntimeError("REPAIR_BASE_ACTIVATION_PRESENT")
        if not str(repair.get("status") or "").startswith("PASS__"):
            raise RuntimeError("REPAIR_RECEIPT_NOT_PASS")
        auth=repair.get("authority") or {}
        if auth.get("general_repair_verified") is not True:
            raise RuntimeError("GENERAL_REPAIR_UNVERIFIED")
        if auth.get("rank20_v3_retry_authority") is not False or auth.get("rank20_v3_replacement_authority") is not False:
            raise RuntimeError("REPAIR_RECEIPT_RETRY_AUTHORITY_INVALID")
        effect=reclass.get("scheduling_effect") or {}
        if effect.get("remove_from_active_gap_b_internal_route_count") is not True:
            raise RuntimeError("ACTIVE_GAP_B_REMOVAL_NOT_ASSERTED")
        if effect.get("active_gap_b_rows_after_reclassification")!=2:
            raise RuntimeError("ACTIVE_GAP_B_COUNT_INVALID")
        if set(effect.get("active_gap_b_rows") or [])!={"PROWORK_GDPVAL_GE_1846","CHARTOGRAPHY_TOOLS_GE_89"}:
            raise RuntimeError("ACTIVE_GAP_B_ROWS_INVALID")
        if effect.get("parked_row")!="TB_SCIENCE_GE_58_7":
            raise RuntimeError("PARKED_ROW_INVALID")
        if "NO_TB_SCIENCE_TARGET_CLOSURE" not in set(reclass.get("hard_nonclaims") or []):
            raise RuntimeError("TARGET_CLOSURE_NONCLAIM_MISSING")
        return {
            "schema":SCHEMA,
            "pass":True,
            "status":"PASS__TB_RANK20_V3_RETIRED__GENERAL_CALLER_REPAIR_VERIFIED__NO_AUTHORIZED_INTERNAL_ACTION__PARKED_OUTSIDE_ACTIVE_GAP_B",
            "current_tb_git_blob_sha":TB_BLOB,
            "repair_verification_git_blob_sha":REPAIR_BLOB,
            "active_gap_b_rows_after_reclassification":2,
            "parked_unresolved_tb_row":True,
            "tb_target_closed":False,
            "retry_authority":False,
            "replacement_authority":False,
            "execution_authority":False,
            "acceptance_credit_delta":0,
            "capability_credit_delta":0,
            "terminal_credit_delta":0,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED",
            "reason":type(exc).__name__+":"+str(exc),
            "active_gap_b_rows_after_reclassification":None,
            "tb_target_closed":False,
            "execution_authority":False,
            "terminal_credit_delta":0,
        }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
