"""Independent verifier for R3 realization-observation binding on the frozen V7 professional subject."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_r3_realization_witness_verify_v1 as witness_verify
from canonical.runtime import professional_step_binding_authority_v1 as step_auth

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R3_REALIZATION_OBSERVATION"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V1.json"
BINDING_BLOB="dbf8665c70c2e9ca432ec03fb0bdf5f17d0adf00"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
STEP_ID="RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS"
RUN_CONTEXT="sha256:a0c03647ce739eee1ee92c6e4ef26347b2e98082bed68de2742d57abdbc83b70"
EVIDENCE_SHA="1edf6c89f6ee05871be7600a6812552184bcbdea299ed73e6589da7c20b9b5b0"

REFS={
 "subject_verification":("canonical/verification/PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V7_VERIFY_20261010_V1.json","9bca985bfcef8f5cc6d62b42a51ccc72a6abfd2c"),
 "proof_bound_profile_execution":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V7_PROOF_BOUND_STEP_VERIFY_20261010_V1.json","b7a9df36780513ad73fd14c6a2756c8474d8434d"),
 "r3_realization_semantic_scope":("canonical/governance/PROFESSIONAL_QUALITY_R3_REALIZATION_SEMANTIC_SCOPE_20261010_V1.json","1edbd92b4e7b01591162d692f1d4c9b785b4c102"),
 "r3_realization_semantic_verification":("canonical/verification/PROFESSIONAL_QUALITY_R3_REALIZATION_SEMANTIC_VERIFY_20261010_V1.json","3c9a6f03c9dfb7597cdb7c5ca01e9eaf66a596e0"),
 "r3_scoped_integration_verification":("canonical/verification/PROFESSIONAL_QUALITY_R3_SEMANTIC_SCOPED_INTEGRATION_VERIFY_20261010_V1.json","86efb5396f90a4182d90029b47868123226fa05c"),
 "predecessor_render_preflight":("canonical/governance/NATIVE_ARTIFACT_RENDER_PRESERVATION_PREFLIGHT_V1.json","b5ddc896811875b59840959e27dbb515265fc9f8"),
 "predecessor_render_public_verification":("canonical/verification/NATIVE_ARTIFACT_RENDER_PRESERVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json","1a0b4ca6627aaf28eb25f6990682e87319d14d6d"),
 "exact_realization_witness":("canonical/evidence/PROFESSIONAL_R3_V7_REALIZATION_WITNESS_20261010_V1.json","95e08e82ffba5c84426e07b0f8d2556f7308f5a0"),
 "current_stack_public_verification":("canonical/verification/PROFESSIONAL_R3_V7_REALIZATION_WITNESS_PUBLIC_VERIFY_20261010_V1.json","64e7355020d700b066090d524a92737547ae1b02"),
 "render_step_receipt":("canonical/governance/PROFESSIONAL_R3_V7_RENDER_STEP_RESULT_BINDING_20261010_V1.json","76c262ee9eb355ca2bac32ede86e9c64c284ebaf"),
 "render_step_independent_verification":("canonical/verification/PROFESSIONAL_R3_V7_RENDER_STEP_RESULT_BINDING_INDEPENDENT_VERIFICATION_20261010_V1.json","12084180959187e9e2789cafd3cefa88a8d83795"),
}
CODE_REFS={
 "witness_verifier":("canonical/runtime/professional_quality_r3_realization_witness_verify_v1.py","316d9df9ebf73756a28c11e70be7cc167c1a6c5b"),
 "witness_verifier_tests":("canonical/tests/test_professional_quality_r3_realization_witness_verify_v1.py","78c18458ad6a7913e127142fbfb30a2c4c7bd6cb"),
}
REQUIRED_GUARANTEES={
 "EXACT_V7_SUBJECT_TUPLE_BOUND","EXACT_V3_RENDER_PROFILE_STEP_BOUND",
 "EXACT_SOURCE_AND_OUTPUT_ARTIFACT_BYTES_CONTENT_ADDRESSED",
 "EXACT_SOURCE_AND_OUTPUT_AUDIENCE_VIEW_PNG_BYTES_CONTENT_ADDRESSED",
 "CANONICAL_V7_RUN_CONTEXT_DIGEST_BOUND","CURRENT_UBUNTU_RENDER_STACK_FRESHLY_REPLAYED",
 "PREDECESSOR_RENDER_STACK_VERSION_AUTHORITY_NOT_TRANSPORTED",
 "HISTORICAL_RENDER_PRESERVATION_TESTS_PASS_ON_CURRENT_STACK",
 "EXACT_BOUNDED_PDF_STRUCTURAL_ORACLE_PASS","EXACT_BOUNDED_PDF_RENDER_OBSERVATION_PASS",
 "V7_RENDER_STEP_RECEIPT_AUTHENTICATED_BY_CANONICAL_STEP_BINDING_KERNEL",
 "STEP_PRODUCER_AND_INDEPENDENT_VERIFIER_IDENTITIES_DISTINCT",
 "CALLER_SUPPLIED_RENDER_STEP_RESULT_HAS_ZERO_AUTHORITY_WITHOUT_CONTENT_ADDRESSED_RECEIPT",
}
REQUIRED_LIMITS={
 "NO_ARBITRARY_SEMANTIC_TARGET_CORRECTNESS","NO_WHOLE_CONTRACT_SCOPE_EQUIVALENCE",
 "NO_GLOBAL_R3_ROOT_CLOSURE","NO_ALL_RENDERER_ENVIRONMENT_INVARIANCE",
 "NO_GLOBAL_SUBJECT_IDENTITY_AUTHORITY","NO_QUALITY_AUTHORITY","NO_ACCEPTANCE_AUTHORITY",
 "NO_PROMOTION_AUTHORITY","NO_TERMINAL_AUTHORITY","NO_R4_THROUGH_R12_ROOT_SUBJECT_BINDING",
 "NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION",
}
SELF_FALSE=(
 "global_subject_identity_authority","root_subject_binding_authority","semantic_truth_authority",
 "execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority",
)

def _blob(p:Path)->str:
 d=p.read_bytes(); return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _read(root:Path,path:str,sha:str):
 p=(root/path).resolve()
 try:p.relative_to(root.resolve())
 except ValueError:return None,"OUTSIDE_ROOT:"+path
 if not p.is_file() or p.is_symlink():return None,"FILE_INVALID:"+path
 if _blob(p)!=sha:return None,"BLOB_STALE:"+path
 try:d=json.loads(p.read_text(encoding="utf-8"))
 except Exception:return None,"JSON_INVALID:"+path
 return (d,None) if isinstance(d,dict) else (None,"DOCUMENT_INVALID:"+path)

def _fail(reason:str,**extra:Any):
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,"root_id":ROOT_ID,
 "root_subject_binding_authority":False,"semantic_truth_authority":False,"execution_authority":False,
 "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
 "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def validate_binding_document(b:Mapping[str,Any])->str|None:
 if b.get("schema")!=BINDING_SCHEMA or b.get("root_id")!=ROOT_ID:return "BINDING_IDENTITY_INVALID"
 if (b.get("subject_kind"),b.get("subject_id"),b.get("subject_sha256"))!=("DECLARED_SYSTEM",SUBJECT_ID,SUBJECT_SHA256):
  return "SUBJECT_TUPLE_MISMATCH"
 for f in SELF_FALSE:
  if b.get(f) is not False:return "BINDING_SELF_AUTHORITY_FORBIDDEN:"+f
 if b.get("realization_executor_external_root_support") is not True or b.get("candidate_executor_inside_subject_required") is not False:
  return "REALIZATION_EXECUTOR_BOUNDARY_INVALID"
 if b.get("exact_v7_step_receipt_authenticated") is not True:return "STEP_AUTHENTICATION_CLAIM_MISSING"
 bs=b.get("binding_scope") or {}
 if bs.get("behavior_id")!=BEHAVIOR_ID or bs.get("step_id")!=STEP_ID:return "BINDING_STEP_IDENTITY_INVALID"
 if bs.get("run_context_sha256")!=RUN_CONTEXT or bs.get("evidence_sha256")!=EVIDENCE_SHA:return "BINDING_EVIDENCE_IDENTITY_INVALID"
 if not REQUIRED_GUARANTEES<=set(bs.get("guarantees") or []):return "BINDING_GUARANTEES_INSUFFICIENT"
 if not REQUIRED_LIMITS<=set(bs.get("limitations") or []):return "BINDING_LIMITATIONS_INSUFFICIENT"
 return None

def validate_public_verification(d:Mapping[str,Any])->str|None:
 if d.get("schema")!="PROJECT_BRAIN_PROFESSIONAL_R3_V7_REALIZATION_WITNESS_PUBLIC_VERIFY_V1":return "PUBLIC_VERIFY_SCHEMA_INVALID"
 if d.get("pass") is not True or d.get("independent_verified") is not True:return "PUBLIC_VERIFY_NOT_INDEPENDENT_PASS"
 if d.get("semantic_preservation_verified") is not True or d.get("evidence_scope_verified") is not True:return "PUBLIC_VERIFY_PREMISE_MISSING"
 runner=d.get("public_runner") or {}
 if runner.get("repository")!="moxnixmdj/verification-capsule-runner" or runner.get("pull_request")!=2618:return "PUBLIC_RUNNER_IDENTITY_INVALID"
 if runner.get("workflow_run_id")!=38051863009 or runner.get("job_id")!=114212442560 or runner.get("conclusion")!="success":return "PUBLIC_RUN_IDENTITY_INVALID"
 if runner.get("head_sha")!="c7f073d5f1940330fe98fc215b6bc299c3c17da9":return "PUBLIC_HEAD_IDENTITY_INVALID"
 if runner.get("runner_label")!="ubuntu-24.04" or runner.get("standard_github_hosted_runner") is not True:return "PUBLIC_RUNNER_CLASS_INVALID"
 replay=d.get("replay") or {}
 if replay.get("predecessor_exact_stack_transport_claimed") is not False:return "VERSION_TRANSPORT_FORBIDDEN"
 if replay.get("historical_render_preservation_tests_passed")!=3 or replay.get("historical_render_preservation_tests_failed")!=0:return "HISTORICAL_REPLAY_INSUFFICIENT"
 if replay.get("exact_v7_witness_step")!="PASS":return "PUBLIC_WITNESS_NOT_PASS"
 exact=d.get("exact_evidence") or {}
 if exact.get("git_blob_sha")!="95e08e82ffba5c84426e07b0f8d2556f7308f5a0" or exact.get("evidence_sha256")!=EVIDENCE_SHA:return "PUBLIC_EVIDENCE_MISMATCH"
 auth=d.get("authority") or {}
 if any(auth.get(x) is not False for x in ("root_subject_binding_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority")):
  return "PUBLIC_VERIFY_AUTHORITY_OVERCLAIM"
 return None

def verify(*,repo_root:str|Path|None=None):
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 b,e=_read(root,BINDING_PATH,BINDING_BLOB)
 if e:return _fail(e)
 bad=validate_binding_document(b)
 if bad:return _fail(bad)
 sref=b.get("subject") or {}
 if sref.get("path")!=SUBJECT_PATH or sref.get("git_blob_sha")!=SUBJECT_BLOB:return _fail("SUBJECT_REFERENCE_MISMATCH")
 s,e=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
 if e:return _fail(e)
 if s.get("subject_id")!=SUBJECT_ID or s.get("subject_sha256")!=SUBJECT_SHA256:return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")

 refs=b.get("bridge_evidence")
 if not isinstance(refs,Mapping):return _fail("BRIDGE_EVIDENCE_INVALID")
 docs={}
 for k,(path,sha) in REFS.items():
  ref=refs.get(k)
  if not isinstance(ref,Mapping) or ref.get("path")!=path or ref.get("git_blob_sha")!=sha:return _fail("BRIDGE_REFERENCE_MISMATCH:"+k)
  d,e=_read(root,path,sha)
  if e:return _fail(e)
  docs[k]=d
 for k,(path,sha) in CODE_REFS.items():
  ref=refs.get(k)
  if not isinstance(ref,Mapping) or ref.get("path")!=path or ref.get("git_blob_sha")!=sha:return _fail("BRIDGE_REFERENCE_MISMATCH:"+k)
  p=(root/path).resolve()
  try:p.relative_to(root.resolve())
  except ValueError:return _fail("OUTSIDE_ROOT:"+path)
  if not p.is_file() or p.is_symlink():return _fail("FILE_INVALID:"+path)
  if _blob(p)!=sha:return _fail("BLOB_STALE:"+path)

 if not str(docs["subject_verification"].get("status") or "").startswith("PASS__"):return _fail("SUBJECT_VERIFY_NOT_PASS")
 pv=docs["proof_bound_profile_execution"]
 if (pv.get("replay") or {}).get("tests_passed")!=15:return _fail("V7_PROOF_BOUND_REPLAY_INSUFFICIENT")
 proves=set(pv.get("proves") or [])
 if "CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY_AT_V7_ENTRY" not in proves:return _fail("CALLER_STEP_NONAUTHORITY_UNPROVED")
 if "ALL_SEVEN_PREVIOUSLY_UNBOUND_LOAD_BEARING_PROFILE_STEPS_REQUIRE_CONTENT_ADDRESSED_STEP_BINDINGS" not in proves:return _fail("SEVEN_STEP_BINDING_REQUIREMENT_UNPROVED")

 sem=docs["r3_realization_semantic_scope"]
 limits=set(sem.get("limitations") or [])
 if "NO_ARBITRARY_SEMANTIC_TARGET_SELECTION" not in limits or "NO_GLOBAL_R3_ROOT_CLOSURE" not in limits:return _fail("R3_SEMANTIC_SCOPE_TOO_BROAD")
 if sem.get("global_root_closure") is not False or sem.get("terminal_authority") is not False:return _fail("R3_SEMANTIC_SCOPE_AUTHORITY_OVERCLAIM")
 sv=docs["r3_realization_semantic_verification"]
 if not str(sv.get("status") or "").startswith("PASS__"):return _fail("R3_SEMANTIC_VERIFY_NOT_PASS")
 si=docs["r3_scoped_integration_verification"]
 if not str(si.get("status") or "").startswith("PASS__"):return _fail("R3_SCOPED_INTEGRATION_NOT_PASS")

 pred=docs["predecessor_render_public_verification"]
 if not str(pred.get("status") or "").startswith("PASS__"):return _fail("PREDECESSOR_RENDER_VERIFY_NOT_PASS")
 preflight=docs["predecessor_render_preflight"]
 if preflight.get("execution_authority") is not False or preflight.get("capability_credit_delta")!=0:return _fail("PREDECESSOR_PREFLIGHT_AUTHORITY_OVERCLAIM")

 wout=witness_verify.verify_witness(docs["exact_realization_witness"])
 if not wout.get("pass"):return _fail("EXACT_WITNESS_INVALID",witness=wout)
 pubbad=validate_public_verification(docs["current_stack_public_verification"])
 if pubbad:return _fail(pubbad)

 step_binding={
  "receipt":{"path":REFS["render_step_receipt"][0],"git_blob_sha":REFS["render_step_receipt"][1]},
  "verification":{"path":REFS["render_step_independent_verification"][0],"git_blob_sha":REFS["render_step_independent_verification"][1]},
 }
 sout=step_auth.authenticate_step_binding(
  step_binding,behavior_id=BEHAVIOR_ID,subject_id=SUBJECT_ID,subject_sha256=SUBJECT_SHA256,
  step_id=STEP_ID,run_context_sha256=RUN_CONTEXT,repo_root=root,
 )
 if not sout.get("pass"):return _fail("V7_RENDER_STEP_BINDING_INVALID",step=sout)
 if sout.get("evidence_sha256")!=EVIDENCE_SHA:return _fail("STEP_EVIDENCE_MISMATCH")

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R3_BOUND_TO_V7_SUBJECT_WITH_EXACT_AUTHENTICATED_REALIZATION_AND_CURRENT_STACK_PUBLIC_REPLAY",
  "root_id":ROOT_ID,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,
  "subject_binding_git_blob_sha":BINDING_BLOB,
  "run_context_sha256":RUN_CONTEXT,"evidence_sha256":EVIDENCE_SHA,
  "root_subject_binding_authority":True,
  "bounded_exact_realization_instance_proved":True,
  "global_r3_root_closed":False,
  "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
