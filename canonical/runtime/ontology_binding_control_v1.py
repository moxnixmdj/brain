"""Proof-carrying bounded ontology/concept binding V1.

Similarity may generate candidates but cannot certify concept identity.
Positive authority comes only from a content-addressed ontology snapshot plus
exact labels/aliases or ontology-declared sufficient context facts. Ambiguity is
preserved unless one concept is proved, or all exact-label survivors have one
complete identical decision signature.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_ONTOLOGY_BINDING_CONTROL_V1"
ONTOLOGY_SCHEMA="PROJECT_BRAIN_AUTHENTICATED_ONTOLOGY_SNAPSHOT_V1"
OUTPUTS={"CONCEPT_IDENTITY","CURRENT_DECISION_SUBSTITUTION"}

class OntologyBindingError(ValueError):
    pass

def _canon(v: Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def _sha(v: Any)->str:
    return sha256(_canon(v).encode()).hexdigest()

def _norm(v: Any)->str:
    return " ".join(str(v if v is not None else "").strip().split()).casefold()

def ontology_sha256(o: Mapping[str,Any])->str:
    return _sha(dict(o))

def context_facts_sha256(facts: Sequence[str])->str:
    return _sha(sorted({_norm(x) for x in facts if _norm(x)}))

def _fact_sets(raw: Any,cid:str)->list[list[str]]:
    if raw is None: return []
    if not isinstance(raw,Sequence) or isinstance(raw,(str,bytes)):
        raise OntologyBindingError("SUFFICIENT_FACT_SETS_INVALID:"+cid)
    out=[]
    for i,row in enumerate(raw):
        if not isinstance(row,Sequence) or isinstance(row,(str,bytes)) or not row:
            raise OntologyBindingError(f"SUFFICIENT_FACT_SET_INVALID:{cid}:{i}")
        fs=sorted({_norm(x) for x in row if _norm(x)})
        if not fs:
            raise OntologyBindingError(f"SUFFICIENT_FACT_SET_EMPTY:{cid}:{i}")
        if fs not in out: out.append(fs)
    return out

def _ontology(raw: Any,scope:str,expected:str)->tuple[list[dict[str,Any]],str]:
    if not isinstance(raw,Mapping): raise OntologyBindingError("ONTOLOGY_NOT_OBJECT")
    if raw.get("schema")!=ONTOLOGY_SCHEMA: raise OntologyBindingError("ONTOLOGY_SCHEMA_INVALID")
    if str(raw.get("scope_id") or "").strip()!=scope: raise OntologyBindingError("ONTOLOGY_SCOPE_MISMATCH")
    if not isinstance(expected,str) or len(expected)!=64: raise OntologyBindingError("EXPECTED_ONTOLOGY_SHA256_REQUIRED")
    actual=ontology_sha256(raw)
    if actual!=expected: raise OntologyBindingError("ONTOLOGY_CONTENT_ADDRESS_MISMATCH")
    if not str(raw.get("scheme_id") or "").strip(): raise OntologyBindingError("ONTOLOGY_SCHEME_ID_REQUIRED")
    if not str(raw.get("source_id") or "").strip(): raise OntologyBindingError("ONTOLOGY_SOURCE_ID_REQUIRED")
    entries=raw.get("entries")
    if not isinstance(entries,Sequence) or isinstance(entries,(str,bytes)) or not entries:
        raise OntologyBindingError("ONTOLOGY_ENTRIES_INVALID")
    out=[]; seen=set()
    for i,e in enumerate(entries):
        if not isinstance(e,Mapping): raise OntologyBindingError(f"ONTOLOGY_ENTRY_NOT_OBJECT:{i}")
        cid=str(e.get("concept_id") or "").strip(); pref=str(e.get("preferred_label") or "").strip()
        if not cid or cid in seen: raise OntologyBindingError(f"CONCEPT_ID_INVALID_OR_DUPLICATE:{i}")
        if not pref: raise OntologyBindingError("PREFERRED_LABEL_REQUIRED:"+cid)
        seen.add(cid)
        alts=e.get("alt_labels") or []
        if not isinstance(alts,Sequence) or isinstance(alts,(str,bytes)):
            raise OntologyBindingError("ALT_LABELS_INVALID:"+cid)
        labels=[_norm(pref)]
        for x in alts:
            n=_norm(x)
            if not n: raise OntologyBindingError("ALT_LABEL_EMPTY:"+cid)
            if n not in labels: labels.append(n)
        sig=e.get("decision_signature")
        if sig is not None and not isinstance(sig,Mapping):
            raise OntologyBindingError("DECISION_SIGNATURE_NOT_OBJECT:"+cid)
        complete=e.get("decision_signature_complete") is True
        if complete and sig is None: raise OntologyBindingError("COMPLETE_DECISION_SIGNATURE_MISSING:"+cid)
        out.append({
            "concept_id":cid,"preferred_label":pref,"labels":labels,
            "sufficient_fact_sets":_fact_sets(e.get("sufficient_fact_sets"),cid),
            "decision_signature":deepcopy(dict(sig)) if isinstance(sig,Mapping) else None,
            "decision_signature_complete":complete,
        })
    return out,actual

def _context(raw:Any,expected:Any)->tuple[set[str],str|None]:
    if raw is None:
        if expected is not None: raise OntologyBindingError("CONTEXT_DIGEST_WITHOUT_CONTEXT")
        return set(),None
    if not isinstance(raw,Sequence) or isinstance(raw,(str,bytes)): raise OntologyBindingError("CONTEXT_FACTS_INVALID")
    facts=sorted({_norm(x) for x in raw if _norm(x)})
    if not facts: raise OntologyBindingError("CONTEXT_FACTS_EMPTY")
    if not isinstance(expected,str) or len(expected)!=64: raise OntologyBindingError("EXPECTED_CONTEXT_SHA256_REQUIRED")
    actual=context_facts_sha256(facts)
    if actual!=expected: raise OntologyBindingError("CONTEXT_FACTS_CONTENT_ADDRESS_MISMATCH")
    return set(facts),actual

def _missing(e:Mapping[str,Any],facts:set[str])->list[str]:
    choices=[sorted(set(row)-facts) for row in e.get("sufficient_fact_sets") or []]
    choices=[x for x in choices if x]
    return sorted(choices,key=lambda x:(len(x),x))[0] if choices else []

def resolve(problem: Mapping[str,Any])->dict[str,Any]:
    if not isinstance(problem,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"PROBLEM_NOT_OBJECT","terminal_authority":False,"terminal_credit_delta":0}
    allowed={"mention_id","mention_surface","scope_id","required_output","ontology","expected_ontology_sha256","context_facts","expected_context_sha256","candidate_concept_ids","candidate_relations"}
    extra=set(problem)-allowed
    if extra:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"UNMODELED_FIELDS:"+",".join(sorted(map(str,extra))),"terminal_authority":False,"terminal_credit_delta":0}
    mid=str(problem.get("mention_id") or "").strip(); surface=str(problem.get("mention_surface") or "").strip()
    scope=str(problem.get("scope_id") or "").strip(); required=str(problem.get("required_output") or "CONCEPT_IDENTITY").strip().upper()
    if not mid: raise OntologyBindingError("MENTION_ID_REQUIRED")
    if not surface: raise OntologyBindingError("MENTION_SURFACE_REQUIRED")
    if not scope: raise OntologyBindingError("SCOPE_ID_REQUIRED")
    if required not in OUTPUTS: raise OntologyBindingError("REQUIRED_OUTPUT_INVALID")
    entries,odigest=_ontology(problem.get("ontology"),scope,str(problem.get("expected_ontology_sha256") or ""))
    facts,fdigest=_context(problem.get("context_facts"),problem.get("expected_context_sha256"))
    by={e["concept_id"]:e for e in entries}; mention=_norm(surface)
    exact=[e["concept_id"] for e in entries if mention in set(e["labels"])]
    raw_ids=problem.get("candidate_concept_ids") or []
    if not isinstance(raw_ids,Sequence) or isinstance(raw_ids,(str,bytes)): raise OntologyBindingError("CANDIDATE_CONCEPT_IDS_INVALID")
    candidate_ids=[]
    for x in raw_ids:
        cid=str(x or "").strip()
        if not cid or cid not in by: raise OntologyBindingError("CANDIDATE_CONCEPT_ID_UNKNOWN")
        if cid not in candidate_ids: candidate_ids.append(cid)
    raw_rel=problem.get("candidate_relations") or []
    if not isinstance(raw_rel,Sequence) or isinstance(raw_rel,(str,bytes)): raise OntologyBindingError("CANDIDATE_RELATIONS_INVALID")
    rels=[]
    for x in raw_rel:
        if not isinstance(x,Mapping): raise OntologyBindingError("CANDIDATE_RELATION_NOT_OBJECT")
        rels.append(deepcopy(dict(x)))
    fact_proved=[]; witnesses={}
    for e in entries:
        good=[row for row in e["sufficient_fact_sets"] if set(row).issubset(facts)]
        if good:
            fact_proved.append(e["concept_id"]); witnesses[e["concept_id"]]=sorted(good,key=lambda x:(len(x),x))[0]
    identity=False; cid=None; basis=None
    if len(exact)==1:
        identity=True; cid=exact[0]; basis="UNIQUE_EXACT_ONTOLOGY_LABEL_OR_ALT_LABEL"
    elif len(exact)>1:
        narrowed=[x for x in exact if x in fact_proved]
        if len(narrowed)==1:
            identity=True; cid=narrowed[0]; basis="AMBIGUOUS_EXACT_LABEL_DISAMBIGUATED_BY_ONTOLOGY_SUFFICIENT_FACT_SET"
    elif len(fact_proved)==1:
        identity=True; cid=fact_proved[0]; basis="UNIQUE_ONTOLOGY_SUFFICIENT_FACT_SET"
    survivors=list(exact) or list(candidate_ids) or [e["concept_id"] for e in entries]
    domain_complete=bool(exact)
    substitution=False; shared=None
    if not identity and domain_complete and len(survivors)>1:
        rows=[by[x] for x in survivors]
        if all(x["decision_signature_complete"] for x in rows):
            sigs=[x["decision_signature"] for x in rows]
            if all(x==sigs[0] for x in sigs[1:]):
                substitution=True; shared=deepcopy(sigs[0])
    strongest="CONCEPT_IDENTITY" if identity else ("CURRENT_DECISION_SUBSTITUTION" if substitution else "UNKNOWN")
    passed=identity if required=="CONCEPT_IDENTITY" else (identity or substitution)
    targets=[]
    if not passed:
        for x in survivors:
            miss=_missing(by[x],facts)
            if miss: targets.append({"concept_id":x,"minimum_missing_sufficient_fact_set":miss})
        targets.sort(key=lambda x:(len(x["minimum_missing_sufficient_fact_set"]),x["concept_id"]))
    return {
        "schema":SCHEMA,"pass":passed,
        "status":"PASS__AUTHENTICATED_ONTOLOGY_BINDING_RECOMPUTED" if passed else "OPEN__ONTOLOGY_BINDING_NOT_PROVED",
        "action":"USE_PROVED_BINDING_WITHIN_BOUND_SCOPE" if passed else "PRESERVE_SURVIVING_CONCEPTS_AND_ACQUIRE_ONLY_MINIMUM_DISCRIMINATING_FACTS",
        "mention_id":mid,"mention_surface":surface,"scope_id":scope,"required_output":required,
        "strongest_proved_binding":strongest,"identity_proved":identity,"concept_id":cid,
        "concept_preferred_label":by[cid]["preferred_label"] if cid else None,"identity_basis":basis,
        "identity_fact_witness":witnesses.get(cid) if cid else None,
        "current_decision_substitution_proved":substitution,"shared_decision_signature":shared,
        "exact_label_candidate_ids":exact,"fact_proved_candidate_ids":sorted(fact_proved),
        "surviving_candidate_ids":survivors,"candidate_domain_complete_for_decision_substitution":domain_complete,
        "next_evidence_targets":targets,"ontology_sha256":odigest,"context_facts_sha256":fdigest,
        "candidate_concept_ids":candidate_ids,"candidate_concept_ids_are_authority":False,
        "candidate_relations":rels,"candidate_relations_are_authority":False,
        "similarity_can_certify_identity":False,"expected_digest_authority_is_external_to_this_module":True,
        "scope_leakage_authorized":False,"transitive_mapping_promotion_authorized":False,
        "semantic_truth_authority":False,"execution_authority":False,"promotion_authority":False,
        "acceptance_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
    }
