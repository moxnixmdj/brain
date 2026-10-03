"""Common frozen tool-authority compiler for Tool Discovery V5.

This is a target-preserving harness boundary, not a Brain-only registry.
Both BRAIN and COMPARATOR roles are gated by the exact same frozen authority.
Unknown identities are not candidate-visible initially; the sole authoritative
DISCOVER source returns the complete identity/metadata universe for the exact
requirement query while hidden capability truth remains private behind bounded
safe probes.

The construction is parametric in any finite authority snapshot. It therefore
turns "is the declared discovery-source union complete?" from an empirical
ecosystem claim into a by-construction property of the common matched harness.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

SOURCE_ID="COMMON_FROZEN_TOOL_AUTHORITY"

class AuthorityError(ValueError):
    pass


def _canon(obj:Any)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()


def _sha(obj:Any)->str:
    return "sha256:"+hashlib.sha256(_canon(obj)).hexdigest()


def _required(xs:Sequence[str])->list[str]:
    out=sorted({str(x) for x in xs if str(x)})
    if not out or any(any(ch.isspace() for ch in x) for x in out):
        raise AuthorityError("INVALID_REQUIRED_CAPABILITIES")
    return out


class CommonFrozenToolAuthority:
    """One exact authority snapshot shared by Brain and comparator."""

    def __init__(self, entries:Sequence[Mapping[str,Any]], *, epoch:int=0):
        if isinstance(epoch,bool) or not isinstance(epoch,int) or epoch<0:
            raise AuthorityError("INVALID_EPOCH")
        self._epoch=epoch
        self._registry:dict[str,dict[str,Any]]={}
        self._hidden:dict[str,frozenset[str]]={}
        for raw in entries:
            if not isinstance(raw,Mapping):
                raise AuthorityError("ENTRY_NOT_MAPPING")
            tid=str(raw.get("tool_id") or "")
            if not tid or tid in self._registry:
                raise AuthorityError("INVALID_OR_DUPLICATE_TOOL_ID")
            cost=raw.get("cost")
            if isinstance(cost,bool) or not isinstance(cost,(int,float)) or not math.isfinite(float(cost)) or float(cost)<0:
                raise AuthorityError("INVALID_TOOL_COST")
            public={
                "tool_id":tid,
                "cost":float(cost),
                "available":raw.get("available") is True,
                "authorized":raw.get("authorized") is True,
                "epoch":epoch,
            }
            meta=raw.get("meta")
            if isinstance(meta,Mapping):
                public["meta"]=dict(meta)
            self._registry[tid]=public
            hidden=raw.get("hidden_capabilities",[])
            if not isinstance(hidden,(list,tuple,set,frozenset)):
                raise AuthorityError("HIDDEN_CAPABILITIES_NOT_SEQUENCE")
            self._hidden[tid]=frozenset(str(x) for x in hidden if str(x))

    @property
    def epoch(self)->int:
        return self._epoch

    def registry_ids(self)->tuple[str,...]:
        return tuple(sorted(self._registry))

    def _hidden_commitment(self)->str:
        return _sha({tid:sorted(self._hidden[tid]) for tid in sorted(self._hidden)})

    def _source_payload(self)->dict[str,Any]:
        return {
            "epoch":self._epoch,
            "registry":[self._registry[tid] for tid in sorted(self._registry)],
            "hidden_commitment":self._hidden_commitment(),
        }

    def discovery_source(self)->dict[str,Any]:
        return {
            "source_id":SOURCE_ID,
            "cost":0.0,
            "available":True,
            "authorized":True,
            "authoritative":True,
            "source_epoch":self._epoch,
            "source_digest":_sha(self._source_payload()),
        }

    def source_set_digest(self)->str:
        return _sha([self.discovery_source()])

    def initial_public(self, required_capabilities:Sequence[str], *, constraint:Mapping[str,Any]|None=None)->dict[str,Any]:
        req=_required(required_capabilities)
        return {
            "required_capabilities":req,
            "constraint":dict(constraint) if isinstance(constraint,Mapping) else None,
            "visible_tools":[],
            "prior_probe_receipts":[],
            "discovery_sources":[self.discovery_source()],
            "discovery_receipts":[],
            "version_events":[],
            "decision_epoch":self._epoch,
            "source_set_digest":self.source_set_digest(),
        }

    def discover(self, required_capabilities:Sequence[str])->dict[str,Any]:
        req=_required(required_capabilities)
        query=" ".join(req)
        # Safe probing is an evaluation-harness operation, not an assertion that
        # the capability is supported. Every queried requirement can be tested
        # without exposing hidden support truth.
        tools=[]
        for tid in sorted(self._registry):
            row=dict(self._registry[tid])
            row["safe_probe_capabilities"]=list(req)
            tools.append(row)
        source=self.discovery_source()
        return {
            "kind":"DISCOVERY_RESULT",
            "source_id":SOURCE_ID,
            "complete":True,
            "decision_epoch":self._epoch,
            "source_epoch":self._epoch,
            "source_digest":source["source_digest"],
            "source_set_digest":self.source_set_digest(),
            "query":query,
            "tools":tools,
        }

    def probe(self, tool_id:str, capability:str, *, episode_epoch:int, required_capabilities:Sequence[str])->dict[str,Any]:
        if episode_epoch!=self._epoch:
            raise AuthorityError("EPOCH_CHANGED_RESTART_EPISODE")
        tid=str(tool_id or ""); cap=str(capability or "")
        if tid not in self._registry:
            raise AuthorityError("UNREGISTERED_TOOL_ID")
        req=_required(required_capabilities)
        if cap not in req:
            raise AuthorityError("PROBE_OUTSIDE_EXACT_REQUIREMENT_QUERY")
        return {
            "kind":"SAFE_CAPABILITY_PROBE",
            "tool_id":tid,
            "capability":cap,
            "epoch":self._epoch,
            "supported":cap in self._hidden[tid],
        }

    def gate_invoke(self, role:str, tool_id:str, *, episode_epoch:int)->dict[str,Any]:
        if role not in {"BRAIN","COMPARATOR"}:
            raise AuthorityError("INVALID_ROLE")
        if episode_epoch!=self._epoch:
            raise AuthorityError("EPOCH_CHANGED_RESTART_EPISODE")
        tid=str(tool_id or "")
        if tid not in self._registry:
            raise AuthorityError("UNREGISTERED_TOOL_ID")
        return {"role":role,"tool_id":tid,"epoch":self._epoch}

    def replace(self, entries:Sequence[Mapping[str,Any]])->"CommonFrozenToolAuthority":
        return CommonFrozenToolAuthority(entries,epoch=self._epoch+1)


def prove_common_authority_instance(entries:Sequence[Mapping[str,Any]], required_capabilities:Sequence[str])->dict[str,Any]:
    a=CommonFrozenToolAuthority(entries)
    req=_required(required_capabilities)
    public=a.initial_public(req)
    source=public["discovery_sources"][0]
    receipt=a.discover(req)
    ids=tuple(sorted(str(x["tool_id"]) for x in receipt["tools"]))
    hidden_text=json.dumps(receipt,sort_keys=True).lower()
    brain_ids=tuple(
        tid for tid in a.registry_ids()
        if a.gate_invoke("BRAIN",tid,episode_epoch=a.epoch)["tool_id"]==tid
    )
    comparator_ids=tuple(
        tid for tid in a.registry_ids()
        if a.gate_invoke("COMPARATOR",tid,episode_epoch=a.epoch)["tool_id"]==tid
    )
    return {
        "status":"PASS__COMMON_AUTHORITY_COMPLETE_INTERFACE_BY_CONSTRUCTION"
            if (
                public["visible_tools"]==[]
                and source["source_id"]==SOURCE_ID
                and source["authoritative"] is True
                and receipt["complete"] is True
                and receipt["source_set_digest"]==public["source_set_digest"]
                and ids==a.registry_ids()==brain_ids==comparator_ids
                and "_hidden" not in hidden_text
                and "hidden_capabilities" not in hidden_text
                and all(x["safe_probe_capabilities"]==req for x in receipt["tools"])
            ) else "FAIL_CLOSED",
        "identity_universe_complete":ids==a.registry_ids(),
        "same_brain_comparator_authority":brain_ids==comparator_ids==a.registry_ids(),
        "identities_initially_hidden":public["visible_tools"]==[],
        "hidden_capability_truth_not_disclosed":"hidden_capabilities" not in hidden_text and "_hidden" not in hidden_text,
        "all_exact_requirement_probes_safely_decidable":all(x["safe_probe_capabilities"]==req for x in receipt["tools"]),
        "source_set_complete_by_construction":True,
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
