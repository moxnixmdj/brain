from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping

class PortfolioAccountingError(ValueError): pass

@dataclass(frozen=True)
class Artifact:
    artifact_id:str
    content_sha256:str
    byte_count:int
    category:str

_ALLOWED={"LEARNED_TARGET","DETERMINISTIC_TARGET","SHARED_CAPABILITY","PERSISTENT_TASK_STATE"}

def artifact(artifact_id:str,content_sha256:str,byte_count:int,category:str)->Artifact:
    if not isinstance(artifact_id,str) or not artifact_id: raise PortfolioAccountingError("ARTIFACT_ID_INVALID")
    if not isinstance(content_sha256,str) or len(content_sha256)!=64: raise PortfolioAccountingError("SHA_INVALID")
    if not isinstance(byte_count,int) or isinstance(byte_count,bool) or byte_count<0: raise PortfolioAccountingError("BYTE_COUNT_INVALID")
    if category not in _ALLOWED: raise PortfolioAccountingError("CATEGORY_INVALID")
    return Artifact(artifact_id,content_sha256,byte_count,category)

def _index(artifacts:Iterable[Artifact]):
    by_id={}
    by_sha={}
    for a in artifacts:
        if a.artifact_id in by_id and by_id[a.artifact_id]!=a:
            raise PortfolioAccountingError("ARTIFACT_ID_CONFLICT")
        by_id[a.artifact_id]=a
        if a.content_sha256 in by_sha and by_sha[a.content_sha256].byte_count!=a.byte_count:
            raise PortfolioAccountingError("CONTENT_SIZE_CONFLICT")
        by_sha.setdefault(a.content_sha256,a)
    return by_id,by_sha

def standalone_bytes(capability_refs:Iterable[str],artifacts:Iterable[Artifact])->int:
    by_id,_=_index(artifacts)
    refs=list(capability_refs)
    if any(r not in by_id for r in refs): raise PortfolioAccountingError("UNKNOWN_REF")
    # Content-addressed dedupe even within one capability.
    seen=set(); total=0
    for r in refs:
        a=by_id[r]
        if a.content_sha256 not in seen:
            seen.add(a.content_sha256); total+=a.byte_count
    return total

def portfolio_total_bytes(capability_map:Mapping[str,Iterable[str]],artifacts:Iterable[Artifact])->int:
    by_id,_=_index(artifacts)
    if not isinstance(capability_map,Mapping): raise PortfolioAccountingError("CAPABILITY_MAP_INVALID")
    seen=set(); total=0
    for cid,refs in capability_map.items():
        if not isinstance(cid,str) or not cid: raise PortfolioAccountingError("CAPABILITY_ID_INVALID")
        for r in refs:
            if r not in by_id: raise PortfolioAccountingError("UNKNOWN_REF")
            a=by_id[r]
            if a.content_sha256 not in seen:
                seen.add(a.content_sha256); total+=a.byte_count
    return total

def marginal_bytes(existing_refs:Iterable[str],new_refs:Iterable[str],artifacts:Iterable[Artifact])->int:
    by_id,_=_index(artifacts)
    existing_sha=set()
    for r in existing_refs:
        if r not in by_id: raise PortfolioAccountingError("UNKNOWN_REF")
        existing_sha.add(by_id[r].content_sha256)
    total=0; added=set()
    for r in new_refs:
        if r not in by_id: raise PortfolioAccountingError("UNKNOWN_REF")
        a=by_id[r]
        if a.content_sha256 not in existing_sha and a.content_sha256 not in added:
            added.add(a.content_sha256); total+=a.byte_count
    return total

def category_bytes(capability_map:Mapping[str,Iterable[str]],artifacts:Iterable[Artifact])->dict[str,int]:
    by_id,_=_index(artifacts)
    seen=set(); totals={k:0 for k in sorted(_ALLOWED)}
    for refs in capability_map.values():
        for r in refs:
            if r not in by_id: raise PortfolioAccountingError("UNKNOWN_REF")
            a=by_id[r]
            if a.content_sha256 in seen: continue
            seen.add(a.content_sha256)
            totals[a.category]+=a.byte_count
    totals["TARGET_ADAPTED_TOTAL"]=totals["LEARNED_TARGET"]+totals["DETERMINISTIC_TARGET"]+totals["SHARED_CAPABILITY"]
    return totals

def report(capability_map:Mapping[str,Iterable[str]],artifacts:Iterable[Artifact],*,reference_machine_id:str)->dict:
    arts=list(artifacts)
    total=portfolio_total_bytes(capability_map,arts)
    standalone={cid:standalone_bytes(refs,arts) for cid,refs in capability_map.items()}
    summed=sum(standalone.values())
    cats=category_bytes(capability_map,arts)
    return {
        "reference_machine_id":reference_machine_id,
        "portfolio_unique_bytes":total,
        "portfolio_unique_bits":8*total,
        "summed_standalone_bytes":summed,
        "reuse_savings_bytes":summed-total,
        "standalone_bytes":standalone,
        "category_bytes":cats,
        "shared_capability_bytes_are_free":False,
    }
