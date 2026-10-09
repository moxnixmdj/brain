"""Independent verifier for OEWN decision-manifest lattice V1."""
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.certified_oewn_decision_evidence_v1 import parse_sense_evidence
from canonical.runtime.semantic_information_frontier_v1 import solve as solve_frontier
from canonical.runtime.oewn_release_sense_universe_v1 import (
    SCHEMA as OEWN_SCHEMA, RELEASE_ID, RELEASE_SHA256,
)

SCHEMA="PROJECT_BRAIN_OEWN_DECISION_MANIFEST_LATTICE_VERIFY_V1"
PROBLEM_SCHEMA="PROJECT_BRAIN_OEWN_DECISION_MANIFEST_LATTICE_V1"


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip(): raise ValueError(name+"_INVALID")
    return v.strip()


def _universe(value:Any)->dict[str,Any]:
    if not isinstance(value,Mapping) or value.get("schema")!=OEWN_SCHEMA:
        raise ValueError("SENSE_UNIVERSE_SCHEMA_INVALID")
    required={
        "pass":True,
        "release_id":RELEASE_ID,
        "archive_sha256":RELEASE_SHA256,
        "candidate_set_complete_relative_to_release":True,
        "open_world_english_sense_completeness_claimed":False,
    }
    for k,v in required.items():
        if value.get(k)!=v: raise ValueError("SENSE_UNIVERSE_BINDING_INVALID:"+k)
    rows=value.get("senses")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        raise ValueError("SENSES_INVALID")
    ids=[]; seen=set()
    for row in rows:
        if not isinstance(row,Mapping): raise ValueError("SENSE_NOT_OBJECT")
        sid=_token(row.get("sense_id"),"SENSE_ID")
        if sid in seen: raise ValueError("SENSE_ID_DUPLICATE")
        seen.add(sid); ids.append(sid)
    ids.sort()
    return {
        "lemma":_token(value.get("lemma"),"LEMMA").casefold(),
        "part_of_speech":value.get("requested_part_of_speech"),
        "sense_ids":ids,
    }


