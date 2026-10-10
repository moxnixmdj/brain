from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from execution_guard.logical_attempt_identity_v2 import logical_attempt_id

ROOT = Path(__file__).resolve().parents[2]
SEED = "canonical/governance/TB_SCIENCE_RANK20_EXECUTION_CLAIM_SEED_20261010_V1.json"
BINDING = "canonical/governance/TB_SCIENCE_RANK20_LOGICAL_ATTEMPT_CLAIM_BINDING_20261010_V1.json"
AUTHORITY = "canonical/governance/TB_SCIENCE_RANK20_ONE_SLOT_EXECUTION_AUTHORITY_20261010_V1.json"
LEDGER = "canonical/governance/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261010_V42.json"
ADMISSION = "canonical/governance/TB_SCIENCE_RANK20_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_20261010_V1.json"
ADMISSION_VERIFY = "canonical/verification/TB_SCIENCE_RANK20_CAPABILITY_FIRST_ADMISSION_INDEPENDENT_VERIFICATION_20261010_V1.json"

SLOT = "terminal-bench-science/hysteretic-aquifer-control::trial-0"
TASK_DIGEST = "sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"
CLAIM_SHA256 = "1b5a30a3a5d42006b5dd440ec71362dac9728b5d2c2abdca45bfda80de2898b5"
CLAIM_DIGEST = "sha256:" + CLAIM_SHA256
ATTEMPT_ID = "c02b0f18205db3b81fe40f843a451e696375fbfcd5fd75fd01d8c8d411456fcc"

EXPECTED_BLOBS = {
    SEED: "b058e29630d8b4eb100e08082a8d9c7053516647",
    BINDING: "9bfc6e9bde3d196443acebf9a0dd0ac1cfd23ab8",
    AUTHORITY: "2888ea4e942584e79837060f31bc594639d089d7",
    LEDGER: "3d88e976fc24d4ced184680f611220456e444543",
    ADMISSION: "b03861813f9b9a730659e6e0b6e7301a45061b04",
    ADMISSION_VERIFY: "d12c7c1f9e1259eaf3950689556fd0e6a37ba705",
    "execution_guard/logical_attempt_identity_v2.py": "67ff638459af1bb50a094e9479fb4aa5e2a3de1c",
    "canonical/runtime/harbor_science_planner_v7.py": "e5d6ab78b6cf5bacee568cd3701410a8745b9ce8",
    "canonical/runtime/harbor_science_agent_v13.py": "470bfe079aeffaa07a3b92975b4edea17c9a20e1",
}

def _blob(path: str) -> str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

def _load(path: str) -> dict[str, Any]:
    value=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path+":OBJECT_REQUIRED")
    return value

