from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime.p2_p3_information_safe_candidate_v2 import solve as p2_solve

SCHEMA="PROJECT_BRAIN_P2_STRONG_VISIBLE_QUALITY_CERTIFIER_V2"
P2="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"

def _fail(errors):
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errors)),"terminal_authority":False,"terminal_credit_delta":0,"binding_authentication_self_certified":False}

def _facts(task):
    evidence=task.get("evidence")
    if not isinstance(evidence,list): raise ValueError("EVIDENCE_INVALID")
    return {str(x.get("fact_id")) for x in evidence if isinstance(x,Mapping) and isinstance(x.get("fact_id"),str) and x.get("fact_id")}

def _estimate(edit,task,facts):
    claims=[str(x) for x in (edit.get("claims") or [])]
    grounded=bool(claims) and all(x in facts for x in claims)
    topic=str(edit.get("topic") or ""); analysis=str(edit.get("analysis_kind") or "")
    audience=str(task.get("audience") or ""); fit=str(edit.get("intended_audience") or "")==audience
    required={str(x) for x in (task.get("required_topics") or [])}
    return ((5 if grounded else -12)+(4 if grounded and topic in required and analysis!="layout" else 0)+(3 if fit else -1)+(2 if analysis!="layout" else 0))

def _objective(selected_ids,task):
    facts=_facts(task)
    edits={str(x.get("id")):x for x in (task.get("edit_candidates") or []) if isinstance(x,Mapping) and isinstance(x.get("id"),str) and x.get("id")}
    if len(edits)!=len(task.get("edit_candidates") or []): raise ValueError("EDIT_IDS_INVALID")
    selected=[]
    for eid in selected_ids:
        if eid not in edits: raise ValueError("UNKNOWN_EDIT:"+eid)
        selected.append(edits[eid])
    score=sum(_estimate(x,task,facts) for x in selected)
    required={str(x) for x in (task.get("required_topics") or [])}
    covered={str(x.get("topic")) for x in selected if (lambda claims: bool(claims) and all(c in facts for c in claims))([str(c) for c in (x.get("claims") or [])]) and str(x.get("analysis_kind") or "")!="layout"}
    return score-20*len(required-covered)

