#!/usr/bin/env python3
"""Verify independent XLSX writer/reader libraries against canonical Brain data."""
from __future__ import annotations
import importlib.util,json,pathlib,sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"canonical"/"runtime"))
import astra_runtime

WRITER_SOURCE={"type":"apt","origin":"Ubuntu","packages":[{
  "name":"python3-xlsxwriter","version":"3.1.9-1",
  "sha256":"234db5c80ba8d2eaf9933a95566f81a86aa01bb15b884f2ee6c932847e58bfd2"
}]}
READER_SOURCE={"type":"apt","origin":"Ubuntu","packages":[{
  "name":"python3-openpyxl","version":"3.1.2+dfsg-6",
  "sha256":"0892bf202df1f56bb36530c3ba9ac9f24f6a5b115442e7aa602b12e46aa0433c"
}]}

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def main():
    if len(sys.argv) not in (2,3):
        raise SystemExit("usage: verify_xlsx_library_roundtrip.py RESULT_JSON [MISSION_ID]")
    result_path=(ROOT/sys.argv[1]).resolve()
    verification_mission_id=sys.argv[2] if len(sys.argv)==3 else "ASTRA-VERIFY-XLSX-LIBRARY-ROUNDTRIP-001"
    astra_runtime._ensure_apt_dependencies(WRITER_SOURCE)
    astra_runtime._ensure_apt_dependencies(READER_SOURCE)
    writer=load("xlsx_writer_verify",ROOT/"canonical/runtime/bound_capabilities/xlsx_table_xlsxwriter.py")
    reader=load("xlsx_reader_verify",ROOT/"canonical/runtime/bound_capabilities/xlsx_verify_openpyxl.py")
    goal=(
      "Create an XLSX spreadsheet workbook at canonical/astra_runtime/tmp/XLSX_LIBRARY_ROUNDTRIP_VERIFY.xlsx "
      "containing exactly one row for every VERIFIED_BOUND_CAPABILITY with columns capability_id, status, source_type, provides, and incremental_spend_usd."
    )
    w=writer.run({
      "json_path":"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
      "output_path":"canonical/astra_runtime/tmp/XLSX_LIBRARY_ROUNDTRIP_VERIFY.xlsx",
      "goal":goal
    },ROOT)
    v=reader.run({
      "json_path":"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
      "xlsx_path":"canonical/astra_runtime/tmp/XLSX_LIBRARY_ROUNDTRIP_VERIFY.xlsx",
      "goal":goal
    },ROOT)
    result={
      "schema":"PROJECT_BRAIN_XLSX_LIBRARY_ROUNDTRIP_VERIFICATION_V1",
      "verification_mission_id":verification_mission_id,
      "status":"VERIFIED" if v.get("verified") is True else "FAILED",
      "writer_package":WRITER_SOURCE["packages"][0],
      "reader_package":READER_SOURCE["packages"][0],
      "supplier_independent":WRITER_SOURCE["packages"][0]["name"]!=READER_SOURCE["packages"][0]["name"],
      "writer_result":w,
      "reader_result":v,
      "verified":v.get("verified") is True,
    }
    result_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if not result["verified"] or not result["supplier_independent"]:
        raise RuntimeError("XLSX_LIBRARY_ROUNDTRIP_NOT_VERIFIED")
    print("XLSX_LIBRARY_ROUNDTRIP_VERIFIED",json.dumps(result,sort_keys=True))

if __name__=="__main__": main()
