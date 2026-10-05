"""Pinned HTTPS read-only tool acquisition for H100.

Authority is intentionally tiny:
- GET only;
- literal endpoint comes only from a content-addressed pack;
- HTTPS only;
- frozen host allowlist;
- no credentials or caller headers;
- http.client does not follow redirects;
- exact expected status, byte count, and SHA-256 required;
- verified bytes may only be written inside a caller-supplied sandbox root.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from canonical.runtime import h100_typed_effect_tool_acquisition_v1 as effectrt
from canonical.runtime import h100_verified_effect_tool_registry_v1 as effect_registry

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_PINNED_HTTPS_TOOL_ACQUISITION_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_PINNED_HTTPS_TOOL_ACQUISITION_RESULT_V1"
PACK_SCHEMA="PROJECT_BRAIN_H100_PINNED_HTTPS_FETCH_TOOL_PACK_V1"
_SHA256_RE=re.compile(r"^[0-9a-f]{64}$")

class PinnedHTTPSToolError(ValueError):
    pass

def _git_blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _validate_pack_obj(pack:Mapping[str,Any],contract:Mapping[str,Any])->None:
    required={
        "schema","tool_id","source_class","scheme","host","path","expected_status",
        "expected_bytes","expected_sha256","output_path","hard_nonclaim"
    }
    if set(pack)!=required:
        raise PinnedHTTPSToolError("PACK_FIELDS_INVALID")
    if pack.get("schema")!=PACK_SCHEMA or pack.get("source_class")!="CONTENT_ADDRESSED_PINNED_HTTPS_FETCH_TOOL_PACK":
        raise PinnedHTTPSToolError("PACK_SCHEMA_OR_SOURCE_INVALID")
    if pack.get("scheme")!="https":
        raise PinnedHTTPSToolError("SCHEME_NOT_HTTPS")
    host=pack.get("host")
    if not isinstance(host,str) or host not in set(contract["allowed_hosts"]):
        raise PinnedHTTPSToolError("HOST_NOT_ALLOWLISTED")
    raw_path=pack.get("path")
    if not isinstance(raw_path,str) or not raw_path.startswith("/"):
        raise PinnedHTTPSToolError("REMOTE_PATH_INVALID")
    parsed=urlsplit(raw_path)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or parsed.path!=raw_path:
        raise PinnedHTTPSToolError("REMOTE_PATH_HAS_FORBIDDEN_COMPONENT")
    if ".." in Path(raw_path).parts:
        raise PinnedHTTPSToolError("REMOTE_PATH_TRAVERSAL")
    if pack.get("expected_status")!=200:
        raise PinnedHTTPSToolError("EXPECTED_STATUS_NOT_200")
    n=pack.get("expected_bytes")
    if not isinstance(n,int) or isinstance(n,bool) or n<0 or n>int(contract["max_response_bytes"]):
        raise PinnedHTTPSToolError("EXPECTED_BYTES_INVALID")
    sha=pack.get("expected_sha256")
    if not isinstance(sha,str) or not _SHA256_RE.fullmatch(sha):
        raise PinnedHTTPSToolError("EXPECTED_SHA256_INVALID")
    effectrt._validate_path(pack.get("output_path"))

def load_tool_pack(path:Path,expected_git_blob_sha:str,contract:Mapping[str,Any])->dict[str,Any]:
    raw=Path(path).read_bytes()
    actual=_git_blob_sha(raw)
    if actual!=expected_git_blob_sha:
        raise PinnedHTTPSToolError("PACK_GIT_BLOB_SHA_MISMATCH")
    try:
        pack=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise PinnedHTTPSToolError("PACK_JSON_INVALID") from exc
    _validate_pack_obj(pack,contract)
    return {"pack":pack,"git_blob_sha":actual}

def fetch_verified(loaded:Mapping[str,Any],sandbox_root:Path,contract:Mapping[str,Any])->dict[str,Any]:
    pack=loaded["pack"]
    host=str(pack["host"]); path=str(pack["path"])
    conn=http.client.HTTPSConnection(host,443,timeout=float(contract["timeout_seconds"]))
    try:
        conn.request("GET",path,headers={"User-Agent":"Project-Brain-H100-Pinned-Fetch/1","Accept":"application/octet-stream"})
        resp=conn.getresponse()
        status=int(resp.status)
        if status!=int(pack["expected_status"]):
            raise PinnedHTTPSToolError("HTTP_STATUS_MISMATCH")
        if resp.getheader("Location") is not None:
            raise PinnedHTTPSToolError("REDIRECT_HEADER_REJECTED")
        limit=int(contract["max_response_bytes"])
        raw=resp.read(limit+1)
        if len(raw)>limit:
            raise PinnedHTTPSToolError("RESPONSE_TOO_LARGE")
    finally:
        conn.close()
    if len(raw)!=int(pack["expected_bytes"]):
        raise PinnedHTTPSToolError("RESPONSE_BYTE_COUNT_MISMATCH")
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=pack["expected_sha256"]:
        raise PinnedHTTPSToolError("RESPONSE_SHA256_MISMATCH")
    root=Path(sandbox_root); root.mkdir(parents=True,exist_ok=True)
    target=effectrt._safe_target(root,str(pack["output_path"]))
    target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_name(target.name+".tmp-h100-net")
    tmp.write_bytes(raw); os.replace(tmp,target)
    return {
        "tool_id":pack["tool_id"],
        "host":host,
        "remote_path":path,
        "output_path":pack["output_path"],
        "status":status,
        "bytes":len(raw),
        "sha256":sha,
        "network_calls":1,
        "shell_calls":0,
        "subprocess_calls":0,
        "arbitrary_code_execution":0,
        "credentials_used":0,
        "redirects_followed":0,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
    }

def _existing_registry_absent(tool_id:str)->bool:
    snap=effect_registry.registry_snapshot()
    return all(row.get("tool_id")!=tool_id for row in snap["entries"])

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    contract=pre["network_contract"]
    results=[]; all_pass=True
    for spec in pre["packs"]:
        loaded=load_tool_pack(ROOT/spec["path"],spec["git_blob_sha"],contract)
        absent=_existing_registry_absent(spec["tool_id"])
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first=fetch_verified(loaded,Path(a),contract)
            second=fetch_verified(loaded,Path(b),contract)
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
        "status":"PASS__PINNED_HTTPS_READ_ONLY_TOOL_ACQUISITION_TWO_OF_TWO__ZERO_CREDIT" if all_pass else "FAIL__PINNED_HTTPS_TOOL_RESIDUAL",
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
