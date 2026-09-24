#!/usr/bin/env python3
"""Fresh verification for an automatically synthesized pending CLI binding."""
from __future__ import annotations
import hashlib,json,pathlib,sys

import astra_runtime
from bound_capabilities import cli_command

ROOT=pathlib.Path(__file__).resolve().parents[2]

def _inside(raw):
    p=(ROOT/str(raw)).resolve()
    if p!=ROOT.resolve() and ROOT.resolve() not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def main():
    if len(sys.argv)!=3:
        raise SystemExit("usage: verify_pending_cli_binding.py PENDING_JSON RESULT_JSON")
    pending_path=_inside(sys.argv[1])
    result_path=_inside(sys.argv[2])
    pending=json.loads(pending_path.read_text(encoding="utf-8"))
    if pending.get("schema")!="PROJECT_BRAIN_PENDING_AUTO_BINDING_V1":
        raise RuntimeError("PENDING_BINDING_SCHEMA_INVALID")
    entry=pending["registry_entry"]
    source=entry.get("source") or {}
    if source.get("type")!="apt":
        raise RuntimeError("PENDING_BINDING_SOURCE_NOT_APT")
    dependency=astra_runtime._ensure_apt_dependencies(source)
    args=dict(pending["verification_args"])
    observed=cli_command.run(args,ROOT)
    out=_inside(observed["output_path"])
    raw=out.read_bytes()
    expected_prefix=bytes.fromhex(str(args.get("output_prefix_hex") or ""))
    independent_ok=(
        observed.get("output_verified") is True
        and observed.get("returncode")==0
        and bool(raw)
        and (not expected_prefix or raw.startswith(expected_prefix))
        and hashlib.sha256(raw).hexdigest()==observed.get("output_sha256")
    )
    if not independent_ok:
        raise RuntimeError("PENDING_BINDING_INDEPENDENT_EFFECT_CHECK_FAILED")
    result={
      "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
      "capability_id":pending["capability_id"],
      "verification_mission_id":pending["verification_mission_id"],
      "dependency":dependency,
      "adapter_result":observed,
      "independent_output_sha256":hashlib.sha256(raw).hexdigest(),
      "independent_output_bytes":len(raw),
      "independent_verified":True,
      "status":"VERIFIED"
    }
    result_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PENDING_CLI_BINDING_EFFECT_VERIFIED",json.dumps(result,sort_keys=True))
if __name__=="__main__":
    main()
