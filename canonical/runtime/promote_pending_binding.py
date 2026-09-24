#!/usr/bin/env python3
"""Promote a pending auto binding after a fresh verification result."""
from __future__ import annotations
import json,pathlib,sys

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
    if verified.get("verification_mission_id")!=pending.get("verification_mission_id"):
        raise RuntimeError("VERIFICATION_MISSION_MISMATCH")
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
    REGISTRY.write_text(json.dumps(registry,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    original=_inside(pending["origin_mission_path"])
    if original.parent!=(ROOT/"canonical"/"astra_runtime"/"missions").resolve():
        raise RuntimeError("ORIGIN_MISSION_PATH_INVALID")
    mission=json.loads(original.read_text(encoding="utf-8"))
    constraints=mission.setdefault("constraints",{})
    constraints["auto_acquisition_promoted"]={
      "capability_id":cid,
      "verification_mission_id":pending["verification_mission_id"],
      "verification_result_path":str(verify_path.relative_to(ROOT))
    }
    original.write_text(json.dumps(mission,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    pending["status"]="PROMOTED_VERIFIED"
    pending["verification_result_path"]=str(verify_path.relative_to(ROOT))
    pending_path.write_text(json.dumps(pending,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PENDING_CAPABILITY_PROMOTED",cid)
if __name__=="__main__":
    main()
