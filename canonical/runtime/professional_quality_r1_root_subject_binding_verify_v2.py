"""Independent verifier for the stronger V5 R1 professional root/subject binding."""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R1_TARGET_SPECIFICATION"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R1_ROOT_SUBJECT_BINDING_20261010_V2.json"
EXPECTED_BINDING_BLOB="710a8ad78dffb4910a50b3b67c56b22e1e2db224"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V5_DECLARED_SYSTEM_SUBJECT_20261010_V4.json"
SUBJECT_BLOB="7bce06f0f58c1406e00de4d16db5b851b4a79327"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V5_AUTHENTICATED_TARGET_SYSTEM_20261010_V4"
SUBJECT_SHA256="1837e5cdd4c56ebb27ed2feb93f81b21f119e54aee6e0527d2781b235b652b29"

EXPECTED_REFS={
 "subject_verification":("canonical/verification/PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V4_VERIFY_20261010_V1.json","29559409be6f2700a8022a09e70b37ff7d657b4f"),
 "authenticated_target_handoff":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V5_TARGET_HANDOFF_INDEPENDENT_VERIFY_20261010_V3.json","d9bd9acf085cda6c340e90cd921ca977967fc8a4"),
 "r1_target_semantics":("canonical/verification/PROFESSIONAL_QUALITY_R1_TARGET_SEMANTIC_VERIFY_20261010_V1.json","dfffdd6eff129ce7498c4e4aa8a822cd4a5cda22"),
 "r1_structural_target":("canonical/verification/PROFESSIONAL_QUALITY_R1_STRUCTURAL_TARGET_VERIFY_20261010_V1.json","dcee55ba17d15154117100de6aebd34716ad3e3e"),
}

REQUIRED_MATERIAL={
 ("canonical/runtime/professional_quality_p1_router_v5.py","8583b63571b5bfe86a473dcba1a716b98821cd5c"),
 ("canonical/runtime/general_adequate_decision_controller_v1.py","368c6ac07e8feaf1a0c880de5388b618def912e2"),
 ("canonical/runtime/professional_quality_p1_router_v4.py","8e5d473b5606251752c4968dfd35290e9b991f16"),
 ("canonical/runtime/professional_quality_p1_router_v3.py","cdb6716ac6d562d1ab222242d07aeecc5cdfac78"),
 ("canonical/runtime/professional_quality_p1_router_v2.py","bdbbc53ab1e50743869ec515a019bfc17218f126"),
 ("canonical/runtime/professional_target_semantic_certificate_v1.py","583612b0e2226053ac758683087b5c5d0f510996"),
 ("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json","ae250d5bc5da73b23600670be354ffba31e65e53"),
}

REQUIRED_GUARANTEES={
 "RAW_GOAL_AND_EXACT_DECISION_PAYLOAD_CONTENT_BINDING_REQUIRED_BEFORE_TARGET_ROUTING",
 "TARGET_INSTANCE_MAY_ENTER_ONLY_FROM_AUTHENTICATED_DECISION_PAYLOAD",
 "UNBOUND_TOP_LEVEL_TARGET_INSTANCE_SUBSTITUTION_FAILS_CLOSED",
 "TARGET_COMPILATION_STEP_SELF_ATTESTATION_FAILS_CLOSED",
 "GOAL_OR_TARGET_PAYLOAD_TAMPER_AFTER_BINDING_FAILS_CLOSED",
 "TARGET_BINDING_REQUIRES_DISTINCT_NONEMPTY_PRODUCER_AND_INDEPENDENT_VERIFIER_IDENTITIES",
 "CANONICAL_TARGET_CONTRACT_SEMANTICS_REPLAYED_BEFORE_V3_DELEGATION",
}
REQUIRED_LIMITS={
 "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS",
 "NO_CLAIM_AN_AUTHENTICATED_FULL_GOAL_BINDING_EXISTS_FOR_EVERY_INPUT",
 "NO_GLOBAL_R1_ROOT_CLOSURE",
 "NO_LIVE_DEFAULT_PROMOTION",
}


