"""Decision-relative partial-effect pruning over semantic lattice V8."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime import cross_document_effect_semantic_lattice_v8 as v8
from canonical.runtime.partial_effect_query_irrelevance_v1 import prove_inapplicable
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V9"

def evaluate(problem:Mapping[str,Any],*,relation_verifier=None)->dict[str,Any]:
    base=v8.evaluate(problem,relation_verifier=relation_verifier)
    if base.get("status")=="FAIL_CLOSED":
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "reason":"V8_FAIL_CLOSED:"+str(base.get("reason") or "UNKNOWN"),
            "v8_result":base,"semantic_truth_authority":False,"terminal_authority":False,
        }
    if base.get("pass") is True:
        return {
            **deepcopy(dict(base)),
            "schema":SCHEMA,
            "status":"PASS__V8_ALREADY_CLOSED",
            "pruned_partial_effects":[],
            "semantic_truth_authority":False,
            "terminal_authority":False,
        }

    query=base.get("query")
    if not isinstance(query,Mapping):
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "reason":"V8_QUERY_MISSING","semantic_truth_authority":False,"terminal_authority":False,
        }

    pruned_keys=set()
    pruned=[]
    exact_effects={}
    for doc in base.get("lattice_documents") or []:
        if not isinstance(doc,Mapping):
            continue
        did=str(doc.get("document_id") or "")
        states=doc.get("effect_states")
        if not did or not isinstance(states,Mapping):
            continue
        for eid,state in states.items():
            if not isinstance(state,Mapping):
                continue
            key=(did,str(eid))
            if state.get("kind") in {"EXACT_RELATION","EXACT_FIELDS"} and isinstance(state.get("effect"),Mapping):
                exact_effects[key]=deepcopy(dict(state["effect"]))
                continue
            if state.get("kind")!="PARTIAL_FIELDS":
                continue
            proof=prove_inapplicable(state,query)
            if proof.get("status")=="FAIL_CLOSED":
                return {
                    "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                    "reason":"PARTIAL_IRRELEVANCE_PROOF_FAIL_CLOSED:"+str(proof.get("reason")),
                    "semantic_truth_authority":False,"terminal_authority":False,
                }
            if proof.get("pass") is True:
                pruned_keys.add(key)
                pruned.append({
                    "document_id":did,
                    "effect_id":str(eid),
                    "reason":deepcopy(proof.get("reason")),
                    "proof_status":proof.get("status"),
                })

    remaining_atoms=[]
    for atom in base.get("open_lattice_atoms") or []:
        if not isinstance(atom,Mapping):
            continue
        key=(str(atom.get("document_id") or ""),str(atom.get("effect_id") or ""))
        if key in pruned_keys:
            continue
        remaining_atoms.append(deepcopy(dict(atom)))

    common={
        "schema":SCHEMA,
        "case_id":base.get("case_id"),
        "query":deepcopy(dict(query)),
        "lattice_documents":deepcopy(base.get("lattice_documents") or []),
        "proof_receipts":deepcopy(base.get("proof_receipts") or []),
        "refinement_count":base.get("refinement_count"),
        "pruned_partial_effects":sorted(pruned,key=lambda x:(x["document_id"],x["effect_id"])),
        "open_lattice_atoms":remaining_atoms,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "pruning_boundary":"ONLY_EXACT_VALID_TIME_OR_EXACT_CONDITION_MISMATCH_MAY_PRUNE_PARTIAL_EFFECTS",
    }

    if remaining_atoms:
        return {
            **common,
            "status":"OPEN__QUERY_RELEVANT_EFFECT_FIELD_TOP_REMAINS_AFTER_PARTIAL_PRUNING",
            "pass":False,
            "next_proof_obligations":[deepcopy(x.get("proof_obligation")) for x in remaining_atoms],
            "query_relative_effect_semantics_finite":False,
        }

    if not exact_effects:
        return {
            **common,
            "status":"OPEN__NO_APPLICABLE_EXACT_EFFECT_AFTER_PARTIAL_PRUNING",
            "pass":False,
            "next_proof_obligations":[],
            "query_relative_effect_semantics_finite":True,
        }

    by_doc={}
    for (did,_),effect in exact_effects.items():
        by_doc.setdefault(did,[]).append(effect)
    ws_docs=[]
    for did in sorted(by_doc):
        slots=[]
        for effect in sorted(by_doc[did],key=lambda x:x["effect_id"]):
            eid=effect["effect_id"]
            slots.append({
                "slot_id":did+"::"+eid,
                "hypothesis_set_complete":True,
                "hypotheses":[{"hypothesis_id":did+"::"+eid+"::exact","effect":effect}],
            })
        ws_docs.append({"document_id":did,"effect_slots":slots})

    wsp={
        "schema":worldset.SCHEMA,
        "case_id":str(base.get("case_id") or ""),
        "hypothesis_set_complete":True,
        "compatibility_constraints_complete":True,
        "incompatible_hypothesis_sets":[],
        "documents":ws_docs,
        "query":deepcopy(dict(query)),
    }
    finite=worldset.evaluate(wsp)
    checked=worldset_verify.verify(wsp,finite)
    if checked.get("verified") is not True:
        return {
            **common,
            "status":"FAIL_CLOSED","pass":False,
            "reason":"FINITE_WORLDSET_VERIFY_FAILED:"+",".join(checked.get("errors") or []),
        }

    if finite.get("pass") is not True:
        return {
            **common,
            "status":"OPEN__PARTIAL_PRUNING_COMPLETE__EFFECT_COMPOSITION_NOT_CLOSED",
            "pass":False,
            "query_relative_effect_semantics_finite":True,
            "finite_worldset_result":finite,
            "finite_worldset_verification":checked,
            "possible_outcomes":deepcopy(finite.get("possible_outcomes") or []),
            "minimum_discriminator_slots":deepcopy(finite.get("minimum_discriminator_slots") or []),
            "world_count":finite.get("world_count"),
            "next_proof_obligations":[],
        }

    return {
        **common,
        "status":"PASS__PARTIAL_EFFECT_PRUNING_AND_COMPOSITION_VERIFIED",
        "pass":True,
        "query_relative_effect_semantics_finite":True,
        "finite_worldset_result":finite,
        "finite_worldset_verification":checked,
        "effective_value":deepcopy(finite.get("effective_value")),
        "world_count":finite.get("world_count"),
        "next_proof_obligations":[],
    }
