"""Independent verifier for R3 realization binding on the frozen V7 professional subject."""
from __future__ import annotations

import base64
import hashlib
import json
from hashlib import sha1
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_step_binding_authority_v1 as step_authority

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_VERIFY_V1"
ROOT_ID="R3_REALIZATION_OBSERVATION"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V1.json"
EXPECTED_BINDING_BLOB="211e264d445810e93fcca91c18bcbeea2b279e54"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
STEP_ID="RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS"
RUN_CONTEXT_SHA256="sha256:0dc8d549586a7d53801b8d825ce86abdf708d6b60fc98c20f3486e3158a4b7a3"
EVIDENCE_SHA256="176234b80f16f636c3573f50fe538a2b5208a8617755b8a18f5a2df825e0e20e"

REFS={
    "realization_semantic_verification":(
        "canonical/verification/PROFESSIONAL_QUALITY_R3_REALIZATION_SEMANTIC_VERIFY_20261010_V1.json",
        "3c9a6f03c9dfb7597cdb7c5ca01e9eaf66a596e0",
    ),
    "scoped_integration_verification":(
        "canonical/verification/PROFESSIONAL_QUALITY_R3_SEMANTIC_SCOPED_INTEGRATION_VERIFY_20261010_V1.json",
        "86efb5396f90a4182d90029b47868123226fa05c",
    ),
    "native_render_public_verification":(
        "canonical/verification/NATIVE_ARTIFACT_RENDER_PRESERVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
        "1a0b4ca6627aaf28eb25f6990682e87319d14d6d",
    ),
    "proof_bound_v7_step_execution":(
        "canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V7_PROOF_BOUND_STEP_VERIFY_20261010_V1.json",
        "b7a9df36780513ad73fd14c6a2756c8474d8434d",
    ),
    "durable_realization_evidence":(
        "canonical/evidence/PROFESSIONAL_V7_R3_DURABLE_REALIZATION_EVIDENCE_20261010_V1.json",
        "f18329cac5c702f3503863819b5e3c92cb16d382",
    ),
    "render_step_receipt":(
        "canonical/governance/PROFESSIONAL_V7_R3_RENDER_STEP_BINDING_20261010_V1.json",
        "276ffbda0ecc68aa65228386d9ca19b3a0bc6c9b",
    ),
    "render_step_independent_verification":(
        "canonical/verification/PROFESSIONAL_V7_R3_RENDER_STEP_BINDING_INDEPENDENT_VERIFY_20261010_V1.json",
        "250b610205c42b8ced3c5c3eb8963dc5d770b07c",
    ),
}

def _blob(path:Path)->str:
    data=path.read_bytes()
    return sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

def _read(root:Path,path:str,sha:str)->dict[str,Any]:
    full=(root/path).resolve()
    full.relative_to(root.resolve())
    if not full.is_file() or full.is_symlink():
        raise ValueError("FILE_INVALID:"+path)
    if _blob(full)!=sha:
        raise ValueError("BLOB_STALE:"+path)
    doc=json.loads(full.read_text(encoding="utf-8"))
    if not isinstance(doc,dict):
        raise ValueError("DOCUMENT_INVALID:"+path)
    return doc