def _blob(path:Path)->str:
    data=path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode()+data).hexdigest()


def _resolve(root:Path,raw:Any)->Path|None:
    if not isinstance(raw,str) or not raw.startswith("canonical/"):
        return None
    p=(root/raw).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError:
        return None
    return p


def _read(root:Path,path:str,sha:str)->tuple[dict[str,Any]|None,str|None]:
    p=_resolve(root,path)
    if p is None or not p.is_file() or p.is_symlink():
        return None,"FILE_INVALID:"+path
    if _blob(p)!=sha:
        return None,"BLOB_STALE:"+path
    try:
        doc=json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None,"JSON_INVALID:"+path
    if not isinstance(doc,dict):
        return None,"DOCUMENT_INVALID:"+path
    return doc,None


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "root_id":ROOT_ID,"root_subject_binding_authority":False,
        "global_subject_identity_authority":False,"semantic_truth_authority":False,
        "execution_authority":False,"quality_authority":False,
        "acceptance_authority":False,"promotion_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,**extra,
    }


def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    binding,error=_read(root,BINDING_PATH,EXPECTED_BINDING_BLOB)
    if error:return _fail(error)
    assert binding is not None

    if binding.get("schema")!=BINDING_SCHEMA:return _fail("BINDING_SCHEMA_INVALID")
    if binding.get("root_id")!=ROOT_ID:return _fail("ROOT_ID_MISMATCH")
    if (
        binding.get("subject_kind")!="DECLARED_SYSTEM"
        or binding.get("subject_id")!=SUBJECT_ID
        or binding.get("subject_sha256")!=SUBJECT_SHA256
    ):
        return _fail("SUBJECT_TUPLE_MISMATCH")
    for field in ("root_subject_binding_authority","global_subject_identity_authority","terminal_authority"):
        if binding.get(field) is not False:
            return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN:"+field)

    subject_ref=binding.get("subject") or {}
    if subject_ref.get("path")!=SUBJECT_PATH or subject_ref.get("git_blob_sha")!=SUBJECT_BLOB:
        return _fail("SUBJECT_REFERENCE_MISMATCH")
    subject,error=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
    if error:return _fail(error)
    assert subject is not None
    if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA256:
        return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
    material={
        (x.get("path"),x.get("git_blob_sha"))
        for x in (subject.get("system_material") or {}).get("components",[])
        if isinstance(x,Mapping)
    }
    if not REQUIRED_MATERIAL<=material:
        return _fail("R1_LOAD_BEARING_MATERIAL_NOT_IN_SUBJECT")

    refs=binding.get("bridge_evidence")
    if not isinstance(refs,Mapping):
        return _fail("BRIDGE_EVIDENCE_INVALID")
    docs={}
    for key,(path,sha) in EXPECTED_REFS.items():
        ref=refs.get(key)
        if not isinstance(ref,Mapping) or ref.get("path")!=path or ref.get("git_blob_sha")!=sha:
            return _fail("BRIDGE_REFERENCE_MISMATCH:"+key)
        doc,error=_read(root,path,sha)
        if error:return _fail(error)
        docs[key]=doc

    sv=docs["subject_verification"]
    replay=sv.get("real_subject_replay") or {}
    if (
        replay.get("pass") is not True
        or replay.get("component_count")!=16
        or replay.get("component_currentness_verified") is not True
        or replay.get("subject_identity_verified") is not True
    ):
        return _fail("SUBJECT_VERIFICATION_INSUFFICIENT")
    if sv.get("root_subject_binding_authority") is not False:
        return _fail("SUBJECT_VERIFY_AUTHORITY_OVERCLAIM")

    handoff=docs["authenticated_target_handoff"]
    hr=handoff.get("replay") or {}
    if hr.get("total_tests_passed")!=31 or hr.get("total_tests_failed")!=0:
        return _fail("V5_HANDOFF_REPLAY_INSUFFICIENT")
    hsubject=handoff.get("subject") or {}
    if hsubject.get("git_blob_sha")!="8583b63571b5bfe86a473dcba1a716b98821cd5c":
        return _fail("V5_HANDOFF_RUNTIME_MISMATCH")
    producer=handoff.get("producer_id")
    verifier=(handoff.get("independent_verifier") or {}).get("independent_verifier_id")
    if not isinstance(producer,str) or not producer.strip():
        return _fail("V5_HANDOFF_PRODUCER_ID_MISSING")
    if not isinstance(verifier,str) or not verifier.strip() or verifier.strip()==producer.strip():
        return _fail("V5_HANDOFF_INDEPENDENCE_INVALID")
    proved=set(handoff.get("proves") or [])
    required_handoff_proofs={
        "UNBOUND_TOP_LEVEL_TARGET_INSTANCE_CANNOT_ENTER_V5",
        "CALLER_CANNOT_SELF_ATTEST_COMPILE_TARGET_SPEC_AND_HARD_CONSTRAINTS",
        "TARGET_INSTANCE_IS_EXTRACTED_ONLY_FROM_EXACT_DECISION_PAYLOAD_BOUND_TO_EXACT_RAW_GOAL",
        "GOAL_OR_DECISION_PAYLOAD_TAMPER_BREAKS_CONTENT_BINDING_BEFORE_V4",
        "PRODUCER_AND_VERIFIER_IDENTITIES_MUST_BE_DISTINCT",
    }
    if not required_handoff_proofs<=proved:
        return _fail("V5_HANDOFF_PROOF_SET_INSUFFICIENT")
    if handoff.get("quality_authority") is not False or handoff.get("terminal_authority") is not False:
        return _fail("V5_HANDOFF_AUTHORITY_OVERCLAIM")

    sem=docs["r1_target_semantics"]
    sem_scope=sem.get("claim_scope") or {}
    if sem.get("replay",{}).get("tests_passed")!=5:
        return _fail("R1_SEMANTIC_REPLAY_INSUFFICIENT")
    if sem_scope.get("kind")!="EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS":
        return _fail("R1_SEMANTIC_SCOPE_INVALID")
    if "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS" not in set(sem_scope.get("limitations") or []):
        return _fail("R1_SEMANTIC_SCOPE_TOO_BROAD")

    structural=docs["r1_structural_target"]
    if structural.get("replay",{}).get("tests_passed")!=21:
        return _fail("R1_STRUCTURAL_REPLAY_INSUFFICIENT")
    if structural.get("current_truth",{}).get("semantic_truth_closed") is not False:
        return _fail("R1_STRUCTURAL_SEMANTIC_OVERCLAIM")

    scope=binding.get("binding_scope")
    if not isinstance(scope,Mapping):
        return _fail("BINDING_SCOPE_INVALID")
    if scope.get("behavior_id")!="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
        return _fail("BINDING_BEHAVIOR_ID_INVALID")
    if not REQUIRED_GUARANTEES<=set(scope.get("guarantees") or []):
        return _fail("BINDING_GUARANTEES_INSUFFICIENT")
    if not REQUIRED_LIMITS<=set(scope.get("limitations") or []):
        return _fail("BINDING_LIMITATIONS_INSUFFICIENT")

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__R1_ROOT_BOUND_TO_AUTHENTICATED_TARGET_HANDOFF_SUBJECT",
        "root_id":ROOT_ID,
        "subject_kind":"DECLARED_SYSTEM",
        "subject_id":SUBJECT_ID,
        "subject_sha256":SUBJECT_SHA256,
        "subject_binding_git_blob_sha":EXPECTED_BINDING_BLOB,
        "root_subject_binding_authority":True,
        "global_subject_identity_authority":False,
        "binding_scope":dict(scope),
        "semantic_truth_authority":False,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
