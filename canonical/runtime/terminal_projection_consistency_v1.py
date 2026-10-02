"""Fail-closed consistency reducer for Project Brain terminal projections.

Derived projections must agree with the currently bound independent calibration
and atomic-residual receipts. This checker grants no capability, family,
execution, or promotion credit.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]

def load(rel:str)->dict[str,Any]:
    v=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError(rel)
    return v

def git_blob_sha(rel:str)->str:
    b=(ROOT/rel).read_bytes()
    h=hashlib.sha1(); h.update(f"blob {len(b)}\0".encode()); h.update(b)
    return h.hexdigest()

def evaluate_documents(
    authority:Mapping[str,Any], closure:Mapping[str,Any], matrix:Mapping[str,Any],
    calibration:Mapping[str,Any], residual:Mapping[str,Any], plan:Mapping[str,Any],
    kernel:Mapping[str,Any], actual_blob_shas:Mapping[str,str]|None=None,
)->dict[str,Any]:
    e:list[str]=[]
    cres=calibration.get("result")
    if not isinstance(cres,Mapping):
        e.append("CALIBRATION_RESULT_MISSING"); cres={}
    calibrated=cres.get("acceptance_calibrated_families")
    if not isinstance(calibrated,list) or any(not isinstance(x,str) for x in calibrated):
        e.append("CALIBRATION_FAMILY_SET_INVALID"); calibrated=[]
    calibrated_set=set(calibrated)
    ccount=cres.get("acceptance_calibrated_family_count")
    pending=cres.get("acceptance_pending_family_count")
    if type(ccount) is not int or type(pending) is not int or ccount+pending!=19:
        e.append("CALIBRATION_COUNTS_INVALID")
    if type(ccount) is int and len(calibrated_set)!=ccount:
        e.append("CALIBRATION_COUNT_SET_MISMATCH")

    pcount=residual.get("predicate_count")
    proved=residual.get("proved_predicate_count")
    opened=residual.get("open_predicate_count")
    blocked=residual.get("blocked_predicate_count")
    refuted=residual.get("refuted_predicate_count",0)
    if any(type(x) is not int for x in (pcount,proved,opened,blocked,refuted)):
        e.append("RESIDUAL_COUNTS_INVALID")
    elif pcount!=38 or proved+opened+blocked+refuted!=pcount:
        e.append("RESIDUAL_ACCOUNTING_MISMATCH")
    actions=residual.get("authorized_acceptance_case_actions",residual.get("authorized_actions"))
    if not isinstance(actions,list):
        e.append("RESIDUAL_ACTIONS_INVALID"); actions=[]

    truth=authority.get("truth")
    if not isinstance(truth,Mapping):
        e.append("AUTHORITY_TRUTH_MISSING"); truth={}
    if type(ccount) is int and type(pending) is int:
        want=f"{ccount}/19_PASS__{pending}/19_OPEN"
        if truth.get("opus55_acceptance")!=want:
            e.append("AUTHORITY_ACCEPTANCE_COUNT_MISMATCH")
    expected_achieved=bool(ccount==19 and pending==0 and proved==38 and blocked==0 and opened==0 and refuted==0)
    if truth.get("achieved") is not expected_achieved:
        e.append("AUTHORITY_ACHIEVED_MISMATCH")

    summary=closure.get("opus55_acceptance_summary")
    if not isinstance(summary,Mapping):
        e.append("CLOSURE_ACCEPTANCE_SUMMARY_MISSING"); summary={}
    if summary.get("calibrated_family_count")!=ccount or summary.get("pending_family_count")!=pending:
        e.append("CLOSURE_ACCEPTANCE_SUMMARY_MISMATCH")
    if set(summary.get("calibrated_families") or [])!=calibrated_set:
        e.append("CLOSURE_ACCEPTANCE_FAMILY_SET_MISMATCH")
    preds=closure.get("terminal_predicates")
    if not isinstance(preds,Mapping):
        e.append("CLOSURE_TERMINAL_PREDICATES_MISSING"); preds={}
    if preds.get("all_frozen_opus_acceptance_predicates_pass") is not (ccount==19):
        e.append("CLOSURE_ACCEPTANCE_PREDICATE_MISMATCH")
    if ccount!=19 and preds.get("proof_bundle_frozen") is not False:
        e.append("CLOSURE_PREMATURE_PROOF_BUNDLE_FREEZE")

    msum=matrix.get("postwave_acceptance_summary")
    if not isinstance(msum,Mapping):
        e.append("MATRIX_ACCEPTANCE_SUMMARY_MISSING"); msum={}
    if msum.get("calibrated_family_count")!=ccount or msum.get("pending_acceptance_family_count")!=pending:
        e.append("MATRIX_ACCEPTANCE_SUMMARY_MISMATCH")
    if set(msum.get("calibrated_families") or [])!=calibrated_set:
        e.append("MATRIX_ACCEPTANCE_FAMILY_SET_MISMATCH")
    if msum.get("verified_owned_family_count")!=2:
        e.append("MATRIX_VERIFIED_OWNED_COUNT_NOT_2")
    if msum.get("promotion_authority") is not False:
        e.append("MATRIX_PREMATURE_PROMOTION_AUTHORITY")

    if plan.get("residual_family_count")!=pending:
        e.append("PLAN_PENDING_FAMILY_COUNT_MISMATCH")
    pf=plan.get("residual_families")
    if not isinstance(pf,list):
        e.append("PLAN_RESIDUAL_FAMILIES_MISSING")
    else:
        names={r.get("family") for r in pf if isinstance(r,Mapping)}
        if len(names)!=pending or names & calibrated_set:
            e.append("PLAN_RESIDUAL_FAMILY_SET_MISMATCH")
    state=plan.get("current_acceptance_state")
    if not isinstance(state,Mapping):
        e.append("PLAN_CURRENT_ACCEPTANCE_STATE_MISSING"); state={}
    expected_state={
        "calibrated_family_count":ccount,"pending_family_count":pending,
        "atomic_predicates_total":pcount,"proved_atomic_predicates":proved,
        "blocked_atomic_predicates":blocked,"open_direct_atomic_predicates":opened,
    }
    for k,v in expected_state.items():
        if state.get(k)!=v: e.append(f"PLAN_STATE_MISMATCH:{k}")
    if state.get("authorized_acceptance_case_actions")!=actions:
        e.append("PLAN_ACTION_SET_MISMATCH")

    ks=kernel.get("current_expected_state")
    if not isinstance(ks,Mapping):
        e.append("KERNEL_CURRENT_STATE_MISSING"); ks={}
    expected_kernel={
        "residual_registry_families":17,"acceptance_pending_families":pending,
        "atomic_predicates":pcount,"receipt_saturation_complete":True,
        "proved_predicates":proved,"open_direct_predicates":opened,
        "blocked_predicates":blocked,
        "authorized_acceptance_case_actions":len(actions),
        "terminal_promotion_allowed":expected_achieved,
    }
    for k,v in expected_kernel.items():
        if ks.get(k)!=v: e.append(f"KERNEL_STATE_MISMATCH:{k}")

    af=authority.get("atomic_acceptance_frontier")
    if not isinstance(af,Mapping):
        e.append("AUTHORITY_ATOMIC_FRONTIER_MISSING"); af={}
    if (af.get("proved"),af.get("open_direct"),af.get("blocked"),af.get("total"))!=(proved,opened,blocked,pcount):
        e.append("AUTHORITY_ATOMIC_FRONTIER_MISMATCH")
    if af.get("authorized_acceptance_case_actions")!=actions:
        e.append("AUTHORITY_ACTION_SET_MISMATCH")

    if actual_blob_shas is not None:
        sources=authority.get("sources")
        if not isinstance(sources,Mapping):
            e.append("AUTHORITY_SOURCES_MISSING"); sources={}
        for key in ("terminal_closure_manifest","ownership_matrix","residual_plan","acceptance_residual_proof_kernel_v2","acceptance_calibration"):
            row=sources.get(key)
            if not isinstance(row,Mapping):
                e.append(f"AUTHORITY_SOURCE_MISSING:{key}"); continue
            path=row.get("path"); want=row.get("git_blob_sha")
            if not isinstance(path,str) or actual_blob_shas.get(path)!=want:
                e.append(f"AUTHORITY_SOURCE_BLOB_MISMATCH:{key}")
        source=af.get("source")
        current=None
        if isinstance(source,str):
            current=actual_blob_shas.get(source)
        bound=None
        for k,row in sources.items():
            if isinstance(row,Mapping) and row.get("path")==source:
                bound=row.get("git_blob_sha"); break
        if not isinstance(source,str) or current is None or bound!=current:
            e.append("AUTHORITY_RESIDUAL_SOURCE_BLOB_MISMATCH")

    e=sorted(set(e))
    return {
        "schema":"PROJECT_BRAIN_TERMINAL_PROJECTION_CONSISTENCY_VERDICT_V2",
        "status":"PASS" if not e else "FAIL_CLOSED","pass":not e,"errors":e,
        "acceptance_calibrated_families":ccount,"acceptance_pending_families":pending,
        "atomic_predicates_proved":proved,"atomic_predicates_blocked":blocked,
        "authorized_acceptance_case_actions":len(actions),
        "terminal_goal_achieved":expected_achieved,
        "capability_credit_delta":0,"family_credit_delta":0,
        "promotion_authority":False,"execution_authority":False,
        "rule":"DERIVED_PROJECTIONS_MUST_EQUAL_CURRENT_BOUND_CALIBRATION_AND_RESIDUAL_RECEIPTS__ALL_LOAD_BEARING_HASH_POINTERS_MUST_RESOLVE",
    }

def evaluate_live()->dict[str,Any]:
    authority=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
    sources=authority.get("sources",{})
    calrow=sources.get("acceptance_calibration",{})
    calpath=calrow.get("path")
    residual_path=authority.get("atomic_acceptance_frontier",{}).get("source")
    if not isinstance(calpath,str) or not isinstance(residual_path,str):
        return {"status":"FAIL_CLOSED","pass":False,"errors":["DYNAMIC_AUTHORITY_PATH_MISSING"]}
    paths={
        "authority":"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
        "closure":"canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
        "matrix":"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
        "calibration":calpath,"residual":residual_path,
        "plan":"canonical/governance/OPUS55_ACCEPTANCE_RESIDUAL_MINIMUM_PROOF_PLAN_V1.json",
        "kernel":"canonical/governance/OPUS55_ACCEPTANCE_RESIDUAL_PROOF_KERNEL_V2.json",
    }
    docs={k:load(v) for k,v in paths.items()}
    all_paths=set(paths.values())
    for row in sources.values():
        if isinstance(row,Mapping) and isinstance(row.get("path"),str):
            all_paths.add(row["path"])
    shas={p:git_blob_sha(p) for p in all_paths if (ROOT/p).is_file()}
    return evaluate_documents(
        docs["authority"],docs["closure"],docs["matrix"],docs["calibration"],
        docs["residual"],docs["plan"],docs["kernel"],shas,
    )

def main()->int:
    out=evaluate_live(); print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("pass") else 1

if __name__=="__main__": raise SystemExit(main())
