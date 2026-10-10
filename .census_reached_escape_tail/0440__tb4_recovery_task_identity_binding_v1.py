from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TB4_RECOVERY_TASK_IDENTITY_VERDICT_V1"

def evaluate(cut: Mapping[str,Any], manifest: Mapping[str,Any]) -> dict[str,Any]:
    errors=[]
    if cut.get("schema")!="PROJECT_BRAIN_TB4_MINIMUM_CARRIER_RECOVERY_CUT_V1":
        errors.append("CUT_SCHEMA")
    if manifest.get("schema")!="PROJECT_BRAIN_TB4_RECOVERY_TASK_IDENTITY_MANIFEST_20261006_V1":
        errors.append("MANIFEST_SCHEMA")
    source=manifest.get("source")
    if not isinstance(source,Mapping):
        errors.append("SOURCE_MISSING"); source={}
    if source.get("repository")!="harbor-framework/terminal-bench":
        errors.append("SOURCE_REPOSITORY")
    if source.get("frozen_commit")!="452bf305c6daa62fc59061d22133a7cbc7c1572e":
        errors.append("FROZEN_COMMIT")
    for k in ("instruction_files_read","solution_files_read","test_payload_files_read","terminal_cases_executed"):
        if source.get(k)!=0:
            errors.append("NONZERO_"+k.upper())
    rows=manifest.get("tasks")
    chosen=cut.get("minimum_recovery_set")
    resource_rows=cut.get("resource_exceed_tasks")
    if not isinstance(rows,list) or len(rows)!=8:
        errors.append("MANIFEST_NOT_EXACT_EIGHT"); rows=[]
    if not isinstance(chosen,list) or len(chosen)!=8:
        errors.append("CUT_NOT_EXACT_EIGHT"); chosen=[]
    if not isinstance(resource_rows,list):
        errors.append("RESOURCE_ROWS_MISSING"); resource_rows=[]
    expected=set(chosen)
    observed={r.get("name") for r in rows if isinstance(r,Mapping)}
    if observed!=expected:
        errors.append("TASK_SET_MISMATCH")
    if len(observed)!=len(rows):
        errors.append("DUPLICATE_TASK_NAMES")
    cutmap={r.get("task"):r for r in resource_rows if isinstance(r,Mapping)}
    for r in rows:
        if not isinstance(r,Mapping): errors.append("TASK_ROW_INVALID"); continue
        name=r.get("name")
        if name not in cutmap:
            errors.append("TASK_NOT_IN_RESOURCE_CUT:"+str(name)); continue
        if not isinstance(r.get("git_blob_sha"),str) or len(r["git_blob_sha"])!=40:
            errors.append("INVALID_BLOB_SHA:"+str(name))
        expected_path="tasks/"+str(name).split("/",1)[1]+"/task.toml" if "/" in str(name) else ""
        if r.get("path")!=expected_path:
            errors.append("PATH_MISMATCH:"+str(name))
        for k in ("cpus","memory_mb","storage_mb","gpus"):
            if r.get(k)!=cutmap[name].get(k):
                errors.append("RESOURCE_MISMATCH:"+str(name)+":"+k)
    maxes={
        "cpus_at_least":max((r.get("cpus",0) for r in rows),default=0),
        "usable_memory_mb_at_least":max((r.get("memory_mb",0) for r in rows),default=0),
        "free_storage_mb_at_least":max((r.get("storage_mb",0) for r in rows),default=0),
        "gpus_required":max((r.get("gpus",0) for r in rows),default=0),
    }
    env=cut.get("minimum_carrier_envelope",{})
    for k,v in maxes.items():
        if env.get(k)!=v: errors.append("ENVELOPE_MISMATCH:"+k)
    return {
        "schema":SCHEMA,
        "status":"PASS__EXACT_EIGHT_TASK_IDENTITIES_BOUND_TO_FROZEN_TB4_COMMIT__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "frozen_commit":source.get("frozen_commit"),
        "task_count":len(rows),
        "task_names":sorted(observed),
        "minimum_carrier_envelope":maxes if not errors else None,
        "task_identity_bound":not errors,
        "protocol_equivalence_bound":False,
        "execution_authority":False,
        "promotion_authority":False,
        "terminal_credit_delta":0,
    }
