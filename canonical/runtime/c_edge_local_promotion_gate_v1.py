from __future__ import annotations
from typing import Any, Mapping, Sequence

class CPromotionError(ValueError):
    pass

DIRECT_MODES={
    "UNIVERSAL",
    "EXHAUSTIVE_FINITE",
    "ABSOLUTE_DOMINANCE",
    "PUBLIC_FIXED_BAR",
    "MATCHED_COMPARATOR",
    "THEORETICAL_CEILING",
    "OBJECTIVE_CEILING",
}

def verify_credited_proof_graph(rows: Sequence[Mapping[str,Any]]) -> dict[str,Any]:
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        raise CPromotionError("ROWS_INVALID")
    by_id={}
    for raw in rows:
        if not isinstance(raw,Mapping):
            raise CPromotionError("ROW_INVALID")
        rid=str(raw.get("route_id") or "")
        if not rid or rid in by_id:
            raise CPromotionError("ROUTE_ID_INVALID_OR_DUPLICATE")
        by_id[rid]=dict(raw)

    visiting=set(); done=set(); transport_edges=[]; direct_roots=[]
    def visit(rid:str):
        if rid in done:return
        if rid in visiting:raise CPromotionError("PROOF_GRAPH_CYCLE:"+rid)
        visiting.add(rid)
        row=by_id[rid]
        kind=row.get("proof_kind")
        if kind=="DIRECT":
            mode=str(row.get("direct_mode") or "")
            if mode not in DIRECT_MODES:
                raise CPromotionError("DIRECT_MODE_INVALID:"+rid)
            if row.get("direct_scope_complete_verified") is not True:
                raise CPromotionError("DIRECT_SCOPE_NOT_VERIFIED:"+rid)
            if row.get("direct_independent_verified") is not True:
                raise CPromotionError("DIRECT_INDEPENDENCE_NOT_VERIFIED:"+rid)
            if row.get("parent_route_id") is not None or row.get("transform_certificate") is not None:
                raise CPromotionError("DIRECT_ROUTE_HAS_TRANSPORT_FIELDS:"+rid)
            direct_roots.append(rid)
        elif kind=="TRANSPORT":
            parent=str(row.get("parent_route_id") or "")
            if parent not in by_id:
                raise CPromotionError("TRANSPORT_PARENT_MISSING:"+rid)
            cert=row.get("transform_certificate")
            if not isinstance(cert,Mapping):
                raise CPromotionError("TRANSFORM_CERTIFICATE_MISSING:"+rid)
            required=(
                "implementation_content_addressed",
                "load_bearing_state_quotient_complete",
                "target_evaluator_pullbacks_complete",
                "hard_constraint_preimages_complete",
                "independent_or_objective_verified",
            )
            missing=[k for k in required if cert.get(k) is not True]
            if missing:
                raise CPromotionError("TRANSFORM_CERTIFICATE_INCOMPLETE:"+rid+":"+",".join(missing))
            visit(parent)
            transport_edges.append((parent,rid))
        else:
            raise CPromotionError("PROOF_KIND_INVALID:"+rid)
        visiting.remove(rid);done.add(rid)

    for rid in by_id:visit(rid)
    return {
        "status":"PASS__ALL_CREDITED_ROUTES_DIRECT_OR_EDGE_LOCAL_C_CERTIFIED",
        "pass":True,
        "credited_route_count":len(by_id),
        "direct_root_count":len(direct_roots),
        "transport_edge_count":len(transport_edges),
        "direct_roots":tuple(sorted(direct_roots)),
        "transport_edges":tuple(sorted(transport_edges)),
        "uninstantiated_or_uncredited_transforms_required_preproof":False,
        "terminal_credit_delta":0,
    }

def prospective_promotion_allowed(
    *,
    current_rows: Sequence[Mapping[str,Any]],
    candidate: Mapping[str,Any],
) -> bool:
    rows=[dict(x) for x in current_rows]+[dict(candidate)]
    try:
        verify_credited_proof_graph(rows)
        return True
    except CPromotionError:
        return False
