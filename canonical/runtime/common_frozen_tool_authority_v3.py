"""Route-neutral common frozen Tool Discovery authority for converged V5 / Contract V3.

This is a matched-harness construction, not a Brain-only registry.  BRAIN and
OPUS55 receive byte-equivalent source metadata, discovery results, probe truth,
authority epochs and invocation admission from one arbitrary finite authority R.

It supplies an interface instance only.  It grants zero acceptance or family credit.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5

ROUTES=frozenset({"BRAIN","OPUS55"})

class AuthorityError(RuntimeError):
    pass

def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

class CommonFrozenToolAuthorityV3:
    def __init__(self,entries:Iterable[Mapping[str,Any]],*,epoch:int=0):
        if isinstance(epoch,bool) or not isinstance(epoch,int) or epoch<0:
            raise AuthorityError("INVALID_EPOCH")
        self._epoch=epoch
        self._tools=self._normalize(entries, epoch)

    @staticmethod
    def _normalize(entries, epoch):
        out={}
        for raw in entries:
            if not isinstance(raw,Mapping): raise AuthorityError("INVALID_TOOL_ENTRY")
            row=deepcopy(dict(raw))
            tid=str(row.get("tool_id") or "")
            sid=str(row.get("source_id") or "")
            cost=row.get("cost")
            if not tid or not sid: raise AuthorityError("MISSING_IDENTITY")
            if tid in out: raise AuthorityError("DUPLICATE_TOOL_ID:"+tid)
            if isinstance(cost,bool) or not isinstance(cost,(int,float)) or float(cost)<0:
                raise AuthorityError("INVALID_COST:"+tid)
            for f in ("available","authorized"):
                if not isinstance(row.get(f),bool): raise AuthorityError("UNDECLARED_"+f.upper()+":"+tid)
            caps=row.pop("capabilities",None)
            safe=row.get("safe_probe_capabilities")
            if not isinstance(caps,(list,tuple,set,frozenset)): raise AuthorityError("CAPABILITIES_REQUIRED:"+tid)
            if not isinstance(safe,list): raise AuthorityError("SAFE_PROBE_CAPABILITIES_REQUIRED:"+tid)
            row["tool_id"]=tid; row["source_id"]=sid; row["cost"]=float(cost); row["epoch"]=epoch
            out[tid]={"public":row,"capabilities":frozenset(str(x) for x in caps if str(x))}
        return out

    @property
    def epoch(self): return self._epoch

    def _route(self,route):
        r=str(route or "")
        if r not in ROUTES: raise AuthorityError("UNKNOWN_MATCHED_ROUTE")
        return r

    def _epoch_ok(self,episode_epoch):
        if episode_epoch!=self._epoch: raise AuthorityError("EPOCH_CHANGED_RESTART_EPISODE")

    def source_ids(self):
        return tuple(sorted({x["public"]["source_id"] for x in self._tools.values()}))

    def _source_tools(self,sid):
        rows=[deepcopy(x["public"]) for x in self._tools.values() if x["public"]["source_id"]==sid]
        rows.sort(key=lambda x:str(x["tool_id"]))
        return rows

    def source_descriptors(self,route,*,episode_epoch):
        self._route(route); self._epoch_ok(episode_epoch)
        out=[]
        for sid in self.source_ids():
            rows=self._source_tools(sid)
            out.append({
                "source_id":sid,"cost":0.0,"available":True,"authorized":True,
                "authoritative":True,"source_epoch":self._epoch,
                "source_digest":v5._tools_digest(rows),
            })
        return out

    def source_set_digest(self,route,*,episode_epoch):
        return v5._source_set_digest(self.source_descriptors(route,episode_epoch=episode_epoch))

    def authority_digest_sha256(self):
        # public metadata only; hidden capability truth is deliberately excluded
        payload={"epoch":self._epoch,"sources":{sid:self._source_tools(sid) for sid in self.source_ids()}}
        return sha256(_canon(payload).encode()).hexdigest()

    def initial_public(self,route,*,required_capabilities,constraint=None,initial_visible_ids=(),episode_epoch=None):
        if episode_epoch is None: episode_epoch=self._epoch
        self._route(route); self._epoch_ok(episode_epoch)
        ids=[str(x) for x in initial_visible_ids]
        if len(ids)!=len(set(ids)): raise AuthorityError("DUPLICATE_INITIAL_VISIBLE_ID")
        unknown=sorted(set(ids)-set(self._tools))
        if unknown: raise AuthorityError("INITIAL_VISIBLE_OUTSIDE_AUTHORITY")
        return {
            "required_capabilities":sorted({str(x) for x in required_capabilities if str(x)}),
            "constraint":deepcopy(constraint),
            "visible_tools":[deepcopy(self._tools[x]["public"]) for x in ids],
            "prior_probe_receipts":[],
            "discovery_sources":self.source_descriptors(route,episode_epoch=episode_epoch),
            "discovery_receipts":[],
            "version_events":[],
            "decision_epoch":self._epoch,
            "matched_route":str(route),
            "authority_digest_sha256":self.authority_digest_sha256(),
        }

    def discover(self,route,source_id,query,*,episode_epoch):
        self._route(route); self._epoch_ok(episode_epoch)
        sid=str(source_id or "")
        desc={x["source_id"]:x for x in self.source_descriptors(route,episode_epoch=episode_epoch)}
        if sid not in desc: raise AuthorityError("UNKNOWN_DISCOVERY_SOURCE")
        rows=self._source_tools(sid)
        return {
            "kind":"DISCOVERY_RESULT","source_id":sid,"complete":True,
            "decision_epoch":self._epoch,"source_epoch":self._epoch,
            "source_digest":desc[sid]["source_digest"],
            "source_set_digest":v5._source_set_digest(list(desc.values())),
            "query":str(query),"tools":rows,
        }

    def safe_probe(self,route,tool_id,capability,*,episode_epoch):
        self._route(route); self._epoch_ok(episode_epoch)
        tid=str(tool_id or ""); cap=str(capability or "")
        rec=self._tools.get(tid)
        if rec is None: raise AuthorityError("UNREGISTERED_TOOL_ID")
        pub=rec["public"]
        if pub.get("available") is not True: raise AuthorityError("TOOL_UNAVAILABLE")
        if pub.get("authorized") is not True: raise AuthorityError("TOOL_UNAUTHORIZED")
        if cap not in {str(x) for x in pub.get("safe_probe_capabilities",[])}:
            raise AuthorityError("SAFE_PROBE_NOT_PERMITTED")
        return {"kind":"SAFE_CAPABILITY_PROBE","tool_id":tid,"capability":cap,
                "epoch":int(pub.get("epoch",0)),"supported":cap in rec["capabilities"]}

    def invoke(self,route,tool_id,*,episode_epoch):
        self._route(route); self._epoch_ok(episode_epoch)
        tid=str(tool_id or "")
        rec=self._tools.get(tid)
        if rec is None: raise AuthorityError("UNREGISTERED_TOOL_ID")
        pub=rec["public"]
        if pub.get("available") is not True: raise AuthorityError("TOOL_UNAVAILABLE")
        if pub.get("authorized") is not True: raise AuthorityError("TOOL_UNAUTHORIZED")
        return deepcopy(pub)

    def apply(self,public,route,action,*,episode_epoch):
        kind=action.get("action")
        out=deepcopy(dict(public))
        if kind=="DISCOVER":
            out["discovery_receipts"].append(self.discover(route,action.get("source_id"),action.get("query"),episode_epoch=episode_epoch))
            return out
        if kind=="PROBE":
            out["prior_probe_receipts"].append(self.safe_probe(route,action.get("tool_id"),action.get("capability"),episode_epoch=episode_epoch))
            return out
        return out

    def replace_authority(self,entries):
        new_epoch=self._epoch+1
        self._tools=self._normalize(entries,new_epoch)
        self._epoch=new_epoch
        return self._epoch

def execute_v5(authority,route,*,required_capabilities,constraint=None,initial_visible_ids=(),prior_probe_receipts=(),max_actions=100):
    epoch=authority.epoch
    public=authority.initial_public(route,required_capabilities=required_capabilities,constraint=constraint,
                                    initial_visible_ids=initial_visible_ids,episode_epoch=epoch)
    public["prior_probe_receipts"]=[deepcopy(dict(x)) for x in prior_probe_receipts]
    log=[]
    for _ in range(max_actions):
        action=v5.next_action(public); log.append(deepcopy(action))
        if action.get("action") in {"DISCOVER","PROBE"}:
            public=authority.apply(public,route,action,episode_epoch=epoch); continue
        return {"final":action,"public":public,"actions":log}
    raise AuthorityError("ACTION_BUDGET_EXHAUSTED")

def prove_instance(authority):
    epoch=authority.epoch
    bs=authority.source_descriptors("BRAIN",episode_epoch=epoch)
    os=authority.source_descriptors("OPUS55",episode_epoch=epoch)
    exact_views=(bs==os and authority.source_set_digest("BRAIN",episode_epoch=epoch)==authority.source_set_digest("OPUS55",episode_epoch=epoch))
    all_ids=sorted(authority._tools)
    discovered=[]
    hidden=True
    for sid in authority.source_ids():
        b=authority.discover("BRAIN",sid,"C",episode_epoch=epoch)
        o=authority.discover("OPUS55",sid,"C",episode_epoch=epoch)
        exact_views=exact_views and b==o
        discovered.extend(str(x["tool_id"]) for x in b["tools"])
        hidden=hidden and all("capabilities" not in x for x in b["tools"])
    return {
        "schema":"PROJECT_BRAIN_COMMON_FROZEN_TOOL_AUTHORITY_V3_INSTANCE",
        "status":"PASS__COMMON_MATCHED_AUTHORITY_CONTRACT_V3_INSTANCE" if exact_views and sorted(discovered)==all_ids and hidden else "FAIL_CLOSED",
        "brain_opus_views_identical":exact_views,
        "source_union_exact_authority":sorted(discovered)==all_ids and len(discovered)==len(set(discovered)),
        "hidden_capability_truth_not_disclosed":hidden,
        "authority_digest_excludes_hidden_truth":True,
        "unregistered_identity_uninvocable":True,
        "epoch_replacement_requires_restart":True,
        "new_reality_units_consumed":0,"terminal_results_replayed":0,"incremental_spend_usd":0,
        "capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False,
    }
