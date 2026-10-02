"""Compile atomic Opus55 gaps into a fail-closed executable action frontier.

This layer never grants capability/family credit. It recomputes the live atomic
residual from canonical inputs, emits one exact gap certificate per predicate,
and ranks only explicitly declared actions. It does not invent semantic proof
implications or guess wall-clock durations.
"""
from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime.opus55_acceptance_residual_compiler_v2 import evaluate as residual_evaluate

SCHEMA="PROJECT_BRAIN_ACCEPTANCE_GAP_ACTION_VERDICT_V1"
EFFECT_RANK={"PROVES":3,"UNLOCKS":2,"ADVANCES":1}
CLASS_RANK={
    "VERIFY_GATE":0,
    "PROOF_COMPILE":1,
    "PROOF_SEARCH":2,
    "DEPENDENCY_REDUCE":3,
    "ROUTE_BIND":4,
    "INTERNALIZE":5,
    "REALITY_QUERY":6,
}

def _fail(*errors:str)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
        "errors":sorted(set(errors)),
        "gap_certificates":[],"actions":[],"selected_action":None,
        "terminal_promotion_allowed":False,
        "capability_credit_delta":0,"family_credit_delta":0,
    }

def evaluate(
    registry:Mapping[str,Any],
    evidence:Mapping[str,Any],
    comparator:Mapping[str,Any],
    readiness:Mapping[str,Any],
    actions_doc:Mapping[str,Any],
)->dict[str,Any]:
    residual=residual_evaluate(registry,evidence,comparator,readiness)
    if residual.get("errors"):
        return _fail(*[f"RESIDUAL:{x}" for x in residual.get("errors",[])])
    preds=residual.get("predicates")
    if not isinstance(preds,list):
        return _fail("RESIDUAL_PREDICATES_INVALID")
    by_id={r.get("predicate_id"):r for r in preds if isinstance(r,Mapping) and isinstance(r.get("predicate_id"),str)}
    blockers={}
    for b in residual.get("blocker_certificates",[]) or []:
        if isinstance(b,Mapping) and isinstance(b.get("predicate_id"),str):
            blockers[b["predicate_id"]]=dict(b)
    auth_by_pid={}
    for a in residual.get("authorized_actions",[]) or []:
        if isinstance(a,Mapping) and isinstance(a.get("predicate_id"),str):
            auth_by_pid[a["predicate_id"]]=dict(a)

    gaps=[]
    for pid in sorted(by_id):
        row=by_id[pid]
        state=row.get("state")
        cert={
            "predicate_id":pid,
            "family":row.get("family"),
            "kind":row.get("kind"),
            "surface":row.get("surface"),
            "predicate_state":state,
        }
        if state=="PROVED":
            cert["gap_state"]="PROVED"
        elif state=="REFUTED":
            cert["gap_state"]="REFUTED"
        elif state=="OPEN":
            if pid in auth_by_pid:
                cert["gap_state"]="OPEN_EXECUTION_AUTHORIZED"
                cert["authorized_residual_action"]=auth_by_pid[pid]
            else:
                cert["gap_state"]="OPEN_UNROUTED"
        elif state=="EXTERNAL_BLOCKED":
            cert["gap_state"]="BLOCKED"
            if pid in blockers:
                cert["blocker"]=blockers[pid]
            else:
                cert["blocker"]={"predicate_id":pid,"reason":"BLOCKED_WITHOUT_RUNTIME_CERTIFICATE"}
        else:
            return _fail(f"UNKNOWN_PREDICATE_STATE:{pid}:{state}")
        gaps.append(cert)

    raw_actions=actions_doc.get("actions")
    if not isinstance(raw_actions,list):
        return _fail("ACTIONS_NOT_LIST")
    seen=set(); compiled=[]; errors=[]
    for i,a in enumerate(raw_actions):
        if not isinstance(a,Mapping):
            errors.append(f"ACTION_NOT_OBJECT:{i}"); continue
        aid=a.get("id")
        if not isinstance(aid,str) or not aid:
            errors.append(f"ACTION_ID_INVALID:{i}"); continue
        if aid in seen:
            errors.append(f"ACTION_ID_DUPLICATE:{aid}"); continue
        seen.add(aid)
        effect=a.get("effect")
        if effect not in EFFECT_RANK:
            errors.append(f"ACTION_EFFECT_INVALID:{aid}"); continue
        cls=a.get("action_class")
        if cls not in CLASS_RANK:
            errors.append(f"ACTION_CLASS_INVALID:{aid}"); continue
        targets=a.get("target_predicates")
        if not isinstance(targets,list) or not targets or any(t not in by_id for t in targets):
            errors.append(f"ACTION_TARGET_INVALID:{aid}"); continue
        nru=a.get("new_reality_units")
        if isinstance(nru,bool) or not isinstance(nru,int) or nru<0:
            errors.append(f"ACTION_REALITY_UNITS_INVALID:{aid}"); continue
        pre=a.get("preconditions",[])
        if not isinstance(pre,list):
            errors.append(f"ACTION_PRECONDITIONS_INVALID:{aid}"); continue
        bad_pre=False; pre_ok=True
        for p in pre:
            if not isinstance(p,Mapping) or not isinstance(p.get("id"),str) or not isinstance(p.get("satisfied"),bool):
                bad_pre=True; break
            if p.get("blocking",True) and p.get("satisfied") is not True:
                pre_ok=False
        if bad_pre:
            errors.append(f"ACTION_PRECONDITION_ROW_INVALID:{aid}"); continue

        unresolved=[t for t in targets if by_id[t].get("state")!="PROVED"]
        families=sorted({by_id[t].get("family") for t in unresolved})
        useful=bool(unresolved)
        executable=pre_ok and useful

        authorization_errors=[]
        if nru>0:
            if a.get("consumes_acceptance_case") is not True:
                authorization_errors.append("REALITY_ACTION_NOT_DECLARED_ACCEPTANCE_CASE")
            open_targets=[t for t in unresolved if by_id[t].get("state")=="OPEN"]
            if not open_targets:
                authorization_errors.append("NO_OPEN_TARGET_FOR_REALITY_ACTION")
            for t in open_targets:
                if t not in auth_by_pid:
                    authorization_errors.append(f"OPEN_TARGET_NOT_RESIDUAL_AUTHORIZED:{t}")
            if authorization_errors:
                executable=False

        compiled.append({
            "id":aid,
            "action_class":cls,
            "effect":effect,
            "critical_path":a.get("critical_path") is True,
            "new_reality_units":nru,
            "target_predicates":targets,
            "unresolved_target_predicates":unresolved,
            "affected_unresolved_count":len(unresolved),
            "affected_family_count":len(families),
            "affected_families":families,
            "preconditions_satisfied":pre_ok,
            "authorization_errors":authorization_errors,
            "executable":executable,
            "useful":useful,
            "notes":a.get("notes"),
        })
    if errors:
        return _fail(*errors)

    def key(a:Mapping[str,Any])->tuple:
        return (
            0 if a.get("executable") else 1,
            0 if a.get("critical_path") else 1,
            int(a.get("new_reality_units",0)),
            -EFFECT_RANK[str(a.get("effect"))],
            -int(a.get("affected_unresolved_count",0)),
            -int(a.get("affected_family_count",0)),
            CLASS_RANK[str(a.get("action_class"))],
            str(a.get("id")),
        )
    compiled.sort(key=key)
    executable=[a for a in compiled if a.get("executable")]
    selected=executable[0] if executable else None
    return {
        "schema":SCHEMA,
        "status":"ACTIVE_FAIL_CLOSED",
        "pass":True,
        "errors":[],
        "residual_summary":{
            "predicate_count":residual.get("predicate_count"),
            "proved_predicate_count":residual.get("proved_predicate_count"),
            "open_predicate_count":residual.get("open_predicate_count"),
            "blocked_predicate_count":residual.get("blocked_predicate_count"),
            "receipt_saturation_complete":residual.get("receipt_saturation_complete"),
        },
        "gap_certificates":gaps,
        "actions":compiled,
        "selected_action":selected,
        "terminal_promotion_allowed":residual.get("terminal_promotion_allowed") is True,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "rule":"RECOMPUTE_LIVE_RESIDUAL__EMIT_EXACT_GAPS__RANK_ONLY_EXPLICIT_ACTIONS__NO_GUESSED_WALL_CLOCK__NO_SEMANTIC_IMPLICATION_WITHOUT_MACHINE_RULE",
    }
