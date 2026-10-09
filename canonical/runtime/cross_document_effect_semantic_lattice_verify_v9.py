"""Independent verifier for decision-relative partial-effect pruning lattice V9."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from typing import Any, Mapping

from canonical.runtime import cross_document_effect_semantic_lattice_v8 as v8
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v8 as v8_verify
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_VERIFY_V9"

def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def _exact(component:Mapping[str,Any]|None)->tuple[bool,Any]:
    if not isinstance(component,Mapping):
        return False,None
    if str(component.get("kind") or "").startswith("EXACT"):
        return True,deepcopy(component.get("value"))
    return False,None

def _reason(state:Mapping[str,Any],query:Mapping[str,Any])->dict[str,Any]|None:
    components=state.get("components")
    if not isinstance(components,Mapping):
        return None
    as_of=date.fromisoformat(str(query["as_of"]))
    context=query["context"]

    ok,start=_exact(components.get("valid_from"))
    if ok and start is not None and as_of<date.fromisoformat(str(start)):
        return {"kind":"VALID_FROM_AFTER_QUERY","valid_from":start,"as_of":query["as_of"]}

    ok,end=_exact(components.get("valid_until"))
    if ok and end is not None and as_of>=date.fromisoformat(str(end)):
        return {"kind":"VALID_UNTIL_NOT_AFTER_QUERY","valid_until":end,"as_of":query["as_of"]}

    ok,conditions=_exact(components.get("conditions"))
    if ok:
        if not isinstance(conditions,Mapping):
            raise ValueError("EXACT_CONDITIONS_NOT_OBJECT")
        for key,expected in conditions.items():
            if key not in context or _canon(context[key])!=_canon(expected):
                return {
                    "kind":"CONDITION_MISMATCH",
                    "condition_key":key,
                    "expected":deepcopy(expected),
                    "observed":deepcopy(context.get(key)),
                    "context_key_present":key in context,
                }
    return None

def _expected(problem:Mapping[str,Any],*,relation_verifier=None)->dict[str,Any]:
    base=v8.evaluate(problem,relation_verifier=relation_verifier)
    checked=v8_verify.verify(problem,base,relation_verifier=relation_verifier)
    if checked.get("verified") is not True:
        raise ValueError("V8_INDEPENDENT_VERIFICATION_FAILED:"+",".join(checked.get("errors") or []))
    if base.get("pass") is True:
        return {
            "status":"PASS__V8_ALREADY_CLOSED","pass":True,
            "pruned_partial_effects":[],
            "open_lattice_atoms":deepcopy(base.get("open_lattice_atoms") or []),
            "next_proof_obligations":deepcopy(base.get("next_proof_obligations") or []),
            "query_relative_effect_semantics_finite":base.get("query_relative_effect_semantics_finite"),
            "effective_value":deepcopy(base.get("effective_value")),
            "world_count":base.get("world_count"),
        }

    query=base.get("query")
    if not isinstance(query,Mapping):
        raise ValueError("V8_QUERY_MISSING")

    exact={}
    pruned=[]; pruned_keys=set()
    for doc in base.get("lattice_documents") or []:
        if not isinstance(doc,Mapping): continue
        did=str(doc.get("document_id") or "")
        states=doc.get("effect_states")
        if not did or not isinstance(states,Mapping): continue
        for eid,state in states.items():
            if not isinstance(state,Mapping): continue
            key=(did,str(eid))
            if state.get("kind") in {"EXACT_RELATION","EXACT_FIELDS"} and isinstance(state.get("effect"),Mapping):
                exact[key]=deepcopy(dict(state["effect"]))
            elif state.get("kind")=="PARTIAL_FIELDS":
                why=_reason(state,query)
                if why is not None:
                    pruned_keys.add(key)
                    pruned.append({
                        "document_id":did,"effect_id":str(eid),
                        "reason":why,
                        "proof_status":{
                            "VALID_FROM_AFTER_QUERY":"PASS__PROVED_INAPPLICABLE_VALID_FROM",
                            "VALID_UNTIL_NOT_AFTER_QUERY":"PASS__PROVED_INAPPLICABLE_VALID_UNTIL",
                            "CONDITION_MISMATCH":"PASS__PROVED_INAPPLICABLE_CONDITION",
                        }[why["kind"]],
                    })

    atoms=[]
    for atom in base.get("open_lattice_atoms") or []:
        if not isinstance(atom,Mapping): continue
        key=(str(atom.get("document_id") or ""),str(atom.get("effect_id") or ""))
        if key not in pruned_keys:
            atoms.append(deepcopy(dict(atom)))

    if atoms:
        return {
            "status":"OPEN__QUERY_RELEVANT_EFFECT_FIELD_TOP_REMAINS_AFTER_PARTIAL_PRUNING",
            "pass":False,
            "pruned_partial_effects":sorted(pruned,key=lambda x:(x["document_id"],x["effect_id"])),
            "open_lattice_atoms":atoms,
            "next_proof_obligations":[deepcopy(x.get("proof_obligation")) for x in atoms],
            "query_relative_effect_semantics_finite":False,
        }

    if not exact:
        return {
            "status":"OPEN__NO_APPLICABLE_EXACT_EFFECT_AFTER_PARTIAL_PRUNING",
            "pass":False,
            "pruned_partial_effects":sorted(pruned,key=lambda x:(x["document_id"],x["effect_id"])),
            "open_lattice_atoms":[],
            "next_proof_obligations":[],
            "query_relative_effect_semantics_finite":True,
        }

    by_doc={}
    for (did,_),effect in exact.items():
        by_doc.setdefault(did,[]).append(effect)
    docs=[]
    for did in sorted(by_doc):
        slots=[]
        for effect in sorted(by_doc[did],key=lambda x:x["effect_id"]):
            eid=effect["effect_id"]
            slots.append({
                "slot_id":did+"::"+eid,
                "hypothesis_set_complete":True,
                "hypotheses":[{"hypothesis_id":did+"::"+eid+"::exact","effect":effect}],
            })
        docs.append({"document_id":did,"effect_slots":slots})
    wsp={
        "schema":worldset.SCHEMA,
        "case_id":str(base.get("case_id") or ""),
        "hypothesis_set_complete":True,
        "compatibility_constraints_complete":True,
        "incompatible_hypothesis_sets":[],
        "documents":docs,
        "query":deepcopy(dict(query)),
    }
    finite=worldset.evaluate(wsp)
    wc=worldset_verify.verify(wsp,finite)
    if wc.get("verified") is not True:
        raise ValueError("WORLDSET_VERIFY_FAILED:"+",".join(wc.get("errors") or []))

    common={
        "pruned_partial_effects":sorted(pruned,key=lambda x:(x["document_id"],x["effect_id"])),
        "open_lattice_atoms":[],
        "next_proof_obligations":[],
        "query_relative_effect_semantics_finite":True,
        "world_count":finite.get("world_count"),
    }
    if finite.get("pass") is True:
        return {
            **common,
            "status":"PASS__PARTIAL_EFFECT_PRUNING_AND_COMPOSITION_VERIFIED",
            "pass":True,
            "effective_value":deepcopy(finite.get("effective_value")),
        }
    return {
        **common,
        "status":"OPEN__PARTIAL_PRUNING_COMPLETE__EFFECT_COMPOSITION_NOT_CLOSED",
        "pass":False,
        "possible_outcomes":deepcopy(finite.get("possible_outcomes") or []),
        "minimum_discriminator_slots":deepcopy(finite.get("minimum_discriminator_slots") or []),
    }

def verify(problem:Mapping[str,Any],result:Mapping[str,Any],*,relation_verifier=None)->dict[str,Any]:
    errors=[]
    try:
        expected=_expected(problem,relation_verifier=relation_verifier)
        if not isinstance(result,Mapping):
            raise ValueError("RESULT_NOT_OBJECT")
        keys=[
            "status","pass","pruned_partial_effects","open_lattice_atoms",
            "next_proof_obligations","query_relative_effect_semantics_finite",
        ]
        if expected.get("pass") is True:
            keys+=["effective_value","world_count"]
        elif expected.get("query_relative_effect_semantics_finite") is True:
            keys+=["possible_outcomes","minimum_discriminator_slots","world_count"]
        for key in keys:
            if result.get(key)!=expected.get(key):
                errors.append("MISMATCH:"+key)
        if result.get("semantic_truth_authority") is not False:
            errors.append("SEMANTIC_TRUTH_AUTHORITY_CLAIMED")
        if result.get("terminal_authority") is not False:
            errors.append("TERMINAL_AUTHORITY_CLAIMED")
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_PARTIAL_EFFECT_PRUNING_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "boundary":"INDEPENDENT_V8_REVERIFICATION_PLUS_SEPARATE_APPLICABILITY_PRUNING_AND_FINITE_WORLDSET_RECOMPUTATION",
    }
