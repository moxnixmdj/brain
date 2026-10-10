"""Re-key the verified V7 R2 finite candidate basis onto the repaired V7 subject."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import professional_quality_r2_candidate_branch_basis_v2 as base

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R2_REPAIRED_V7_REKEY_ADAPTER_V1"
OLD_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
OLD_SHA="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
NEW_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V7"
NEW_SHA="7e2904f3205b283a3a0f9e7583b36599cc2da4a96fd31b1777c226ca5c16c9e4"

def _fail(reason:str)->dict[str,Any]:
    return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "candidate_generation_authority":False,"global_candidate_search_complete":False,
      "quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0}

def generate(*,target_instance:Mapping[str,Any],incumbent:Mapping[str,Any],repo_root:str|Path|None=None)->dict[str,Any]:
    if base.SUBJECT_ID!=OLD_ID or base.SUBJECT_SHA256!=OLD_SHA:
        return _fail("BASE_SUBJECT_IDENTITY_DRIFT")
    out=base.generate(target_instance=target_instance,incumbent=incumbent,repo_root=repo_root)
    if out.get("pass") is not True:return _fail("BASE_GENERATOR_FAILED")
    if out.get("subject_id")!=OLD_ID or out.get("subject_sha256")!=OLD_SHA:return _fail("BASE_OUTPUT_SUBJECT_MISMATCH")
    rows=deepcopy(out["candidates"])
    for row in rows:
        identity={"subject_id":NEW_ID,"subject_sha256":NEW_SHA,
          "profile_git_blob_sha":out["profile_git_blob_sha"],
          "target_sha256":out["target_sha256"],"incumbent_sha256":out["incumbent_sha256"],
          "operator":row["operator"]}
        row["candidate_id"]="pq-r2:"+base._sha256(identity)
    result=deepcopy(out)
    result.update({"schema":SCHEMA,"status":"PASS__EXACT_BIJECTIVE_SUBJECT_REKEY",
      "subject_id":NEW_ID,"subject_sha256":NEW_SHA,"candidates":rows,
      "candidate_universe_sha256":base._sha256([r["candidate_id"] for r in rows]),
      "transport_kind":"BYTE_PRESERVING_SUBJECT_EXTENSION__IDENTITY_REKEY_ONLY",
      "candidate_generation_authority":True,"global_candidate_search_complete":False,
      "quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0})
    return result

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    args=args or {}
    return generate(target_instance=args.get("target_instance"),incumbent=args.get("incumbent"),repo_root=root)
