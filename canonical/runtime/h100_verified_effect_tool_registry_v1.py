"""Verified effect-tool registry V1 for H100.

Only content-addressed tool packs that already passed the typed effect broker
verification are registered here. All execution delegates back through the
confined broker; the registry adds naming and reuse, not new authority.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import h100_typed_effect_tool_acquisition_v1 as broker

SCHEMA="PROJECT_BRAIN_H100_VERIFIED_EFFECT_TOOL_REGISTRY_V1"
PRE=broker.ROOT/"canonical/governance/H100_EFFECT_TOOL_REGISTRY_V1_PRECOMMIT.json"
PRIOR="canonical/verification/H100_TYPED_EFFECT_TOOL_ACQUISITION_SECOND_CARRIER_VERIFICATION_20261005_V1.json"

REGISTRY=(
    {
        "tool_id":"JSON_RECEIPT_WRITER_V1",
        "pack_path":"canonical/capabilities/h100/tool_packs/JSON_RECEIPT_WRITER_V1.json",
        "pack_git_blob_sha":"2a609877738005bc1bd8e9ad19bca32cb08b8bf1",
        "prior_verification":PRIOR,
    },
    {
        "tool_id":"JSONL_LEDGER_APPEND_V1",
        "pack_path":"canonical/capabilities/h100/tool_packs/JSONL_LEDGER_APPEND_V1.json",
        "pack_git_blob_sha":"0e723280a781dd3ab76e34621257c06113769629",
        "prior_verification":PRIOR,
    },
)
_BY_ID={row["tool_id"]:row for row in REGISTRY}

class EffectToolRegistryError(ValueError):
    pass

def _contract()->dict[str,Any]:
    return json.loads(broker.PRE.read_text())["tool_contract"]

def registry_snapshot()->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_EFFECT_TOOL_REGISTRY_V1_READY",
        "entry_count":len(REGISTRY),
        "entries":[dict(x) for x in REGISTRY],
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "authority":"REGISTERED_TYPED_EFFECT_PACKS_ONLY",
    }

def invoke(tool_id:str,payload:Mapping[str,Any],sandbox_root:Path)->dict[str,Any]:
    entry=_BY_ID.get(str(tool_id))
    if entry is None:
        raise EffectToolRegistryError("TOOL_ID_NOT_VERIFIED")
    loaded=broker.load_tool_pack(
        broker.ROOT/entry["pack_path"],
        entry["pack_git_blob_sha"],
        _contract(),
    )
    out=broker.execute_tool(
        loaded,payload,Path(sandbox_root),int(_contract()["max_output_bytes_per_file"])
    )
    row=dict(out)
    row["schema"]=SCHEMA
    row["status"]="VERIFIED_EFFECT_TOOL_INVOKED"
    row["prior_verification"]=entry["prior_verification"]
    row["raw_tool_acquisition_attempts_before_hit"]=0
    return row
