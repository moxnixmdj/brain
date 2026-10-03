"""Fail-closed atomic guard for terminal derived-state promotion.

The guard does not derive semantics. It requires all load-bearing reducers to
carry independent content-addressed receipts bound to one source root and one
transaction id, prevents count regressions, and makes terminal truth equivalent
to complete atomic/family/composition closure.
"""
from __future__ import annotations
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_TERMINAL_CLOSURE_SUPERTRANSACTION_GUARD_V1"
HEX=set("0123456789abcdef")
REQUIRED_STAGES={"acceptance_reduction","family_reduction","composition_reduction","frontier_recompile","projection_consistency"}

def _sha(v:Any)->bool:
    return isinstance(v,str) and len(v)==40 and set(v.lower())<=HEX

def _count(m:Mapping[str,Any],k:str,total:int)->int|None:
    v=m.get(k)
    return v if not isinstance(v,bool) and isinstance(v,int) and 0<=v<=total else None

def _fail(*errors:str)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","transaction_admissible":False,"errors":sorted(set(errors)),
            "capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False}

def evaluate(doc:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(doc,Mapping) or doc.get("schema")!=SCHEMA: return _fail("SCHEMA_INVALID")
    before=doc.get("before"); after=doc.get("after"); receipts=doc.get("stage_receipts")
    root=doc.get("source_root"); tx=doc.get("transaction_id")
    if not isinstance(before,Mapping) or not isinstance(after,Mapping): return _fail("BEFORE_AFTER_REQUIRED")
    if not _sha(root) or not isinstance(tx,str) or not tx: return _fail("SOURCE_ROOT_OR_TRANSACTION_ID_INVALID")
    if not isinstance(receipts,list): return _fail("STAGE_RECEIPTS_INVALID")
    errors=[]; seen=set()
    for i,row in enumerate(receipts):
        if not isinstance(row,Mapping): errors.append(f"STAGE_RECEIPT_NOT_OBJECT:{i}"); continue
        stage=row.get("stage")
        if stage not in REQUIRED_STAGES or stage in seen: errors.append(f"STAGE_INVALID_OR_DUPLICATE:{i}"); continue
        seen.add(stage)
        if row.get("independent") is not True or not str(row.get("status","")).startswith("INDEPENDENT"):
            errors.append(f"STAGE_NOT_INDEPENDENT_PASS:{stage}")
        if row.get("source_root")!=root or row.get("transaction_id")!=tx:
            errors.append(f"STAGE_ROOT_OR_TRANSACTION_MISMATCH:{stage}")
        if not isinstance(row.get("path"),str) or not row.get("path") or not _sha(row.get("git_blob_sha")):
            errors.append(f"STAGE_RECEIPT_NOT_CONTENT_ADDRESSED:{stage}")
    missing=sorted(REQUIRED_STAGES-seen)
    if missing: errors.append("MISSING_STAGES:"+",".join(missing))

    ba=_count(before,"atomic_proved",38); aa=_count(after,"atomic_proved",38)
    bf=_count(before,"families_accepted",19); af=_count(after,"families_accepted",19)
    bc=_count(before,"composition_interfaces_proved",12); ac=_count(after,"composition_interfaces_proved",12)
    if None in (ba,aa,bf,af,bc,ac): errors.append("COUNT_INVALID")
    else:
        if aa<ba: errors.append("ATOMIC_REGRESSION")
        if af<bf: errors.append("FAMILY_REGRESSION")
        if ac<bc: errors.append("COMPOSITION_REGRESSION")

    bp=before.get("protected_terminal_facts"); ap=after.get("protected_terminal_facts")
    if not isinstance(bp,list) or not isinstance(ap,list): errors.append("PROTECTED_FACTS_INVALID")
    elif not set(bp).issubset(set(ap)): errors.append("PROTECTED_TERMINAL_FACT_REGRESSION")

    terminal=after.get("terminal_goal_achieved"); interaction=after.get("composition_interaction_pass")
    if not isinstance(terminal,bool) or not isinstance(interaction,bool): errors.append("TERMINAL_OR_INTERACTION_FLAG_INVALID")
    elif terminal and not (aa==38 and af==19 and ac==12 and interaction): errors.append("PREMATURE_TERMINAL_TRUE")
    elif not terminal and aa==38 and af==19 and ac==12 and interaction: errors.append("TERMINAL_FALSE_DESPITE_COMPLETE_CLOSURE")
    if errors: return _fail(*errors)

    return {"schema":SCHEMA,"status":"PASS__ATOMIC_CLOSURE_TRANSACTION_ADMISSIBLE","transaction_admissible":True,
            "source_root":root,"transaction_id":tx,"terminal_goal_achieved":terminal,
            "after":{"atomic_proved":aa,"families_accepted":af,"composition_interfaces_proved":ac,"composition_interaction_pass":interaction},
            "rule":"NO_PARTIAL_DERIVED_STATE_PROMOTION__ALL_REQUIRED_REDUCERS_ONE_SOURCE_ROOT__TERMINAL_TRUE_IFF_38_OF_38_AND_19_OF_19_AND_12_OF_12_AND_INTERACTION_PASS",
            "capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False}
