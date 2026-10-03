"""Parametric complete discovery interface over a common frozen tool authority.

This is environment-side proof machinery, not candidate policy code. One frozen
instance contains:
  * public tool metadata shared by Brain and Opus,
  * hidden capability truth visible only to the safe-probe oracle,
  * one authoritative discovery source whose result is exactly the public
    authority manifest.

The implementation is parametric in the finite authority manifest. Therefore no
tool identity is assumed or pre-enumerated by the policy. A content digest binds
every discovery/probe receipt to the exact frozen instance.

Version changes produce a new instance generation. Calls made with an older
episode token fail closed, satisfying the contract's stable-epoch-or-restart
rule.
"""
from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from typing import Any, Mapping, Sequence

SOURCE_ID="COMMON_FROZEN_BRAIN_OPUS_TOOL_AUTHORITY"
SCHEMA="PROJECT_BRAIN_COMMON_AUTHORITY_DISCOVERY_INTERFACE_V1"
PUBLIC_KEYS=(
    "tool_id","cost","available","authorized","epoch","meta","schema_tags",
    "provider","region","risk","tags",
)

class InterfaceError(ValueError):
    pass

def _canonical(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def _sha(value:Any)->str:
    return hashlib.sha256(_canonical(value)).hexdigest()

def _nonnegative_number(value:Any,label:str)->float:
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise InterfaceError(label+":NOT_NUMBER")
    x=float(value)
    if not math.isfinite(x) or x<0:
        raise InterfaceError(label+":NOT_FINITE_NONNEGATIVE")
    return x

def _public_tool(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        raise InterfaceError("TOOL_NOT_MAPPING")
    tid=str(raw.get("tool_id") or "")
    if not tid:
        raise InterfaceError("TOOL_ID_MISSING")
    if raw.get("available") not in (True,False):
        raise InterfaceError("TOOL_AVAILABLE_NOT_BOOLEAN:"+tid)
    if raw.get("authorized") not in (True,False):
        raise InterfaceError("TOOL_AUTHORIZED_NOT_BOOLEAN:"+tid)
    epoch=raw.get("epoch",0)
    if isinstance(epoch,bool) or not isinstance(epoch,int) or epoch<0:
        raise InterfaceError("TOOL_EPOCH_INVALID:"+tid)
    _nonnegative_number(raw.get("cost",0.0),"TOOL_COST:"+tid)
    forbidden={"hidden_capabilities","capabilities","supported_capabilities","_oracle"}
    if forbidden & set(raw):
        raise InterfaceError("PUBLIC_METADATA_CONTAINS_HIDDEN_CAPABILITY_FIELD:"+tid)
    out={k:deepcopy(raw[k]) for k in PUBLIC_KEYS if k in raw}
    out["tool_id"]=tid
    out["cost"]=float(raw.get("cost",0.0))
    out["available"]=bool(raw["available"])
    out["authorized"]=bool(raw["authorized"])
    out["epoch"]=epoch
    return out

def _normalize_truth(
    tools:Mapping[str,Mapping[str,Any]],
    hidden_truth:Mapping[str,Any],
)->dict[str,dict[str,list[str]]]:
    if not isinstance(hidden_truth,Mapping):
        raise InterfaceError("HIDDEN_TRUTH_NOT_MAPPING")
    unknown=sorted(set(map(str,hidden_truth))-set(tools))
    if unknown:
        raise InterfaceError("HIDDEN_TRUTH_UNKNOWN_TOOL:"+",".join(unknown))
    out:dict[str,dict[str,list[str]]]={}
    for tid,tool in tools.items():
        raw_epochs=hidden_truth.get(tid)
        if not isinstance(raw_epochs,Mapping):
            raise InterfaceError("HIDDEN_TRUTH_TOOL_MISSING:"+tid)
        epochs:dict[str,list[str]]={}
        for raw_epoch,raw_caps in raw_epochs.items():
            try:
                epoch=int(raw_epoch)
            except (TypeError,ValueError):
                raise InterfaceError("HIDDEN_TRUTH_EPOCH_INVALID:"+tid)
            if epoch<0 or str(epoch)!=str(raw_epoch):
                raise InterfaceError("HIDDEN_TRUTH_EPOCH_INVALID:"+tid)
            if not isinstance(raw_caps,(list,tuple,set)):
                raise InterfaceError("HIDDEN_TRUTH_CAPS_NOT_SEQUENCE:"+tid)
            caps=sorted({str(x) for x in raw_caps if str(x)})
            epochs[str(epoch)]=caps
        current=str(tool["epoch"])
        if current not in epochs:
            raise InterfaceError("HIDDEN_TRUTH_CURRENT_EPOCH_MISSING:"+tid)
        out[tid]=dict(sorted(epochs.items(),key=lambda x:int(x[0])))
    return out

def freeze_instance(
    public_tools:Sequence[Mapping[str,Any]],
    hidden_truth:Mapping[str,Any],
    *,
    generation:int=0,
)->dict[str,Any]:
    if not isinstance(public_tools,(list,tuple)) or not public_tools:
        raise InterfaceError("FINITE_NONEMPTY_TOOL_AUTHORITY_REQUIRED")
    if isinstance(generation,bool) or not isinstance(generation,int) or generation<0:
        raise InterfaceError("GENERATION_INVALID")
    tools:dict[str,dict[str,Any]]={}
    for raw in public_tools:
        row=_public_tool(raw)
        tid=row["tool_id"]
        if tid in tools:
            raise InterfaceError("DUPLICATE_TOOL_ID:"+tid)
        tools[tid]=row
    truth=_normalize_truth(tools,hidden_truth)
    public_manifest=[tools[k] for k in sorted(tools)]
    public_digest=_sha(public_manifest)
    hidden_digest=_sha(truth)
    frozen_core={
        "schema":SCHEMA,
        "generation":generation,
        "public_tools":public_manifest,
        "hidden_truth":truth,
        "public_authority_sha256":public_digest,
        "hidden_oracle_sha256":hidden_digest,
    }
    frozen_core["instance_sha256"]=_sha(frozen_core)
    return frozen_core

def validate_instance(instance:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(instance,Mapping) or instance.get("schema")!=SCHEMA:
        raise InterfaceError("INSTANCE_SCHEMA_INVALID")
    rebuilt=freeze_instance(
        list(instance.get("public_tools") or []),
        dict(instance.get("hidden_truth") or {}),
        generation=instance.get("generation"),
    )
    for key in ("public_authority_sha256","hidden_oracle_sha256","instance_sha256"):
        if instance.get(key)!=rebuilt[key]:
            raise InterfaceError("INSTANCE_DIGEST_MISMATCH:"+key)
    return rebuilt

def public_interface_descriptor(instance:Mapping[str,Any])->dict[str,Any]:
    frozen=validate_instance(instance)
    return {
        "schema":SCHEMA,
        "instance_sha256":frozen["instance_sha256"],
        "generation":frozen["generation"],
        "public_authority_sha256":frozen["public_authority_sha256"],
        "discovery_sources":[{
            "source_id":SOURCE_ID,
            "cost":0.0,
            "available":True,
            "authority_sha256":frozen["public_authority_sha256"],
        }],
    }

def begin_episode(
    instance:Mapping[str,Any],
    required_capabilities:Sequence[str],
    *,
    constraint:Any=None,
)->dict[str,Any]:
    frozen=validate_instance(instance)
    required=sorted({str(x) for x in required_capabilities if str(x)})
    if not required:
        raise InterfaceError("REQUIRED_CAPABILITIES_EMPTY")
    descriptor=public_interface_descriptor(frozen)
    return {
        "required_capabilities":required,
        "constraint":deepcopy(constraint),
        "visible_tools":[],
        "discovery_sources":descriptor["discovery_sources"],
        "prior_probe_receipts":[],
        "discovery_receipts":[],
        "version_events":[],
        "interface_instance_sha256":frozen["instance_sha256"],
        "interface_generation":frozen["generation"],
        "public_authority_sha256":frozen["public_authority_sha256"],
    }

def _assert_episode_current(instance:Mapping[str,Any],episode:Mapping[str,Any])->dict[str,Any]:
    frozen=validate_instance(instance)
    if episode.get("interface_instance_sha256")!=frozen["instance_sha256"]:
        raise InterfaceError("STALE_EPISODE_RESTART_REQUIRED")
    if episode.get("interface_generation")!=frozen["generation"]:
        raise InterfaceError("STALE_EPISODE_RESTART_REQUIRED")
    if episode.get("public_authority_sha256")!=frozen["public_authority_sha256"]:
        raise InterfaceError("EPISODE_AUTHORITY_MISMATCH")
    return frozen

def discover(
    instance:Mapping[str,Any],
    episode:Mapping[str,Any],
    source_id:str,
    query:str,
)->dict[str,Any]:
    frozen=_assert_episode_current(instance,episode)
    if source_id!=SOURCE_ID:
        raise InterfaceError("DISCOVERY_SOURCE_INVALID")
    if not isinstance(query,str) or not query.strip():
        raise InterfaceError("DISCOVERY_QUERY_EMPTY")
    return {
        "kind":"DISCOVERY_RESULT",
        "source_id":SOURCE_ID,
        "authority_sha256":frozen["public_authority_sha256"],
        "instance_sha256":frozen["instance_sha256"],
        "generation":frozen["generation"],
        "complete":True,
        "tools":deepcopy(frozen["public_tools"]),
    }

def apply_discovery(episode:Mapping[str,Any],receipt:Mapping[str,Any])->dict[str,Any]:
    if receipt.get("kind")!="DISCOVERY_RESULT" or receipt.get("complete") is not True:
        raise InterfaceError("DISCOVERY_RECEIPT_INVALID")
    if receipt.get("source_id")!=SOURCE_ID:
        raise InterfaceError("DISCOVERY_SOURCE_INVALID")
    if receipt.get("authority_sha256")!=episode.get("public_authority_sha256"):
        raise InterfaceError("DISCOVERY_AUTHORITY_MISMATCH")
    if receipt.get("instance_sha256")!=episode.get("interface_instance_sha256"):
        raise InterfaceError("DISCOVERY_INSTANCE_MISMATCH")
    if receipt.get("generation")!=episode.get("interface_generation"):
        raise InterfaceError("DISCOVERY_GENERATION_MISMATCH")
    prior=list(episode.get("discovery_receipts") or [])
    if any(isinstance(x,Mapping) and x.get("source_id")==SOURCE_ID for x in prior):
        raise InterfaceError("DISCOVERY_SOURCE_ALREADY_QUERIED")

    visible:dict[str,dict[str,Any]]={}
    for raw in list(episode.get("visible_tools") or [])+list(receipt.get("tools") or []):
        row=_public_tool(raw)
        tid=row["tool_id"]
        if tid in visible and _canonical(visible[tid])!=_canonical(row):
            raise InterfaceError("CONFLICTING_PUBLIC_TOOL_METADATA:"+tid)
        visible[tid]=row
    out=deepcopy(dict(episode))
    out["visible_tools"]=[visible[k] for k in sorted(visible)]
    out["discovery_receipts"]=prior+[deepcopy(dict(receipt))]
    return out

def safe_probe(
    instance:Mapping[str,Any],
    episode:Mapping[str,Any],
    tool_id:str,
    capability:str,
)->dict[str,Any]:
    frozen=_assert_episode_current(instance,episode)
    tid=str(tool_id or ""); cap=str(capability or "")
    tools={x["tool_id"]:x for x in frozen["public_tools"]}
    if tid not in tools:
        raise InterfaceError("PROBE_UNKNOWN_TOOL")
    if not cap:
        raise InterfaceError("PROBE_CAPABILITY_EMPTY")
    epoch=tools[tid]["epoch"]
    truth=frozen["hidden_truth"][tid][str(epoch)]
    return {
        "kind":"SAFE_CAPABILITY_PROBE",
        "tool_id":tid,
        "capability":cap,
        "epoch":epoch,
        "supported":cap in truth,
        "instance_sha256":frozen["instance_sha256"],
        "generation":frozen["generation"],
    }

def apply_probe(episode:Mapping[str,Any],receipt:Mapping[str,Any])->dict[str,Any]:
    if receipt.get("kind")!="SAFE_CAPABILITY_PROBE":
        raise InterfaceError("PROBE_RECEIPT_INVALID")
    if receipt.get("instance_sha256")!=episode.get("interface_instance_sha256"):
        raise InterfaceError("PROBE_INSTANCE_MISMATCH")
    if receipt.get("generation")!=episode.get("interface_generation"):
        raise InterfaceError("PROBE_GENERATION_MISMATCH")
    out=deepcopy(dict(episode))
    receipts=list(out.get("prior_probe_receipts") or [])
    key=(receipt.get("tool_id"),receipt.get("capability"),receipt.get("epoch"))
    if any(
        (x.get("tool_id"),x.get("capability"),x.get("epoch"))==key
        for x in receipts if isinstance(x,Mapping)
    ):
        raise InterfaceError("DUPLICATE_CURRENT_EPOCH_PROBE")
    receipts.append(deepcopy(dict(receipt)))
    out["prior_probe_receipts"]=receipts
    return out

def evolve_tool(
    instance:Mapping[str,Any],
    tool_id:str,
    *,
    new_epoch:int,
    new_capabilities:Sequence[str],
    public_metadata_updates:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    frozen=validate_instance(instance)
    tid=str(tool_id or "")
    rows={x["tool_id"]:deepcopy(x) for x in frozen["public_tools"]}
    if tid not in rows:
        raise InterfaceError("VERSION_UNKNOWN_TOOL")
    old_epoch=rows[tid]["epoch"]
    if isinstance(new_epoch,bool) or not isinstance(new_epoch,int) or new_epoch<=old_epoch:
        raise InterfaceError("VERSION_EPOCH_MUST_ADVANCE")
    updates=dict(public_metadata_updates or {})
    forbidden={"tool_id","epoch","hidden_capabilities","capabilities","supported_capabilities","_oracle"}
    if forbidden & set(updates):
        raise InterfaceError("VERSION_PUBLIC_UPDATE_FORBIDDEN_FIELD")
    rows[tid].update(deepcopy(updates))
    rows[tid]["epoch"]=new_epoch
    truth=deepcopy(frozen["hidden_truth"])
    truth[tid][str(new_epoch)]=sorted({str(x) for x in new_capabilities if str(x)})
    return freeze_instance(
        [rows[k] for k in sorted(rows)],
        truth,
        generation=frozen["generation"]+1,
    )
