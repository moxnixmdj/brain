from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_LIVEBENCH_IF_EXECUTION_PRECOMMIT_V1"
EXPECTED={
 "candidate":"8f99aa371061160822670fc6f5da2ce3a01cc260063330ed6e5954a2cac68c9a",
 "harness":"76aa46d80fc5153bab6015d324747f7bef8048b73e69bf84d4079d59d4f59793",
 "scorer":"d500c0b8ad7bcf545800a3f815123bfcc955845fba4587d783d93a4f8750cfd1",
 "environment":"0c414ba07aac3babb0752949c670a8d6287a7cf9cdc13c5614918c3c9ad2702c",
 "policy":"3e77340568dce7d6ff8f77f94de7e1fe38b85c705d88ba1067447f716a456e90",
}

def digest(obj: Any) -> str:
    raw=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def verify_precommit(m: Mapping[str,Any]) -> dict[str,Any]:
    errors=[]
    if m.get("schema")!=SCHEMA: errors.append("SCHEMA_MISMATCH")
    for k in ("candidate","harness","scorer","environment","policy"):
        if digest(m.get(k))!=EXPECTED[k]:
            errors.append("COMPONENT_DIGEST_MISMATCH:"+k)
        if (m.get("component_sha256") or {}).get(k)!=EXPECTED[k]:
            errors.append("DECLARED_COMPONENT_DIGEST_MISMATCH:"+k)
    c=m.get("candidate") or {}
    if c.get("commit")!="d5de4f5808dced840da34d051e3f9a5ff06e2e54": errors.append("CANDIDATE_COMMIT_MISMATCH")
    if c.get("tree")!="fd39e966d4686c7317b9a1558b360eb0c58ad76f": errors.append("CANDIDATE_TREE_MISMATCH")
    p=m.get("policy") or {}
    if p.get("allow_optional_model_planner") is not False: errors.append("OPTIONAL_MODEL_PLANNER_NOT_FORBIDDEN")
    if p.get("external_tools_allowed") is not False: errors.append("EXTERNAL_TOOLS_NOT_FORBIDDEN")
    if p.get("required_cognition_dependency_class")!="MODEL_INDEPENDENT": errors.append("MODEL_INDEPENDENCE_NOT_REQUIRED")
    if p.get("result_sink")!="WRITE_ONLY_ESCROW": errors.append("WRITE_ONLY_ESCROW_NOT_REQUIRED")
    for k in ("result_visible_to_candidate_before_fixed_point","result_visible_to_planner_before_fixed_point","result_visible_to_zero_reality_work_before_fixed_point","candidate_mutation_allowed","unrelated_work_mutation_allowed","acceptance_credit_before_predicate_activation"):
        if p.get(k) is not False: errors.append("POLICY_FAIL_CLOSED_FIELD_INVALID:"+k)
    env=m.get("environment") or {}
    if env.get("resource_fit_status")!="OPEN__ZERO_CASE_PREFLIGHT_REQUIRED": errors.append("RESOURCE_FIT_MUST_REMAIN_OPEN")
    if env.get("paid_external_model_or_api_allowed") is not False: errors.append("PAID_EXTERNAL_PROVIDER_NOT_FORBIDDEN")
    if env.get("larger_or_paid_runner_allowed") is not False: errors.append("PAID_RUNNER_NOT_FORBIDDEN")
    exposure=m.get("case_exposure") or {}
    if exposure.get("terminal_case_content_read") is not False: errors.append("TERMINAL_CASE_CONTENT_READ")
    if exposure.get("terminal_cases_consumed")!=0: errors.append("TERMINAL_CASES_CONSUMED_NONZERO")
    passed=not errors
    return {
      "schema":SCHEMA,
      "precommit_pass":passed,
      "errors":errors,
      "component_sha256":dict(EXPECTED),
      "terminal_cases_consumed":0,
      "resource_fit_proved":False,
      "generic_isolation_instantiation_proved":False,
      "shadow_collection_authority":False,
      "fresh_reality_authority":False,
      "execution_authority":False,
      "promotion_authority":False,
      "acceptance_credit_authorized":False,
    }
