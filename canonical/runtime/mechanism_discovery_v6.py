"""Universal Learning V6 mechanism discovery primitives.

Finite, fail-closed mechanism learning:
- candidate mechanisms are explicit deterministic predictive programs over named probes,
- observations eliminate inconsistent mechanisms,
- decision-equivalent mechanisms are quotient-compressed,
- exhausting the declared class does NOT mean the environment is unknowable; it means
  the model class must expand,
- inferred mechanisms and invariants remain candidates until separately verified.
"""
from __future__ import annotations
import hashlib, json
from typing import Any, Iterable, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_MECHANISM_DISCOVERY_V6"

class MechanismDiscoveryError(ValueError):
    pass

def _s(x:Any)->str:
    return " ".join(str(x or "").split())

def _normalized_candidate(raw:Mapping[str,Any])->dict[str,Any]:
    mid=_s(raw.get("id"))
    if not mid:
        raise MechanismDiscoveryError("MECHANISM_ID_REQUIRED")
    action=_s(raw.get("best_action"))
    if not action:
        raise MechanismDiscoveryError("MECHANISM_BEST_ACTION_REQUIRED")
    preds=raw.get("predictions")
    if not isinstance(preds,Mapping) or not preds:
        raise MechanismDiscoveryError("MECHANISM_PREDICTIONS_REQUIRED")
    norm={}
    for k,v in preds.items():
        probe=_s(k); outcome=_s(v)
        if not probe or not outcome:
            raise MechanismDiscoveryError("MECHANISM_PREDICTION_INVALID")
        norm[probe]=outcome
    invariants=sorted({_s(x) for x in raw.get("invariants",[]) if _s(x)})
    provenance=[_s(x) for x in raw.get("provenance",[]) if _s(x)]
    return {
        "id":mid,
        "best_action":action,
        "predictions":dict(sorted(norm.items())),
        "invariants":invariants,
        "provenance":provenance,
    }

