from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_LIVEBENCH_IF_EXECUTION_PRECOMMIT_V2"
EXPECTED={
 "candidate":"8f99aa371061160822670fc6f5da2ce3a01cc260063330ed6e5954a2cac68c9a",
 "harness":"dcb03697e0f38d50933ca38650809fc80343737e4be3105966f2851e510c4b9e",
 "scorer":"d500c0b8ad7bcf545800a3f815123bfcc955845fba4587d783d93a4f8750cfd1",
 "environment":"4acea3a01cf7b6ac89c5134c269d7c20241cdce46f38487e6da9a3640ab49f6a",
 "policy":"3e77340568dce7d6ff8f77f94de7e1fe38b85c705d88ba1067447f716a456e90",
}
RESOURCE_RECEIPT_BLOB="8a603c1f48aad6e0fc79c2c76d2db437efde3893"
SHADOW_V2_BLOB="8a13e29ddc160ea4af62aed434fb8a1a65afb998"

def digest(obj: Any) -> str:
    raw=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def verify_precommit_v2(m: Mapping[str,Any]) -> dict[str,Any]:
    errors=[]
    if m.get("schema")!=SCHEMA:
        errors.append("SCHEMA_MISMATCH")
    for k in ("candidate","harness","scorer","environment","policy"):
        if digest(m.get(k))!=EXPECTED[k]:
            errors.append("COMPONENT_DIGEST_MISMATCH:"+k)
        if (m.get("component_sha256") or {}).get(k)!=EXPECTED[k]:
            errors.append("DECLARED_COMPONENT_DIGEST_MISMATCH:"+k)

    h=m.get("harness") or {}
    if h.get("shadow_lease_runtime_path")!="canonical/runtime/shadow_reality_lease_v2.py":
        errors.append("SHADOW_V2_RUNTIME_PATH_MISMATCH")
    if h.get("shadow_lease_runtime_git_blob_sha")!=SHADOW_V2_BLOB:
        errors.append("SHADOW_V2_RUNTIME_BLOB_MISMATCH")

    env=m.get("environment") or {}
    pkgs={(str(x[0]),str(x[1])) for x in env.get("packages") or [] if isinstance(x,list) and len(x)>=2}
    for required in (("spacy","3.8.16"),("en-core-web-sm","3.8.0")):
        if required not in pkgs:
            errors.append("MISSING_REPAIRED_SCORER_PACKAGE:"+required[0])
    if env.get("resource_fit_status")!="INDEPENDENT_ZERO_CASE_PUBLIC_RUNNER_PASS":
        errors.append("RESOURCE_FIT_STATUS_NOT_PASS")
    rv=env.get("resource_fit_verification") or {}
    if rv.get("git_blob_sha")!=RESOURCE_RECEIPT_BLOB:
        errors.append("RESOURCE_FIT_RECEIPT_BLOB_MISMATCH")
    if rv.get("positive_run_id")!=37184530130:
        errors.append("RESOURCE_FIT_POSITIVE_RUN_MISMATCH")

    exposure=m.get("case_exposure") or {}
    if exposure.get("terminal_case_content_read") is not False:
        errors.append("TERMINAL_CASE_CONTENT_READ")
    if exposure.get("terminal_cases_consumed")!=0:
        errors.append("TERMINAL_CASES_CONSUMED_NONZERO")

    passed=not errors
    return {
      "schema":SCHEMA,
      "successor_precommit_pass":passed,
      "errors":errors,
      "component_sha256":dict(EXPECTED),
      "resource_fit_truth_repair_bound":passed,
      "shadow_v2_bound":passed,
      "terminal_cases_consumed":0,
      "case_reveal_authority":False,
      "shadow_collection_authority":False,
      "fresh_reality_authority":False,
      "execution_authority":False,
      "promotion_authority":False,
      "acceptance_credit_authorized":False,
    }
