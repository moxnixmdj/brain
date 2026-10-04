from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_LIVEBENCH_IF_EXECUTION_PRECOMMIT_V3"
EXPECTED={
 "candidate":"8f99aa371061160822670fc6f5da2ce3a01cc260063330ed6e5954a2cac68c9a",
 "harness":"dcb03697e0f38d50933ca38650809fc80343737e4be3105966f2851e510c4b9e",
 "scorer":"a59cdfcfdad0efb0c5ff24e626dab23e8011ef166ef6b88740435df5452b1ebb",
 "environment":"605c8a53775d6436eb3c756386f383792c0b2cd33721ffdb8e10f33d497b14e1",
 "policy":"3e77340568dce7d6ff8f77f94de7e1fe38b85c705d88ba1067447f716a456e90",
}
REQUIRED_LEGACY={
 "livebench/gen_ground_truth_judgment.py",
 "livebench/if_runner/instruction_following_eval/evaluation_main.py",
 "livebench/if_runner/instruction_following_eval/instructions_registry.py",
 "livebench/if_runner/instruction_following_eval/instructions.py",
 "livebench/if_runner/instruction_following_eval/instructions_util.py",
 "livebench/process_results/instruction_following/utils.py",
}
REQUIRED_PACKAGES={("langdetect","1.0.9"),("immutabledict","4.3.1"),("pandas","2.3.3")}

def digest(obj: Any)->str:
    raw=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def verify_precommit(m: Mapping[str,Any])->dict[str,Any]:
    errors=[]
    if m.get("schema")!=SCHEMA: errors.append("SCHEMA_MISMATCH")
    for k in ("candidate","harness","scorer","environment","policy"):
        if digest(m.get(k))!=EXPECTED[k]: errors.append("COMPONENT_DIGEST_MISMATCH:"+k)
        if (m.get("component_sha256") or {}).get(k)!=EXPECTED[k]: errors.append("DECLARED_COMPONENT_DIGEST_MISMATCH:"+k)
    c=m.get("candidate") or {}
    if c.get("commit")!="d5de4f5808dced840da34d051e3f9a5ff06e2e54": errors.append("CANDIDATE_COMMIT_MISMATCH")
    if c.get("tree")!="fd39e966d4686c7317b9a1558b360eb0c58ad76f": errors.append("CANDIDATE_TREE_MISMATCH")
    s=m.get("scorer") or {}
    if s.get("dispatch_cutoff")!="2025-11-25": errors.append("DISPATCH_CUTOFF_MISMATCH")
    if s.get("dispatch_rule")!="category == instruction_following AND livebench_release_date < 2025-11-25 => legacy instruction_following_process_results; otherwise current IFBench path": errors.append("DISPATCH_RULE_MISMATCH")
    paths={x[0] for x in s.get("verifier_files",[]) if isinstance(x,list) and len(x)==2}
    if not REQUIRED_LEGACY.issubset(paths): errors.append("LEGACY_SCORER_CLOSURE_INCOMPLETE")
    env=m.get("environment") or {}
    pkgs={(x[0],x[1]) for x in env.get("packages",[]) if isinstance(x,list) and len(x)>=2}
    if not REQUIRED_PACKAGES.issubset(pkgs): errors.append("LEGACY_ENVIRONMENT_EXTENSION_INCOMPLETE")
    if env.get("paid_external_model_or_api_allowed") is not False: errors.append("PAID_EXTERNAL_PROVIDER_NOT_FORBIDDEN")
    if env.get("larger_or_paid_runner_allowed") is not False: errors.append("PAID_RUNNER_NOT_FORBIDDEN")
    if env.get("resource_fit_status")!="LEGACY_EXTENSION_ZERO_CASE_PUBLIC_RUNNER_VERIFICATION_REQUIRED": errors.append("LEGACY_EXTENSION_PREFLIGHT_MUST_REMAIN_OPEN")
    x=m.get("case_exposure") or {}
    if x.get("prior_failed_attempt_brain_inferences")!=0: errors.append("PRIOR_BRAIN_INFERENCE_COUNT_DRIFT")
    if x.get("prior_failed_attempt_score_exists") is not False: errors.append("PRIOR_SCORE_MUST_NOT_EXIST")
    for f in ("repair_design_terminal_prompt_content_used","repair_design_candidate_response_used","repair_design_score_used"):
        if x.get(f) is not False: errors.append("REPAIR_CONTAMINATION:"+f)
    passed=not errors
    return {
      "schema":SCHEMA,
      "precommit_pass":passed,
      "errors":errors,
      "component_sha256":dict(EXPECTED),
      "candidate_unchanged":passed,
      "legacy_dispatch_bound":passed,
      "legacy_environment_preflight_proved":False,
      "terminal_cases_consumed_this_epoch":0,
      "execution_authority":False,
      "promotion_authority":False,
      "fresh_reality_authority":False,
      "acceptance_credit_authorized":False,
    }
