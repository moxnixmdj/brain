"""Fresh V2 replay of the pinned HTTPS acquisition contract.

Authority implementation is inherited from V1. V2 changes only the fresh pack
schema/precommit after the V1 fixture-construction failure; network semantics and
security boundary are unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import h100_pinned_https_tool_acquisition_v1 as v1

ROOT=v1.ROOT
PRE=ROOT/"canonical/governance/H100_PINNED_HTTPS_TOOL_ACQUISITION_PRECOMMIT_V2.json"
SCHEMA="PROJECT_BRAIN_H100_PINNED_HTTPS_TOOL_ACQUISITION_RESULT_V2"
PACK_SCHEMA="PROJECT_BRAIN_H100_PINNED_HTTPS_FETCH_TOOL_PACK_V2"

PinnedHTTPSToolError=v1.PinnedHTTPSToolError

def _validate_pack_obj(pack:Mapping[str,Any],contract:Mapping[str,Any])->None:
    required={
        "schema","tool_id","source_class","scheme","host","path","expected_status",
        "expected_bytes","expected_sha256","output_path","hard_nonclaim"
    }
    if set(pack)!=required:
        raise PinnedHTTPSToolError("PACK_FIELDS_INVALID")
    if pack.get("schema")!=PACK_SCHEMA or pack.get("source_class")!="CONTENT_ADDRESSED_PINNED_HTTPS_FETCH_TOOL_PACK":
        raise PinnedHTTPSToolError("PACK_SCHEMA_OR_SOURCE_INVALID")
    shadow=dict(pack); shadow["schema"]=v1.PACK_SCHEMA
    v1._validate_pack_obj(shadow,contract)

def load_tool_pack(path:Path,expected_git_blob_sha:str,contract:Mapping[str,Any])->dict[str,Any]:
    raw=Path(path).read_bytes()
    actual=v1._git_blob_sha(raw)
    if actual!=expected_git_blob_sha:
        raise PinnedHTTPSToolError("PACK_GIT_BLOB_SHA_MISMATCH")
    try:
        pack=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise PinnedHTTPSToolError("PACK_JSON_INVALID") from exc
    _validate_pack_obj(pack,contract)
    return {"pack":pack,"git_blob_sha":actual}

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    contract=pre["network_contract"]
    results=[]; all_pass=True
    import tempfile
    for spec in pre["packs"]:
        loaded=load_tool_pack(ROOT/spec["path"],spec["git_blob_sha"],contract)
        absent=v1._existing_registry_absent(spec["tool_id"])
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first=v1.fetch_verified(loaded,Path(a),contract)
            second=v1.fetch_verified(loaded,Path(b),contract)
            raw1=Path(a,loaded["pack"]["output_path"]).read_bytes()
            raw2=Path(b,loaded["pack"]["output_path"]).read_bytes()
            deterministic=raw1==raw2
            passed=(
                absent and deterministic and
                first["status"]==spec["expected_status"] and
                first["bytes"]==spec["expected_bytes"] and
                first["sha256"]==spec["expected_sha256"] and
                second["sha256"]==spec["expected_sha256"]
            )
            results.append({
                "tool_id":spec["tool_id"],
                "existing_effect_registry_absent":absent,
                "pack_git_blob_sha":loaded["git_blob_sha"],
                "deterministic_replay":deterministic,
                "first":first,"second":second,
                "pass":passed,
            })
            all_pass=all_pass and passed
    return {
        "schema":SCHEMA,
        "status":"PASS__FRESH_PINNED_HTTPS_READ_ONLY_TOOL_ACQUISITION_TWO_OF_TWO__ZERO_CREDIT" if all_pass else "FAIL__PINNED_HTTPS_V2_RESIDUAL",
        "v1_failure_preserved":"canonical/verification/H100_PINNED_HTTPS_TOOL_ACQUISITION_V1_FAILURE_20261005.json",
        "tools":results,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "shell_calls":0,
        "subprocess_calls":0,
        "arbitrary_code_execution":0,
        "caller_supplied_endpoints":0,
        "credentials_used":0,
        "redirects_followed":0,
        "h100_terminal_credit_delta":0,
        "hard_nonclaims":[
            "PINNED_HTTPS_GET_IS_NOT_ARBITRARY_NETWORK_SERVICE_AUTHORITY",
            "NO_AUTHENTICATED_MUTATING_OR_CALLER_SELECTED_ENDPOINTS",
            "NO_H100_TERMINAL_CREDIT"
        ],
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
