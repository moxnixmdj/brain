from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_LIVEBENCH_IF_PUBLIC_STANDARD_ZERO_SPEND_CARRIER_BINDING_V1"
EXPECTED_REPOSITORY="moxnixmdj/verification-capsule-runner"
ALLOWED_STANDARD_RUNNERS={"ubuntu-24.04","ubuntu-latest","ubuntu-22.04","ubuntu-26.04"}

def verify_binding(binding: Mapping[str,Any])->dict[str,Any]:
    errors=[]
    if binding.get("repository")!=EXPECTED_REPOSITORY:
        errors.append("PUBLIC_VERIFICATION_REPOSITORY_MISMATCH")
    if binding.get("repository_is_public") is not True:
        errors.append("REPOSITORY_PUBLIC_VISIBILITY_NOT_PROVED")
    runner=str(binding.get("runner_label") or "")
    if runner not in ALLOWED_STANDARD_RUNNERS:
        errors.append("NONSTANDARD_OR_UNBOUND_RUNNER")
    if binding.get("standard_public_runner_zero_incremental_spend_verified") is not True:
        errors.append("PUBLIC_STANDARD_RUNNER_ZERO_SPEND_RULE_NOT_PROVED")
    if binding.get("larger_or_paid_runner_allowed") is not False:
        errors.append("PAID_OR_LARGER_RUNNER_NOT_FORBIDDEN")
    if binding.get("paid_external_model_or_api_allowed") is not False:
        errors.append("PAID_EXTERNAL_PROVIDER_NOT_FORBIDDEN")
    passed=not errors
    return {
        "schema":SCHEMA,
        "zero_incremental_spend_or_entitlement_verified":passed,
        "cost_binding_pass":passed,
        "errors":errors,
        "resource_fit_proved":False,
        "execution_success_proved":False,
        "generic_isolation_instantiation_proved":False,
        "fresh_reality_authority":False,
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_authorized":False,
    }
