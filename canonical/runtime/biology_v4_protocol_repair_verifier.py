from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

BIOLOGY="BIOLOGY_RESEARCH_AND_DEVELOPMENT"
NEW_ID="EXPERIMENTAL_PROTOCOL_CAUSAL_DIAGNOSIS_AND_ADAPTATION_001"
NEW_TRANSFORM="experimental_protocol_causal_diagnosis_adaptation_and_repair"
FAMILIES=(
    "AGENTIC_SCIENTIFIC_RESEARCH",
    "MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING",
    "UNKNOWN_DOMAIN_ADAPTATION",
    "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
)

class ProtocolRepairError(ValueError):
    pass

def rows(doc: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    x=doc.get("mappings")
    if not isinstance(x,list): raise ProtocolRepairError("MAPPINGS_REQUIRED")
    return {r["surface"]:r for r in x}

def contracts(doc: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    x=doc.get("active_contracted_residuals")
    if not isinstance(x,list): raise ProtocolRepairError("CONTRACTS_REQUIRED")
    return {r["behavior_id"]:r for r in x}

def verify(reg2:Mapping[str,Any], reg3:Mapping[str,Any], map3:Mapping[str,Any], map4:Mapping[str,Any],
           *, reg2_sha:str, reg3_sha:str, map3_sha:str, search_sha:str) -> dict[str,Any]:
    if reg3.get("schema")!="PROJECT_BRAIN_BEHAVIORAL_CONTRACT_REGISTRY_V3":
        raise ProtocolRepairError("REGISTRY_V3_SCHEMA")
    if reg3.get("predecessor",{}).get("git_blob_sha")!=reg2_sha:
        raise ProtocolRepairError("REGISTRY_PREDECESSOR_SHA")
    if reg3.get("truth_repair",{}).get("source_verification_git_blob_sha")!=search_sha:
        raise ProtocolRepairError("REGISTRY_SEARCH_SHA")

    c2,c3=contracts(reg2),contracts(reg3)
    if set(c3)-set(c2)!={NEW_ID} or set(c2)-set(c3):
        raise ProtocolRepairError("CONTRACT_SET_DELTA_NOT_EXACT")
    for k in c2:
        if c2[k]!=c3[k]: raise ProtocolRepairError("OLD_CONTRACT_DRIFT:"+k)

    f2=reg2["family_to_residual_contracts"]
    f3=reg3["family_to_residual_contracts"]
    if set(f2)!=set(f3): raise ProtocolRepairError("FAMILY_SET_DRIFT")
    for fam in f2:
        expected=list(f2[fam]) + ([NEW_ID] if fam in FAMILIES else [])
        if list(f3[fam])!=expected:
            raise ProtocolRepairError("FAMILY_MAPPING_DELTA:"+fam)

    if map4.get("schema")!="PROJECT_BRAIN_OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_V4":
        raise ProtocolRepairError("MAPPING_V4_SCHEMA")
    if map4.get("predecessor",{}).get("git_blob_sha")!=map3_sha:
        raise ProtocolRepairError("MAPPING_PREDECESSOR_SHA")
    if map4.get("authorities",{}).get("behavioral_contract_registry_v3",{}).get("git_blob_sha")!=reg3_sha:
        raise ProtocolRepairError("REGISTRY_V3_BINDING_SHA")

    m3,m4=rows(map3),rows(map4)
    if set(m3)!=set(m4): raise ProtocolRepairError("SURFACE_SET_DRIFT")
    for surface in set(m3)-{BIOLOGY}:
        if m3[surface]!=m4[surface]: raise ProtocolRepairError("NONBIOLOGY_DRIFT:"+surface)

    b3=dict(m3[BIOLOGY]); b4=dict(m4[BIOLOGY])
    dec3=list(b3.pop("behavioral_decomposition"))
    dec4=list(b4.pop("behavioral_decomposition"))
    req3=list(b3.pop("required_behavioral_contracts"))
    req4=list(b4.pop("required_behavioral_contracts"))
    b4.pop("v4_repair",None)
    old_transfer=b3.pop("terminal_transfer")
    new_transfer=b4.pop("terminal_transfer")
    if b3!=b4: raise ProtocolRepairError("UNAUTHORIZED_BIOLOGY_DRIFT")
    if dec4!=dec3+[NEW_TRANSFORM]: raise ProtocolRepairError("TRANSFORM_DELTA_NOT_EXACT")
    if req4!=req3+[NEW_ID]: raise ProtocolRepairError("REQUIRED_CONTRACT_DELTA_NOT_EXACT")
    if old_transfer==new_transfer or "NO_G_PROMOTION" not in new_transfer:
        raise ProtocolRepairError("G_FIREWALL_NOT_EXPLICIT")

    if map4.get("mapping_result",{}).get("constructive_unmapped_transform_count")!="UNKNOWN_PENDING_V4_RECHECK":
        raise ProtocolRepairError("V4_NOT_FAIL_CLOSED")
    if "NO_G_ROUTE_PROMOTION" not in set(map4.get("hard_nonclaims") or []):
        raise ProtocolRepairError("NO_G_NONCLAIM_MISSING")
    for doc in (map4,):
        acc=doc.get("accounting",{})
        for key in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
            if acc.get(key)!=0: raise ProtocolRepairError("CREDIT_INFLATION:"+key)

    return {
        "status":"PASS__BIOLOGY_V4_PROTOCOL_TRANSFORM_MINIMAL_REPAIR__FRESH_RECHECK_REQUIRED__ZERO_CREDIT",
        "new_contract":NEW_ID,
        "new_transform":NEW_TRANSFORM,
        "registry_contract_delta":1,
        "mapping_transform_delta":1,
        "g_route_promoted":False,
        "semantic_losslessness_proved":False,
        "terminal_credit_delta":0,
    }

def load(path:str)->dict[str,Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("reg2"); p.add_argument("reg3"); p.add_argument("map3"); p.add_argument("map4")
    p.add_argument("--reg2-sha",required=True); p.add_argument("--reg3-sha",required=True)
    p.add_argument("--map3-sha",required=True); p.add_argument("--search-sha",required=True)
    a=p.parse_args()
    print(json.dumps(verify(load(a.reg2),load(a.reg3),load(a.map3),load(a.map4),
      reg2_sha=a.reg2_sha,reg3_sha=a.reg3_sha,map3_sha=a.map3_sha,search_sha=a.search_sha),sort_keys=True))
