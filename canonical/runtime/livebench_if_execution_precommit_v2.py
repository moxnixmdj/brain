from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_LIVEBENCH_IF_EXECUTION_PRECOMMIT_V2"
EXPECTED={
 "candidate":"8f99aa371061160822670fc6f5da2ce3a01cc260063330ed6e5954a2cac68c9a",
 "harness":"dcb03697e0f38d50933ca38650809fc80343737e4be3105966f2851e510c4b9e",
 "scorer":"d500c0b8ad7bcf545800a3f815123bfcc955845fba4587d783d93a4f8750cfd1",
 "environment":"382778b03559c5f60cb0a99ab47c99fb9d4c614ed9bd223d1862063a1d4ae465",
 "policy":"3e77340568dce7d6ff8f77f94de7e1fe38b85c705d88ba1067447f716a456e90",
}
RESOURCE_RECEIPT_PATH="canonical/verification/LIVEBENCH_ZERO_CASE_RESOURCE_FIT_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
RESOURCE_RECEIPT_BLOB="667943c418a434988d915bfb2ac736679af3bf7b"

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

    h=m.get("harness") or {}
    if h.get("shadow_lease_runtime_path")!="canonical/runtime/shadow_reality_lease_v2.py":
        errors.append("SHADOW_LEASE_V2_NOT_BOUND")
    if h.get("shadow_lease_runtime_git_blob_sha")!="8a13e29ddc160ea4af62aed434fb8a1a65afb998":
        errors.append("SHADOW_LEASE_V2_BLOB_MISMATCH")

    p=m.get("policy") or {}
    if p.get("allow_optional_model_planner") is not False: errors.append("OPTIONAL_MODEL_PLANNER_NOT_FORBIDDEN")
    if p.get("external_tools_allowed") is not False: errors.append("EXTERNAL_TOOLS_NOT_FORBIDDEN")
    if p.get("required_cognition_dependency_class")!="MODEL_INDEPENDENT": errors.append("MODEL_INDEPENDENCE_NOT_REQUIRED")
    if p.get("result_sink")!="WRITE_ONLY_ESCROW": errors.append("WRITE_ONLY_ESCROW_NOT_REQUIRED")
    for k in ("result_visible_to_candidate_before_fixed_point","result_visible_to_planner_before_fixed_point","result_visible_to_zero_reality_work_before_fixed_point","candidate_mutation_allowed","unrelated_work_mutation_allowed","acceptance_credit_before_predicate_activation"):
        if p.get(k) is not False: errors.append("POLICY_FAIL_CLOSED_FIELD_INVALID:"+k)

    env=m.get("environment") or {}
    if env.get("resource_fit_status")!="PROVED__ZERO_CASE_PUBLIC_STANDARD_RUNNER":
        errors.append("RESOURCE_FIT_STATUS_NOT_PROVED")
    if env.get("paid_external_model_or_api_allowed") is not False: errors.append("PAID_EXTERNAL_PROVIDER_NOT_FORBIDDEN")
    if env.get("larger_or_paid_runner_allowed") is not False: errors.append("PAID_RUNNER_NOT_FORBIDDEN")
    packages={(row[0],row[1]) for row in env.get("packages",[]) if isinstance(row,list) and len(row)>=2}
    for required in (("spacy","3.8.16"),("en-core-web-sm","3.8.0")):
        if required not in packages: errors.append("REPAIRED_SCORER_DEPENDENCY_MISSING:"+":".join(required))

    rv=m.get("resource_fit_verification") or {}
    if rv.get("path")!=RESOURCE_RECEIPT_PATH: errors.append("RESOURCE_FIT_RECEIPT_PATH_MISMATCH")
    if rv.get("git_blob_sha")!=RESOURCE_RECEIPT_BLOB: errors.append("RESOURCE_FIT_RECEIPT_BLOB_MISMATCH")

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
      "resource_fit_proved":passed,
      "shadow_lease_v2_bound":passed,
      "shadow_collection_authority":False,
      "fresh_reality_authority":False,
      "execution_authority":False,
      "promotion_authority":False,
      "acceptance_credit_authorized":False,
    }
