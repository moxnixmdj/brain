#!/usr/bin/env python3
"""Promote freshly verified reusable SQLite producer and CLI verifier capabilities."""
from __future__ import annotations
import json,pathlib,sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
REG=ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: promote_sqlite_capabilities.py VERIFY_JSON")
    vp=(ROOT/sys.argv[1]).resolve()
    v=json.loads(vp.read_text(encoding="utf-8"))
    if v.get("schema")!="PROJECT_BRAIN_SQLITE_ROUNDTRIP_VERIFICATION_V1" or v.get("verified") is not True:
        raise RuntimeError("SQLITE_VERIFICATION_NOT_PROMOTABLE")
    if v.get("producer_verifier_independent") is not True:
        raise RuntimeError("SQLITE_VERIFIER_NOT_INDEPENDENT")
    mid=str(v.get("verification_mission_id") or "")
    cli=v["verifier_package"]
    reg=json.loads(REG.read_text(encoding="utf-8"))
    caps=reg.setdefault("capabilities",{})
    common=["sqlite","database","table","rows","columns"]
    caps["sqlite.table.create_from_json_records"]={
      "provides":["sqlite.table.create_from_json_records"],
      "requires":[],
      "keywords":common+["create"],
      "cost":1,
      "platforms":["linux"],
      "adapter_module":"sqlite_table_stdlib",
      "entrypoint":"run",
      "action_template":{
        "type":"invoke_capability",
        "args":{
          "capability_id":"sqlite.table.create_from_json_records",
          "json_path":"${input.json_path}",
          "output_path":"${input.output_path}",
          "goal":"${input.goal}"
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True}
      },
      "source":{
        "type":"python_stdlib","module":"sqlite3",
        "adapter_path":"canonical/runtime/bound_capabilities/sqlite_table_stdlib.py"
      },
      "incremental_spend_usd":0,
      "status":"VERIFIED_BOUND_CAPABILITY",
      "verification":{
        "mission_id":mid,
        "verification_result_path":str(vp.relative_to(ROOT)),
        "observed_effect":v.get("producer_result"),
        "independently_verified":True,
        "independent_verifier_package":cli["name"]
      }
    }
    caps["sqlite.table.verify_against_json_records"]={
      "provides":["sqlite.table.verify_against_json_records"],
      "requires":[],
      "keywords":common+["verify","query","independently"],
      "cost":1,
      "platforms":["linux"],
      "adapter_module":"sqlite_verify_cli",
      "entrypoint":"run",
      "action_template":{
        "type":"invoke_capability",
        "args":{
          "capability_id":"sqlite.table.verify_against_json_records",
          "json_path":"${input.json_path}",
          "sqlite_path":"${input.sqlite_path}",
          "goal":"${input.goal}"
        },
        "expect":{"type":"field_equals","field":"verified","value":True}
      },
      "source":{"type":"apt","origin":"Ubuntu","packages":[{
        "name":cli["name"],"version":cli["version"],"sha256":cli["sha256"]
      }]},
      "incremental_spend_usd":0,
      "status":"VERIFIED_BOUND_CAPABILITY",
      "verification":{
        "mission_id":mid,
        "verification_result_path":str(vp.relative_to(ROOT)),
        "observed_effect":v.get("verifier_result"),
        "independently_verified":True,
        "producer_source":"python_stdlib:sqlite3"
      }
    }
    REG.write_text(json.dumps(reg,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("SQLITE_CAPABILITIES_PROMOTED")

if __name__=="__main__": main()
