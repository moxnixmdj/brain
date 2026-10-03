#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/"canonical/governance/ROOT2_UNIVERSAL_COMPARATOR_CAPSULE_V1.json"
FAN=ROOT/"canonical/governance/ROOT2_OWNER_CHANNEL_FANOUT_V1.json"
EXPECTED_OWNERS={"Artificial Analysis","Vals AI","Cursor","Cognition","Zapier"}
EXPECTED_PREDS={
"PROWORK_GDPVAL_GE_1846","PROWORK_AA_BRIEFCASE_GE_1822","ARTIFACT_AA_BRIEFCASE_GE_1822",
"FINANCE_ACCOUNTING_INDEX_GE_61","FINANCE_AGENT_V2_GE_58_59","MYSTERYMECHANISM_GE_49_55",
"CODING_CURSORBENCH_GE_57_8","CODING_FRONTIERCODE_GE_54_4","AUTOMATIONBENCH_GE_40"
}

def load(path:Path)->dict[str,Any]:
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError("OBJECT_REQUIRED")
    return x

def verify(capsule:dict[str,Any],fanout:dict[str,Any])->dict[str,Any]:
    errors=[]
    seams=capsule.get("current_brain_execution_seams") or {}
    if seams.get("generic_external_task_entrypoint") is not None:
        errors.append("GENERIC_ENTRYPOINT_UNEXPECTEDLY_CLAIMED_BOUND")
    for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
        if capsule.get(k)!=0 or fanout.get(k)!=0: errors.append("NONZERO_CREDIT:"+k)
    if capsule.get("incremental_spend_usd")!=0 or fanout.get("incremental_spend_usd")!=0:
        errors.append("NONZERO_SPEND")
    rows=fanout.get("channels")
    if not isinstance(rows,list) or len(rows)!=5: errors.append("FIVE_CHANNELS_REQUIRED"); rows=rows or []
    owners={r.get("owner") for r in rows if isinstance(r,dict)}
    if owners!=EXPECTED_OWNERS: errors.append("OWNER_SET_MISMATCH")
    if any(r.get("state")!="OUTREACH_SENT" for r in rows if isinstance(r,dict)):
        errors.append("OWNER_CHANNEL_NOT_STARTED")
    preds=set()
    for r in rows:
        if isinstance(r,dict): preds.update(r.get("expected_predicates") or [])
    if preds!=EXPECTED_PREDS: errors.append("TARGET_PREDICATE_SET_MISMATCH")
    if fanout.get("deduplication",{}).get("directly_targeted_root2_fixed_bar_predicates")!=9:
        errors.append("TARGET_COUNT_MISMATCH")
    rules=set(capsule.get("hard_rules") or [])
    for rule in (
        "NO_ACCEPTANCE_CREDIT_FROM_CAPSULE_EXISTENCE",
        "NO_RUNNABLE_CLAIM_UNTIL_GENERIC_EXTERNAL_TASK_ENTRYPOINT_IS_CONTENT_ADDRESSED_AND_INDEPENDENTLY_VERIFIED",
        "NO_UNDECLARED_PAID_FALLBACK",
    ):
        if rule not in rules: errors.append("MISSING_CAPSULE_RULE:"+rule)
    return {
      "schema":"PROJECT_BRAIN_ROOT2_OWNER_FANOUT_AND_CAPSULE_VERIFIER_V1",
      "status":"PASS__OWNER_CHANNELS_STARTED__CAPSULE_FAIL_CLOSED_ON_MISSING_GENERIC_ENTRYPOINT__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":sorted(set(errors)),
      "owner_channel_count":len(owners),
      "directly_targeted_root2_fixed_bar_predicates":len(preds),
      "generic_external_task_entrypoint_bound":False,
      "incremental_spend_usd":0,
      "new_reality_units_consumed":0,
      "terminal_cases_consumed":0,
      "acceptance_credit_delta":0,
      "family_credit_delta":0,
      "capability_credit_delta":0,
      "ownership_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
      "fresh_reality_authority":False,
    }

if __name__=="__main__":
    out=verify(load(CAP),load(FAN))
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
