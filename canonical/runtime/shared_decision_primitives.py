"""Brain-owned bounded shared decision primitives.

These primitives intentionally solve only cases where requirements, capabilities,
evidence relations, and causal support are explicit. Unknown semantics fail closed.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
import math
from typing import FrozenSet, Iterable, Sequence


def _finite_nonnegative(value: float) -> bool:
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(float(value)) and float(value)>=0.0


def _finite01(value: float) -> bool:
    return _finite_nonnegative(value) and float(value)<=1.0


def _unique_nonempty(values) -> bool:
    vals=list(values)
    return all(isinstance(x,str) and bool(x.strip()) for x in vals) and len(vals)==len(set(vals))

@dataclass(frozen=True)
class ToolRoute:
    route_id: str
    capabilities: FrozenSet[str]
    cost: float = 0.0
    available: bool = True
    authorized: bool = True
    verified: bool = True

@dataclass(frozen=True)
class ToolDecision:
    status: str
    route_id: str | None
    reason: str

def select_verified_tool(required: Iterable[str], routes: Sequence[ToolRoute]) -> ToolDecision:
    req=frozenset(required)
    if not _unique_nonempty(r.route_id for r in routes):
        return ToolDecision("ESCALATE",None,"ROUTE_IDENTITIES_INVALID_OR_DUPLICATE")
    eligible=[
        r for r in routes
        if r.available and r.authorized and r.verified
        and _finite_nonnegative(r.cost)
        and req.issubset(r.capabilities)
    ]
    if not eligible:
        return ToolDecision("ESCALATE",None,"NO_VERIFIED_SUFFICIENT_ROUTE")
    eligible.sort(key=lambda r:(r.cost,len(r.capabilities-req),r.route_id))
    return ToolDecision("SELECT",eligible[0].route_id,"MIN_COST_VERIFIED_SUFFICIENT_ROUTE")

@dataclass(frozen=True)
class Task:
    task_id: str
    deps: FrozenSet[str]
    required_capabilities: FrozenSet[str]
    priority: int = 0

@dataclass(frozen=True)
class Worker:
    worker_id: str
    capabilities: FrozenSet[str]

def _downstream_counts(tasks: Sequence[Task]) -> dict[str,int]:
    children={t.task_id:set() for t in tasks}
    for t in tasks:
        for d in t.deps:
            if d in children:
                children[d].add(t.task_id)
    out={}
    for root in children:
        seen=set()
        stack=list(children[root])
        while stack:
            x=stack.pop()
            if x in seen: continue
            seen.add(x)
            stack.extend(children.get(x,()))
        out[root]=len(seen)
    return out

def assign_ready_tasks(
    tasks: Sequence[Task],
    workers: Sequence[Worker],
    completed: Iterable[str],
    already_assigned: Iterable[str]=(),
) -> dict[str,str]:
    completed=set(completed)
    assigned=set(already_assigned)
    if not _unique_nonempty(t.task_id for t in tasks):
        return {}
    if not _unique_nonempty(w.worker_id for w in workers):
        return {}
    downstream=_downstream_counts(tasks)
    ready=[
        t for t in tasks
        if t.task_id not in completed and t.task_id not in assigned and t.deps.issubset(completed)
    ]
    ready.sort(key=lambda t:(-downstream.get(t.task_id,0),-t.priority,t.task_id))
    free=sorted(workers,key=lambda w:w.worker_id)
    result={}
    used=set()
    for task in ready:
        candidates=[
            w for w in free
            if w.worker_id not in used and task.required_capabilities.issubset(w.capabilities)
        ]
        if not candidates:
            continue
        candidates.sort(key=lambda w:(len(w.capabilities-task.required_capabilities),w.worker_id))
        w=candidates[0]
        result[task.task_id]=w.worker_id
        used.add(w.worker_id)
    return result

@dataclass(frozen=True)
class ResearchAction:
    action_id: str
    covers: FrozenSet[str]
    cost: float
    reliability: float = 1.0
    verified: bool = True

@dataclass(frozen=True)
class ResearchDecision:
    status: str
    action_id: str | None
    unresolved: FrozenSet[str]
    reason: str

def next_research_action(
    material_requirements: Iterable[str],
    resolved_requirements: Iterable[str],
    actions: Sequence[ResearchAction],
) -> ResearchDecision:
    unresolved=frozenset(material_requirements)-frozenset(resolved_requirements)
    if not _unique_nonempty(a.action_id for a in actions):
        return ResearchDecision("ESCALATE",None,unresolved,"ACTION_IDENTITIES_INVALID_OR_DUPLICATE")
    if not unresolved:
        return ResearchDecision("STOP",None,unresolved,"ALL_MATERIAL_REQUIREMENTS_RESOLVED")
    scored=[]
    for a in actions:
        new=len(a.covers & unresolved)
        if not a.verified or new==0 or not _finite_nonnegative(a.cost) or not _finite01(a.reliability):
            continue
        denom=a.cost if a.cost>0 else 1e-12
        score=(new*a.reliability)/denom
        scored.append((score,new,a.reliability,-a.cost,a.action_id,a))
    if not scored:
        return ResearchDecision("ESCALATE",None,unresolved,"NO_VERIFIED_ACTION_ADDS_REQUIREMENT_COVERAGE")
    scored.sort(reverse=True)
    return ResearchDecision("ACT",scored[0][-1].action_id,unresolved,"MAX_VERIFIED_COVERAGE_PER_COST")

@dataclass(frozen=True)
class EvidenceUnit:
    evidence_id: str
    supports: FrozenSet[str]
    cost: float = 1.0
    reliability: float = 1.0
    conflicts_with: FrozenSet[str] = frozenset()

@dataclass(frozen=True)
class EvidenceDecision:
    status: str
    evidence_ids: tuple[str,...]
    unsupported_claims: FrozenSet[str]
    reason: str

def minimal_support_bundle(required_claims: Iterable[str], units: Sequence[EvidenceUnit]) -> EvidenceDecision:
    required=frozenset(required_claims)
    if not required:
        return EvidenceDecision("PASS",(),frozenset(),"NO_REQUIRED_CLAIMS")
    n=len(units)
    if n>20:
        return EvidenceDecision("ESCALATE",(),required,"TOO_MANY_UNITS_FOR_EXACT_BOUNDED_SEARCH")
    if not _unique_nonempty(u.evidence_id for u in units):
        return EvidenceDecision("ESCALATE",(),required,"EVIDENCE_IDENTITIES_INVALID_OR_DUPLICATE")
    valid=[
        u for u in units
        if _finite_nonnegative(u.cost) and _finite01(u.reliability)
    ]
    if len(valid)!=len(units):
        return EvidenceDecision("ESCALATE",(),required,"EVIDENCE_COST_OR_RELIABILITY_INVALID")
    best=None
    # Exhaust the bounded subset universe. Objective is truly minimum total cost,
    # then minimum cardinality, then maximum reliability, then lexical IDs.
    for k in range(n+1):
        for idxs in combinations(range(n),k):
            subset=[units[i] for i in idxs]
            ids={u.evidence_id for u in subset}
            if any((u.conflicts_with & ids) for u in subset):
                continue
            covered=frozenset().union(*(u.supports for u in subset)) if subset else frozenset()
            if not required.issubset(covered):
                continue
            total_cost=sum(float(u.cost) for u in subset)
            rel=sum(float(u.reliability) for u in subset)
            key=(total_cost,k,-rel,tuple(sorted(ids)))
            if best is None or key<best[0]:
                best=(key,tuple(sorted(ids)))
    if best is None:
        covered=frozenset().union(*(u.supports for u in units)) if units else frozenset()
        return EvidenceDecision("ESCALATE",(),required-covered,"REQUIRED_CLAIM_WITHOUT_NONCONFLICTING_SUPPORT")
    return EvidenceDecision("PASS",best[1],frozenset(),"MINIMUM_COST_NONCONFLICTING_COMPLETE_SUPPORT")

@dataclass(frozen=True)
class FailureCandidate:
    candidate_id: str
    step_index: int
    causal_supported: bool
    intervenable: bool
    evidence_strength: float
    predicted_rescue: float

@dataclass(frozen=True)
class RepairDecision:
    status: str
    candidate_id: str | None
    reason: str

def select_repair_target(
    candidates: Sequence[FailureCandidate],
    *,
    min_evidence: float = 0.5,
) -> RepairDecision:
    if not _finite01(min_evidence):
        return RepairDecision("ESCALATE",None,"MIN_EVIDENCE_INVALID")
    if not _unique_nonempty(c.candidate_id for c in candidates):
        return RepairDecision("ESCALATE",None,"CANDIDATE_IDENTITIES_INVALID_OR_DUPLICATE")
    eligible=[
        c for c in candidates
        if c.causal_supported and c.intervenable
        and isinstance(c.step_index,int) and not isinstance(c.step_index,bool) and c.step_index>=0
        and _finite01(c.evidence_strength) and _finite01(c.predicted_rescue)
        and c.evidence_strength>=min_evidence and c.predicted_rescue>0
    ]
    if not eligible:
        return RepairDecision("ESCALATE",None,"NO_CAUSALLY_SUPPORTED_INTERVENABLE_REPAIR")
    eligible.sort(key=lambda c:(c.step_index,-c.predicted_rescue,-c.evidence_strength,c.candidate_id))
    return RepairDecision("SELECT",eligible[0].candidate_id,"EARLIEST_CAUSALLY_SUPPORTED_RESCUE_TARGET")

# ---- Cross-lane bounded control primitives (M2/M4/M5 zero-reality subtraction) ----

from typing import Mapping

@dataclass(frozen=True)
class ArtifactOperation:
    operation_id: str
    satisfies: FrozenSet[str]
    cost: float = 0.0
    deterministic: bool = True
    preserves_unrequested_structure: bool = True
    available: bool = True

@dataclass(frozen=True)
class ArtifactPlanDecision:
    status: str
    operation_ids: tuple[str,...]
    uncovered: FrozenSet[str]
    reason: str

def plan_artifact_operations(
    required_changes: Iterable[str],
    operations: Sequence[ArtifactOperation],
) -> ArtifactPlanDecision:
    """Exact bounded set-cover over deterministic structure-preserving operations."""
    required=frozenset(required_changes)
    if not required:
        return ArtifactPlanDecision("PASS",(),frozenset(),"NO_REQUIRED_CHANGES")
    ids=[o.operation_id for o in operations]
    if len(ids)!=len(set(ids)) or any(not isinstance(x,str) or not x.strip() for x in ids):
        return ArtifactPlanDecision("ESCALATE",(),required,"OPERATION_IDENTITIES_INVALID_OR_DUPLICATE")
    eligible=[
        o for o in operations
        if o.available and o.deterministic and o.preserves_unrequested_structure
        and _finite_nonnegative(o.cost)
    ]
    if len(eligible)>20:
        return ArtifactPlanDecision("ESCALATE",(),required,"TOO_MANY_OPERATIONS_FOR_EXACT_BOUNDED_SEARCH")
    best=None
    for k in range(len(eligible)+1):
        for idxs in combinations(range(len(eligible)),k):
            subset=[eligible[i] for i in idxs]
            covered=frozenset().union(*(o.satisfies for o in subset)) if subset else frozenset()
            if not required.issubset(covered):
                continue
            chosen=tuple(sorted(o.operation_id for o in subset))
            key=(sum(float(o.cost) for o in subset),k,chosen)
            if best is None or key<best[0]:
                best=(key,chosen)
    if best is None:
        covered=frozenset().union(*(o.satisfies for o in eligible)) if eligible else frozenset()
        return ArtifactPlanDecision("ESCALATE",(),required-covered,"NO_STRUCTURE_PRESERVING_OPERATION_COVERAGE")
    return ArtifactPlanDecision("PASS",best[1],frozenset(),"MINIMUM_COST_COMPLETE_STRUCTURE_PRESERVING_PLAN")

@dataclass(frozen=True)
class TraceDecision:
    event_id: str
    step_index: int
    intervenable: bool = True
    authorized: bool = True

@dataclass(frozen=True)
class FailureControlDecision:
    status: str
    candidate_ids: tuple[str,...]
    reason: str

def enumerate_nonreplayable_failure_candidates(
    decisions: Sequence[TraceDecision],
    failure_step_index: int,
) -> FailureControlDecision:
    """Losslessly enumerate prior authorized/intervenable decisions.

    Temporal precedence is not treated as causal support. The returned set is only
    a conservative candidate universe for later invariant, intervention, replay,
    or causal-ranking evidence.
    """
    ids=[d.event_id for d in decisions]
    if len(ids)!=len(set(ids)) or any(not isinstance(x,str) or not x.strip() for x in ids):
        return FailureControlDecision("ESCALATE",(),"DECISION_IDENTITIES_INVALID_OR_DUPLICATE")
    if not isinstance(failure_step_index,int) or isinstance(failure_step_index,bool) or failure_step_index<0:
        return FailureControlDecision("ESCALATE",(),"FAILURE_STEP_INVALID")
    if any(not isinstance(d.step_index,int) or isinstance(d.step_index,bool) or d.step_index<0 for d in decisions):
        return FailureControlDecision("ESCALATE",(),"DECISION_STEP_INVALID")
    candidates=tuple(
        d.event_id
        for d in sorted(decisions,key=lambda d:(d.step_index,d.event_id))
        if d.step_index < failure_step_index and d.intervenable and d.authorized
    )
    if not candidates:
        return FailureControlDecision("ESCALATE",(),"NO_PRIOR_AUTHORIZED_INTERVENABLE_DECISION_CANDIDATES")
    return FailureControlDecision("CANDIDATES",candidates,"LOSSLESS_PRIOR_DECISION_CANDIDATE_SET__NO_CAUSAL_CLAIM")

