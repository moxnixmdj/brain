from __future__ import annotations
from typing import Any,Mapping
from canonical.runtime.p3_binary_objective_decision_v1 import evaluate as decide
from canonical.runtime.p3_bounded_objective_role_presentation_compiler_v1 import evaluate as present
from canonical.runtime import synthesis_grounded_expression_ir_v1 as render

SCHEMA="PROJECT_BRAIN_P3_BOUNDED_BINARY_DERIVED_DECISION_EXPRESSION_V1"

def fail(reason,**detail):
 out={"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "decision_expression_covered":False,"both_role_facts_expressed_verbatim":False,
 "decision_provenance_preserved":False,"real_context_top_law_scope_membership_authenticated":False,
 "policy_adequacy_authority":False,"db_admission_authority":False,
 "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
 if detail:out["detail"]=detail
 return out

def prov(rows):
 if not isinstance(rows,list) or not rows:raise ValueError("PROVENANCE_REQUIRED")
 out=[];seen=set()
 for p in rows:
  if not isinstance(p,Mapping):raise ValueError("PROVENANCE_ROW_INVALID")
  s=p.get("source_id");l=p.get("locator")
  if not isinstance(s,str) or not s.strip():raise ValueError("PROVENANCE_SOURCE_ID_REQUIRED")
  if l is not None and (not isinstance(l,str) or not l.strip()):raise ValueError("PROVENANCE_LOCATOR_INVALID")
  k=(s,l or "")
  if k in seen:continue
  seen.add(k);q={"source_id":s}
  if l is not None:q["locator"]=l
  out.append(q)
 return out

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
 try:
  if not isinstance(payload,Mapping):return fail("PAYLOAD_MAPPING_REQUIRED")
  objective=payload.get("objective");public=payload.get("v2_input")
  if not isinstance(objective,str) or not objective.strip():return fail("OBJECTIVE_REQUIRED")
  if not isinstance(public,Mapping) or not isinstance(public.get("task"),Mapping):return fail("V2_INPUT_REQUIRED")
  task=public["task"];claims=task.get("claims");evidence=task.get("evidence");profile=task.get("audience_profile")
  if not isinstance(claims,list) or not isinstance(evidence,list) or not isinstance(profile,Mapping):return fail("CLAIMS_EVIDENCE_AUDIENCE_REQUIRED")
  c=profile.get("constraints")
  if not isinstance(c,Mapping):return fail("AUDIENCE_CONSTRAINTS_REQUIRED")
  if str(c.get("output_format") or "").upper() not in {"BULLETS","PARAGRAPHS"}:return fail("FORMAT_UNSUPPORTED")
  if str(c.get("citation_mode") or "").upper()!="INLINE_SOURCE_IDS" or str(c.get("style") or "").upper()!="VERBATIM_GROUNDED":return fail("STYLE_OR_CITATION_UNSUPPORTED")
  if c.get("required_sections",[])!=[] or c.get("allowed_sections") is not None or c.get("require_title",False) is not False:return fail("SECTION_OR_TITLE_CONSTRAINT_UNSUPPORTED")
  if c.get("item_order","INPUT")!="INPUT":return fail("CALLER_ITEM_ORDER_UNSUPPORTED")
  try:max_items=int(c.get("max_items"))
  except Exception:return fail("MAX_ITEMS_REQUIRED")
  if max_items<2:return fail("DECISION_PLUS_FACTS_INFEASIBLE_UNDER_ITEM_BUDGET")
  pr=present(payload)
  if pr.get("pass") is not True:return fail("BOUND_ROLE_PRESENTATION_COMPILER_FAILED",presentation=pr)
  dr=decide({"objective":objective,"claims":claims,"evidence":evidence})
  if dr.get("pass") is not True:return fail("BINARY_OBJECTIVE_DECISION_NOT_DERIVED",decision=dr)
  if dr.get("decision_derived") is not True or type(dr.get("decision_truth")) is not bool:return fail("DECISION_RECEIPT_INVALID")
  order=list(pr.get("objective_role_order") or [])
  if len(order)!=2 or len(set(order))!=2:return fail("OBJECTIVE_ROLE_ORDER_INVALID")
  byc={x.get("claim_id"):x for x in claims if isinstance(x,Mapping)}
  binds=(dr.get("relevance_receipt") or {}).get("claim_role_evidence_bindings")
  if not isinstance(binds,list) or len(binds)!=2:return fail("ROLE_EVIDENCE_BINDINGS_INVALID")
  c2e={x.get("claim_id"):x.get("evidence_id") for x in binds if isinstance(x,Mapping)}
  bye={x.get("evidence_id"):x for x in evidence if isinstance(x,Mapping)}
  rows=[]
  for cid in order:
   cl=byc.get(cid);ev=bye.get(c2e.get(cid))
   if not isinstance(cl,Mapping) or not isinstance(ev,Mapping):return fail("ROLE_ROW_MISSING")
   t=str(cl.get("text") or "").strip()
   if t!=str(ev.get("text") or "").strip():return fail("ROLE_FACT_NOT_VERBATIM_EVIDENCE",claim_id=cid)
   rows.append((cid,t,prov(ev.get("provenance"))))
  op=dr.get("operator")
  if not isinstance(op,str) or not op:return fail("DECISION_OPERATOR_REQUIRED")
  label=op if dr.get("threshold") is None else op+":"+str(dr["threshold"])
  dt=f"DECISION[{label}](LEFT,RIGHT)="+("TRUE" if dr["decision_truth"] else "FALSE")
  dp=prov(dr.get("decision_provenance"))
  items=[{"id":"DERIVED_DECISION","kind":"CLAIM","text":dt,"provenance":dp}]
  if max_items>=3:
   mode="SEPARATE_ROLE_FACT_ITEMS"
   items += [{"id":"ROLE_FACT_LEFT","kind":"CLAIM","text":rows[0][1],"provenance":rows[0][2]},
             {"id":"ROLE_FACT_RIGHT","kind":"CLAIM","text":rows[1][1],"provenance":rows[1][2]}]
  else:
   mode="PACKED_TWO_VERBATIM_ROLE_FACTS"
   items.append({"id":"ROLE_FACTS","kind":"CLAIM","text":rows[0][1]+" "+rows[1][1],"provenance":prov(rows[0][2]+rows[1][2])})
  rc=dict(c);rc["item_order"]=[x["id"] for x in items]
  rr=render.solve({"schema":render.INPUT_SCHEMA,"task":{"items":items,"constraints":rc}})
  if rr.get("status")!="PASS":return fail("REALIZER_FAIL_CLOSED",realizer=rr)
  a=rr.get("audit") or {}
  if a.get("dropped_item_count")!=0 or a.get("rewritten_material_item_count")!=0 or a.get("new_material_claim_count")!=0 or a.get("all_items_provenance_bound") is not True:return fail("REALIZER_AUDIT_INCOMPLETE",audit=a)
  txt=rr.get("rendered_text")
  if not isinstance(txt,str) or dt not in txt:return fail("DECISION_NOT_RENDERED")
  if rows[0][1] not in txt or rows[1][1] not in txt:return fail("ROLE_FACT_VERBATIM_PRESERVATION_FAILED")
  if txt.find(dt)>txt.find(rows[0][1]):return fail("DECISION_NOT_FIRST")
  return {"schema":SCHEMA,"pass":True,"status":"PASS__BOUND_BINARY_DECISION_GROUNDED_AND_EXPRESSED",
   "decision_derived":True,"required_decision_semantics_covered":True,"decision_expression_covered":True,
   "decision_truth":dr["decision_truth"],"decision_operator":op,"decision_text":dt,
   "decision_provenance":dp,"decision_provenance_preserved":True,
   "both_role_facts_expressed_verbatim":True,"role_fact_order":order,"fact_packaging":mode,
   "rendered_text":txt,"render_trace":rr.get("trace"),"realizer_audit":a,
   "decision_receipt":dr,"presentation_receipt":pr,
   "real_context_top_law_scope_membership_authenticated":False,
   "policy_adequacy_authority":False,"db_admission_authority":False,"u_subtraction_authority":False,
   "terminal_authority":False,"terminal_credit_delta":0,
   "boundary":"BOUND_BINARY_DECISION_FORMAL_EXPRESSION_PLUS_BOTH_VERBATIM_ROLE_FACTS__NO_GENERAL_PRESENTATION_ADEQUACY__TOP_LAW_SCOPE_MEMBERSHIP_SEPARATE"}
 except Exception as e:return fail("INVALID_INPUT",exception_type=type(e).__name__,detail_text=str(e)[:200])

def run(args:Mapping[str,Any]|None=None,root:Any=None):return evaluate(args or {})
