from __future__ import annotations
from typing import Any, Mapping, Sequence

FIELDS=(
    "predicate_id","state","proof_kind","source_path","source_sha","basis",
    "scope_complete","independent_or_objective",
)
CERT_FIELDS=(
    "implementation_content_addressed",
    "load_bearing_state_quotient_complete",
    "target_evaluator_pullbacks_complete",
    "hard_constraint_preimages_complete",
    "independent_or_objective_verified",
)

def _norm(row:Mapping[str,Any])->dict[str,Any]:
    return {k:row.get(k) for k in FIELDS}

def _cert_ok(cert:Any)->bool:
    return isinstance(cert,Mapping) and all(cert.get(k) is True for k in CERT_FIELDS)

def verify_acceptance_c_gate(
    claims: Sequence[Mapping[str,Any]],
    baseline_rows: Sequence[Mapping[str,Any]],
) -> dict[str,Any]:
    baseline={str(x.get("predicate_id")):_norm(x) for x in baseline_rows if isinstance(x,Mapping)}
    proved={str(x.get("predicate_id")):x for x in claims if isinstance(x,Mapping) and x.get("state")=="PROVED"}
    errors=[]; grandfathered=[]; direct=[]; transported=[]
    for pid,row in sorted(proved.items()):
        current=_norm(row)
        if pid in baseline and current==baseline[pid]:
            grandfathered.append(pid)
            continue

        route_kind=row.get("c_route_kind")
        if route_kind=="DIRECT":
            if row.get("scope_complete") is not True:
                errors.append("DIRECT_SCOPE_NOT_COMPLETE:"+pid)
            if row.get("independent_or_objective") is not True:
                errors.append("DIRECT_NOT_INDEPENDENT_OR_OBJECTIVE:"+pid)
            if row.get("c_parent_predicate_id") is not None:
                errors.append("DIRECT_HAS_PARENT:"+pid)
            if row.get("c_transform_certificate") is not None:
                errors.append("DIRECT_HAS_TRANSFORM_CERTIFICATE:"+pid)
            if not any(e.endswith(":"+pid) for e in errors):
                direct.append(pid)
        elif route_kind=="TRANSPORT":
            parent=str(row.get("c_parent_predicate_id") or "")
            if parent not in proved:
                errors.append("TRANSPORT_PARENT_NOT_PROVED:"+pid)
            if row.get("scope_complete") is not True:
                errors.append("TRANSPORT_SCOPE_NOT_COMPLETE:"+pid)
            if row.get("independent_or_objective") is not True:
                errors.append("TRANSPORT_NOT_INDEPENDENT_OR_OBJECTIVE:"+pid)
            if not _cert_ok(row.get("c_transform_certificate")):
                errors.append("TRANSPORT_C_CERTIFICATE_INCOMPLETE:"+pid)
            if not any(e.endswith(":"+pid) for e in errors):
                transported.append(pid)
        elif route_kind is None:
            errors.append("NEW_OR_MUTATED_PROVED_ROW_REQUIRES_EXPLICIT_C_ROUTE_KIND:"+pid)
        else:
            errors.append("C_ROUTE_KIND_INVALID:"+pid)

    return {
      "schema":"PROJECT_BRAIN_C_ACCEPTANCE_LEDGER_TRANSPORT_GATE_V2",
      "status":"PASS__LEDGER_C_ROUTE_CLASSIFICATION_COMPLETE" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "proved_count":len(proved),
      "grandfathered_exact_baseline_count":len(grandfathered),
      "new_or_mutated_direct_count":len(direct),
      "transported_count":len(transported),
      "terminal_credit_delta":0,
    }
