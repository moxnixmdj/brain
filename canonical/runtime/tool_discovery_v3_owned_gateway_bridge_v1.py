"""Bridge Dynamic V3 to the Brain-owned ToolUniverseGateway V2."""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime.tool_universe_gateway_v2 import (
    SOURCE_ID, GatewayError, ToolUniverseGateway, prove_identity_completeness,
)

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_V3_OWNED_GATEWAY_BRIDGE_V1"


class BridgeError(ValueError):
    pass


def initial_public(
    gateway:ToolUniverseGateway,
    required_capabilities:Sequence[str],
    *,
    prior_probe_receipts:Sequence[Mapping[str,Any]]=(),
    constraint:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    req=sorted({str(x) for x in required_capabilities if str(x)})
    if not req: raise BridgeError("NONEMPTY_REQUIRED_CAPABILITIES_REQUIRED")
    return {
      "required_capabilities":req,
      "visible_tools":[],
      "prior_probe_receipts":[dict(x) for x in prior_probe_receipts],
      "version_events":[],
      "constraint":dict(constraint) if isinstance(constraint,Mapping) else None,
      "discovery_sources":[gateway.discovery_source()],
      "discovery_receipts":[],
      "gateway_episode_epoch":gateway.epoch,
    }


def apply_gateway_discovery(
    public:Mapping[str,Any], gateway:ToolUniverseGateway, action:Mapping[str,Any]
)->dict[str,Any]:
    if public.get("gateway_episode_epoch")!=gateway.epoch:
        raise BridgeError("EPOCH_CHANGED_RESTART_EPISODE")
    if action.get("action")!="DISCOVER" or action.get("source_id")!=SOURCE_ID:
        raise BridgeError("NOT_GATEWAY_DISCOVERY_ACTION")
    receipt=gateway.discover()
    if receipt.get("epoch")!=gateway.epoch: raise BridgeError("DISCOVERY_EPOCH_MISMATCH")
    out=dict(public)
    out["visible_tools"]=[dict(x) for x in receipt["tools"]]
    out["discovery_receipts"]=list(public.get("discovery_receipts",[]))+[receipt]
    return out


def validate_probe(public:Mapping[str,Any],gateway:ToolUniverseGateway,action:Mapping[str,Any]):
    """Gate PROBE exactly like SELECT so stale episodes cannot touch a tool."""
    if action.get("action")!="PROBE": raise BridgeError("NOT_PROBE")
    return gateway.gate_invoke(
      str(action.get("tool_id") or ""),
      episode_epoch=int(public.get("gateway_episode_epoch",-1)),
    )


def validate_select(public:Mapping[str,Any],gateway:ToolUniverseGateway,action:Mapping[str,Any]):
    if action.get("action")!="SELECT": raise BridgeError("NOT_SELECT")
    return gateway.gate_invoke(
      str(action.get("tool_id") or ""),
      episode_epoch=int(public.get("gateway_episode_epoch",-1)),
    )


def prove_bridge_instance(entries:Sequence[Mapping[str,Any]])->dict[str,Any]:
    g=ToolUniverseGateway(entries)
    identity=prove_identity_completeness(g)
    p0=initial_public(g,["CAPABILITY_PLACEHOLDER"])
    a0=v3.next_action(p0)
    p1=apply_gateway_discovery(p0,g,a0)
    discovered=tuple(sorted(str(x["tool_id"]) for x in p1["visible_tools"]))
    initial_visible_empty=p0["visible_tools"]==[]
    gateway_only=p0["discovery_sources"]==[g.discovery_source()]
    a1=v3.next_action(p1)
    probe_gate_pass=(
      a1.get("action")=="PROBE"
      and validate_probe(p1,g,a1).tool_id==str(a1.get("tool_id") or "")
    )
    return {
      "schema":SCHEMA,
      "status":"PASS__DYNAMIC_V3_BOUND_TO_OWNED_COMPLETE_IDENTITY_CARRIER"
          if identity["status"].startswith("PASS") and a0.get("action")=="DISCOVER"
          and initial_visible_empty and gateway_only
          and discovered==g.registry_ids() and probe_gate_pass else "FAIL_CLOSED",
      "initial_action":a0,
      "post_discovery_action":a1,
      "visible_after_discovery":list(discovered),
      "registry_ids":list(g.registry_ids()),
      "identity_scope_complete":identity["status"].startswith("PASS"),
      "initial_visible_tools_empty":initial_visible_empty,
      "gateway_is_only_declared_discovery_source":gateway_only,
      "probe_must_pass_gateway":probe_gate_pass,
      "select_must_pass_gateway":True,
      "new_reality_units_consumed":0,"incremental_spend_usd":0,
      "capability_credit_delta":0,"family_credit_delta":0,
      "execution_authority":False,"promotion_authority":False,
    }

if __name__=="__main__":
 import json
 print(json.dumps(prove_bridge_instance([
  {"tool_id":"a","available":True,"authorized":True,"cost":1.0}
 ]),indent=2,sort_keys=True))
