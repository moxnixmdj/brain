from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import secrets
import shutil
import tempfile
from typing import Any, Mapping

from canonical.runtime import d_finality_execution_epoch_v1 as d_epoch
from canonical.runtime import d_finality_canonical_resolver_v1 as resolver
from canonical.runtime import d_finality_zero_ambient_frontdoor_v1 as frontdoor
from canonical.runtime import zero_ambient_namespace_launcher_v1 as zero_ambient

SCHEMA="PROJECT_BRAIN_D_FINAL_DECISION_VERIFY_PHYSICAL_CANARY_V1"
CID="bound:decision.synthesis.verify.stdlib"
OPERATIVE="decision.synthesis.verify.stdlib"
POLICY_PATH="canonical/governance/D_FINALITY_POLICY_V1.json"
CERT_PATH="canonical/verification/D_FINAL_DECISION_VERIFY_PHYSICAL_CANARY_CERTIFICATE.json"
PREFIX="canonical/astra_runtime/tmp/d-final-live/"

MATERIAL_PATHS=(
    "canonical/runtime/d_finality_zero_ambient_frontdoor_v1.py",
    "canonical/runtime/d_finality_zero_ambient_child_v1.py",
    "canonical/runtime/d_finality_canonical_resolver_v1.py",
    "canonical/runtime/d_finality_execution_epoch_v1.py",
    "canonical/runtime/zero_ambient_namespace_launcher_v1.py",
    "canonical/runtime/d_final_stdlib_bound_executor_v1.py",
    "canonical/runtime/bound_capability_execution_verifier_v1.py",
    "canonical/runtime/capability_planner.py",
    "canonical/runtime/capability_execution_trace_capsule_v1.py",
    "canonical/runtime/composition_state_capsule_v1.py",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
    "canonical/runtime/bound_capabilities/evidence_decision_verify.py",
)
PROVIDER_THEOREM="canonical/verification/D_FINAL_STDLIB_BOUND_PROVIDER_THEOREM_20261009_V1.json"
MEMBER_THEOREM="canonical/verification/D_FINAL_DECISION_VERIFY_MEMBER_THEOREM_20261009_V1.json"


class CanaryError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _sha_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: pathlib.Path, value: Mapping[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(
        json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False)+"\n",
        encoding="utf-8",
    )


def _copy_materials(source: pathlib.Path, target: pathlib.Path) -> list[dict[str,str]]:
    rows=[]
    for rel in MATERIAL_PATHS:
        src=source/rel
        if not src.is_file():
            raise CanaryError("MATERIAL_SOURCE_MISSING:"+rel)
        dst=target/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(src.read_bytes())
        rows.append({"path":rel,"git_blob_sha":d_epoch.git_blob_sha_file(src)})
    return rows


def _policy(source: pathlib.Path, target: pathlib.Path) -> tuple[dict[str,Any],str]:
    src=source/POLICY_PATH
    if not src.is_file():
        raise CanaryError("POLICY_SOURCE_MISSING")
    policy=json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(policy,Mapping):
        raise CanaryError("POLICY_NOT_OBJECT")
    policy=dict(policy)
    expected=d_epoch.policy_sha256(policy)
    if policy.get("policy_sha256")!=expected:
        raise CanaryError("POLICY_SELF_DIGEST_MISMATCH")
    dst=target/POLICY_PATH
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes(src.read_bytes())
    return policy,d_epoch.git_blob_sha_file(dst)


def _proof_basis(source: pathlib.Path) -> dict[str,Any]:
    provider_path=source/PROVIDER_THEOREM
    member_path=source/MEMBER_THEOREM
    provider=json.loads(provider_path.read_text(encoding="utf-8"))
    member=json.loads(member_path.read_text(encoding="utf-8"))
    if "VERIFIED_PROVIDER_THEOREM" not in str(provider.get("status") or ""):
        raise CanaryError("PROVIDER_THEOREM_NOT_VERIFIED")
    if "VERIFIED_MEMBER_MATERIAL_THEOREM" not in str(member.get("status") or ""):
        raise CanaryError("MEMBER_THEOREM_NOT_VERIFIED")
    if str(member.get("capability_id") or "")!=CID:
        raise CanaryError("MEMBER_THEOREM_CAPABILITY_MISMATCH")
    return {
      "provider_theorem_sha256":_sha_file(provider_path),
      "member_theorem_sha256":_sha_file(member_path),
      "provider_theorem_git_blob_sha":d_epoch.git_blob_sha_file(provider_path),
      "member_theorem_git_blob_sha":d_epoch.git_blob_sha_file(member_path),
    }


