"""Bounded deterministic research planning for normalized evidence gaps.

No semantic claims are invented. Queries are compiled from already-normalized gap
fields. Source selection performs exact Pareto dominance over explicit metadata and
returns a frontier when no unique winner is justified.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import FrozenSet,Sequence

@dataclass(frozen=True)
class EvidenceGap:
    gap_id:str
    subject:str
    relation:str
    qualifiers:tuple[str,...]=()
    preferred_domains:tuple[str,...]=()

@dataclass(frozen=True)
class Source:
    source_id:str
    supports:FrozenSet[str]
    authority_rank:int
    directness:float
    age_days:float
    cost:float
    verified_metadata:bool=True

def compile_queries(gap:EvidenceGap)->dict:
    if not gap.gap_id or not gap.subject.strip() or not gap.relation.strip():
        return {"status":"FAIL_CLOSED","reason":"GAP_FIELDS_INCOMPLETE"}
    qbase=f'"{gap.subject.strip()}" "{gap.relation.strip()}"'
    quals=" ".join(x.strip() for x in gap.qualifiers if x.strip())
    base=(qbase+" "+quals).strip()
    queries=[base]
    for domain in sorted(set(x.strip() for x in gap.preferred_domains if x.strip())):
        if any(ch.isspace() for ch in domain) or "/" in domain:
            return {"status":"FAIL_CLOSED","reason":"DOMAIN_INVALID"}
        queries.append(f"site:{domain} {base}")
    return {
        "status":"COMPILED",
        "gap_id":gap.gap_id,
        "queries":queries,
        "scope":"NORMALIZED_EXPLICIT_EVIDENCE_GAP_ONLY",
        "terminal_authority":False,
    }

def _valid(s:Source)->bool:
    return (
        isinstance(s.authority_rank,int) and not isinstance(s.authority_rank,bool) and s.authority_rank>=0
        and isinstance(s.directness,(int,float)) and not isinstance(s.directness,bool) and 0<=float(s.directness)<=1
        and isinstance(s.age_days,(int,float)) and not isinstance(s.age_days,bool) and float(s.age_days)>=0
        and isinstance(s.cost,(int,float)) and not isinstance(s.cost,bool) and float(s.cost)>=0
    )

def source_frontier(required_tags:set[str],sources:Sequence[Source])->dict:
    ids=[s.source_id for s in sources]
    if any(not isinstance(x,str) or not x for x in ids) or len(ids)!=len(set(ids)):
        return {"status":"FAIL_CLOSED","reason":"SOURCE_IDENTITIES_INVALID_OR_DUPLICATE"}
    eligible=[
        s for s in sources
        if s.verified_metadata and _valid(s) and set(required_tags).issubset(s.supports)
    ]
    if not eligible:
        return {"status":"ESCALATE","reason":"NO_VERIFIED_SOURCE_WITH_REQUIRED_EXPLICIT_COVERAGE","frontier":[]}
    kept=[]
    deleted=[]
    for b in eligible:
        dominator=None
        for a in eligible:
            if a.source_id==b.source_id: continue
            no_worse=(
                a.supports.issuperset(b.supports)
                and a.authority_rank<=b.authority_rank
                and a.directness>=b.directness
                and a.age_days<=b.age_days
                and a.cost<=b.cost
            )
            strict=(
                a.supports>b.supports or a.authority_rank<b.authority_rank
                or a.directness>b.directness or a.age_days<b.age_days or a.cost<b.cost
            )
            if no_worse and strict:
                dominator=a.source_id
                break
        if dominator is None: kept.append(b.source_id)
        else: deleted.append({"source_id":b.source_id,"dominated_by":dominator})
    kept=sorted(kept)
    return {
        "status":"SELECT" if len(kept)==1 else "FRONTIER",
        "selected_source_id":kept[0] if len(kept)==1 else None,
        "frontier":kept,
        "dominance_deletions":sorted(deleted,key=lambda x:x["source_id"]),
        "reason":"UNIQUE_PARETO_DOMINANT_SOURCE" if len(kept)==1 else "MULTIPLE_NONDOMINATED_SOURCES_REQUIRE_MORE_INFORMATION_OR_EXPLICIT_UTILITY",
        "terminal_authority":False,
    }
