"""Verify the narrow Tool Discovery frozen-scope interpretation proposition.

This does not prove that the 180-case pool is the complete frozen acceptance
population. It only checks that the predeclared acceptance row is frozen-scope
language while the quarantine's stated objection is open-domain exhaustion.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
CAND=ROOT/"canonical/governance/TOOL_DISCOVERY_FROZEN_SCOPE_INTERPRETATION_REPAIR_V2.json"
SNAPSHOT=ROOT/"canonical/governance/TOOL_DISCOVERY_SCOPE_INTERPRETATION_SOURCE_SNAPSHOT_V2.json"

def evaluate()->dict[str,Any]:
    c=json.loads(CAND.read_text())
    snap=json.loads(SNAPSHOT.read_text())
    hist=c["historical_protocol"]["tool_discovery_row"]
    row=snap["sources"]["historical_protocol"]
    b=snap["sources"]["prewave_binding"]
    q=snap["sources"]["quarantine"]
    errors=[]
    for k in ("family","proof_mode","acceptance"):
        if row.get(k)!=hist.get(k):
            errors.append("CURRENT_PROTOCOL_ROW_DRIFT:"+k)
    acc=str(hist.get("acceptance") or "")
    if "frozen tool ecosystems" not in acc:
        errors.append("HISTORICAL_ACCEPTANCE_NOT_FROZEN_SCOPE")
    if "all open-domain tool ecosystems" in acc.lower():
        errors.append("HISTORICAL_ACCEPTANCE_REQUIRES_OPEN_DOMAIN")
    if b.get("behavior_id")!="TOOL_ROUTE_DISCOVERY_AND_SELECTION_001":
        errors.append("BINDING_BEHAVIOR_ID_MISMATCH")
    pool=b
    if pool.get("terminal_sample_count")!=180:
        errors.append("BINDING_SAMPLE_COUNT_NOT_180")
    if b.get("population_or_source_pool_frozen") is not True:
        errors.append("BINDING_POPULATION_NOT_FROZEN")
    if b.get("every_selected_case_must_pass") is not True:
        errors.append("BINDING_NOT_ALL_SELECTED_CASES")
    claim=str(pool.get("terminal_scope_claim") or "")
    if "NOT_EXHAUSTIVE_PROOF_OF_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS" not in claim:
        errors.append("BINDING_OPEN_DOMAIN_DISCLAIMER_MISSING")
    reasoning=str(q.get("rationale") or "")
    if "all open-domain tool ecosystems" not in reasoning.lower():
        errors.append("QUARANTINE_OPEN_DOMAIN_RATIONALE_NOT_FOUND")
    ok=not errors
    return {
      "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_FROZEN_SCOPE_INTERPRETATION_REPAIR_V2_VERDICT",
      "status":"PASS__OPEN_DOMAIN_DISCLAIMER_DOES_NOT_BY_ITSELF_REFUTE_FROZEN_ACCEPTANCE_SCOPE" if ok else "FAIL_CLOSED",
      "pass":ok,
      "errors":errors,
      "proved_proposition":"OPEN_DOMAIN_EXHAUSTION_IS_NOT_STATED_BY_THE_PREDECLARED_FROZEN_ACCEPTANCE_ROW" if ok else None,
      "still_open":"EXACT_IDENTITY_BETWEEN_180_CASE_SOURCE_POOL_AND_FROZEN_ACCEPTANCE_POPULATION",
      "acceptance_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
      "new_reality_units_consumed":0,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
