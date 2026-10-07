from __future__ import annotations
from canonical.runtime.universal_verified_adaptive_solver_v1 import BUILTIN_VERIFIERS
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS

SCHEMA="PROJECT_BRAIN_ADAPTIVE_SOLVER_REGISTRY_INTEGRITY_V1"
REQUIRED_CURRENT={
 "EXACT_JSON_V1":"CANDIDATE_EQUALS_EXPECTED",
 "P2_AUTHENTICATED_TOP_LAW_V1":"P2_TOP_LAW_PASS",
 "FINANCE_JUDGMENT_CONTROL_V1":"CONFIGURED_TERMINAL_DECISION_ACCEPTED",
 "UNKNOWN_DOMAIN_JUDGMENT_CONTROL_V1":"CONFIGURED_TERMINAL_DECISION_ACCEPTED",
 "SOURCE_ALIGNED_SEMANTIC_POLICY_V6":"COMMON_POLICY_CERTIFIED",
 "TYPED_ACCEPTANCE_PROGRAM_V1":"TYPED_ACCEPTANCE_PROGRAM_PASS",
 "INSTRUCTION_CONSTRAINTS_V1":"INSTRUCTION_CONSTRAINTS_PASS",
 "STRUCTURED_METHOD_EXPRESSION_AST_V2":"STRUCTURED_METHOD_COMPILED",
 "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1":"SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_VERIFIED",
}

def audit()->dict:
    live=set(BUILTIN_VERIFIERS)
    canonical=set(REQUIRED_CURRENT)
    v2=set(SUCCESS_CONDITIONS)
    errors=[]
    if live!=canonical:
        errors.append("LIVE_REGISTRY_DIFFERS_FROM_AUDITED_CURRENT_REGISTRY")
    missing=sorted(live-v2)
    extra=sorted(v2-live)
    wrong=sorted(k for k in live&v2 if SUCCESS_CONDITIONS[k]!=REQUIRED_CURRENT.get(k))
    safe=not errors and not missing and not extra and not wrong
    return {
      "schema":SCHEMA,
      "status":"PASS__V2_REGISTRY_FULLY_BOUND" if safe else "DETECTED_V2_REGISTRY_BINDING_DRIFT",
      "pass":safe,
      "live_verifiers":sorted(live),
      "v2_bound_verifiers":sorted(v2),
      "missing_success_conditions_in_v2":missing,
      "extra_success_conditions_in_v2":extra,
      "wrong_success_conditions_in_v2":wrong,
      "new_credit_safe_through_v2":safe,
      "source_aligned_acceptance_credit_safe_through_v2":safe and "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1" in v2,
      "errors":errors,
      "terminal_authority":False,
      "capability_credit_delta":0,
    }
