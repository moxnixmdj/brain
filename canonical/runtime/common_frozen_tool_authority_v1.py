"""Common frozen matched tool authority for Tool Discovery V6.

Both BRAIN and COMPARATOR are gated by the exact same finite authority snapshot.
Tool identities are hidden initially and partitioned across any finite number of
authoritative discovery sources. Each source digest is exactly the digest of the
public tool metadata it returns, using the same canonicalization as the V5 proof
core. Hidden capability truth is never part of discovery metadata.

Safe-probe permission is fixed metadata of the frozen authority snapshot. It is
not synthesized from the current query. Therefore source content digests remain
stable within an authority epoch. V6 handles any authority/tool version change as
an episode-restart boundary before old discovery metadata can be reused.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

DEFAULT_SOURCE_ID="SRC0"


class AuthorityError(ValueError):
    pass


def _required(xs:Sequence[str])->list[str]:
    out=sorted({str(x) for x in xs if str(x)})
    if not out or any(any(ch.isspace() for ch in x) for x in out):
        raise AuthorityError("INVALID_REQUIRED_CAPABILITIES")
    return out


def _tools_digest(tools:Sequence[Mapping[str,Any]])->str:
    rows=[dict(x) for x in tools]
    rows.sort(key=lambda row:str(row.get("tool_id") or ""))
    raw=json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return "sha256:"+hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _source_set_digest(sources:Sequence[Mapping[str,Any]])->str:
    payload=[]
    for source in sources:
        payload.append({
            "source_id":str(source.get("source_id") or ""),
            "cost":float(source.get("cost",0.0)),
            "available":source.get("available"),
            "authorized":source.get("authorized"),
            "authoritative":source.get("authoritative"),
            "source_epoch":source.get("source_epoch"),
            "source_digest":str(source.get("source_digest") or ""),
        })
    payload.sort(key=lambda row:row["source_id"])
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return "sha256:"+hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CommonFrozenToolAuthority:
    """One finite, content-addressed tool authority shared by both matched roles."""

    def __init__(self, entries:Sequence[Mapping[str,Any]], *, epoch:int=0):
        if isinstance(epoch,bool) or not isinstance(epoch,int) or epoch<0:
            raise AuthorityError("INVALID_EPOCH")
        if not isinstance(entries,Sequence):
            raise AuthorityError("ENTRIES_NOT_SEQUENCE")
        self._epoch=epoch
        self._registry:dict[str,dict[str,Any]]={}
        self._hidden:dict[str,frozenset[str]]={}
        self._source_for_tool:dict[str,str]={}
        self._source_cost:dict[str,float]={}

        for raw in entries:
            if not isinstance(raw,Mapping):
                raise AuthorityError("ENTRY_NOT_MAPPING")
            tid=str(raw.get("tool_id") or "")
            if not tid or tid in self._registry:
                raise AuthorityError("INVALID_OR_DUPLICATE_TOOL_ID")
            cost=raw.get("cost")
            if isinstance(cost,bool) or not isinstance(cost,(int,float)) or not math.isfinite(float(cost)) or float(cost)<0:
                raise AuthorityError("INVALID_TOOL_COST")

            sid=str(raw.get("source_id") or DEFAULT_SOURCE_ID)
            scost=raw.get("source_cost",0.0)
            if isinstance(scost,bool) or not isinstance(scost,(int,float)) or not math.isfinite(float(scost)) or float(scost)<0:
                raise AuthorityError("INVALID_SOURCE_COST")
            scost=float(scost)
            if sid in self._source_cost and self._source_cost[sid]!=scost:
                raise AuthorityError("CONFLICTING_SOURCE_COST")
            self._source_cost[sid]=scost

            safe=raw.get("safe_probe_capabilities",[])
            if not isinstance(safe,(list,tuple,set,frozenset)):
                raise AuthorityError("SAFE_PROBE_CAPABILITIES_NOT_SEQUENCE")
            safe_ids=sorted({str(x) for x in safe if str(x)})

            public={
                "tool_id":tid,
                "cost":float(cost),
                "available":raw.get("available") is True,
                "authorized":raw.get("authorized") is True,
                "epoch":epoch,
                "safe_probe_capabilities":safe_ids,
            }
            meta=raw.get("meta")
            if isinstance(meta,Mapping):
                public["meta"]=dict(meta)
            self._registry[tid]=public
            self._source_for_tool[tid]=sid

            hidden=raw.get("hidden_capabilities",[])
            if not isinstance(hidden,(list,tuple,set,frozenset)):
                raise AuthorityError("HIDDEN_CAPABILITIES_NOT_SEQUENCE")
            self._hidden[tid]=frozenset(str(x) for x in hidden if str(x))

    @property
    def epoch(self)->int:
        return self._epoch

    def registry_ids(self)->tuple[str,...]:
        return tuple(sorted(self._registry))

    def source_ids(self)->tuple[str,...]:
        return tuple(sorted(self._source_cost))

    def public_tools_for_source(self, source_id:str)->list[dict[str,Any]]:
        sid=str(source_id or "")
        if sid not in self._source_cost:
            raise AuthorityError("UNKNOWN_SOURCE_ID")
        return [
            dict(self._registry[tid])
            for tid in sorted(self._registry)
            if self._source_for_tool[tid]==sid
        ]

    def discovery_sources(self)->list[dict[str,Any]]:
        return [
            {
                "source_id":sid,
                "cost":self._source_cost[sid],
                "available":True,
                "authorized":True,
                "authoritative":True,
                "source_epoch":self._epoch,
                "source_digest":_tools_digest(self.public_tools_for_source(sid)),
            }
            for sid in self.source_ids()
        ]

    def source_set_digest(self)->str:
        return _source_set_digest(self.discovery_sources())

    def initial_public(
        self,
        required_capabilities:Sequence[str],
        *,
        constraint:Mapping[str,Any]|None=None,
        prior_probe_receipts:Sequence[Mapping[str,Any]]=(),
    )->dict[str,Any]:
        req=_required(required_capabilities)
        return {
            "required_capabilities":req,
            "constraint":dict(constraint) if isinstance(constraint,Mapping) else None,
            "visible_tools":[],
            "prior_probe_receipts":[dict(x) for x in prior_probe_receipts],
            "discovery_sources":self.discovery_sources(),
            "discovery_receipts":[],
            "version_events":[],
            "decision_epoch":self._epoch,
            "source_set_digest":self.source_set_digest(),
        }

    def discover(self, source_id:str, required_capabilities:Sequence[str])->dict[str,Any]:
        sid=str(source_id or "")
        req=_required(required_capabilities)
        sources={x["source_id"]:x for x in self.discovery_sources()}
        if sid not in sources:
            raise AuthorityError("UNKNOWN_SOURCE_ID")
        return {
            "kind":"DISCOVERY_RESULT",
            "source_id":sid,
            "complete":True,
            "decision_epoch":self._epoch,
            "source_epoch":self._epoch,
            "source_digest":sources[sid]["source_digest"],
            "source_set_digest":self.source_set_digest(),
            "query":" ".join(req),
            "tools":self.public_tools_for_source(sid),
        }

    def probe(
        self,
        tool_id:str,
        capability:str,
        *,
        episode_epoch:int,
        required_capabilities:Sequence[str],
    )->dict[str,Any]:
        if episode_epoch!=self._epoch:
            raise AuthorityError("EPOCH_CHANGED_RESTART_EPISODE")
        tid=str(tool_id or ""); cap=str(capability or "")
        if tid not in self._registry:
            raise AuthorityError("UNREGISTERED_TOOL_ID")
        req=_required(required_capabilities)
        if cap not in req:
            raise AuthorityError("PROBE_OUTSIDE_EXACT_REQUIREMENT_QUERY")
        if cap not in set(self._registry[tid]["safe_probe_capabilities"]):
            raise AuthorityError("PROBE_NOT_SAFE_FOR_FROZEN_AUTHORITY")
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

    def version_change_event(self, tool_id:str, *, new_epoch:int|None=None)->dict[str,Any]:
        tid=str(tool_id or "")
        if tid not in self._registry:
            raise AuthorityError("UNREGISTERED_TOOL_ID")
        epoch=self._epoch+1 if new_epoch is None else new_epoch
        if isinstance(epoch,bool) or not isinstance(epoch,int) or epoch<=self._epoch:
            raise AuthorityError("INVALID_NEW_EPOCH")
        return {"kind":"TOOL_VERSION_CHANGED","tool_id":tid,"new_epoch":epoch}

    def replace(self, entries:Sequence[Mapping[str,Any]])->"CommonFrozenToolAuthority":
        return CommonFrozenToolAuthority(entries,epoch=self._epoch+1)


def prove_common_authority_instance(
    entries:Sequence[Mapping[str,Any]],
    required_capabilities:Sequence[str],
)->dict[str,Any]:
    a=CommonFrozenToolAuthority(entries)
    req=_required(required_capabilities)
    public=a.initial_public(req)
    receipts=[a.discover(sid,req) for sid in a.source_ids()]
    ids=tuple(sorted(str(t["tool_id"]) for r in receipts for t in r["tools"]))
    receipt_text=json.dumps(receipts,sort_keys=True).lower()
    brain_ids=tuple(
        tid for tid in a.registry_ids()
        if a.gate_invoke("BRAIN",tid,episode_epoch=a.epoch)["tool_id"]==tid
    )
    comparator_ids=tuple(
        tid for tid in a.registry_ids()
        if a.gate_invoke("COMPARATOR",tid,episode_epoch=a.epoch)["tool_id"]==tid
    )
    source_ids=tuple(sorted(x["source_id"] for x in public["discovery_sources"]))
    complete_sources=tuple(sorted(str(r["source_id"]) for r in receipts))
    digests_ok=all(
        _tools_digest(r["tools"])==r["source_digest"]
        for r in receipts
    ) and all(
        r["source_set_digest"]==_source_set_digest(public["discovery_sources"])
        for r in receipts
    )
    return {
        "status":"PASS__COMMON_AUTHORITY_COMPLETE_INTERFACE_BY_CONSTRUCTION"
            if (
                public["visible_tools"]==[]
                and source_ids==complete_sources==a.source_ids()
                and all(x["authoritative"] is True for x in public["discovery_sources"])
                and all(r["complete"] is True for r in receipts)
                and digests_ok
                and ids==a.registry_ids()==brain_ids==comparator_ids
                and "hidden_capabilities" not in receipt_text
                and "supported" not in receipt_text
            ) else "FAIL_CLOSED",
        "identity_universe_complete":ids==a.registry_ids(),
        "source_union_complete":source_ids==complete_sources==a.source_ids(),
        "same_brain_comparator_authority":brain_ids==comparator_ids==a.registry_ids(),
        "identities_initially_hidden":public["visible_tools"]==[],
        "hidden_capability_truth_not_disclosed":(
            "hidden_capabilities" not in receipt_text and "supported" not in receipt_text
        ),
        "source_and_source_set_digests_exact":digests_ok,
        "source_set_complete_by_construction":True,
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
