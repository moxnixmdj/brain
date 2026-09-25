#!/usr/bin/env python3
"""Fresh producer/verifier-independent SQLite round-trip verification."""
from __future__ import annotations
import importlib.util,json,pathlib,sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"canonical"/"runtime"))
import astra_runtime

CLI_SOURCE={"type":"apt","origin":"Ubuntu","packages":[{
  "name":"sqlite3","version":"3.45.1-1ubuntu2.8",
  "sha256":"78493e56909614ec1d588c9fae1739a704d9e1a6ff65509b1f06c3e4d53ed0c3"
}]}

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def main():
    if len(sys.argv) not in (2,3):
        raise SystemExit("usage: verify_sqlite_roundtrip.py RESULT_JSON [MISSION_ID]")
    result_path=(ROOT/sys.argv[1]).resolve()
    mission_id=sys.argv[2] if len(sys.argv)==3 else "ASTRA-VERIFY-SQLITE-ROUNDTRIP-001"
    astra_runtime._ensure_apt_dependencies(CLI_SOURCE)
    producer=load("sqlite_producer_verify",ROOT/"canonical/runtime/bound_capabilities/sqlite_table_stdlib.py")
    verifier=load("sqlite_cli_verify",ROOT/"canonical/runtime/bound_capabilities/sqlite_verify_cli.py")
    goal=(
      "Create a SQLite database at canonical/astra_runtime/tmp/SQLITE_ROUNDTRIP_VERIFY.sqlite "
      "with a table named verified_capabilities containing exactly one row for every VERIFIED_BOUND_CAPABILITY "
      "and columns capability_id, status, source_type, provides, and incremental_spend_usd."
    )
    p=producer.run({
      "json_path":"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
      "output_path":"canonical/astra_runtime/tmp/SQLITE_ROUNDTRIP_VERIFY.sqlite",
      "goal":goal
    },ROOT)
    verifier_goal=(
      "Finally independently query the SQLite database and verify that every VERIFIED_BOUND_CAPABILITY "
      "appears exactly once, that no non-verified capability appears, and that every stored value "
      "matches the canonical registry."
    )
    v=verifier.run({
      "json_path":"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
      "sqlite_path":"canonical/astra_runtime/tmp/SQLITE_ROUNDTRIP_VERIFY.sqlite",
      "goal":verifier_goal
    },ROOT)
    result={
      "schema":"PROJECT_BRAIN_SQLITE_ROUNDTRIP_VERIFICATION_V1",
      "verification_mission_id":mission_id,
      "producer_source":{"type":"python_stdlib","module":"sqlite3"},
      "verifier_package":CLI_SOURCE["packages"][0],
      "producer_verifier_independent":True,
      "producer_result":p,
      "verifier_result":v,
      "verified":bool(v.get("verified")) and p.get("output_sha256")==v.get("sqlite_sha256"),
      "status":"VERIFIED" if bool(v.get("verified")) and p.get("output_sha256")==v.get("sqlite_sha256") else "FAILED"
    }
    result_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if result["verified"] is not True:
        raise RuntimeError("SQLITE_ROUNDTRIP_NOT_VERIFIED")
    print("SQLITE_ROUNDTRIP_VERIFIED",json.dumps(result,sort_keys=True))

if __name__=="__main__": main()
