"""Construct the four priority route fibers from the task-acceptance theorem.

The construction is structural. It proves only that the priority classifier
partitions whatever semantic task domain is supplied. It does not prove that
the supplied task domain covers the real Opus 5.5 target.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_OPUS55_TASK_ACCEPTANCE_ROUTE_FIBER_PARTITION_RUNTIME_V1"
ROUTES = ("E_EXACT_SOLVED", "M_RESTRICTED_SOLVED", "H_SEPARATING", "OTHER")
FIBER_DEFINITIONS = {
    "E_EXACT_SOLVED": "E",
    "M_RESTRICTED_SOLVED": "NOT_E_AND_M",
    "H_SEPARATING": "NOT_E_AND_NOT_M_AND_H",
    "OTHER": "NOT_E_AND_NOT_M_AND_NOT_H",
}
_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

class RoutePartitionError(ValueError):
    pass

def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise RoutePartitionError(f"{label}_INVALID_CONTENT_ADDRESS")
    return value

def classify(e: bool, m: bool, h: bool) -> str:
    if type(e) is not bool or type(m) is not bool or type(h) is not bool:
        raise RoutePartitionError("ROUTE_PREDICATES_MUST_BE_BOOL")
    if e:
        return "E_EXACT_SOLVED"
    if m:
        return "M_RESTRICTED_SOLVED"
    if h:
        return "H_SEPARATING"
    return "OTHER"

def truth_table() -> list[dict[str, Any]]:
    rows=[]
    for e in (False, True):
        for m in (False, True):
            for h in (False, True):
                rows.append({"E":e,"M":m,"H":h,"route":classify(e,m,h)})
    return rows

def _semantic_atom_hashes(domain_semantics_sha: str, route_predicate_semantics_sha: str) -> dict[str, str]:
    # Each atom hash binds the domain, the independently checked route-predicate
    # semantic specification, and the exact priority-fiber formula.
    out={}
    for route in ROUTES:
        payload={
            "domain_semantics_sha":domain_semantics_sha,
            "route_predicate_semantics_sha":route_predicate_semantics_sha,
            "route":route,
            "fiber_formula":FIBER_DEFINITIONS[route],
        }
        raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
        out[route]=hashlib.sha256(raw).hexdigest()
    return out

def build_partition(
    *,
    domain_id: str,
    domain_semantics_sha: str,
    route_predicate_semantics_sha: str,
    partition_proof_source_sha: str,
    independent_or_objective: bool,
) -> dict[str, Any]:
    try:
        if not isinstance(domain_id,str) or not domain_id:
            raise RoutePartitionError("DOMAIN_ID_INVALID")
        domain_semantics_sha=_sha(domain_semantics_sha,"DOMAIN_SEMANTICS_SHA")
        route_predicate_semantics_sha=_sha(route_predicate_semantics_sha,"ROUTE_PREDICATE_SEMANTICS_SHA")
        partition_proof_source_sha=_sha(partition_proof_source_sha,"PARTITION_PROOF_SOURCE_SHA")
        if independent_or_objective is not True:
            raise RoutePartitionError("INDEPENDENT_OR_OBJECTIVE_REQUIRED_TRUE")

        rows=truth_table()
        if len(rows) != 8:
            raise RoutePartitionError("TRUTH_TABLE_NOT_TOTAL")
        seen={(r["E"],r["M"],r["H"]) for r in rows}
        if len(seen) != 8:
            raise RoutePartitionError("TRUTH_TABLE_DUPLICATE_VALUATION")
        if any(r["route"] not in ROUTES for r in rows):
            raise RoutePartitionError("UNKNOWN_ROUTE")

        atoms=_semantic_atom_hashes(domain_semantics_sha,route_predicate_semantics_sha)
        universe_raw=json.dumps(atoms,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
        universe_sha256=hashlib.sha256(universe_raw).hexdigest()
        return {
            "schema":SCHEMA,
            "status":"PASS",
            "universe_id":f"{domain_id}:TASK_ACCEPTANCE_ROUTE_FIBERS_V1",
            "universe_sha256":universe_sha256,
            "universe_atoms":atoms,
            "partition_certificate":{
                "source_sha":partition_proof_source_sha,
                "independent_or_objective":True,
                "pairwise_disjoint_proved":True,
                "atoms_define_declared_omega_proved":True,
                "proof_shape":"TOTAL_SINGLE_VALUED_PRIORITY_CLASSIFIER_FIBERS",
                "truth_table_rows":8,
            },
            "route_order":list(ROUTES),
            "target_domain_coverage_proved":False,
            "capability_credit_delta":0,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "reason":type(exc).__name__+":"+str(exc),
            "target_domain_coverage_proved":False,
            "capability_credit_delta":0,
        }
