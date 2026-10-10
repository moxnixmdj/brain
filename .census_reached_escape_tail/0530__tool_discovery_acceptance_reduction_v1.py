"""Fail-closed Tool Discovery acceptance reduction.

Consumes the independently verified universal formal scope proof and the current
atomic evidence bindings. It can produce a closure *candidate* for
TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR, but grants zero credit until this
reduction is independently verified and promoted into current authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_V1"
TARGET="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
FAMILY="TOOL_DISCOVERY_SELECTION_AND_LEARNING"

EXPECTED={
 "canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":
   "f44e2378cf00f86a59159cb9d8edb35f0a7c27f4",
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":
   "0ed075c1efa053fe6e4eb3519d9903cf63fcf163",
 "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
   "62394e5b7d221ec9f69c3458f669e40e253a9d09",
 "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json":
   "ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":
   "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
}


def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def load(rel:str)->dict[str,Any]:
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))


def reduce(
    *,
    scope_receipt:Mapping[str,Any],
    bindings:Mapping[str,Any],
    protocols:Mapping[str,Any],
    firewall:Mapping[str,Any],
    registry:Mapping[str,Any],
)->dict[str,Any]:
    errors=[]

    runner=scope_receipt.get("independent_runner")
    verified=scope_receipt.get("verified")
    if not isinstance(runner,Mapping) or runner.get("conclusion")!="success":
        errors.append("SCOPE_RECEIPT_INDEPENDENT_RUNNER_NOT_SUCCESS")
    if not isinstance(verified,Mapping):
        verified={}
        errors.append("SCOPE_RECEIPT_VERIFIED_BLOCK_MISSING")
    required_scope={
      "universal_scope_proved":True,
      "uses_empirical_generalization":False,
      "source_180_of_180_load_bearing":False,
      "internet_wide_tool_identity_completeness_claim":False,
      "zero_credit_preserved":True,
    }
    for key,want in required_scope.items():
        if verified.get(key)!=want:
            errors.append("SCOPE_RECEIPT_MISMATCH:"+key)
    if verified.get("basis_kind")!="UNIVERSAL_FORMAL_SCOPE_PROOF":
        errors.append("SCOPE_BASIS_NOT_UNIVERSAL_FORMAL")
    if verified.get("target_predicate")!=TARGET:
        errors.append("SCOPE_TARGET_MISMATCH")

    if "UNIVERSAL_FORMAL_SCOPE_PROOF" not in (
        firewall.get("admissible_absolute_dominance_bases") or []
    ):
        errors.append("FIREWALL_DOES_NOT_ADMIT_UNIVERSAL_FORMAL_SCOPE_PROOF")

    prow=next((x for x in protocols.get("protocols",[])
               if x.get("family")==FAMILY),None)
    if not isinstance(prow,Mapping):
        errors.append("TOOL_DISCOVERY_PROTOCOL_MISSING")
    else:
        if prow.get("proof_mode")!="MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER":
            errors.append("PROTOCOL_MODE_MISMATCH")
        acc=str(prow.get("acceptance") or "")
        if "terminal-success/valid-route bounds >= Opus matched bounds" not in acc:
            errors.append("PROTOCOL_ACCEPTANCE_NONINFERIORITY_MISSING")

    reg=next((x for x in registry.get("predicates",[]) if x.get("id")==TARGET),None)
    if not isinstance(reg,Mapping) or reg.get("family")!=FAMILY:
        errors.append("TARGET_REGISTRY_BINDING_INVALID")

    claims={
      str(x.get("predicate_id")):x
      for x in bindings.get("claims",[])
      if isinstance(x,Mapping)
    }
    current=claims.get(TARGET)
    if not isinstance(current,Mapping):
        errors.append("CURRENT_TARGET_CLAIM_MISSING")
    else:
        if current.get("state")!="EXTERNAL_BLOCKED":
            errors.append("CURRENT_TARGET_NOT_SCOPE_BLOCKED")
        if current.get("blocker")!="ABSOLUTE_SCOPE_COMPLETENESS_MISSING":
            errors.append("CURRENT_BLOCKER_NOT_SCOPE_COMPLETENESS")
    for pid in (
      "TOOL_LEARNING_SECOND_TASK_TRANSFER",
      "TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION",
    ):
        if (claims.get(pid) or {}).get("state")!="PROVED":
            errors.append("DEPENDENT_ATOM_NOT_PROVED:"+pid)

    ok=not errors
    candidate_claim=None
    if ok:
        candidate_claim={
          "predicate_id":TARGET,
          "state":"PROVED",
          "proof_kind":"ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS",
          "source_path":"canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
          "source_sha":"f44e2378cf00f86a59159cb9d8edb35f0a7c27f4",
          "family":FAMILY,
          "independent_or_objective":True,
          "scope_complete":True,
          "objective_ceiling":True,
          "brain_value":1,
          "objective_ceiling_value":1,
          "basis":"INDEPENDENT_UNIVERSAL_FORMAL_PROOF_COVERS_EVERY_VALID_INSTANCE_OF_THE_EXACT_FROZEN_HIDDEN_TOOL_PROTOCOL__FINITE_180_OF_180_SAMPLE_NON_LOAD_BEARING",
        }

    return {
      "schema":SCHEMA,
      "status":(
        "CANDIDATE_ACCEPTANCE_CLOSURE__TOOL_DISCOVERY_3_OF_3__INDEPENDENT_REDUCTION_VERIFICATION_REQUIRED"
        if ok else "FAIL_CLOSED"
      ),
      "pass":ok,
      "errors":errors,
      "target_predicate":TARGET,
      "candidate_claim":candidate_claim,
      "family_candidate_state":"PASS_3_OF_3" if ok else "OPEN",
      "uses_empirical_generalization":False,
      "source_180_of_180_load_bearing":False,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0,
      "acceptance_credit_delta":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "ownership_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
      "fresh_reality_authority":False,
    }


def verify()->dict[str,Any]:
    for rel,want in EXPECTED.items():
        got=blob_sha(ROOT/rel)
        if got!=want:
            raise AssertionError((rel,got,want))
    return reduce(
      scope_receipt=load("canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
      bindings=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
      protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
      firewall=load("canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"),
      registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
    )


def main()->int:
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__=="__main__":
    raise SystemExit(main())
