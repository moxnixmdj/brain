from __future__ import annotations
from typing import Any, Mapping, Sequence

DIRECT_PROOF_KINDS={
    "RECEIPT",
    "ABSOLUTE_CEILING",
    "ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS",
    "SCOPE_COMPLETE_STRONGER_PROOF",
    "CLEAN_CASE_INDEPENDENT_FORMAL_POINTWISE_DOMINANCE",
    "INDEPENDENT_CONTENT_BOUND_UNIVERSAL_FORMAL_SCOPE_PROOF",
    "PUBLIC_FIXED_BAR",
    "MATCHED_COMPARATOR",
    "UNIVERSAL",
    "EXHAUSTIVE_FINITE",
}
TRANSPORT_MARKERS=("TRANSPORT","TRANSFER","DERIVED","COMPOSITION_INHERIT","PULLBACK")

def _is_transport_kind(kind:str)->bool:
    k=kind.upper()
    return any(m in k for m in TRANSPORT_MARKERS)

def _cert_ok(cert:Any)->bool:
    if not isinstance(cert,Mapping):return False
    return all(cert.get(k) is True for k in (
        "implementation_content_addressed",
        "load_bearing_state_quotient_complete",
        "target_evaluator_pullbacks_complete",
        "hard_constraint_preimages_complete",
        "independent_or_objective_verified",
    ))

def verify_claims(claims:Sequence[Mapping[str,Any]], *, grandfathered_ids:Sequence[str]=()) -> dict[str,Any]:
    grandfathered=set(map(str,grandfathered_ids))
    proved={str(x.get("predicate_id")):x for x in claims if isinstance(x,Mapping) and x.get("state")=="PROVED"}
    errors=[]; direct=[]; transported=[]; grandfathered_rows=[]
    for pid,row in sorted(proved.items()):
        kind=str(row.get("proof_kind") or "")
        if pid in grandfathered:
            grandfathered_rows.append(pid)
            continue
        route_kind=row.get("c_route_kind")
        if route_kind is None:
            if kind in DIRECT_PROOF_KINDS:
                if row.get("scope_complete") is not True or row.get("independent_or_objective") is not True:
                    errors.append("DIRECT_PROOF_NOT_SCOPE_COMPLETE_INDEPENDENT:"+pid)
                else:direct.append(pid)
                continue
            if _is_transport_kind(kind):
                errors.append("TRANSPORT_ROUTE_KIND_NOT_EXPLICIT:"+pid)
            else:
                errors.append("UNKNOWN_PROOF_KIND_REQUIRES_EXPLICIT_C_ROUTE_KIND:"+pid+":"+kind)
            continue
        if route_kind=="DIRECT":
            if kind not in DIRECT_PROOF_KINDS:
                errors.append("DIRECT_KIND_NOT_WHITELISTED:"+pid+":"+kind)
            elif row.get("scope_complete") is not True or row.get("independent_or_objective") is not True:
                errors.append("DIRECT_PROOF_NOT_SCOPE_COMPLETE_INDEPENDENT:"+pid)
            else:direct.append(pid)
        elif route_kind=="TRANSPORT":
            parent=str(row.get("c_parent_predicate_id") or "")
            if parent not in proved:
                errors.append("TRANSPORT_PARENT_NOT_PROVED:"+pid)
            if not _cert_ok(row.get("c_transform_certificate")):
                errors.append("TRANSPORT_C_CERTIFICATE_INCOMPLETE:"+pid)
            if not errors or not any(e.endswith(":"+pid) for e in errors):
                transported.append(pid)
        else:
            errors.append("C_ROUTE_KIND_INVALID:"+pid)
    return {
        "status":"PASS__ACCEPTANCE_LEDGER_C_EDGE_GATE" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":errors,
        "proved_count":len(proved),
        "direct_count":len(direct),
        "transported_count":len(transported),
        "grandfathered_count":len(grandfathered_rows),
        "terminal_credit_delta":0,
    }