def _expected(problem:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(problem,Mapping) or problem.get("schema")!=PROBLEM_SCHEMA:
        raise ValueError("PROBLEM_SCHEMA_INVALID")
    if set(problem)!={"schema","scope_id","sense_universe","source_id","source_text"}:
        raise ValueError("PROBLEM_FIELDS_INVALID")
    scope=_token(problem.get("scope_id"),"SCOPE_ID")
    source=_token(problem.get("source_id"),"SOURCE_ID")
    text=problem.get("source_text")
    if not isinstance(text,str) or not text: raise ValueError("SOURCE_TEXT_INVALID")
    u=_universe(problem.get("sense_universe"))
    ids=list(u["sense_ids"]); idset=set(ids)
    parsed=parse_sense_evidence(text,source=source)
    if parsed.get("status")=="UNRESOLVED":
        return {"status":"OPEN__SOURCE_DECISION_EVIDENCE_UNRESOLVED","pass":False}
    if parsed.get("status")!="PARSED":
        raise ValueError("SOURCE_PARSE_FAILED")

    terminals={}; obs={}; observed={}
    for row in parsed.get("clauses") or []:
        kind=row.get("kind")
        if kind=="TERMINAL_SIGNATURE":
            sid=str(row.get("sense_id") or "")
            if sid not in idset: raise ValueError("TERMINAL_SENSE_NOT_IN_UNIVERSE")
            terminals[sid]=deepcopy(dict(row.get("terminal_signature") or {}))
        elif kind=="OBSERVATION_OUTCOME":
            sid=str(row.get("sense_id") or ""); oid=str(row.get("observation_id") or "")
            if sid not in idset: raise ValueError("OBSERVATION_SENSE_NOT_IN_UNIVERSE")
            obs.setdefault(oid,[]).append((sid,float(row.get("cost_units")),deepcopy(row.get("outcome"))))
        elif kind=="OBSERVED_OUTCOME":
            observed[str(row.get("observation_id") or "")]=deepcopy(row.get("observed_outcome"))

    terminal_states={}; open_atoms=[]
    for sid in ids:
        if sid in terminals:
            terminal_states[sid]={"kind":"EXACT","terminal_signature":deepcopy(terminals[sid])}
        else:
            terminal_states[sid]={"kind":"TOP"}
            open_atoms.append({
                "dimension":"TERMINAL_SIGNATURE","sense_id":sid,"state":"TOP",
                "proof_obligation":{
                    "kind":"PROVE_SENSE_TERMINAL_SIGNATURE","scope_id":scope,
                    "source_id":source,"sense_id":sid,
                },
            })
    if open_atoms:
        return {
            "status":"OPEN__SENSE_TERMINAL_SIGNATURE_TOP_REMAINS","pass":False,
            "terminal_states":terminal_states,"open_lattice_atoms":open_atoms,
            "next_proof_obligations":[deepcopy(x["proof_obligation"]) for x in open_atoms],
        }

    states={}; complete=[]; partial=[]
    for oid in sorted(set(obs)|set(observed)):
        by={}; costs=set()
        for sid,cost,outcome in obs.get(oid,[]):
            if sid in by: raise ValueError("OBSERVATION_SENSE_DUPLICATE")
            by[sid]=outcome; costs.add(cost)
        if len(costs)>1: raise ValueError("OBSERVATION_COST_INCONSISTENT")
        cost=next(iter(costs)) if costs else None
        missing=sorted(idset-set(by))
        states[oid]={
            "observation_id":oid,"cost_units":cost,
            "outcome_states":{
                sid:({"kind":"EXACT","outcome":deepcopy(by[sid])} if sid in by else {"kind":"TOP"})
                for sid in ids
            },
            "observed_outcome":(
                {"kind":"EXACT","value":deepcopy(observed[oid])}
                if oid in observed else {"kind":"UNOBSERVED"}
            ),
            "outcome_map_complete":not missing and cost is not None,
        }
        if not missing and cost is not None:
            complete.append({
                "observation_id":oid,"outcome_map_complete":True,
                "outcomes":deepcopy(by),"cost_units":float(cost),
            })
        else:
            partial.append({
                "kind":"COMPLETE_OBSERVATION_OUTCOME_MAP","scope_id":scope,
                "source_id":source,"observation_id":oid,
                "missing_sense_ids":missing,"cost_missing":cost is None,
            })

    complete_by={x["observation_id"]:x for x in complete}
    incomplete_observed=sorted(x for x in observed if x not in complete_by)
    if incomplete_observed:
        return {
            "status":"OPEN__OBSERVED_OUTCOME_MAP_TOP_REMAINS","pass":False,
            "terminal_states":terminal_states,"observation_states":states,
            "blocking_observation_ids":incomplete_observed,
            "next_proof_obligations":[x for x in partial if x["observation_id"] in incomplete_observed],
        }

    surviving=list(ids)
    for oid,value in observed.items():
        row=complete_by[oid]
        surviving=[sid for sid in surviving if row["outcomes"][sid]==value]
    if not surviving:
        return {
            "status":"MODEL_FALSIFIED__OBSERVED_OUTCOMES_EXCLUDE_ALL_RELEASE_SENSES",
            "pass":False,"terminal_states":terminal_states,
            "observation_states":states,"surviving_sense_ids":[],
            "next_proof_obligations":[],
        }

    sigs={sid:terminals[sid] for sid in surviving}
    if len({json.dumps(sigs[s],sort_keys=True,separators=(",",":"),ensure_ascii=False) for s in surviving})==1:
        return {
            "status":"PASS__SENSE_DECISION_SUFFICIENT","pass":True,
            "terminal_states":terminal_states,"observation_states":states,
            "surviving_sense_ids":surviving,
            "intended_sense_identified":len(surviving)==1,
            "identified_sense_id":surviving[0] if len(surviving)==1 else None,
            "terminal_signature":deepcopy(sigs[surviving[0]]),
            "next_proof_obligations":[],
        }

    remaining=[
        {
            "observation_id":row["observation_id"],
            "outcome_map_complete":True,
            "outcomes":{sid:deepcopy(row["outcomes"][sid]) for sid in surviving},
            "cost_units":row["cost_units"],
        }
        for row in complete if row["observation_id"] not in observed
    ]
    frontier=solve_frontier({
        "hypothesis_set_complete":True,
        "worlds":[
            {"world_id":sid,"terminal_signature_complete":True,"terminal_signature":deepcopy(sigs[sid])}
            for sid in surviving
        ],
        "observations":remaining,
    })
    if frontier.get("pass") is True:
        return {
            "status":"OPEN__MINIMUM_TERMINAL_DISCRIMINATOR_REQUIRED","pass":False,
            "terminal_states":terminal_states,"observation_states":states,
            "surviving_sense_ids":surviving,
            "next_observation_id":frontier.get("first_observation_id"),
            "minimum_worst_case_cost_units":frontier.get("minimum_worst_case_cost_units"),
            "next_proof_obligations":[],
        }
    return {
        "status":"OPEN__SEPARATING_OBSERVATION_REQUIRED","pass":False,
        "terminal_states":terminal_states,"observation_states":states,
        "surviving_sense_ids":surviving,
        "unresolved_pairs":deepcopy(frontier.get("unresolved_pairs") or []),
        "next_proof_obligations":(
            partial if partial else [{
                "kind":"DISCOVER_OR_PROVE_SEPARATING_OBSERVATION",
                "scope_id":scope,"source_id":source,
                "surviving_sense_ids":surviving,
            }]
        ),
    }


def verify(problem:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    try:
        exp=_expected(problem)
        if not isinstance(result,Mapping): raise ValueError("RESULT_NOT_OBJECT")
        for key,val in exp.items():
            if result.get(key)!=val: errors.append("MISMATCH:"+key)
        if result.get("semantic_truth_authority") is not False:
            errors.append("SEMANTIC_TRUTH_AUTHORITY_CLAIMED")
        if result.get("terminal_authority") is not False:
            errors.append("TERMINAL_AUTHORITY_CLAIMED")
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    return {
        "schema":SCHEMA,"verified":not errors,
        "status":"PASS__INDEPENDENT_OEWN_MANIFEST_LATTICE_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),"producer_independent":True,
        "semantic_truth_authority":False,"terminal_authority":False,
        "boundary":"INDEPENDENT_SOURCE_CLAUSE_REPARSE_TERMINAL_AND_OBSERVATION_TOP_RECOMPUTATION",
    }