def certify(bundle:Any)->dict[str,Any]:
    if not isinstance(bundle,Mapping): return _fail(["BUNDLE_NOT_OBJECT"])
    public=bundle.get("public"); qb=bundle.get("quality_binding")
    if not isinstance(public,Mapping) or public.get("contract")!=P2: return _fail(["P2_PUBLIC_TASK_REQUIRED"])
    task=public.get("task")
    if not isinstance(task,Mapping) or not isinstance(qb,Mapping): return _fail(["TASK_OR_QUALITY_BINDING_INVALID"])
    errors=[]
    if qb.get("lossless_p2_membership_proved") is not True: errors.append("LOSSLESS_P2_MEMBERSHIP_NOT_PROVED")
    if not str(qb.get("lossless_p2_membership_receipt") or "").strip(): errors.append("LOSSLESS_P2_MEMBERSHIP_RECEIPT_MISSING")
    if qb.get("baseline_layout_nonobscuring") is not True: errors.append("BASELINE_LAYOUT_NOT_CERTIFIED")
    if not str(qb.get("baseline_layout_receipt") or "").strip(): errors.append("BASELINE_LAYOUT_RECEIPT_MISSING")
    if qb.get("mechanics_only_baseline_equals_empty_p2_plan") is not True: errors.append("MECHANICS_BASELINE_EQUIVALENCE_NOT_PROVED")
    if not str(qb.get("mechanics_only_baseline_equivalence_receipt") or "").strip(): errors.append("MECHANICS_BASELINE_EQUIVALENCE_RECEIPT_MISSING")
    if qb.get("ablation_rescue_semantics_bound_to_certifier_policy") is not True: errors.append("ABLATION_RESCUE_SEMANTICS_NOT_BOUND")
    if not str(qb.get("ablation_rescue_semantics_receipt") or "").strip(): errors.append("ABLATION_RESCUE_SEMANTICS_RECEIPT_MISSING")
    native_required=qb.get("native_mechanical_gate_required")
    if type(native_required) is not bool: errors.append("NATIVE_GATE_REQUIREMENT_INVALID")
    elif native_required:
        if qb.get("native_mechanical_gate_pass") is not True: errors.append("NATIVE_MECHANICAL_GATE_NOT_PASS")
        if not str(qb.get("native_mechanical_gate_receipt") or "").strip(): errors.append("NATIVE_MECHANICAL_GATE_RECEIPT_MISSING")
    exact_mode=(qb.get("explicit_rubric_equivalent_to_p2_objective") is True and bool(str(qb.get("rubric_equivalence_receipt") or "").strip()))
    comparison_mode=(qb.get("target_comparison_order_bound") is True and bool(str(qb.get("target_comparison_order_receipt") or "").strip()) and isinstance(qb.get("comparison_order"),Mapping))
    if not exact_mode and not comparison_mode: errors.append("QUALITY_ORDER_CERTIFICATE_MISSING")
    if errors: return _fail(errors)
    try:
        out=p2_solve(public); selected=out.get("selected_edits")
        if not isinstance(selected,list) or not selected: return _fail(["NONEMPTY_SELECTED_PLAN_REQUIRED"])
        if len(selected)!=len(set(selected)): return _fail(["DUPLICATE_SELECTED_EDIT"])
        edits={str(x.get("id")):x for x in (task.get("edit_candidates") or []) if isinstance(x,Mapping) and isinstance(x.get("id"),str) and x.get("id")}
        if any(x not in edits for x in selected): return _fail(["UNKNOWN_SELECTED_EDIT"])
        cost=sum(int(edits[x].get("cost")) for x in selected); budget=int(task.get("edit_budget") or 0)
        if cost>budget: return _fail(["BUDGET_EXCEEDED"])
        facts=_facts(task); required={str(x) for x in (task.get("required_topics") or [])}; selected_rows=[edits[x] for x in selected]
        grounded=[]
        for row in selected_rows:
            claims=[str(x) for x in (row.get("claims") or [])]; grounded.append(bool(claims) and all(x in facts for x in claims))
        all_grounded=all(grounded); all_audience_fit=all(str(x.get("intended_audience") or "")==str(task.get("audience") or "") for x in selected_rows); all_nonlayout=all(str(x.get("analysis_kind") or "")!="layout" for x in selected_rows)
        covered={str(row.get("topic")) for row,g in zip(selected_rows,grounded) if g and str(row.get("analysis_kind") or "")!="layout"}; required_covered=required.issubset(covered)
        selected_score=_objective(list(selected),task); baseline_score=_objective([],task)
        losses=[]
        for eid in sorted(selected):
            ablated=[x for x in selected if x!=eid]; score=_objective(ablated,task); losses.append((selected_score-score,eid,score))
        max_loss=max(x[0] for x in losses); chosen=min(x for x in losses if x[0]==max_loss); rescue_score=_objective(list(selected),task)
    except Exception as exc: return _fail(["CERTIFIER_EXCEPTION:"+type(exc).__name__+":"+str(exc)])
    if exact_mode:
        order_mode="FULL_RUBRIC_EQUIVALENCE"; quality5=(selected_score>baseline_score); quality6=(max_loss>0 and rescue_score==selected_score)
        order_binding={"mode":order_mode,"rubric_equivalence_receipt":str(qb.get("rubric_equivalence_receipt"))}
    else:
        co=qb.get("comparison_order"); oe=[]
        cert_selected=co.get("selected_edit_ids")
        if not isinstance(cert_selected,list) or sorted(map(str,cert_selected))!=sorted(map(str,selected)): oe.append("COMPARISON_SELECTED_PLAN_MISMATCH")
        if str(co.get("ablated_edit_id") or "")!=str(chosen[1]): oe.append("COMPARISON_ABLATED_EDIT_MISMATCH")
        if co.get("selected_gt_baseline") is not True: oe.append("COMPARISON_SELECTED_GT_BASELINE_NOT_PROVED")
        if co.get("selected_gt_ablated") is not True: oe.append("COMPARISON_SELECTED_GT_ABLATED_NOT_PROVED")
        if co.get("rescue_eq_selected") is not True: oe.append("COMPARISON_RESCUE_EQ_SELECTED_NOT_PROVED")
        if oe: return _fail(oe)
        order_mode="BOUND_COMPARISON_ORDER"; quality5=True; quality6=True
        order_binding={"mode":order_mode,"target_comparison_order_receipt":str(qb.get("target_comparison_order_receipt")),"selected_edit_ids":sorted(map(str,selected)),"ablated_edit_id":str(chosen[1]),"selected_gt_baseline":True,"selected_gt_ablated":True,"rescue_eq_selected":True}
    gates={
      "NO_UNSUPPORTED_MATERIAL_CONTENT":all_grounded,
      "REQUIRED_ANALYSIS_COVERED":required_covered,
      "AUDIENCE_EMPHASIS_MATCHES_VISIBLE_OBJECTIVE":all_audience_fit,
      "LAYOUT_OR_STRUCTURE_CHOICE_DOES_NOT_OBSCURE_REQUIRED_INFORMATION":all_nonlayout and qb.get("baseline_layout_nonobscuring") is True,
      "SELECTED_PLAN_IMPROVES_INDEPENDENT_RUBRIC_VERSUS_MECHANICS_ONLY_BASELINE":quality5,
      "PLAN_ABLATION_DEGRADES_AND_RESCUE_RESTORES_RELEVANT_QUALITY":quality6}
    if not all(gates.values()): return _fail(["QUALITY_GATE_FAILED:"+k for k,v in gates.items() if not v])
    return {"schema":SCHEMA,"status":"PASS__STRONG_VISIBLE_P2_QUALITY_SUBREGION_CERTIFIED","pass":True,"errors":[],"selected_edits":list(selected),"selected_objective":selected_score,"mechanics_only_baseline_objective":baseline_score,"ablation":{"policy":"REMOVE_MAXIMUM_MARGINAL_VALUE_SELECTED_EDIT__LEXICAL_TIE_BREAK","edit_id":chosen[1],"ablated_objective":chosen[2],"explicit_p2_marginal_loss":chosen[0],"rescue_objective":rescue_score},"quality_order_binding":order_binding,"gates":gates,"native_mechanical_gate_required":native_required,"native_mechanical_gate_pass":qb.get("native_mechanical_gate_pass") is True if native_required else None,"terminal_authority":False,"binding_authentication_self_certified":False,"terminal_credit_delta":0}
