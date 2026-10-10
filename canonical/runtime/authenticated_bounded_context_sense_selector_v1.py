"""Authenticated bounded context-sense selector V1.

Generic finite sense-selection kernel.

The caller may supply *requests*, but may not self-certify semantic facts. This
module invokes three verifier callbacks:
  1. candidate_universe_verifier(request)
  2. discriminator_matrix_verifier(request)
  3. observation_verifier(request) for each observed context item

A selection is authorized by this kernel only when:
- the candidate verifier proves a complete bounded candidate universe;
- the matrix verifier proves complete outcome maps over exactly that universe;
- every applied observation is independently authenticated;
- filtering leaves exactly one candidate.

If multiple candidates remain, the exact semantic information frontier is used
to identify the minimum next discriminator relative to that authenticated
bounded universe. Missing-path or failed observations never prove negation.

This module grants no open-world/global identity or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.semantic_information_frontier_v1 import solve as solve_frontier

SCHEMA="PROJECT_BRAIN_AUTHENTICATED_BOUNDED_CONTEXT_SENSE_SELECTOR_V1"


def _base(status:str,*,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "selected_candidate_id":None,
        "bounded_selection_authority":False,
        "semantic_identity_authority":False,
        "global_identity_authority":False,
        "open_world_candidate_set_complete":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **extra,
    }


def _ids(value:Any,name:str)->list[str]:
    if (
        not isinstance(value,Sequence)
        or isinstance(value,(str,bytes))
        or not value
    ):
        raise ValueError(name+"_REQUIRED")
    rows=[str(x).strip() for x in value]
    if any(not x for x in rows) or len(rows)!=len(set(rows)):
        raise ValueError(name+"_INVALID_OR_DUPLICATE")
    return rows


def _candidate_authority(value:Any)->dict[str,Any]:
    if not isinstance(value,Mapping):
        raise ValueError("CANDIDATE_VERIFIER_RESULT_NOT_OBJECT")
    row=deepcopy(dict(value))
    if row.get("status")=="FAIL_CLOSED":
        raise ValueError("CANDIDATE_UNIVERSE_FAIL_CLOSED:"+str(row.get("reason") or "UNKNOWN"))
    if row.get("pass") is not True:
        raise ValueError("CANDIDATE_UNIVERSE_NOT_PROVED")
    if row.get("candidate_universe_complete") is not True:
        raise ValueError("CANDIDATE_UNIVERSE_COMPLETENESS_UNPROVED")
    scope=str(row.get("scope_id") or "").strip()
    if not scope:
        raise ValueError("CANDIDATE_SCOPE_ID_REQUIRED")
    ids=_ids(row.get("candidate_ids"),"CANDIDATE_IDS")
    auth=str(row.get("authority_sha256") or "").strip()
    if not auth:
        raise ValueError("CANDIDATE_AUTHORITY_SHA256_REQUIRED")
    return {
        **row,
        "scope_id":scope,
        "candidate_ids":ids,
        "authority_sha256":auth,
    }


def _matrix_authority(value:Any,candidate:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(value,Mapping):
        raise ValueError("MATRIX_VERIFIER_RESULT_NOT_OBJECT")
    row=deepcopy(dict(value))
    if row.get("status")=="FAIL_CLOSED":
        raise ValueError("DISCRIMINATOR_MATRIX_FAIL_CLOSED:"+str(row.get("reason") or "UNKNOWN"))
    if row.get("pass") is not True:
        raise ValueError("DISCRIMINATOR_MATRIX_NOT_PROVED")
    if row.get("semantic_truth_authority") is not True:
        raise ValueError("MATRIX_SEMANTIC_TRUTH_AUTHORITY_REQUIRED")
    if row.get("outcome_maps_complete_relative_to_matrix_domain") is not True:
        raise ValueError("MATRIX_OUTCOME_MAP_COMPLETENESS_UNPROVED")
    scope=str(row.get("scope_id") or "").strip()
    if scope!=candidate["scope_id"]:
        raise ValueError("MATRIX_SCOPE_MISMATCH")
    domain=_ids(row.get("candidate_domain"),"MATRIX_CANDIDATE_DOMAIN")
    if set(domain)!=set(candidate["candidate_ids"]) or len(domain)!=len(candidate["candidate_ids"]):
        raise ValueError("MATRIX_DOMAIN_MISMATCH")

    observations=row.get("observations")
    if not isinstance(observations,Sequence) or isinstance(observations,(str,bytes)):
        raise ValueError("MATRIX_OBSERVATIONS_INVALID")
    parsed=[]
    seen=set()
    for i,obs in enumerate(observations):
        if not isinstance(obs,Mapping):
            raise ValueError("MATRIX_OBSERVATION_NOT_OBJECT:"+str(i))
        oid=str(obs.get("observation_id") or "").strip()
        if not oid or oid in seen:
            raise ValueError("MATRIX_OBSERVATION_ID_INVALID_OR_DUPLICATE")
        seen.add(oid)
        outcomes=obs.get("outcomes")
        if not isinstance(outcomes,Mapping) or set(outcomes)!=set(domain):
            raise ValueError("MATRIX_OBSERVATION_OUTCOME_MAP_INCOMPLETE:"+oid)
        cost=obs.get("cost_units",1)
        if isinstance(cost,bool) or not isinstance(cost,(int,float)) or cost<0:
            raise ValueError("MATRIX_OBSERVATION_COST_INVALID:"+oid)
        parsed.append({
            "observation_id":oid,
            "outcomes":{cid:deepcopy(outcomes[cid]) for cid in domain},
            "cost_units":float(cost),
        })
    matrix_sha=str(row.get("matrix_sha256") or "").strip()
    if not matrix_sha:
        raise ValueError("MATRIX_SHA256_REQUIRED")
    return {
        **row,
        "scope_id":scope,
        "candidate_domain":domain,
        "observations":parsed,
        "matrix_sha256":matrix_sha,
    }


def _verified_observations(
    requests:Any,
    *,
    verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]],
    scope_id:str,
    matrix_ids:set[str],
)->tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    if not isinstance(requests,Sequence) or isinstance(requests,(str,bytes)):
        raise ValueError("OBSERVATION_REQUESTS_INVALID")
    accepted=[]; attempts=[]; seen=set()
    for i,req in enumerate(requests):
        if not isinstance(req,Mapping):
            raise ValueError("OBSERVATION_REQUEST_NOT_OBJECT:"+str(i))
        result=verifier(deepcopy(dict(req)))
        if not isinstance(result,Mapping):
            raise ValueError("OBSERVATION_VERIFIER_RESULT_NOT_OBJECT:"+str(i))
        row=deepcopy(dict(result))
        attempts.append(row)
        if row.get("status")=="FAIL_CLOSED":
            raise ValueError(
                "OBSERVATION_VERIFIER_FAIL_CLOSED:"
                +str(row.get("reason") or "UNKNOWN")
            )
        if row.get("pass") is not True:
            continue
        if row.get("semantic_truth_authority") is not True:
            raise ValueError("OBSERVATION_SEMANTIC_TRUTH_AUTHORITY_REQUIRED")
        if str(row.get("scope_id") or "").strip()!=scope_id:
            raise ValueError("OBSERVATION_SCOPE_MISMATCH")
        oid=str(row.get("observation_id") or "").strip()
        if not oid or oid not in matrix_ids:
            raise ValueError("OBSERVATION_ID_NOT_IN_MATRIX")
        if oid in seen:
            raise ValueError("DUPLICATE_VERIFIED_OBSERVATION:"+oid)
        seen.add(oid)
        if "observed_outcome" not in row:
            raise ValueError("OBSERVED_OUTCOME_REQUIRED")
        auth=str(row.get("authority_sha256") or "").strip()
        if not auth:
            raise ValueError("OBSERVATION_AUTHORITY_SHA256_REQUIRED")
        accepted.append({
            "observation_id":oid,
            "observed_outcome":deepcopy(row["observed_outcome"]),
            "authority_sha256":auth,
        })
    return accepted,attempts


def resolve(
    *,
    candidate_universe_request:Mapping[str,Any],
    candidate_universe_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]],
    discriminator_matrix_request:Mapping[str,Any],
    discriminator_matrix_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]],
    observation_requests:Sequence[Mapping[str,Any]],
    observation_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]],
)->dict[str,Any]:
    try:
        if not isinstance(candidate_universe_request,Mapping):
            return _base("FAIL_CLOSED",reason="CANDIDATE_UNIVERSE_REQUEST_REQUIRED")
        if not isinstance(discriminator_matrix_request,Mapping):
            return _base("FAIL_CLOSED",reason="DISCRIMINATOR_MATRIX_REQUEST_REQUIRED")
        if not callable(candidate_universe_verifier):
            return _base("FAIL_CLOSED",reason="CANDIDATE_UNIVERSE_VERIFIER_REQUIRED")
        if not callable(discriminator_matrix_verifier):
            return _base("FAIL_CLOSED",reason="DISCRIMINATOR_MATRIX_VERIFIER_REQUIRED")
        if not callable(observation_verifier):
            return _base("FAIL_CLOSED",reason="OBSERVATION_VERIFIER_REQUIRED")

        candidate=_candidate_authority(
            candidate_universe_verifier(deepcopy(dict(candidate_universe_request)))
        )
        matrix=_matrix_authority(
            discriminator_matrix_verifier(deepcopy(dict(discriminator_matrix_request))),
            candidate,
        )
        matrix_rows={
            row["observation_id"]:row
            for row in matrix["observations"]
        }
        verified,attempts=_verified_observations(
            observation_requests,
            verifier=observation_verifier,
            scope_id=candidate["scope_id"],
            matrix_ids=set(matrix_rows),
        )

        survivors=list(candidate["candidate_ids"])
        applied=[]
        for obs in verified:
            row=matrix_rows[obs["observation_id"]]
            before=list(survivors)
            survivors=[
                cid for cid in survivors
                if row["outcomes"][cid]==obs["observed_outcome"]
            ]
            applied.append({
                "observation_id":obs["observation_id"],
                "observed_outcome":deepcopy(obs["observed_outcome"]),
                "candidate_ids_before":before,
                "candidate_ids_after":list(survivors),
            })
            if not survivors:
                return _base(
                    "FAIL_CLOSED",
                    reason="AUTHENTICATED_OBSERVATIONS_CONTRADICT_COMPLETE_CANDIDATE_UNIVERSE",
                    scope_id=candidate["scope_id"],
                    candidate_ids=list(candidate["candidate_ids"]),
                    applied_observations=applied,
                    observation_attempts=attempts,
                    candidate_authority=deepcopy(candidate),
                    matrix_authority=deepcopy(matrix),
                )

        common={
            "scope_id":candidate["scope_id"],
            "candidate_ids":list(candidate["candidate_ids"]),
            "surviving_candidate_ids":list(survivors),
            "candidate_universe_complete":True,
            "open_world_candidate_set_complete":False,
            "candidate_authority_sha256":candidate["authority_sha256"],
            "matrix_sha256":matrix["matrix_sha256"],
            "applied_observations":applied,
            "observation_attempts":attempts,
        }
        if len(survivors)==1:
            return _base(
                "PASS__UNIQUE_BOUNDED_CONTEXT_SENSE_SELECTED",
                passed=True,
                selected_candidate_id=survivors[0],
                bounded_selection_authority=True,
                semantic_identity_authority=True,
                **common,
                boundary=(
                    "UNIQUE_ONLY_INSIDE_INDEPENDENTLY_VERIFIED_COMPLETE_BOUND_SCOPE__"
                    "OBSERVATIONS_AND_MATRIX_INDEPENDENTLY_AUTHENTICATED__"
                    "NO_OPEN_WORLD_OR_GLOBAL_IDENTITY"
                ),
            )

        worlds=[
            {
                "world_id":cid,
                "terminal_signature_complete":True,
                "terminal_signature":{"selected_candidate_id":cid},
            }
            for cid in survivors
        ]
        available=[]
        applied_ids={x["observation_id"] for x in verified}
        for oid,row in matrix_rows.items():
            if oid in applied_ids:
                continue
            available.append({
                "observation_id":oid,
                "outcome_map_complete":True,
                "outcomes":{
                    cid:deepcopy(row["outcomes"][cid])
                    for cid in survivors
                },
                "cost_units":row["cost_units"],
            })
        frontier=solve_frontier({
            "hypothesis_set_complete":True,
            "worlds":worlds,
            "observations":available,
        })
        if frontier.get("pass") is True:
            first=frontier.get("first_observation_id")
            if first is None:
                return _base(
                    "OPEN__MULTIPLE_BOUNDED_SENSES_TERMINALLY_DISTINCT_BUT_NO_IDENTITY_REQUIRED",
                    passed=False,
                    **common,
                    semantic_frontier=frontier,
                )
            return _base(
                "OPEN__MINIMUM_AUTHENTICATED_CONTEXT_DISCRIMINATOR_REQUIRED",
                passed=False,
                additional_information_required=True,
                next_observation_id=first,
                minimum_worst_case_cost_units=frontier.get(
                    "minimum_worst_case_cost_units"
                ),
                **common,
                semantic_frontier=frontier,
            )

        return _base(
            "OPEN__STRONGER_AUTHENTIC_INFORMATION_REQUIRED",
            passed=False,
            additional_information_required=True,
            **common,
            semantic_frontier=frontier,
            unresolved_pairs=deepcopy(frontier.get("unresolved_pairs") or []),
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            reason=type(exc).__name__+":"+str(exc),
        )
