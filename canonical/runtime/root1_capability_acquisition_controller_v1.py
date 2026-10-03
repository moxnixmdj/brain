from __future__ import annotations

from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import structural_transfer_v3 as transfer

SCHEMA = "PROJECT_BRAIN_ROOT1_CAPABILITY_ACQUISITION_CONTROLLER_V1"

class Root1ControllerError(ValueError):
    pass

def _items(values: Iterable[Any]) -> set[str]:
    out=set()
    for v in values:
        s=str(v).strip()
        if s:
            out.add(s)
    return out

def _f(x: Any, name: str) -> Fraction:
    if isinstance(x, bool):
        raise Root1ControllerError(name.upper()+"_INVALID")
    try:
        y = x if isinstance(x, Fraction) else Fraction(str(x))
    except Exception as exc:
        raise Root1ControllerError(name.upper()+"_INVALID") from exc
    return y

def classify_root1(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    if not evidence or evidence.get("positive_operational_gap") is not True:
        return {
            "schema": SCHEMA,
            "status": "ROOT1_INACTIVE_NO_ACTION",
            "root1_active": False,
            "reason": "NO_POSITIVE_OPERATIONAL_CAPABILITY_GAP",
            "terminal_work_authorized": False,
        }
    required = {
        "constructive_witness_verified": True,
        "constructive_witness_content_addressed": True,
        "operative_failure_demonstrated": True,
        "acquisition_routes_accounted": True,
        "unresolved_after_available_acquisition": True,
    }
    missing = sorted(k for k,v in required.items() if evidence.get(k) is not v)
    behavior = str(evidence.get("required_behavior") or "").strip()
    if not behavior:
        missing.append("required_behavior")
    if missing:
        return {
            "schema": SCHEMA,
            "status": "ROOT1_NOT_ESTABLISHED",
            "root1_active": False,
            "reason": "UNKNOWN_OR_UNPROVED_IS_NOT_MISSING",
            "failed_requirements": sorted(set(missing)),
            "terminal_work_authorized": False,
        }
    return {
        "schema": SCHEMA,
        "status": "ROOT1_REOPENED_CONSTRUCTIVE_GAP",
        "root1_active": True,
        "required_behavior": behavior,
        "witness_id": str(evidence.get("witness_id") or "").strip() or None,
        "terminal_work_authorized": True,
    }

def minimum_capability_delta(
    *,
    required_primitives: Iterable[Any],
    verified_primitives: Iterable[Any],
    transfer_mappings: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    required = _items(required_primitives)
    verified = _items(verified_primitives)
    applied = transfer.apply(verified_facts=verified, mappings=transfer_mappings)
    covered = set(applied["verified_facts"])
    missing = sorted(required - covered)
    return {
        "schema": SCHEMA,
        "status": "DELTA_EMPTY" if not missing else "CAPABILITY_DELTA_OPEN",
        "required_primitives": sorted(required),
        "verified_or_proven_transfer_primitives": sorted(required & covered),
        "missing_primitives": missing,
        "delta_ratio": str(Fraction(len(missing), len(required))) if required else "0",
        "admitted_transfer_mappings": applied["admitted_transfer_mappings"],
    }

def rank_acquisition_actions(
    actions: Sequence[Mapping[str, Any]],
    *,
    correlation_penalty_weight: Any = "1/2",
) -> list[dict[str, Any]]:
    cpw=_f(correlation_penalty_weight,"correlation_penalty_weight")
    if cpw < 0:
        raise Root1ControllerError("NEGATIVE_CORRELATION_PENALTY_WEIGHT")
    ranked=[]
    seen=set()
    for raw in actions:
        aid=str(raw.get("id") or "").strip()
        if not aid or aid in seen:
            raise Root1ControllerError("ACTION_ID_INVALID_OR_DUPLICATE")
        seen.add(aid)
        if raw.get("safe") is not True:
            continue
        cost=_f(raw.get("incremental_spend_usd",0),"incremental_spend_usd")
        if cost != 0:
            continue
        p=_f(raw.get("p_close",0),"p_close")
        leverage=_f(raw.get("terminal_leverage",0),"terminal_leverage")
        info=_f(raw.get("information_gain",0),"information_gain")
        transfer_gain=_f(raw.get("transfer_gain",0),"transfer_gain")
        proof=_f(raw.get("proof_gain",0),"proof_gain")
        time=_f(raw.get("time",0),"time")
        risk=_f(raw.get("risk",0),"risk")
        corr=_f(raw.get("correlation_with_selected",0),"correlation_with_selected")
        if min(p,leverage,info,transfer_gain,proof,time,risk,corr) < 0:
            raise Root1ControllerError("NEGATIVE_ACTION_DIMENSION:"+aid)
        if p > 1 or corr > 1:
            raise Root1ControllerError("PROBABILITY_OR_CORRELATION_GT_ONE:"+aid)
        den=time+risk
        if den <= 0:
            raise Root1ControllerError("ACTION_TOTAL_COST_MUST_BE_POSITIVE:"+aid)
        gross=p*leverage+info+transfer_gain+proof
        diversity=max(Fraction(0), Fraction(1)-cpw*corr)
        score=(gross*diversity)/den
        if score <= 0:
            continue
        ranked.append({
            "id": aid,
            "source_class": str(raw.get("source_class") or "").strip() or "UNSPECIFIED",
            "route_kind": str(raw.get("route_kind") or "").strip() or "UNSPECIFIED",
            "value_density": str(score),
            "gross_expected_value": str(gross),
            "diversity_multiplier": str(diversity),
            "p_close": str(p),
            "incremental_spend_usd": "0",
        })
    ranked.sort(key=lambda x:(-Fraction(x["value_density"]), x["id"]))
    return ranked

def select_orthogonal_portfolio(
    actions: Sequence[Mapping[str, Any]],
    *,
    max_actions: int = 4,
    max_same_source_class: int = 1,
) -> list[dict[str, Any]]:
    if isinstance(max_actions,bool) or max_actions < 1:
        raise Root1ControllerError("MAX_ACTIONS_INVALID")
    if isinstance(max_same_source_class,bool) or max_same_source_class < 1:
        raise Root1ControllerError("MAX_SAME_SOURCE_CLASS_INVALID")
    ranked=rank_acquisition_actions(actions)
    selected=[]
    counts={}
    for item in ranked:
        sc=item["source_class"]
        if counts.get(sc,0) >= max_same_source_class:
            continue
        selected.append(item)
        counts[sc]=counts.get(sc,0)+1
        if len(selected) >= max_actions:
            break
    return selected

def choose_experiment(experiments: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    ranked=[]
    for raw in experiments:
        eid=str(raw.get("id") or "").strip()
        if not eid:
            raise Root1ControllerError("EXPERIMENT_ID_REQUIRED")
        if raw.get("safe") is not True:
            continue
        if _f(raw.get("incremental_spend_usd",0),"incremental_spend_usd") != 0:
            continue
        gain=_f(raw.get("expected_information_gain",0),"expected_information_gain")
        time=_f(raw.get("time",0),"time")
        risk=_f(raw.get("risk",0),"risk")
        if min(gain,time,risk) < 0:
            raise Root1ControllerError("NEGATIVE_EXPERIMENT_DIMENSION:"+eid)
        den=time+risk
        if den <= 0:
            raise Root1ControllerError("EXPERIMENT_TOTAL_COST_MUST_BE_POSITIVE:"+eid)
        if gain <= 0:
            continue
        ranked.append((gain/den,eid))
    if not ranked:
        return None
    ranked.sort(key=lambda x:(-x[0],x[1]))
    return {"id":ranked[0][1],"information_value_density":str(ranked[0][0])}

def mechanism_graph_frontier(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    edges=[]
    seen=set()
    allowed=("dependencies","forks","authors","papers","issues","pull_requests","releases","downstream_users")
    for c in candidates:
        cid=str(c.get("id") or "").strip()
        if not cid:
            raise Root1ControllerError("CANDIDATE_ID_REQUIRED")
        for field in allowed:
            for x in c.get(field,[]) or []:
                node=str(x).strip()
                if not node:
                    continue
                key=(cid,field,node)
                if key in seen:
                    continue
                seen.add(key)
                edges.append({"candidate_id":cid,"relation":field,"node":node})
    return sorted(edges,key=lambda x:(x["candidate_id"],x["relation"],x["node"]))

def structural_abstraction(
    *,
    concrete_mechanism: str,
    abstract_pattern: str,
    verification_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    concrete=str(concrete_mechanism or "").strip()
    abstract=str(abstract_pattern or "").strip()
    if not concrete or not abstract:
        raise Root1ControllerError("MECHANISM_AND_ABSTRACTION_REQUIRED")
    ids=[]
    for r in verification_receipts:
        rid=str(r.get("receipt_id") or "").strip()
        if not rid:
            raise Root1ControllerError("RECEIPT_ID_REQUIRED")
        if r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion")!="success":
            raise Root1ControllerError("RECEIPT_NOT_ADMISSIBLE:"+rid)
        ids.append(rid)
    if not ids:
        raise Root1ControllerError("VERIFICATION_RECEIPT_REQUIRED")
    return {
        "schema": SCHEMA,
        "status": "PROOF_PRESERVING_ABSTRACTION_CANDIDATE",
        "concrete_mechanism": concrete,
        "abstract_pattern": abstract,
        "verification_receipt_ids": sorted(set(ids)),
        "promotion_authorized": False,
    }

def acquisition_transaction(
    *,
    gap_evidence: Mapping[str, Any] | None,
    required_primitives: Iterable[Any],
    verified_primitives: Iterable[Any],
    transfer_mappings: Sequence[Mapping[str, Any]] = (),
    actions: Sequence[Mapping[str, Any]] = (),
    experiments: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    gate=classify_root1(gap_evidence)
    if not gate["root1_active"]:
        return {
            "schema": SCHEMA,
            "status": "NO_ACTION_ROOT1_INACTIVE",
            "gate": gate,
            "selected_actions": [],
            "selected_experiment": None,
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }
    delta=minimum_capability_delta(
        required_primitives=required_primitives,
        verified_primitives=verified_primitives,
        transfer_mappings=transfer_mappings,
    )
    if not delta["missing_primitives"]:
        return {
            "schema": SCHEMA,
            "status": "CONSTRUCTIVE_GAP_COLLAPSED_BY_EXISTING_OR_PROVEN_TRANSFER",
            "gate": gate,
            "delta": delta,
            "selected_actions": [],
            "selected_experiment": None,
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }
    selected=select_orthogonal_portfolio(actions)
    experiment=None if selected else choose_experiment(experiments)
    return {
        "schema": SCHEMA,
        "status": "ACQUISITION_REQUIRED",
        "gate": gate,
        "delta": delta,
        "selected_actions": selected,
        "selected_experiment": experiment,
        "fresh_reality_authority": False,
        "promotion_authority": False,
    }