def _canonical_sha256(value: Mapping[str, Any]) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def verify_documents(seed: Mapping[str, Any], binding: Mapping[str, Any], authority: Mapping[str, Any], ledger: Mapping[str, Any]) -> list[str]:
    errors: list[str]=[]
    ident=seed.get("identity_state") or {}
    if ident.get("version")!="V2":
        errors.append("SEED_IDENTITY_VERSION_DRIFT")
    if ident.get("execution_claim_binding_digest") is not None or ident.get("logical_attempt_id") is not None or ident.get("minted") is not False:
        errors.append("PRECLAIM_IDENTITY_WAS_PREMATURELY_MINTED")
    if ident.get("legacy_v1_fallback_allowed") is not False:
        errors.append("LEGACY_V1_FALLBACK_ALLOWED")
    for key in ("task_read","task_started","execution_claim_authority","execution_authority","activation_authority","promotion_authority"):
        if seed.get(key) is not False:
            errors.append("SEED_AUTHORITY_OR_EXPOSURE_PRESENT:"+key)

    if binding.get("slot_id")!=SLOT or binding.get("task_digest")!=TASK_DIGEST:
        errors.append("BINDING_SLOT_OR_DIGEST_DRIFT")
    if binding.get("preclaim_seed_blob")!=EXPECTED_BLOBS[SEED]:
        errors.append("BINDING_SEED_BLOB_DRIFT")
    if _canonical_sha256(binding)!=CLAIM_SHA256:
        errors.append("CLAIM_CANONICAL_SHA256_DRIFT")
    derived=logical_attempt_id(slot_id=SLOT,task_digest=TASK_DIGEST,execution_claim_binding_digest=CLAIM_DIGEST)
    if derived!=ATTEMPT_ID:
        errors.append("V2_LOGICAL_ATTEMPT_DERIVATION_DRIFT")

    logical=authority.get("logical_attempt") or {}
    if logical.get("id")!=ATTEMPT_ID or logical.get("execution_claim_binding_digest")!=CLAIM_DIGEST:
        errors.append("AUTHORITY_LOGICAL_ATTEMPT_DRIFT")
    if logical.get("identity_basis")!="SLOT_ID_PLUS_TASK_DIGEST_PLUS_EXECUTION_CLAIM_BINDING_DIGEST":
        errors.append("AUTHORITY_IDENTITY_BASIS_DRIFT")
    if logical.get("legacy_v1_fallback_allowed") is not False:
        errors.append("AUTHORITY_LEGACY_V1_FALLBACK_ALLOWED")
    if authority.get("execution_authority") is not True or authority.get("execution_authority_effective") is not False:
        errors.append("STAGED_EXECUTION_AUTHORITY_STATE_INVALID")
    for key in ("task_read_authority","task_read_authority_effective","activation_authority","promotion_authority","fresh_reality_authority"):
        if authority.get(key) is not False:
            errors.append("PRE_RESEAL_AUTHORITY_PRESENT:"+key)
    state=authority.get("state") or {}
    if state.get("task_read_history") is not False or state.get("task_started") is not False or state.get("benchmark_trials_consumed")!=0:
        errors.append("AUTHORITY_ZERO_EXPOSURE_STATE_DRIFT")

    nxt=ledger.get("next_slot") or {}
    if nxt.get("slot_id")!=SLOT or nxt.get("task_digest")!=TASK_DIGEST:
        errors.append("LEDGER_SLOT_OR_DIGEST_DRIFT")
    if nxt.get("logical_attempt_id")!=ATTEMPT_ID or nxt.get("execution_claim_binding_digest")!=CLAIM_DIGEST:
        errors.append("LEDGER_IDENTITY_DRIFT")
    counts=ledger.get("counts") or {}
    if counts.get("benchmark_trials_consumed")!=18 or counts.get("consumed_failures_final")!=18 or counts.get("started_result_pending")!=0:
        errors.append("LEDGER_COUNTS_DRIFT")
    for key in ("execution_authority","task_read_authority","activation_authority"):
        if ledger.get(key) is not False:
            errors.append("LEDGER_PRE_RESEAL_AUTHORITY_PRESENT:"+key)
    return sorted(errors)

def verify() -> dict[str, Any]:
    errors=[]
    for path,expected in EXPECTED_BLOBS.items():
        got=_blob(path)
        if got!=expected:
            errors.append(f"SOURCE_BLOB_DRIFT:{path}:{got}")
    seed=_load(SEED); binding=_load(BINDING); authority=_load(AUTHORITY); ledger=_load(LEDGER)
    errors.extend(verify_documents(seed,binding,authority,ledger))
    admission=_load(ADMISSION)
    admission_verify=_load(ADMISSION_VERIFY)
    if admission.get("authorized") is not True or admission.get("decision")!="ADMIT_CHECKPOINT_AUDIT_EXECUTION":
        errors.append("CAPABILITY_FIRST_ADMISSION_NOT_ACTIVE")
    if admission.get("execution_authority") is not False or admission.get("logical_attempt_identity",{}).get("legacy_v1_fallback_allowed") is not False:
        errors.append("ADMISSION_AUTHORITY_OR_IDENTITY_POLICY_DRIFT")
    if not str(admission_verify.get("status") or "").startswith("PASS__RANK20_UNEXPOSED_PRECLAIM"):
        errors.append("ADMISSION_INDEPENDENT_VERIFICATION_DRIFT")
    ok=not errors
    return {
        "schema":"PROJECT_BRAIN_TB_SCIENCE_RANK20_CLAIM_BOUND_IDENTITY_VERIFIER_V1",
        "status":"PASS__RANK20_CLAIM_BOUND_V2_IDENTITY_MINTED__ZERO_EXPOSURE__PUBLIC_RESEAL_PENDING" if ok else "FAIL_CLOSED",
        "pass":ok,
        "errors":sorted(errors),
        "slot_id":SLOT,
        "task_digest":TASK_DIGEST,
        "execution_claim_binding_digest":CLAIM_DIGEST,
        "logical_attempt_id":ATTEMPT_ID,
        "legacy_v1_fallback_allowed":False,
        "task_read":False,
        "task_started":False,
        "benchmark_trials_consumed":0,
        "execution_authority_effective":False,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }

if __name__=="__main__":
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
