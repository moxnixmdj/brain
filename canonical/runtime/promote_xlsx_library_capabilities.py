#!/usr/bin/env python3
"""Promote independently verified reusable XLSX writer and verifier capabilities."""
from __future__ import annotations
import json,pathlib,sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
REG=ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: promote_xlsx_library_capabilities.py VERIFY_JSON")
    verify_path=(ROOT/sys.argv[1]).resolve()
    v=json.loads(verify_path.read_text(encoding="utf-8"))
    if v.get("schema")!="PROJECT_BRAIN_XLSX_LIBRARY_ROUNDTRIP_VERIFICATION_V1" or v.get("verified") is not True:
        raise RuntimeError("XLSX_VERIFICATION_NOT_PROMOTABLE")
    if v.get("supplier_independent") is not True:
        raise RuntimeError("XLSX_VERIFIER_NOT_INDEPENDENT")
    writer=v["writer_package"]; reader=v["reader_package"]
    verification_mission_id=str(v.get("verification_mission_id") or "ASTRA-VERIFY-XLSX-LIBRARY-ROUNDTRIP-001")
    reg=json.loads(REG.read_text(encoding="utf-8"))
    caps=reg.setdefault("capabilities",{})
    common_keywords=["xlsx","spreadsheet","workbook","rows","columns"]
    caps["xlsx.table.create_from_json_records"]={
      "provides":["xlsx.table.create_from_json_records"],
      "requires":[],
      "keywords":common_keywords+["create"],
      "cost":2,
      "platforms":["linux"],
      "adapter_module":"xlsx_table_xlsxwriter",
      "entrypoint":"run",
      "action_template":{
        "type":"invoke_capability",
        "args":{
          "capability_id":"xlsx.table.create_from_json_records",
          "json_path":"${input.json_path}",
          "output_path":"${input.output_path}",
          "goal":"${input.goal}"
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True}
      },
      "source":{"type":"apt","origin":"Ubuntu","packages":[{
        "name":writer["name"],"version":writer["version"],"sha256":writer["sha256"]
      }]},
      "incremental_spend_usd":0,
      "status":"VERIFIED_BOUND_CAPABILITY",
      "verification":{
        "mission_id":verification_mission_id,
        "verification_result_path":str(verify_path.relative_to(ROOT)),
        "observed_effect":v.get("writer_result"),
        "independently_verified":True,
        "independent_verifier_package":reader["name"]
      }
    }
    caps["xlsx.table.verify_against_json_records"]={
      "provides":["xlsx.table.verify_against_json_records"],
      "requires":[],
      "keywords":common_keywords+["verify","reopen","independently"],
      "cost":2,
      "platforms":["linux"],
      "adapter_module":"xlsx_verify_openpyxl",
      "entrypoint":"run",
      "action_template":{
        "type":"invoke_capability",
        "args":{
          "capability_id":"xlsx.table.verify_against_json_records",
          "json_path":"${input.json_path}",
          "xlsx_path":"${input.xlsx_path}",
          "goal":"${input.goal}"
        },
        "expect":{"type":"field_equals","field":"verified","value":True}
      },
      "source":{"type":"apt","origin":"Ubuntu","packages":[{
        "name":reader["name"],"version":reader["version"],"sha256":reader["sha256"]
      }]},
      "incremental_spend_usd":0,
      "status":"VERIFIED_BOUND_CAPABILITY",
      "verification":{
        "mission_id":verification_mission_id,
        "verification_result_path":str(verify_path.relative_to(ROOT)),
        "observed_effect":v.get("reader_result"),
        "independently_verified":True,
        "producer_package":writer["name"]
      }
    }
    REG.write_text(json.dumps(reg,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("XLSX_LIBRARY_CAPABILITIES_PROMOTED")

if __name__=="__main__": main()
