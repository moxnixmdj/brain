from __future__ import annotations
from typing import Any, Mapping

BEHAVIOR="SCIENTIFIC_DESIGN_SEARCH_AND_CONSTRAINT_OPTIMIZATION_001"
FAMILIES=(
 "AGENTIC_SCIENTIFIC_RESEARCH",
 "MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING",
 "UNKNOWN_DOMAIN_ADAPTATION",
)

class RegistryRepairError(ValueError):
    pass

def verify(v1:Mapping[str,Any],v2:Mapping[str,Any],*,v1_sha:str)->dict[str,Any]:
    if v2.get("schema")!="PROJECT_BRAIN_BEHAVIORAL_CONTRACT_REGISTRY_V2":
        raise RegistryRepairError("V2_SCHEMA_REQUIRED")
    pred=v2.get("predecessor")
    if not isinstance(pred,Mapping) or pred.get("git_blob_sha")!=v1_sha:
        raise RegistryRepairError("PREDECESSOR_SHA_MISMATCH")
    c1=list(v1.get("active_contracted_residuals") or [])
    c2=list(v2.get("active_contracted_residuals") or [])
    if len(c2)!=len(c1)+1 or c2[:-1]!=c1:
        raise RegistryRepairError("ACTIVE_CONTRACT_DELTA_NOT_EXACTLY_ONE_APPEND")
    new=c2[-1]
    if not isinstance(new,Mapping) or new.get("behavior_id")!=BEHAVIOR:
        raise RegistryRepairError("SCIENTIFIC_DESIGN_CONTRACT_NOT_APPENDED")
    f1=v1.get("family_to_residual_contracts")
    f2=v2.get("family_to_residual_contracts")
    if not isinstance(f1,Mapping) or not isinstance(f2,Mapping) or set(f1)!=set(f2):
        raise RegistryRepairError("FAMILY_SET_DRIFT")
    for fam in f1:
        a=list(f1[fam]); b=list(f2[fam])
        if fam in FAMILIES:
            if b!=a+[BEHAVIOR]:
                raise RegistryRepairError("TARGET_FAMILY_DELTA_INVALID:"+fam)
        elif b!=a:
            raise RegistryRepairError("UNAUTHORIZED_FAMILY_DRIFT:"+fam)
    protected=("terminal_objective","semantic_classes","broad_term_disposition","known_owned_behavioral_leaves","terminal_acceptance_proof_modes","family_mapping_invariant")
    for k in protected:
        if v1.get(k)!=v2.get(k):
            raise RegistryRepairError("PROTECTED_FIELD_DRIFT:"+k)
    return {
      "status":"PASS__EXACTLY_ONE_GENERIC_SCIENTIFIC_DESIGN_CONTRACT_ADDED__THREE_BINDINGS_ONLY__ZERO_CAPABILITY_CREDIT",
      "active_contract_count_before":len(c1),
      "active_contract_count_after":len(c2),
      "added_behavior_id":BEHAVIOR,
      "bound_families":list(FAMILIES),
      "implementation_proved":False,
      "terminal_credit_delta":0
    }
