"""R6 execution-leaf property-truth verifier.

Reuses the independently verified frozen V7 R6 evidence-grounding binding and
challenges its exact runtime semantics. Grants only the R6 execution leaf.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_r6_root_subject_binding_verify_v1 as base

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R6_EXECUTION_PROPERTY_TRUTH_V1"
ROOT_ID="R6_EVIDENCE_GROUNDING_DEPENDENCE"
LEAF_ID="PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION"
MANIFEST_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json"
MANIFEST_BLOB="a7cad32c9fd969ff2c3857bb924c7bd746237ec2"
WHOLE_SCOPE_PATH="canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json"
WHOLE_SCOPE_BLOB="4c2d40a262f18f34bb35f94b59660d60972d45ef"
R6_BINDING_RECEIPT_PATH="canonical/verification/PROFESSIONAL_QUALITY_R6_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1.json"
R6_BINDING_RECEIPT_BLOB="abb4a251345e2701dc42578a1695f5e59f4bb665"
BASE_RUNTIME_PATH="canonical/runtime/professional_quality_r6_root_subject_binding_verify_v1.py"
BASE_RUNTIME_BLOB="a739946e5b467a27bd8ecb93d3181d9025a3abeb"
BASE_TEST_PATH="canonical/tests/test_professional_quality_r6_root_subject_binding_verify_v1.py"
BASE_TEST_BLOB="146642940e955fb7fc0e25926a7f36a95fb35896"
MANIFEST_ACCEPTANCE="RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"

def _blob(path: Path) -> str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "root_id":ROOT_ID,
        "leaf_id":LEAF_ID,
        "leaf_property_truth_authority":False,
        "semantic_truth_authority":False,
        "r6_root_closed":False,
        "global_evidence_completeness_proved":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        **extra,
    }

def _read_json_exact(root: Path, rel: str, expected_blob: str) -> tuple[dict[str, Any] | None, str | None]:
    p=(root/rel).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError:
        return None, "OUTSIDE_ROOT:"+rel
    if not p.is_file() or p.is_symlink():
        return None, "FILE_INVALID:"+rel
    if _blob(p)!=expected_blob:
        return None, "BLOB_STALE:"+rel
    try:
        value=json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None, "JSON_INVALID:"+rel
    if not isinstance(value,dict):
        return None, "DOCUMENT_INVALID:"+rel
    return value,None

def _load_base_docs(root: Path):
    binding=json.loads((root/base.BINDING_PATH).read_text(encoding="utf-8"))
    subject=json.loads((root/base.SUBJECT_PATH).read_text(encoding="utf-8"))
    docs={k:json.loads((root/path).read_text(encoding="utf-8")) for k,(path,_sha) in base.REFS.items()}
    return binding,subject,docs

def _row(case_id: str, observed: Mapping[str, Any], expected_reason: str | None) -> dict[str, Any]:
    return {
        "case_id":case_id,
        "observed_pass":observed.get("pass") is True,
        "observed_status":observed.get("status"),
        "observed_reason":observed.get("reason"),
        "expected_reason":expected_reason,
    }

def run_challenges(*, repo_root: str | Path | None=None) -> list[dict[str, Any]]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    binding,subject,docs=_load_base_docs(root)
    rows=[]

    positive=base.evaluate_documents(deepcopy(binding),deepcopy(subject),deepcopy(docs))
    rows.append(_row("POSITIVE_EXACT_FROZEN_R6_BINDING",positive,None))

    b=deepcopy(binding); b["subject_sha256"]="bad"
    rows.append(_row("NEAR_MISS_WRONG_SUBJECT_TUPLE",base.evaluate_documents(b,deepcopy(subject),deepcopy(docs)),"SUBJECT_TUPLE_MISMATCH"))

    s=deepcopy(subject)
    s["system_material"]["components"]=[
        x for x in s["system_material"]["components"]
        if x.get("path")!="canonical/runtime/professional_quality_leaf_binder_v2.py"
    ]
    rows.append(_row("ADVERSARIAL_MISSING_SUBJECT_EVIDENCE_COMPONENT",base.evaluate_documents(deepcopy(binding),s,deepcopy(docs)),"REQUIRED_EVIDENCE_COMPONENTS_NOT_IN_SUBJECT"))

    d=deepcopy(docs)
    entry=next(x for x in d["scoped_evidence_registry"]["entries"] if x.get("root_id")==ROOT_ID)
    entry["global_root_closure"]=True
    rows.append(_row("ADVERSARIAL_SCOPE_WIDENING",base.evaluate_documents(deepcopy(binding),deepcopy(subject),d),"R6_SCOPE_WIDENING_FORBIDDEN"))

    b=deepcopy(binding); b["evidence_status_string_authority"]=True
    rows.append(_row("ADVERSARIAL_STATUS_STRING_AUTHORITY",base.evaluate_documents(b,deepcopy(subject),deepcopy(docs)),"STATUS_STRING_AUTHORITY_FORBIDDEN"))

    d=deepcopy(docs); d["leaf_evidence_registry"]["admission_law"]="manifest status decides everything"
    rows.append(_row("ADVERSARIAL_LEAF_ADMISSION_LAW_DRIFT",base.evaluate_documents(deepcopy(binding),deepcopy(subject),d),"LEAF_ADMISSION_LAW_MISSING"))

    d=deepcopy(docs)
    premise="RECEIPT_VERIFICATION_BASIS_MUST_BE_CONTENT_ADDRESSED_AND_CURRENT"
    d["leaf_binder_verification"]["proved"]=[x for x in d["leaf_binder_verification"].get("proved",[]) if x!=premise]
    rows.append(_row("ADVERSARIAL_LEAF_BINDER_PREMISE_REMOVAL",base.evaluate_documents(deepcopy(binding),deepcopy(subject),d),"LEAF_BINDER_PREMISE_MISSING"))

    d=deepcopy(docs)
    premise="CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY_AT_V7_ENTRY"
    d["proof_bound_step_verification"]["proves"]=[x for x in d["proof_bound_step_verification"].get("proves",[]) if x!=premise]
    rows.append(_row("ADVERSARIAL_PROOF_BOUND_STEP_PREMISE_REMOVAL",base.evaluate_documents(deepcopy(binding),deepcopy(subject),d),"V7_STEP_PREMISE_MISSING"))

    b=deepcopy(binding); b["execution_authority"]=True
    rows.append(_row("ADVERSARIAL_SELF_AUTHORITY_ESCALATION",base.evaluate_documents(b,deepcopy(subject),deepcopy(docs)),"BINDING_SELF_AUTHORITY_FORBIDDEN"))

    b=deepcopy(binding); b["bridge_evidence"]["leaf_binding_manifest"]["git_blob_sha"]="bad"
    rows.append(_row("ADVERSARIAL_BRIDGE_REFERENCE_DRIFT",base.evaluate_documents(b,deepcopy(subject),deepcopy(docs)),"BRIDGE_REF_MISMATCH"))
    return rows

def verify(*, repo_root: str | Path | None=None) -> dict[str, Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    for rel,sha in ((BASE_RUNTIME_PATH,BASE_RUNTIME_BLOB),(BASE_TEST_PATH,BASE_TEST_BLOB)):
        p=root/rel
        if not p.is_file() or _blob(p)!=sha:
            return _fail("BASE_VERIFIER_BYTES_STALE",path=rel)

    manifest,err=_read_json_exact(root,MANIFEST_PATH,MANIFEST_BLOB)
    if err:return _fail(err)
    scope,err=_read_json_exact(root,WHOLE_SCOPE_PATH,WHOLE_SCOPE_BLOB)
    if err:return _fail(err)
    receipt,err=_read_json_exact(root,R6_BINDING_RECEIPT_PATH,R6_BINDING_RECEIPT_BLOB)
    if err:return _fail(err)

    root_row=next((x for x in manifest.get("roots",[]) if isinstance(x,dict) and x.get("root_id")==ROOT_ID),None)
    if not isinstance(root_row,dict):
        return _fail("R6_ROOT_MANIFEST_ENTRY_MISSING")
    leaf=(root_row.get("execution_leaf") or {})
    if leaf.get("id")!=LEAF_ID or leaf.get("acceptance")!=MANIFEST_ACCEPTANCE:
        return _fail("R6_EXECUTION_MANIFEST_ACCEPTANCE_MISMATCH")
    root_contract=root_row.get("contract")
    if not isinstance(root_contract,str) or not root_contract:
        return _fail("R6_ROOT_CONTRACT_MISSING")

    whole_scope_complete=(
        scope.get("independent_replay",{}).get("scope_complete_count")==24
        and scope.get("independent_replay",{}).get("leaf_count")==24
        and "24_OF_24_SCOPE_COMPLETE" in str(scope.get("status",""))
    )
    if not whole_scope_complete:
        return _fail("WHOLE_LEAF_SCOPE_NOT_COMPLETE")

    historical_receipt_pass=(
        str(receipt.get("status","")).startswith("PASS__")
        and receipt.get("root_subject_binding_authority") is True
        and "NO_GLOBAL_R6_ROOT_CLOSURE" in set(receipt.get("hard_nonclaims") or [])
        and receipt.get("terminal_authority") is False
        and receipt.get("exact_blobs",{}).get("verifier")==BASE_RUNTIME_BLOB
        and receipt.get("exact_blobs",{}).get("tests")==BASE_TEST_BLOB
        and receipt.get("exact_blobs",{}).get("binding")==base.BINDING_BLOB
    )
    if not historical_receipt_pass:
        return _fail("HISTORICAL_R6_BINDING_RECEIPT_INVALID")

    base_result=base.verify(repo_root=root)
    if base_result.get("pass") is not True:
        return _fail("EXACT_FROZEN_R6_BINDING_REPLAY_FAILED",base_result=base_result)

    cases=run_challenges(repo_root=root)
    if len(cases)!=10:
        return _fail("R6_CHALLENGE_CARDINALITY_INVALID",cases=cases)
    for row in cases:
        if row["case_id"].startswith("POSITIVE_"):
            if row["observed_pass"] is not True:
                return _fail("R6_POSITIVE_CHALLENGE_FAILED",case=row,cases=cases)
        else:
            if row["observed_pass"] is not False or row["observed_reason"]!=row["expected_reason"]:
                return _fail("R6_ADVERSARIAL_CHALLENGE_MISMATCH",case=row,cases=cases)

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__R6_EXECUTION_LEAF_PROPERTY_TRUTH__10_OBSERVED_CASES__FROZEN_R6_BINDING_REPLAY__ZERO_ROOT_QUALITY_OR_TERMINAL_CREDIT",
        "root_id":ROOT_ID,
        "leaf_id":LEAF_ID,
        "manifest_acceptance":MANIFEST_ACCEPTANCE,
        "root_contract":root_contract,
        "whole_leaf_scope_complete":True,
        "historical_r6_binding_receipt_pass":True,
        "observed_case_count":len(cases),
        "challenge_cases":cases,
        "leaf_property_truth_authority":True,
        "semantic_truth_authority":False,
        "r6_root_closed":False,
        "global_evidence_completeness_proved":False,
        "real_task_all_evidence_receipts_proved":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