def mechanism_digest(candidate:Mapping[str,Any])->str:
    norm=_normalized_candidate(candidate)
    body=json.dumps(norm,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def normalize_candidates(candidates:Sequence[Mapping[str,Any]])->list[dict[str,Any]]:
    out=[];seen=set()
    for raw in candidates:
        c=_normalized_candidate(raw)
        if c["id"] in seen:
            raise MechanismDiscoveryError("MECHANISM_ID_DUPLICATE")
        seen.add(c["id"])
        c["digest"]=mechanism_digest(c)
        out.append(c)
    if not out:
        raise MechanismDiscoveryError("MECHANISM_CANDIDATE_REQUIRED")
    return sorted(out,key=lambda x:x["id"])

def normalize_observations(observations:Sequence[Mapping[str,Any]])->list[dict[str,str]]:
    out=[];seen={}
    for raw in observations:
        probe=_s(raw.get("probe_id")); outcome=_s(raw.get("outcome"))
        if not probe or not outcome:
            raise MechanismDiscoveryError("OBSERVATION_INVALID")
        if probe in seen and seen[probe]!=outcome:
            raise MechanismDiscoveryError("CONTRADICTORY_OBSERVATION_FOR_DETERMINISTIC_EPOCH")
        seen[probe]=outcome
    for probe,outcome in sorted(seen.items()):
        out.append({"probe_id":probe,"outcome":outcome})
    return out

def update(*,candidates:Sequence[Mapping[str,Any]],observations:Sequence[Mapping[str,Any]])->dict[str,Any]:
    cs=normalize_candidates(candidates)
    obs=normalize_observations(observations)
    survivors=[];eliminated=[]
    for c in cs:
        conflicts=[]
        for o in obs:
            pred=c["predictions"].get(o["probe_id"])
            if pred is None:
                conflicts.append({"probe_id":o["probe_id"],"reason":"PREDICTION_MISSING"})
            elif pred!=o["outcome"]:
                conflicts.append({"probe_id":o["probe_id"],"predicted":pred,"observed":o["outcome"]})
        if conflicts:
            eliminated.append({"id":c["id"],"digest":c["digest"],"conflicts":conflicts})
        else:
            survivors.append(c)
    if not survivors:
        status="MODEL_CLASS_FALSIFIED__EXPAND_HYPOTHESIS_LANGUAGE"
    elif len(survivors)==1:
        status="ONE_SURVIVING_CANDIDATE__NOT_VERIFIED_TRUTH"
    else:
        status="MULTIPLE_SURVIVING_CANDIDATES"
    return {
        "schema":SCHEMA,
        "status":status,
        "survivors":survivors,
        "eliminated":eliminated,
        "observations":obs,
        "model_class_closed":False,
        "true_mechanism_proved":False,
        "promotion_authorized":False,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
    }

def decision_quotient(candidates:Sequence[Mapping[str,Any]])->dict[str,Any]:
    cs=normalize_candidates(candidates)
    groups={}
    for c in cs:
        groups.setdefault(c["best_action"],[]).append(c["id"])
    classes=[
        {"action":action,"mechanism_ids":sorted(ids)}
        for action,ids in sorted(groups.items())
    ]
    return {
        "schema":SCHEMA,
        "equivalence_relation":"SAME_GOAL_CONDITIONED_BEST_ACTION",
        "mechanism_count":len(cs),
        "decision_class_count":len(classes),
        "classes":classes,
        "decision_sufficient_inside_declared_class":len(classes)==1,
        "open_world_sufficiency_proved":False,
    }

def common_invariant_candidates(candidates:Sequence[Mapping[str,Any]])->dict[str,Any]:
    cs=normalize_candidates(candidates)
    common=None
    for c in cs:
        inv=set(c["invariants"])
        common=inv if common is None else common & inv
    common=common or set()
    return {
        "schema":SCHEMA,
        "candidate_invariants":sorted(common),
        "verified_invariants":[],
        "candidate_only":True,
        "separate_verification_required":True,
        "promotion_authorized":False,
    }

def verify_invariant_candidate(*,invariant:str,source_mechanism_ids:Iterable[Any],receipt:Mapping[str,Any])->dict[str,Any]:
    inv=_s(invariant)
    ids=sorted({_s(x) for x in source_mechanism_ids if _s(x)})
    if not inv or not ids:
        raise MechanismDiscoveryError("INVARIANT_AND_SOURCE_IDS_REQUIRED")
    if receipt.get("independent_verified") is not True or receipt.get("exact_byte_bound") is not True or receipt.get("conclusion")!="success":
        raise MechanismDiscoveryError("INVARIANT_RECEIPT_INVALID")
    if receipt.get("behavior_preserving_on_claimed_scope") is not True:
        raise MechanismDiscoveryError("INVARIANT_BEHAVIOR_PRESERVATION_NOT_PROVED")
    if str(receipt.get("scope_relation") or "") not in {"EXACT","PROVEN_SUPERSET"}:
        raise MechanismDiscoveryError("INVARIANT_SCOPE_RELATION_NOT_ADMISSIBLE")
    if _s(receipt.get("invariant"))!=inv:
        raise MechanismDiscoveryError("INVARIANT_RECEIPT_BINDING_MISMATCH")
    bound=sorted({_s(x) for x in receipt.get("source_mechanism_ids",[]) if _s(x)})
    if bound!=ids:
        raise MechanismDiscoveryError("INVARIANT_SOURCE_BINDING_MISMATCH")
    rid=_s(receipt.get("receipt_id"))
    if not rid:
        raise MechanismDiscoveryError("INVARIANT_RECEIPT_ID_REQUIRED")
    return {
        "schema":SCHEMA,
        "invariant":inv,
        "source_mechanism_ids":ids,
        "verified":True,
        "verification_receipt":rid,
        "structural_reuse_authorized":True,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authority":False,
    }