def _sha256_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "root_id":ROOT_ID,
        "root_subject_binding_authority":False,
        "global_subject_identity_authority":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        **extra,
    }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        binding=_read(root,BINDING_PATH,EXPECTED_BINDING_BLOB)
        if binding.get("schema")!="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1":
            return _fail("BINDING_SCHEMA_INVALID")
        if binding.get("root_id")!=ROOT_ID:
            return _fail("BINDING_ROOT_MISMATCH")
        if binding.get("subject_kind")!="DECLARED_SYSTEM" or binding.get("subject_id")!=SUBJECT_ID or binding.get("subject_sha256")!=SUBJECT_SHA256:
            return _fail("SUBJECT_TUPLE_MISMATCH")
        for field in (
            "root_subject_binding_authority","global_subject_identity_authority",
            "semantic_truth_authority","execution_authority","quality_authority",
            "acceptance_authority","promotion_authority","terminal_authority",
        ):
            if binding.get(field) is not False:
                return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN:"+field)

        sref=binding.get("subject") or {}
        if sref.get("path")!=SUBJECT_PATH or sref.get("git_blob_sha")!=SUBJECT_BLOB:
            return _fail("SUBJECT_REFERENCE_MISMATCH")
        subject=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
        if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA256:
            return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
        if subject.get("dependency_closure_complete") is not True:
            return _fail("SUBJECT_DEPENDENCY_CLOSURE_UNPROVED")

        bridge=binding.get("bridge_evidence")
        if not isinstance(bridge,Mapping):
            return _fail("BRIDGE_EVIDENCE_INVALID")
        docs={}
        for key,(path,sha) in REFS.items():
            ref=bridge.get(key)
            if not isinstance(ref,Mapping) or ref.get("path")!=path or ref.get("git_blob_sha")!=sha:
                return _fail("BRIDGE_REFERENCE_MISMATCH:"+key)
            docs[key]=_read(root,path,sha)

        sem=docs["realization_semantic_verification"]
        if not str(sem.get("status") or "").startswith("PASS__") or sem.get("terminal_authority") is not False:
            return _fail("R3_SEMANTIC_VERIFICATION_INSUFFICIENT")
        integ=docs["scoped_integration_verification"]
        if not str(integ.get("status") or "").startswith("PASS__"):
            return _fail("R3_SCOPED_INTEGRATION_INSUFFICIENT")
        render=docs["native_render_public_verification"]
        if "PASS" not in str(render.get("status") or ""):
            return _fail("NATIVE_RENDER_VERIFICATION_INSUFFICIENT")
        v7=docs["proof_bound_v7_step_execution"]
        if not str(v7.get("status") or "").startswith("PASS__"):
            return _fail("V7_STEP_PROVENANCE_VERIFICATION_INSUFFICIENT")
        if "CALLER_STEP_RESULTS_FORBIDDEN" not in str(v7.get("status") or ""):
            return _fail("V7_CALLER_STEP_NONAUTHORITY_UNPROVED")

        evidence=docs["durable_realization_evidence"]
        if evidence.get("evidence_sha256")!=EVIDENCE_SHA256 or evidence.get("run_context_sha256")!=RUN_CONTEXT_SHA256:
            return _fail("DURABLE_EVIDENCE_IDENTITY_MISMATCH")
        ev_subject=evidence.get("subject") or {}
        if ev_subject.get("subject_id")!=SUBJECT_ID or ev_subject.get("subject_sha256")!=SUBJECT_SHA256 or ev_subject.get("git_blob_sha")!=SUBJECT_BLOB:
            return _fail("DURABLE_EVIDENCE_SUBJECT_MISMATCH")
        iv=evidence.get("independent_verification")
        if not isinstance(iv,Mapping) or iv.get("pass") is not True:
            return _fail("PUBLIC_INDEPENDENT_VERIFICATION_NOT_PASS")
        for field in ("independent_verified","semantic_preservation_verified","evidence_scope_verified"):
            if iv.get(field) is not True:
                return _fail("PUBLIC_VERIFICATION_PREMISE_UNPROVED:"+field)
        if iv.get("producer_id")==iv.get("independent_verifier_id"):
            return _fail("PUBLIC_PRODUCER_VERIFIER_NOT_INDEPENDENT")
        if iv.get("evidence_sha256")!=EVIDENCE_SHA256 or iv.get("run_context_sha256")!=RUN_CONTEXT_SHA256:
            return _fail("PUBLIC_VERIFICATION_BINDING_MISMATCH")
        portable=iv.get("portable_evidence")
        if not isinstance(portable,Mapping):
            return _fail("PORTABLE_EVIDENCE_MISSING")
        base=dict(portable)
        claimed=base.pop("evidence_sha256",None)
        if claimed!=EVIDENCE_SHA256 or _sha256_bytes(_canon(base))!=EVIDENCE_SHA256:
            return _fail("PORTABLE_EVIDENCE_DIGEST_MISMATCH")

        for label in ("source_artifact","output_artifact"):
            row=portable.get(label)
            if not isinstance(row,Mapping):
                return _fail("PORTABLE_ARTIFACT_ROW_INVALID:"+label)
            try:
                raw=base64.b64decode(str(row.get("bytes_b64") or ""),validate=True)
            except Exception:
                return _fail("PORTABLE_ARTIFACT_BASE64_INVALID:"+label)
            if _sha256_bytes(raw)!=row.get("sha256"):
                return _fail("PORTABLE_ARTIFACT_HASH_MISMATCH:"+label)

        for label in ("source_audience_view","output_audience_view"):
            rows=portable.get(label)
            if not isinstance(rows,list) or not rows:
                return _fail("PORTABLE_AUDIENCE_ROWS_INVALID:"+label)
            for row in rows:
                if not isinstance(row,Mapping):
                    return _fail("PORTABLE_AUDIENCE_ROW_INVALID:"+label)
                try:
                    raw=base64.b64decode(str(row.get("bytes_b64") or ""),validate=True)
                except Exception:
                    return _fail("PORTABLE_AUDIENCE_BASE64_INVALID:"+label)
                if _sha256_bytes(raw)!=row.get("sha256"):
                    return _fail("PORTABLE_AUDIENCE_HASH_MISMATCH:"+label)

        durable=evidence.get("durable_bytes") or {}
        if durable.get("source_pdf_b64")!=(portable.get("source_artifact") or {}).get("bytes_b64"):
            return _fail("DURABLE_SOURCE_BYTES_MISMATCH")
        if durable.get("output_pdf_b64")!=(portable.get("output_artifact") or {}).get("bytes_b64"):
            return _fail("DURABLE_OUTPUT_BYTES_MISMATCH")
        if durable.get("source_audience_view")!=portable.get("source_audience_view") or durable.get("output_audience_view")!=portable.get("output_audience_view"):
            return _fail("DURABLE_AUDIENCE_BYTES_MISMATCH")

        step_result=step_authority.authenticate_step_binding(
            {
                "receipt":{"path":REFS["render_step_receipt"][0],"git_blob_sha":REFS["render_step_receipt"][1]},
                "verification":{"path":REFS["render_step_independent_verification"][0],"git_blob_sha":REFS["render_step_independent_verification"][1]},
            },
            behavior_id=BEHAVIOR_ID,
            subject_id=SUBJECT_ID,
            subject_sha256=SUBJECT_SHA256,
            step_id=STEP_ID,
            run_context_sha256=RUN_CONTEXT_SHA256,
            repo_root=root,
        )
        if step_result.get("pass") is not True:
            return _fail("V7_STEP_BINDING_AUTHENTICATION_FAILED",step_status=step_result.get("status"),step_reason=step_result.get("reason"))
        if step_result.get("evidence_sha256")!=EVIDENCE_SHA256:
            return _fail("V7_STEP_EVIDENCE_DIGEST_MISMATCH")

        scope=binding.get("binding_scope") or {}
        limitations=set(scope.get("limitations") or [])
        required={
            "NO_GLOBAL_R3_REALIZATION_COMPLETENESS",
            "NO_ARBITRARY_SEMANTIC_TARGET_SELECTION",
            "NO_WHOLE_OPEN_ENDED_PROFESSIONAL_ARTIFACT_CONTRACT_EQUIVALENCE",
            "NO_R4_THROUGH_R12_ROOT_SUBJECT_BINDING",
            "NO_SAME_SUBJECT_COMPOSITION_PASS",
            "NO_LIVE_DEFAULT_PROMOTION",
        }
        if not required<=limitations:
            return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
        if binding.get("actual_v7_step_receipt_proved") is not True:
            return _fail("ACTUAL_V7_STEP_RECEIPT_NOT_BOUND")

        return {
            "schema":SCHEMA,
            "pass":True,
            "status":"PASS__R3_ROOT_BOUND_TO_EXACT_V7_SUBJECT_WITH_DURABLE_ARTIFACT_AND_AUDIENCE_REALIZATION",
            "root_id":ROOT_ID,
            "subject_kind":"DECLARED_SYSTEM",
            "subject_id":SUBJECT_ID,
            "subject_sha256":SUBJECT_SHA256,
            "subject_binding_git_blob_sha":EXPECTED_BINDING_BLOB,
            "run_context_sha256":RUN_CONTEXT_SHA256,
            "evidence_sha256":EVIDENCE_SHA256,
            "root_subject_binding_authority":True,
            "global_subject_identity_authority":False,
            "global_r3_realization_completeness":False,
            "semantic_truth_authority":False,
            "execution_authority":False,
            "quality_authority":False,
            "acceptance_authority":False,
            "promotion_authority":False,
            "terminal_authority":False,
            "terminal_credit_delta":0,
            "incremental_spend_usd":0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__+":"+str(exc))

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
