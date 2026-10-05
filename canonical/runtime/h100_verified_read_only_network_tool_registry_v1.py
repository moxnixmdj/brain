"""Verified read-only network tool registry V1 for H100."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import h100_pinned_https_tool_acquisition_v1 as v1
from canonical.runtime import h100_pinned_https_tool_acquisition_v2 as v2

SCHEMA="PROJECT_BRAIN_H100_VERIFIED_READ_ONLY_NETWORK_TOOL_REGISTRY_V1"
PRE=v2.ROOT/"canonical/governance/H100_READ_ONLY_NETWORK_TOOL_REGISTRY_V1_PRECOMMIT.json"
PRIOR="canonical/verification/H100_PINNED_HTTPS_TOOL_ACQUISITION_V2_SECOND_CARRIER_VERIFICATION_20261005_V1.json"

REGISTRY=(
    {"tool_id":"PINNED_HTTPS_JSON_FIXTURE_V2","pack_path":"canonical/capabilities/h100/tool_packs/PINNED_HTTPS_JSON_FIXTURE_V2.json","pack_git_blob_sha":"2ec2f149d14c433b0ebede9c6197a496b5a5d4ff","prior_verification":PRIOR},
    {"tool_id":"PINNED_HTTPS_TEXT_FIXTURE_V2","pack_path":"canonical/capabilities/h100/tool_packs/PINNED_HTTPS_TEXT_FIXTURE_V2.json","pack_git_blob_sha":"9798633843b4e1d183a1d7b5f85d06c96631ca51","prior_verification":PRIOR},
)
_BY_ID={x["tool_id"]:x for x in REGISTRY}

class ReadOnlyNetworkToolRegistryError(ValueError):
    pass

def _contract()->dict[str,Any]:
    return json.loads(v2.PRE.read_text())["network_contract"]

def registry_snapshot()->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_READ_ONLY_NETWORK_TOOL_REGISTRY_V1_READY",
        "entry_count":len(REGISTRY),
        "entries":[dict(x) for x in REGISTRY],
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "caller_supplied_endpoints":0,
        "credentials_used":0,
    }

def invoke(tool_id:str,sandbox_root:Path)->dict[str,Any]:
    entry=_BY_ID.get(str(tool_id))
    if entry is None:
        raise ReadOnlyNetworkToolRegistryError("NETWORK_TOOL_ID_NOT_VERIFIED")
    loaded=v2.load_tool_pack(v2.ROOT/entry["pack_path"],entry["pack_git_blob_sha"],_contract())
    out=v1.fetch_verified(loaded,Path(sandbox_root),_contract())
    row=dict(out)
    row["schema"]=SCHEMA
    row["status"]="VERIFIED_READ_ONLY_NETWORK_TOOL_INVOKED"
    row["prior_verification"]=entry["prior_verification"]
    row["raw_network_tool_acquisition_attempts_before_hit"]=0
    return row
