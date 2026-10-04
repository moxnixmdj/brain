#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
CONTRACT=ROOT/"canonical/governance/ROOT3_SCOPE_CERTIFICATE_COMPILER_V1.json"

MODES={"EXACT_ENUMERATION","INDUCTIVE_INVARIANT","ASSUME_GUARANTEE_COMPOSITION","EXACT_RESIDUAL_OBSERVATION"}

class ScopeCertificateError(ValueError): pass

def load_contract()->dict[str,Any]:
    x=json.loads(CONTRACT.read_text())
    if not isinstance(x,dict): raise ScopeCertificateError("CONTRACT_OBJECT_REQUIRED")
    return x

def _truthy(cert:Mapping[str,Any], keys:list[str])->bool:
    return all(cert.get(k) is True for k in keys)

def evaluate_certificate(cert:Mapping[str,Any])->dict[str,Any]:
    mode=str(cert.get("mode") or "")
    target=str(cert.get("target_id") or "")
    errors=[]
    if mode not in MODES: errors.append("INVALID_MODE")
    if not target: errors.append("TARGET_ID_REQUIRED")

    if mode=="EXACT_ENUMERATION":
        if not _truthy(cert,["finite_universe_content_addressed","enumeration_exhaustive","property_verified_for_every_member","no_uncovered_member"]):
            errors.append("ENUMERATION_INCOMPLETE")
    elif mode=="INDUCTIVE_INVARIANT":
        if not _truthy(cert,["initial_implies_invariant","invariant_preserved_by_all_allowed_transitions","invariant_implies_target_property","transition_scope_exact_or_superset"]):
            errors.append("INDUCTIVE_PROOF_INCOMPLETE")
    elif mode=="ASSUME_GUARANTEE_COMPOSITION":
        if not _truthy(cert,["all_used_components_scoped_proved","interfaces_compatible","composition_theorem_implies_global_property"]):
            errors.append("COMPOSITION_PROOF_INCOMPLETE")
    elif mode=="EXACT_RESIDUAL_OBSERVATION":
        if not _truthy(cert,["residual_content_addressed_exhaustive","zero_reality_fixed_point_reached","fresh_reality_authorized","all_residual_leaves_independently_verified"]):
            errors.append("RESIDUAL_OBSERVATION_NOT_AUTHORIZED_OR_INCOMPLETE")

    for forbidden in ("representative_examples_only","consensus_only","search_miss_only","cross_family_inheritance"):
        if cert.get(forbidden) is True: errors.append("FORBIDDEN_SHORTCUT:"+forbidden)

    return {
        "target_id":target,
        "mode":mode,
        "closed":not errors,
        "errors":sorted(set(errors)),
    }

def compile_state(certificates:list[Mapping[str,Any]])->dict[str,Any]:
    contract=load_contract()
    campaigns=contract.get("current_campaigns") or []
    targets={t for c in campaigns for t in c.get("targets",[])}
    rows=[evaluate_certificate(c) for c in certificates]
    closed={r["target_id"] for r in rows if r["closed"]}
    unknown=closed-targets
    if unknown:
        raise ScopeCertificateError("UNKNOWN_TARGETS:"+",".join(sorted(unknown)))
    unresolved=sorted(targets-closed)
    return {
        "schema":"PROJECT_BRAIN_ROOT3_SCOPE_CERTIFICATE_COMPILER_RESULT_V1",
        "status":"PASS__ALL_ROOT3_TARGETS_SCOPE_CLOSED" if not unresolved else "OPEN__ROOT3_SCOPE_RESIDUAL_REMAINS",
        "target_count":len(targets),
        "closed_count":len(closed),
        "unresolved_count":len(unresolved),
        "closed_targets":sorted(closed),
        "unresolved_targets":unresolved,
        "certificate_results":rows,
        "fresh_reality_authority":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
    }

if __name__=="__main__":
    import sys
    raw=sys.stdin.read().strip()
    certs=[] if not raw else json.loads(raw)
    if not isinstance(certs,list): raise SystemExit("certificate array required")
    print(json.dumps(compile_state(certs),indent=2,sort_keys=True))
