"""Fail-closed consumption of independently verified false proof atoms.

A false leaf requirement invalidates only certificates that require that exact
proposition. Target predicates are never inferred false or removed. If all
current certificates for a target are blocked, the target is emitted as
requiring an alternative target-preserving certificate.
"""
from __future__ import annotations
from typing import Any, Iterable, Mapping

SCHEMA="PROJECT_BRAIN_PROOF_ATOM_ROUTE_PRUNER_V1"
FALSE_ADJUDICATION="FALSIFIED_UNDER_CURRENT_FROZEN_NO_REPLAY_ROUTE"

def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "blocked_certificate_ids":[],
        "uncovered_target_predicates":[],
        "falsified_atom_count":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

def prune(frontier: Mapping[str, Any], adjudications: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(frontier, Mapping):
        return _fail("FRONTIER_NOT_OBJECT")
    certs=frontier.get("certificates")
    unresolved=frontier.get("unresolved_predicates")
    if not isinstance(certs,list) or not isinstance(unresolved,list):
        return _fail("FRONTIER_SHAPE_INVALID")

    by_id={}
    target_to_certs={str(t):set() for t in unresolved if isinstance(t,str)}
    errors=[]
    for c in certs:
        if not isinstance(c,Mapping):
            errors.append("CERT_NOT_OBJECT")
            continue
        cid=c.get("id")
        targets=c.get("target_predicates")
        reqs=c.get("requires")
        if not isinstance(cid,str) or not cid or cid in by_id:
            errors.append("CERT_ID_INVALID_OR_DUPLICATE")
            continue
        if not isinstance(targets,list) or not targets or not all(isinstance(x,str) and x for x in targets):
            errors.append(f"CERT_TARGETS_INVALID:{cid}")
            continue
        if not isinstance(reqs,list) or not reqs or not all(isinstance(x,str) and x for x in reqs):
            errors.append(f"CERT_REQUIRES_INVALID:{cid}")
            continue
        by_id[cid]=c
        for t in targets:
            if t not in target_to_certs:
                errors.append(f"CERT_TARGET_OUTSIDE_UNRESOLVED:{cid}:{t}")
            else:
                target_to_certs[t].add(cid)
    if errors:
        return _fail(*errors)

    blocked=set()
    false_atoms=[]
    for i,a in enumerate(adjudications):
        if not isinstance(a,Mapping):
            return _fail(f"ADJUDICATION_NOT_OBJECT:{i}")
        status=str(a.get("status",""))
        atom=a.get("atom")
        if not status.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
            return _fail(f"ADJUDICATION_NOT_INDEPENDENT_PASS:{i}")
        if not isinstance(atom,Mapping):
            return _fail(f"ADJUDICATION_ATOM_INVALID:{i}")
        prop=atom.get("proposition")
        cid=atom.get("parent_certificate_id")
        target=atom.get("target_predicate")
        verdict=atom.get("adjudication")
        if verdict != FALSE_ADJUDICATION:
            return _fail(f"ADJUDICATION_KIND_UNSUPPORTED:{i}")
        if not all(isinstance(x,str) and x for x in (prop,cid,target)):
            return _fail(f"ADJUDICATION_FIELDS_INVALID:{i}")
        cert=by_id.get(cid)
        if cert is None:
            return _fail(f"ADJUDICATED_CERT_NOT_FOUND:{cid}")
        if prop not in cert["requires"]:
            return _fail(f"ADJUDICATED_PROPOSITION_NOT_REQUIRED:{cid}:{prop}")
        if target not in cert["target_predicates"]:
            return _fail(f"ADJUDICATED_TARGET_NOT_ON_CERT:{cid}:{target}")
        blocked.add(cid)
        false_atoms.append({
            "proposition":prop,
            "certificate_id":cid,
            "target_predicate":target,
        })

    live_ids=set(by_id)-blocked
    uncovered=sorted(
        t for t,cids in target_to_certs.items()
        if cids and not (cids & live_ids)
    )
    blocked_targets=sorted({
        t for cid in blocked for t in by_id[cid]["target_predicates"]
    })
    still_covered=sorted(set(blocked_targets)-set(uncovered))

    return {
        "schema":SCHEMA,
        "status":"PASS__FALSE_ATOMS_PRUNE_CERTIFICATE_ROUTES__TARGETS_PRESERVED__ZERO_CREDIT",
        "errors":[],
        "frontier_unresolved_target_count":len(target_to_certs),
        "frontier_certificate_count":len(by_id),
        "falsified_atom_count":len(false_atoms),
        "falsified_atoms":sorted(false_atoms,key=lambda x:(x["certificate_id"],x["proposition"])),
        "blocked_certificate_ids":sorted(blocked),
        "blocked_target_predicates":blocked_targets,
        "blocked_targets_still_covered_by_alternative_certificate":still_covered,
        "uncovered_target_predicates":uncovered,
        "alternative_certificate_required":uncovered,
        "target_predicates_removed":[],
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "rule":"FALSE_PROOF_ATOM_BLOCKS_ONLY_REQUIRING_CERTIFICATES__NEVER_FALSIFIES_OR_DELETES_TARGET__UNCOVERED_TARGET_REQUIRES_ALTERNATIVE_TARGET_PRESERVING_CERTIFICATE",
    }
