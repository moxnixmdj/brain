#!/usr/bin/env python3
"""Promote a pending auto binding after a fresh verification result."""
from __future__ import annotations
import hashlib,json,pathlib,re,sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
REGISTRY=ROOT/"canonical"/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json"

def _inside(raw):
    p=(ROOT/str(raw)).resolve()
    if p!=ROOT.resolve() and ROOT.resolve() not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def main():
    if len(sys.argv)!=3:
        raise SystemExit("usage: promote_pending_binding.py PENDING_JSON VERIFY_JSON")
    pending_path=_inside(sys.argv[1])
    verify_path=_inside(sys.argv[2])
    pending=json.loads(pending_path.read_text(encoding="utf-8"))
    verified=json.loads(verify_path.read_text(encoding="utf-8"))
    if pending.get("schema")!="PROJECT_BRAIN_PENDING_AUTO_BINDING_V1":
        raise RuntimeError("PENDING_BINDING_SCHEMA_INVALID")
    if verified.get("schema")!="PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1":
        raise RuntimeError("VERIFICATION_SCHEMA_INVALID")
    cid=pending["capability_id"]
    if verified.get("capability_id")!=cid or verified.get("independent_verified") is not True:
        raise RuntimeError("VERIFICATION_NOT_PROMOTABLE")
    semantic_roundtrip=verified.get("semantic_roundtrip")
    source_type=str(((pending.get("registry_entry") or {}).get("source") or {}).get("type") or "")
    if source_type in {"pypi","npm","git_source_tree"}:
        if not isinstance(semantic_roundtrip,dict):
            raise RuntimeError("VERIFICATION_INDEPENDENCE_EVIDENCE_MISSING")
        independent_verifier=semantic_roundtrip.get("independent_verifier")
        if (
            semantic_roundtrip.get("implementation_independent") is not True
            or not isinstance(independent_verifier,dict)
            or independent_verifier.get("verified") is not True
            or independent_verifier.get("implementation_independent") is not True
            or independent_verifier.get("supplier_class_independent") is not True
        ):
            raise RuntimeError("VERIFICATION_IMPLEMENTATION_NOT_INDEPENDENT")
    elif (
        isinstance(semantic_roundtrip,dict)
        and semantic_roundtrip.get("implementation_independent") is False
    ):
        raise RuntimeError("VERIFICATION_IMPLEMENTATION_NOT_INDEPENDENT")
    if verified.get("verification_mission_id")!=pending.get("verification_mission_id"):
        raise RuntimeError("VERIFICATION_MISSION_MISMATCH")

    original=_inside(pending["origin_mission_path"])
    missions_root=(ROOT/"canonical"/"astra_runtime"/"missions").resolve()
    if original.parent!=missions_root:
        raise RuntimeError("ORIGIN_MISSION_PATH_INVALID")
    if not original.is_file():
        raise RuntimeError("ORIGIN_MISSION_MISSING")
    frozen_sha=str(pending.get("origin_mission_sha256_at_acquisition") or "")
    if not re.fullmatch(r"[0-9a-f]{64}",frozen_sha):
        raise RuntimeError("ORIGIN_MISSION_ACQUISITION_HASH_MISSING")
    current_sha=hashlib.sha256(original.read_bytes()).hexdigest()
    if current_sha!=frozen_sha:
        raise RuntimeError("ORIGIN_MISSION_DRIFT_BEFORE_PROMOTION")
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    caps=registry.setdefault("capabilities",{})
    prior=caps.get(cid)
    entry=json.loads(json.dumps(pending["registry_entry"]))
    if isinstance(prior,dict) and prior.get("status")=="VERIFIED_BOUND_CAPABILITY":
        if prior.get("source")!=entry.get("source") or prior.get("action_template")!=entry.get("action_template"):
            raise RuntimeError("CAPABILITY_ID_VERIFIED_CONFLICT")
    entry["status"]="VERIFIED_BOUND_CAPABILITY"
    entry["verification"]={
      "mission_id":pending["verification_mission_id"],
      "verification_result_path":str(verify_path.relative_to(ROOT)),
      "observed_effect":verified.get("adapter_result"),
      "independent_output_sha256":verified.get("independent_output_sha256"),
      "independent_output_bytes":verified.get("independent_output_bytes"),
      "independent_verified":True,
      "autonomous_acquisition":True
    }
    caps[cid]=entry
    promoted_related=[]
    additional=pending.get("additional_registry_entries") or {}
    if not isinstance(additional,dict):
        raise RuntimeError("ADDITIONAL_REGISTRY_ENTRIES_INVALID")
    for related_id,related_raw in sorted(additional.items()):
        if not isinstance(related_id,str) or not isinstance(related_raw,dict):
            raise RuntimeError("ADDITIONAL_REGISTRY_ENTRY_INVALID")
        related=json.loads(json.dumps(related_raw))
        prior_related=caps.get(related_id)
        if isinstance(prior_related,dict) and prior_related.get("status")=="VERIFIED_BOUND_CAPABILITY":
            if prior_related.get("source")!=related.get("source") or prior_related.get("action_template")!=related.get("action_template"):
                raise RuntimeError("RELATED_CAPABILITY_ID_VERIFIED_CONFLICT")
        related["status"]="VERIFIED_BOUND_CAPABILITY"
        related["verification"]={
          "mission_id":pending["verification_mission_id"],
          "verification_result_path":str(verify_path.relative_to(ROOT)),
          "observed_effect":verified.get("semantic_roundtrip") or verified.get("adapter_result"),
          "independent_verified":True,
          "autonomous_acquisition":True,
          "promoted_with_primary_capability":cid
        }
        caps[related_id]=related
        promoted_related.append(related_id)
    REGISTRY.write_text(json.dumps(registry,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    # Mission authority was frozen before verification and rechecked before
    # any registry mutation. Preserve the verified promotion-time hash as
    # evidence; never rewrite the originating mission.
    pending["origin_mission_sha256_verified_at_promotion"]=current_sha
    pending["status"]="PROMOTED_VERIFIED"
    pending["verification_result_path"]=str(verify_path.relative_to(ROOT))
    pending_path.write_text(json.dumps(pending,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PENDING_CAPABILITY_PROMOTED",cid,"RELATED",",".join(promoted_related))
if __name__=="__main__":
    main()
