"""Deterministic adversarial differential suite for UVCK V2 structure.

This module compares the primary compiler with an independent fixed-point
reference checker across a mutation corpus. It proves only structural
representation/proof behavior, not domain semantic truth, execution closure,
or full integrated adversarial closure.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from canonical.runtime import assurance_closure_compiler_v1 as primary
from canonical.runtime import assurance_closure_reference_checker_v1 as reference

SCHEMA="PROJECT_BRAIN_ASSURANCE_CLOSURE_STRUCTURAL_ADVERSARY_V1"


def _base()->dict[str,Any]:
    return {
        "schema":primary.GRAPH_SCHEMA,
        "root_ids":["root"],
        "nodes":[
            {
                "id":"root","type":"CLAIM","status":"SUPPORTED",
                "depends_on":["e"],"defeated_by":[],
            },
            {
                "id":"e","type":"EVIDENCE","status":"SUPPORTED",
                "authoritative_leaf":True,
            },
        ],
    }


def challenge_corpus()->list[tuple[str,dict[str,Any]]]:
    out=[]
    out.append(("BASE",_base()))

    g=deepcopy(_base()); g["nodes"][1]["status"]="OPEN"
    out.append(("OPEN_EVIDENCE",g))

    g=deepcopy(_base()); g["nodes"][1]["status"]="STALE"
    out.append(("STALE_EVIDENCE",g))

    g=deepcopy(_base()); g["nodes"][1]["authoritative_leaf"]=False
    out.append(("NONAUTHORITATIVE_LEAF",g))

    g=deepcopy(_base()); g["nodes"][0]["depends_on"]=["missing"]
    out.append(("DANGLING_REFERENCE",g))

    g=deepcopy(_base())
    g["nodes"]=[
        {"id":"root","type":"CLAIM","status":"SUPPORTED","depends_on":["d"],"defeated_by":[]},
        {"id":"d","type":"DEPENDENCY","status":"SUPPORTED","depends_on":["root"],"defeated_by":[]},
    ]
    out.append(("DEPENDENCY_CYCLE",g))

    g=deepcopy(_base())
    g["nodes"].extend([
        {"id":"d","type":"DEFEATER","status":"SUPPORTED","depends_on":["de"],"defeated_by":[]},
        {"id":"de","type":"EVIDENCE","status":"SUPPORTED","authoritative_leaf":True},
    ])
    g["nodes"][0]["defeated_by"]=["d"]
    out.append(("SUPPORTED_DEFEATER",g))

    g=deepcopy(_base())
    g["nodes"].append({"id":"d","type":"DEFEATER","status":"OPEN"})
    g["nodes"][0]["defeated_by"]=["d"]
    out.append(("OPEN_DEFEATER",g))

    for order, case_id in (
        (["open_d","active_d"], "MIXED_DEFEATER_OPEN_THEN_ACTIVE"),
        (["active_d","open_d"], "MIXED_DEFEATER_ACTIVE_THEN_OPEN"),
    ):
        g=deepcopy(_base())
        g["nodes"].extend([
            {"id":"open_d","type":"DEFEATER","status":"OPEN"},
            {"id":"active_d","type":"DEFEATER","status":"SUPPORTED","depends_on":["de"],"defeated_by":[]},
            {"id":"de","type":"EVIDENCE","status":"SUPPORTED","authoritative_leaf":True},
        ])
        g["nodes"][0]["defeated_by"]=order
        out.append((case_id,g))

    g=deepcopy(_base())
    g["nodes"].append({"id":"alien","type":"UNMODELED_MAGIC","status":"OPEN"})
    g["nodes"][0]["depends_on"]=["alien"]
    out.append(("UNSUPPORTED_PRIMITIVE",g))

    g=deepcopy(_base())
    g["nodes"].append({"id":"irrelevant","type":"ASSUMPTION","status":"PROVEN_IRRELEVANT"})
    g["nodes"][0]["depends_on"]=["e","irrelevant"]
    out.append(("PROVEN_IRRELEVANT_DEPENDENCY",g))

    g=deepcopy(_base())
    g["nodes"].append({"id":"o","type":"OBLIGATION","status":"OPEN"})
    g["nodes"][0]["depends_on"]=["o"]
    out.append(("OPEN_OBLIGATION",g))
    return out


def _primary_projection(result:dict[str,Any])->dict[str,Any]:
    if result.get("status")=="FAIL_CLOSED":
        return {
            "fail_closed":True,
            "reason":result.get("reason"),
            "representation_closure":result.get("representation_closure"),
            "proof_closure":False,
        }
    return {
        "fail_closed":False,
        "representation_closure":result.get("closure_gates",{}).get("representation_closure"),
        "proof_closure":result.get("closure_gates",{}).get("proof_closure"),
        "root_closed":result.get("root_closed"),
        "active_defeater_ids":result.get("active_defeater_ids"),
        "unresolved_defeater_ids":result.get("unresolved_defeater_ids"),
        "unsupported_primitive_types":result.get("unsupported_primitive_types"),
    }


def _reference_projection(result:dict[str,Any])->dict[str,Any]:
    if result.get("status")=="FAIL_CLOSED":
        return {
            "fail_closed":True,
            "reason":result.get("reason"),
            "representation_closure":result.get("representation_closure"),
            "proof_closure":False,
        }
    return {
        "fail_closed":False,
        "representation_closure":result.get("representation_closure"),
        "proof_closure":result.get("proof_closure"),
        "root_closed":result.get("root_closed"),
        "active_defeater_ids":result.get("active_defeater_ids"),
        "unresolved_defeater_ids":result.get("unresolved_defeater_ids"),
        "unsupported_primitive_types":result.get("unsupported_primitive_types"),
    }


def run()->dict[str,Any]:
    rows=[]
    mismatches=[]
    for case_id,graph in challenge_corpus():
        p=primary.evaluate(graph)
        r=reference.check(graph)
        pp=_primary_projection(p)
        rp=_reference_projection(r)
        if pp["fail_closed"] and rp["fail_closed"]:
            matched=True
        else:
            matched=pp==rp
        row={
            "case_id":case_id,
            "matched":matched,
            "primary_status":p.get("status"),
            "reference_status":r.get("status"),
        }
        rows.append(row)
        if not matched:
            mismatches.append({
                **row,
                "primary_projection":pp,
                "reference_projection":rp,
            })
    return {
        "schema":SCHEMA,
        "pass":not mismatches,
        "status":"PASS__STRUCTURAL_DIFFERENTIAL_CORPUS" if not mismatches else "FAIL__STRUCTURAL_DIFFERENTIAL_MISMATCH",
        "case_count":len(rows),
        "matched_count":sum(1 for x in rows if x["matched"]),
        "mismatches":mismatches,
        "cases":rows,
        "scope":"STRUCTURAL_REPRESENTATION_AND_PROOF_CLOSURE_ONLY",
        "not_proved":[
            "DOMAIN_SEMANTIC_TRUTH",
            "EXECUTION_CLOSURE",
            "INDEPENDENT_RUNTIME_ADVERSARIAL_CLOSURE",
            "TERMINAL_AUTHORITY",
        ],
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
