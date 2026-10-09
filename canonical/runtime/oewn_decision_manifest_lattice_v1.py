"""Proof-carrying OEWN decision-manifest lattice V1.

Candidate senses are complete only relative to the exact OEWN release universe.
For each release sense, the terminal consequence begins at TOP. Source-certified
terminal clauses refine those coordinates to exact signatures.

Observation models are likewise assembled only from exact source clauses. An
observation can discriminate senses only when its cost is consistent and its
outcome map is complete for every release-relative candidate. Exact observed
outcomes may then narrow the surviving sense set.

Absent, partial, or malformed evidence never narrows ambiguity.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime.certified_oewn_decision_evidence_v1 import parse_sense_evidence
from canonical.runtime.semantic_information_frontier_v1 import solve as solve_frontier
from canonical.runtime.oewn_release_sense_universe_v1 import (
    SCHEMA as OEWN_SCHEMA,
    RELEASE_ID,
    RELEASE_SHA256,
)

SCHEMA="PROJECT_BRAIN_OEWN_DECISION_MANIFEST_LATTICE_V1"


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _universe(value:Any)->dict[str,Any]:
    if not isinstance(value,Mapping) or value.get("schema")!=OEWN_SCHEMA:
        raise ValueError("SENSE_UNIVERSE_SCHEMA_INVALID")
    if value.get("pass") is not True:
        raise ValueError("SENSE_UNIVERSE_NOT_PASS")
    if value.get("release_id")!=RELEASE_ID:
        raise ValueError("SENSE_UNIVERSE_RELEASE_ID_INVALID")
    if value.get("archive_sha256")!=RELEASE_SHA256:
        raise ValueError("SENSE_UNIVERSE_RELEASE_HASH_INVALID")
    if value.get("candidate_set_complete_relative_to_release") is not True:
        raise ValueError("SENSE_UNIVERSE_COMPLETENESS_UNPROVED")
    if value.get("open_world_english_sense_completeness_claimed") is not False:
        raise ValueError("OPEN_WORLD_COMPLETENESS_MUST_REMAIN_FALSE")
    lemma=_token(value.get("lemma"),"LEMMA").casefold()
    pos=value.get("requested_part_of_speech")
    if pos is not None and (not isinstance(pos,str) or not pos.strip()):
        raise ValueError("PART_OF_SPEECH_INVALID")
    rows=value.get("senses")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        raise ValueError("NONEMPTY_SENSE_SET_REQUIRED")
    out=[]; seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            raise ValueError("SENSE_NOT_OBJECT:"+str(i))
        sid=_token(row.get("sense_id"),"SENSE_ID")
        syn=_token(row.get("synset_id"),"SYNSET_ID")
        spos=_token(row.get("part_of_speech"),"SENSE_POS")
        if sid in seen:
            raise ValueError("SENSE_ID_DUPLICATE:"+sid)
        seen.add(sid)
        out.append({"sense_id":sid,"synset_id":syn,"part_of_speech":spos})
    out.sort(key=lambda x:(x["part_of_speech"],x["sense_id"],x["synset_id"]))
    return {
        "lemma":lemma,"part_of_speech":pos,
        "senses":out,"sense_ids":[x["sense_id"] for x in out],
    }


def _same(a:Any,b:Any)->bool:
    return a==b


def evaluate(problem:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(problem,Mapping) or problem.get("schema")!=SCHEMA:
            raise ValueError("PROBLEM_SCHEMA_INVALID")
        if set(problem)!={"schema","scope_id","sense_universe","source_id","source_text"}:
            raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
        scope_id=_token(problem.get("scope_id"),"SCOPE_ID")
        source_id=_token(problem.get("source_id"),"SOURCE_ID")
        text=problem.get("source_text")
        if not isinstance(text,str) or not text:
            raise ValueError("SOURCE_TEXT_INVALID")

        universe=_universe(problem.get("sense_universe"))
        sense_ids=list(universe["sense_ids"])
        sense_set=set(sense_ids)
        parsed=parse_sense_evidence(text,source=source_id)
        if parsed.get("status")=="FAIL_CLOSED":
            raise ValueError("SOURCE_EVIDENCE_PARSE_FAIL_CLOSED:"+str(parsed.get("reason") or "UNKNOWN"))
        if parsed.get("status")=="UNRESOLVED":
            return {
                "schema":SCHEMA,"status":"OPEN__SOURCE_DECISION_EVIDENCE_UNRESOLVED",
                "pass":False,"scope_id":scope_id,
                "parse_reason":parsed.get("reason"),
                "candidate_sense_set_complete_relative_to_oewn_release":True,
                "open_world_english_sense_completeness_claimed":False,
                "semantic_truth_authority":False,"terminal_authority":False,
            }

        terminals={}
        obs_rows={}
        observed={}
        clause_receipts=[]
        for row in parsed.get("clauses") or []:
            if not isinstance(row,Mapping):
                continue
            kind=row.get("kind")
            clause_receipts.append(deepcopy(dict(row)))
            if kind=="TERMINAL_SIGNATURE":
                sid=str(row.get("sense_id") or "")
                if sid not in sense_set:
                    raise ValueError("TERMINAL_SENSE_NOT_IN_RELEASE_UNIVERSE:"+sid)
                terminals[sid]=deepcopy(dict(row.get("terminal_signature") or {}))
            elif kind=="OBSERVATION_OUTCOME":
                sid=str(row.get("sense_id") or "")
                oid=str(row.get("observation_id") or "")
                if sid not in sense_set:
                    raise ValueError("OBSERVATION_SENSE_NOT_IN_RELEASE_UNIVERSE:"+sid)
                obs_rows.setdefault(oid,[]).append({
                    "sense_id":sid,
                    "cost_units":row.get("cost_units"),
                    "outcome":deepcopy(row.get("outcome")),
                    "clause_id":row.get("clause_id"),
                })
            elif kind=="OBSERVED_OUTCOME":
                oid=str(row.get("observation_id") or "")
                observed[oid]=deepcopy(row.get("observed_outcome"))

        terminal_states={}
        open_atoms=[]
        for sid in sense_ids:
            if sid in terminals:
                terminal_states[sid]={"kind":"EXACT","terminal_signature":deepcopy(terminals[sid])}
            else:
                terminal_states[sid]={"kind":"TOP"}
                open_atoms.append({
                    "dimension":"TERMINAL_SIGNATURE",
                    "sense_id":sid,
                    "state":"TOP",
                    "proof_obligation":{
                        "kind":"PROVE_SENSE_TERMINAL_SIGNATURE",
                        "scope_id":scope_id,
                        "source_id":source_id,
                        "sense_id":sid,
                    },
                })

        observation_states={}
        complete_observations=[]
        partial_observation_obligations=[]
        for oid in sorted(set(obs_rows)|set(observed)):
            rows=obs_rows.get(oid,[])
            by_sid={}
            costs=set()
            for row in rows:
                sid=row["sense_id"]
                if sid in by_sid:
                    raise ValueError("OBSERVATION_SENSE_DUPLICATE:"+oid+":"+sid)
                by_sid[sid]=deepcopy(row["outcome"])
                costs.add(float(row["cost_units"]))
            if len(costs)>1:
                raise ValueError("OBSERVATION_COST_INCONSISTENT:"+oid)
            cost=(next(iter(costs)) if costs else None)
            missing=sorted(sense_set-set(by_sid))
            state={
                "observation_id":oid,
                "cost_units":cost,
                "outcome_states":{
                    sid:(
                        {"kind":"EXACT","outcome":deepcopy(by_sid[sid])}
                        if sid in by_sid else {"kind":"TOP"}
                    )
                    for sid in sense_ids
                },
                "observed_outcome":(
                    {"kind":"EXACT","value":deepcopy(observed[oid])}
                    if oid in observed else {"kind":"UNOBSERVED"}
                ),
                "outcome_map_complete":not missing and cost is not None,
            }
            observation_states[oid]=state
            if state["outcome_map_complete"]:
                complete_observations.append({
                    "observation_id":oid,
                    "outcome_map_complete":True,
                    "outcomes":deepcopy(by_sid),
                    "cost_units":float(cost),
                })
            else:
                obligation={
                    "kind":"COMPLETE_OBSERVATION_OUTCOME_MAP",
                    "scope_id":scope_id,
                    "source_id":source_id,
                    "observation_id":oid,
                    "missing_sense_ids":missing,
                    "cost_missing":cost is None,
                }
                partial_observation_obligations.append(obligation)

        base={
            "schema":SCHEMA,
            "scope_id":scope_id,
            "release_id":RELEASE_ID,
            "release_sha256":RELEASE_SHA256,
            "lemma":universe["lemma"],
            "part_of_speech":universe["part_of_speech"],
            "candidate_sense_ids":sense_ids,
            "candidate_sense_set_complete_relative_to_oewn_release":True,
            "open_world_english_sense_completeness_claimed":False,
            "terminal_states":terminal_states,
            "observation_states":observation_states,
            "observed_outcomes":deepcopy(observed),
            "source_clause_receipts":clause_receipts,
            "open_lattice_atoms":open_atoms,
            "semantic_truth_authority":False,
            "execution_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
        }

        if open_atoms:
            return {
                **base,
                "status":"OPEN__SENSE_TERMINAL_SIGNATURE_TOP_REMAINS",
                "pass":False,
                "decision_sufficient":False,
                "next_proof_obligations":[deepcopy(x["proof_obligation"]) for x in open_atoms],
            }

        complete_by_id={x["observation_id"]:x for x in complete_observations}
        incomplete_observed=sorted(oid for oid in observed if oid not in complete_by_id)
        if incomplete_observed:
            obligations=[
                x for x in partial_observation_obligations
                if x["observation_id"] in incomplete_observed
            ]
            return {
                **base,
                "status":"OPEN__OBSERVED_OUTCOME_MAP_TOP_REMAINS",
                "pass":False,
                "decision_sufficient":False,
                "blocking_observation_ids":incomplete_observed,
                "next_proof_obligations":obligations,
            }

        surviving=list(sense_ids)
        for oid,value in observed.items():
            row=complete_by_id[oid]
            surviving=[
                sid for sid in surviving
                if _same(row["outcomes"][sid],value)
            ]
        if not surviving:
            return {
                **base,
                "status":"MODEL_FALSIFIED__OBSERVED_OUTCOMES_EXCLUDE_ALL_RELEASE_SENSES",
                "pass":False,
                "decision_sufficient":False,
                "surviving_sense_ids":[],
                "next_proof_obligations":[],
            }

        signatures={sid:terminals[sid] for sid in surviving}
        canon_sigs={json_key for json_key in [
            __import__("json").dumps(signatures[sid],sort_keys=True,separators=(",",":"),ensure_ascii=False)
            for sid in surviving
        ]}
        if len(canon_sigs)==1:
            return {
                **base,
                "status":"PASS__SENSE_DECISION_SUFFICIENT",
                "pass":True,
                "decision_sufficient":True,
                "intended_sense_identified":len(surviving)==1,
                "identified_sense_id":surviving[0] if len(surviving)==1 else None,
                "surviving_sense_ids":surviving,
                "terminal_signature":deepcopy(signatures[surviving[0]]),
                "decision_rule":(
                    "ONE_SURVIVING_SOURCE_EVIDENCE_SENSE"
                    if len(surviving)==1
                    else "ALL_SURVIVING_SENSES_TERMINALLY_EQUIVALENT"
                ),
                "next_proof_obligations":[],
            }

        remaining_observations=[]
        for row in complete_observations:
            oid=row["observation_id"]
            if oid in observed:
                continue
            remaining_observations.append({
                "observation_id":oid,
                "outcome_map_complete":True,
                "outcomes":{sid:deepcopy(row["outcomes"][sid]) for sid in surviving},
                "cost_units":row["cost_units"],
            })
        frontier=solve_frontier({
            "hypothesis_set_complete":True,
            "worlds":[
                {
                    "world_id":sid,
                    "terminal_signature_complete":True,
                    "terminal_signature":deepcopy(signatures[sid]),
                }
                for sid in surviving
            ],
            "observations":remaining_observations,
        })
        if frontier.get("pass") is True:
            return {
                **base,
                "status":"OPEN__MINIMUM_TERMINAL_DISCRIMINATOR_REQUIRED",
                "pass":False,
                "decision_sufficient":False,
                "surviving_sense_ids":surviving,
                "next_observation_id":frontier.get("first_observation_id"),
                "minimum_worst_case_cost_units":frontier.get("minimum_worst_case_cost_units"),
                "information_frontier":frontier,
                "next_proof_obligations":[],
            }

        return {
            **base,
            "status":"OPEN__SEPARATING_OBSERVATION_REQUIRED",
            "pass":False,
            "decision_sufficient":False,
            "surviving_sense_ids":surviving,
            "partial_observation_obligations":partial_observation_obligations,
            "unresolved_pairs":deepcopy(frontier.get("unresolved_pairs") or []),
            "next_proof_obligations":(
                partial_observation_obligations
                if partial_observation_obligations
                else [{
                    "kind":"DISCOVER_OR_PROVE_SEPARATING_OBSERVATION",
                    "scope_id":scope_id,
                    "source_id":source_id,
                    "surviving_sense_ids":surviving,
                }]
            ),
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "candidate_sense_set_complete_relative_to_oewn_release":False,
            "open_world_english_sense_completeness_claimed":False,
            "semantic_truth_authority":False,"terminal_authority":False,
        }
