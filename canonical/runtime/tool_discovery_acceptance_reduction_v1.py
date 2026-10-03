"""Zero-reality Tool Discovery acceptance reduction.

Combines the independently verified exact frozen-scope completeness receipt with
the preserved 180/180 theoretical-ceiling witness through the already hardened
acceptance_proof_transmuter_v1. This is a deduction over immutable evidence, not
a new terminal execution.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import acceptance_proof_transmuter_v1 as transmuter

ROOT=Path(__file__).resolve().parents[2]
SCOPE="canonical/verification/TOOL_DISCOVERY_FROZEN_SCOPE_COMPLETENESS_DISCHARGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
WITNESS="canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json"
PROTOCOLS="canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
TRANSMUTER="canonical/runtime/acceptance_proof_transmuter_v1.py"

EXPECTED={
    SCOPE:"1dc22fb6a0816963b5349ed6a55763b2c42a1cb8",
    WITNESS:"60a7c1139cad315d977bf5ed97e708cc5ec3fcc7",
    PROTOCOLS:"62394e5b7d221ec9f69c3458f669e40e253a9d09",
    TRANSMUTER:"39b5611e53485674b29e2a05da91b89801bc5aa6",
}
FAMILY="TOOL_DISCOVERY_SELECTION_AND_LEARNING"

def _blob(path:str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _load(path:str)->dict[str,Any]:
    v=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError(path+":NOT_OBJECT")
    return v

def evaluate(
    scope_override:Mapping[str,Any]|None=None,
    witness_override:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    drift={p:{"expected":want,"actual":_blob(p)} for p,want in EXPECTED.items() if _blob(p)!=want}
    if drift:
        return _fail("SOURCE_BLOB_DRIFT",source_blob_drift=drift)

    scope=copy.deepcopy(dict(scope_override)) if scope_override is not None else _load(SCOPE)
    witness=copy.deepcopy(dict(witness_override)) if witness_override is not None else _load(WITNESS)
    protocols=_load(PROTOCOLS)

    scope_ok=all([
        str(scope.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),
        scope.get("basis_kind")=="EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
        scope.get("scope_semantics_discharged") is True,
        scope.get("missing_source_facts")==[],
        scope.get("proof_domain")=="EXACT_FROZEN_TOOL_DISCOVERY_TERMINAL_TARGET_ONLY",
        scope.get("public_runner",{}).get("conclusion")=="success",
        scope.get("terminal_cases_replayed")==0,
        scope.get("new_reality_units_consumed")==0,
    ])
    if not scope_ok:
        return _fail("SCOPE_RECEIPT_NOT_ADMISSIBLE")

    witness_ok=all([
        witness.get("family")==FAMILY,
        witness.get("mode")=="ABSOLUTE_DOMINANCE",
        witness.get("verified") is True,
        witness.get("independent") is True,
        witness.get("contamination_clean") is True,
        witness.get("binds_frozen_protocol") is True,
        witness.get("closes_entire_protocol") is True,
        witness.get("scope_relation") in {"EXACT","PROVEN_STRONGER"},
        witness.get("source_case_count")==180,
        witness.get("result",{}).get("direction")=="higher",
        witness.get("result",{}).get("brain_lower_bound")==1,
        witness.get("result",{}).get("theoretical_upper_bound")==1,
    ])
    if not witness_ok:
        return _fail("CEILING_WITNESS_NOT_ADMISSIBLE")

    evidence={
        "id":"TOOL_DISCOVERY_TERMINAL_CEILING_WITH_EXACT_FROZEN_SCOPE_20261003_V1",
        "family":FAMILY,
        "mode":"ABSOLUTE_DOMINANCE",
        "verified":True,
        "independent":True,
        "contamination_clean":True,
        "binds_frozen_protocol":True,
        "scope_relation":"PROVEN_STRONGER",
        "closes_entire_protocol":True,
        "source_witness_path":WITNESS,
        "source_scope_receipt":SCOPE,
        "scope_completeness":{
            "verified":True,
            "independent":True,
            "basis":"EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
            "complete_target_case_set":True,
            "receipt":SCOPE,
        },
        "result":copy.deepcopy(witness["result"]),
    }
    compiled=transmuter.evaluate(protocols,{"evidence":[evidence]})
    row=next((x for x in compiled.get("families",[]) if x.get("family")==FAMILY),None)
    already=sum(
        1 for p in protocols.get("protocols",[])
        if isinstance(p,Mapping) and p.get("status")=="PASS"
    )
    expected_closed=already+1

    pass_ok=all([
        compiled.get("status")=="PASS",
        isinstance(row,Mapping),
        row.get("result_status")=="PASS" if isinstance(row,Mapping) else False,
        row.get("closure_mode")=="ABSOLUTE_DOMINANCE" if isinstance(row,Mapping) else False,
        row.get("witness_reason")=="THEORETICAL_CEILING_DOMINANCE" if isinstance(row,Mapping) else False,
        compiled.get("closed_family_count")==expected_closed,
        compiled.get("family_credit_delta")==0,
        compiled.get("capability_credit_delta")==0,
        compiled.get("execution_authority") is False,
        compiled.get("promotion_authority") is False,
    ])
    if not pass_ok:
        return _fail("ACCEPTANCE_TRANSMUTATION_DID_NOT_CLOSE_EXACTLY_ONE_FAMILY",compiled=compiled)

    return {
        "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_V1",
        "status":"PASS__TOOL_DISCOVERY_ACCEPTANCE_CLOSED_BY_CEILING_PLUS_EXACT_FROZEN_SCOPE__ZERO_REALITY",
        "family":FAMILY,
        "prior_family_status":"DEFINED_RESULT_OPEN",
        "result_family_status":"PASS",
        "closure_mode":"ABSOLUTE_DOMINANCE",
        "witness_reason":"THEORETICAL_CEILING_DOMINANCE",
        "scope_basis":"EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
        "scope_receipt":SCOPE,
        "ceiling_witness":WITNESS,
        "family_count":compiled["family_count"],
        "closed_family_count":compiled["closed_family_count"],
        "open_family_count":compiled["open_family_count"],
        "newly_closed_families":[FAMILY],
        "terminal_goal_achieved":False,
        "terminal_cases_replayed":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "compiled":compiled,
    }

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    out={
        "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_V1",
        "status":"FAIL_CLOSED__"+reason,
        "family":FAMILY,
        "result_family_status":"DEFINED_RESULT_OPEN",
        "terminal_goal_achieved":False,
        "terminal_cases_replayed":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }
    out.update(extra); return out

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