def _row_contract() -> dict[str,Any]:
    return {
      "capability_id":CID,
      "physical_profile":frontdoor.PROFILE,
      "physical_dispatch_kind":"D_FINAL_STDLIB_BOUND_EXECUTOR_V1",
      "dynamic_input_policy":{
        "schema":frontdoor.DYNAMIC_INPUT_SCHEMA,
        "allowed_prefixes":[PREFIX],
        "allowed_extensions":[".json"],
        "max_files":2,
        "max_total_bytes":1_000_000,
        "max_file_bytes":500_000,
      },
      "allowed_request_keys":["input_path","result_path"],
      "request_path_fields":["input_path","result_path"],
      "zero_ambient_launcher_git_blob_sha":d_epoch.git_blob_sha_file(
          pathlib.Path(zero_ambient.__file__).resolve()
      ),
    }


def _build_authority(
    source: pathlib.Path,
    target: pathlib.Path,
) -> tuple[dict[str,Any],dict[str,Any],dict[str,Any]]:
    materials=_copy_materials(source,target)
    policy,policy_blob=_policy(source,target)
    basis=_proof_basis(source)
    row_contract=_row_contract()

    bound_raw=(source/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_bytes()
    registry_snapshot_root=hashlib.sha256(bound_raw).hexdigest()
    state_snapshot_root=_sha({
      "mutable_runtime_state":"NONE",
      "scope":"D_FINAL_STDLIB_DECISION_VERIFY_PHYSICAL_CANARY_V1",
    })
    contract=frontdoor.capability_contract(CID,row_contract)
    cert={
      "schema":d_epoch.CERT_SCHEMA,
      "status":"VERIFIED_D_FINAL",
      "scope":"PHYSICAL_ZERO_AMBIENT_CANARY_ONLY__NOT_CANONICAL_LIVE_AUTHORITY",
      "canary_only":True,
      "live_ownership_authority":False,
      "capability_id":CID,
      "capability_contract_sha256":d_epoch.sha256_json(contract),
      "policy_sha256":d_epoch.policy_sha256(policy),
      "registry_snapshot_root":registry_snapshot_root,
      "state_snapshot_root":state_snapshot_root,
      "materials":materials,
      "material_closure_root":d_epoch.material_closure_root(materials),
      "allowed_capability_ids":[CID],
      "allowed_knowledge_channels":[],
      "allowed_effect_channels":[],
      "donor_authority_zero":True,
      "fresh_replay_pass":True,
      "independent_replay_pass":True,
      "knowledge_capability_nonsmuggling_pass":True,
      "undeclared_dependency_count":0,
      "declared_substrate":[
        "CPYTHON_3_X_STDLIB",
        "LINUX_OS_SUBSTRATE",
        "ZERO_AMBIENT_NAMESPACE_LAUNCHER_V1",
        "READ_ONLY_CANONICAL_JSON_INPUTS",
      ],
      "evidence":{
        **basis,
        "component_replay_basis":"TWO_INDEPENDENT_ZERO_AMBIENT_CARRIERS",
        "physical_frontdoor_current_path_canary_pending":True,
      },
      "hard_nonclaims":[
        "NO_CANONICAL_LIVE_OWNERSHIP_CREDIT",
        "NO_TERMINAL_CREDIT",
      ],
    }
    cert["certificate_sha256"]=d_epoch.certificate_sha256(cert)
    cert_path=target/CERT_PATH
    _write_json(cert_path,cert)
    epoch=d_epoch.verify_certificate(cert,policy=policy,repo_root=target)

    child=target/frontdoor.CHILD_PATH
    row={
      **row_contract,
      "zero_ambient_child_git_blob_sha":d_epoch.git_blob_sha_file(child),
      "status":"VERIFIED_D_FINAL_CURRENT",
      "d_certificate_sha256":cert["certificate_sha256"],
      "material_certificate_sha256":basis["member_theorem_sha256"],
      "provider_theorem_sha256":basis["provider_theorem_sha256"],
      "policy_sha256":policy["policy_sha256"],
      "execution_epoch_sha256":epoch.epoch_sha256,
      "material_closure_root":epoch.material_closure_root,
      "fresh_replay_pass":True,
      "independent_replay_pass":True,
      "donor_authority_zero":True,
      "undeclared_dependency_count":0,
      "certificate_path":CERT_PATH,
      "policy_path":POLICY_PATH,
      "certificate_git_blob_sha":d_epoch.git_blob_sha_file(cert_path),
      "policy_git_blob_sha":policy_blob,
      "canary_only":True,
      "live_ownership_authority":False,
    }
    registry={
      "schema":resolver.REGISTRY_SCHEMA,
      "status":"ACTIVE_FAIL_CLOSED",
      "default":"NOT_D_FINAL_UNLESS_EXACT_CURRENT_ROW",
      "scope":"NONCANONICAL_PHYSICAL_CANARY_ONLY",
      "rows":[row],
    }
    _write_json(target/resolver.DEFAULT_REGISTRY,registry)
    return row,cert,{
      "certificate_sha256":cert["certificate_sha256"],
      "policy_sha256":policy["policy_sha256"],
      "execution_epoch_sha256":epoch.epoch_sha256,
      "material_closure_root":epoch.material_closure_root,
      **basis,
    }


def _fresh_problem_result() -> tuple[dict[str,Any],dict[str,Any],str]:
    nonce=secrets.token_hex(24)
    group_a="ga-"+nonce
    group_b="gb-"+nonce
    problem={
      "schema":"PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
      "decision_id":"D-FINAL-PHYSICAL-"+nonce,
      "question":"Select the stronger fresh route "+nonce,
      "alternatives":[{"id":"A","label":"A"},{"id":"B","label":"B"}],
      "constraints":[
        {"id":"ca-"+nonce,"alternative":"A","required":True,"state":"SATISFIED","description":"fresh","provenance":[{"source":"canary","ref":"ca-"+nonce}]},
        {"id":"cb-"+nonce,"alternative":"B","required":True,"state":"SATISFIED","description":"fresh","provenance":[{"source":"canary","ref":"cb-"+nonce}]},
      ],
      "evidence":[
        {"id":"ea-"+nonce,"alternative":"A","relation":"SUPPORTS","confidence":0.91,"strength":1.0,"independence_group":group_a,"claim":"strong","provenance":[{"source":"canary","ref":"ea-"+nonce}]},
        {"id":"eb-"+nonce,"alternative":"B","relation":"SUPPORTS","confidence":0.51,"strength":1.0,"independence_group":group_b,"claim":"weak","provenance":[{"source":"canary","ref":"eb-"+nonce}]},
      ],
      "policy":{
        "minimum_support_ratio":0.6,
        "maximum_conflict_ratio":0.5,
        "minimum_independent_support_groups":1,
        "minimum_net_margin":0.1,
      },
    }
    result={
      "schema":"PROJECT_BRAIN_TYPED_DECISION_RESULT_V1",
      "decision_id":problem["decision_id"],
      "input_sha256":_sha(problem),
      "status":"DECIDED",
      "selected_alternative":"A",
      "model_dependency_count":0,
      "rankings":[
        {
          "alternative":"A",
          "constraint_state":"ADMISSIBLE",
          "violated_constraints":[],
          "unknown_constraints":[],
          "support_score":0.91,
          "contradiction_score":0.0,
          "net_score":0.91,
          "support_ratio":1.0,
          "conflict_ratio":0.0,
          "independent_support_groups":[group_a],
          "independent_contradiction_groups":[],
          "contributing_evidence":["ea-"+nonce],
          "eligible":True,
        },
        {
          "alternative":"B",
          "constraint_state":"ADMISSIBLE",
          "violated_constraints":[],
          "unknown_constraints":[],
          "support_score":0.51,
          "contradiction_score":0.0,
          "net_score":0.51,
          "support_ratio":1.0,
          "conflict_ratio":0.0,
          "independent_support_groups":[group_b],
          "independent_contradiction_groups":[],
          "contributing_evidence":["eb-"+nonce],
          "eligible":True,
        },
      ],
      "trace":[
        {"step":"validate"},
        {"step":"constraints"},
        {"step":"evidence"},
        {"step":"select"},
      ],
    }
    return problem,result,nonce


def _request(problem: Mapping[str,Any], result: Mapping[str,Any]) -> dict[str,Any]:
    input_path=PREFIX+"problem.json"
    result_path=PREFIX+"result.json"
    return {
      "input_path":input_path,
      "result_path":result_path,
      "d_input_files":[
        {"path":input_path,"json":dict(problem)},
        {"path":result_path,"json":dict(result)},
      ],
    }


def run_canary(repo_root: str|pathlib.Path) -> dict[str,Any]:
    source=pathlib.Path(repo_root).resolve()
    with tempfile.TemporaryDirectory(prefix="brain-d-final-physical-canary-") as td:
        root=pathlib.Path(td)
        row,cert,identity=_build_authority(source,root)

        problem,result,nonce=_fresh_problem_result()
        valid=frontdoor.run(_request(problem,result),capability_id=CID,repo_root=root)
        valid_pass=(
            valid.get("pass") is True
            and valid.get("physical_zero_ambient_enforced") is True
            and valid.get("material_effects_committed")==0
            and (valid.get("child_receipt") or {}).get("post_execution_material_rehash_pass") is True
            and (valid.get("child_receipt") or {}).get("post_execution_dynamic_input_rehash_pass") is True
            and ((valid.get("result") or {}).get("result") or {}).get("verified") is True
        )

        tampered=copy.deepcopy(result)
        tampered["selected_alternative"]="B"
        bad=frontdoor.run(_request(problem,tampered),capability_id=CID,repo_root=root)
        tamper_rejected=bad.get("pass") is False

        adapter=root/"canonical/runtime/bound_capabilities/evidence_decision_verify.py"
        original=adapter.read_bytes()
        adapter.write_bytes(original+b"\n# canary drift\n")
        drift_rejected=False
        drift_reason=None
        try:
            frontdoor.run(_request(problem,result),capability_id=CID,repo_root=root)
        except Exception as exc:
            drift_reason=type(exc).__name__+":"+str(exc)
            drift_rejected="MATERIAL_BLOB_DRIFT" in str(exc)
        finally:
            adapter.write_bytes(original)

        checks={
          "valid_physical_execution_pass":valid_pass,
          "tampered_result_rejected":tamper_rejected,
          "certified_material_drift_rejected_before_execution":drift_rejected,
          "certificate_identity_matches":valid.get("certificate_sha256")==identity["certificate_sha256"],
          "execution_epoch_identity_matches":valid.get("execution_epoch_sha256")==identity["execution_epoch_sha256"],
          "material_closure_identity_matches":valid.get("material_closure_root")==identity["material_closure_root"],
          "dynamic_input_count_two":valid.get("dynamic_input_count")==2,
        }
        passed=all(checks.values())
        return {
          "schema":SCHEMA,
          "status":"PASS__PHYSICAL_ZERO_AMBIENT_D_FINAL_CANARY" if passed else "FAIL",
          "pass":passed,
          "capability_id":CID,
          "fresh_nonce_sha256":hashlib.sha256(nonce.encode()).hexdigest(),
          "problem_sha256":_sha(problem),
          "result_sha256":_sha(result),
          "identity":identity,
          "checks":checks,
          "valid_execution":{
            "launcher_git_blob_sha":valid.get("launcher_git_blob_sha"),
            "child_git_blob_sha":valid.get("child_git_blob_sha"),
            "launcher_policy_sha256":valid.get("launcher_policy_sha256"),
            "broker_sha256":valid.get("broker_sha256"),
            "physical_zero_ambient_enforced":valid.get("physical_zero_ambient_enforced"),
            "material_effects_committed":valid.get("material_effects_committed"),
          },
          "tamper_status":bad.get("status"),
          "tamper_child_reason":(bad.get("child_receipt") or {}).get("reason"),
          "drift_reason":drift_reason,
          "canonical_ownership_credit":False,
          "terminal_credit":False,
        }


if __name__=="__main__":
    root=pathlib.Path(__file__).resolve().parents[2]
    print(json.dumps(run_canary(root),sort_keys=True))
