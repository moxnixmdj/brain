"""Independent verifier for typed-decision-derived Finance terminal signatures."""
from __future__ import annotations
from copy import deepcopy
import json,re
from hashlib import sha256
from typing import Any,Mapping,Sequence

from canonical.runtime import source_grounded_coreference as coref
from canonical.runtime import finance_marked_mention_universe_verify_v1 as marked_verify
from canonical.runtime.bound_capabilities import evidence_decision_verify as decision_verify

SCHEMA="PROJECT_BRAIN_FINANCE_DERIVED_TERMINAL_SIGNATURES_VERIFY_V1"
INPUT_SCHEMA="PROJECT_BRAIN_FINANCE_MARKED_COREFERENCE_TYPED_DECISION_SOURCE_V1"
OUTPUT_SCHEMA="PROJECT_BRAIN_FINANCE_DERIVED_TERMINAL_SIGNATURES_V1"
TERMINAL_PROJECTION_SCHEMA="PROJECT_BRAIN_TYPED_DECISION_TERMINAL_PROJECTION_V1"
TERMINAL={"DECIDED","CONFLICTED","INSUFFICIENT","NO_ADMISSIBLE_ALTERNATIVE"}
REF_FORMS=frozenset(coref._PRONOUNS)
REF_RE=re.compile(r"\b(?:"+"|".join(sorted((re.escape(x) for x in REF_FORMS),key=len,reverse=True))+r")\b",re.I)

def _canon(x:Any)->bytes:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def _sha(x:Any)->str:return sha256(_canon(x)).hexdigest()

def _candidate_ids(source:Mapping[str,Any])->list[str]:
    if not isinstance(source,Mapping) or source.get("schema")!=INPUT_SCHEMA:
        raise ValueError("SOURCE_SCHEMA_INVALID")
    if source.get("domain")!="FINANCE" or source.get("marked_mention_universe_complete") is not True:
        raise ValueError("SOURCE_SCOPE_INVALID")
    segs=source.get("segments")
    if not isinstance(segs,Sequence) or isinstance(segs,(str,bytes,bytearray)) or not segs or len(segs)>256:
        raise ValueError("SEGMENTS_INVALID")
    parts=[]; mentions=[]; ids=set(); offset=0
    for i,raw in enumerate(segs):
        if not isinstance(raw,Mapping): raise ValueError("SEGMENT_NOT_OBJECT:"+str(i))
        kind=str(raw.get("kind") or "").strip().upper()
        if kind=="TEXT":
            text=raw.get("text")
            if not isinstance(text,str): raise ValueError("TEXT_INVALID")
            hidden=REF_RE.search(text)
            if hidden is not None: raise ValueError("SUPPORTED_REFERENCE_FORM_MUST_BE_MARKED")
            parts.append(text); offset+=len(text); continue
        if kind not in {"MENTION","REFERENCE"}: raise ValueError("SEGMENT_KIND_INVALID")
        mid=str(raw.get("mention_id") or "").strip(); text=raw.get("text")
        if not mid or mid in ids or not isinstance(text,str) or not text:
            raise ValueError("MENTION_BINDING_INVALID")
        ids.add(mid); low=text.strip().casefold()
        if kind=="REFERENCE":
            if low not in REF_FORMS or text.strip()!=text or any(ch.isspace() for ch in text):
                raise ValueError("REFERENCE_FORM_UNSUPPORTED")
            entity="UNKNOWN"; _,num=coref._PRONOUNS[low]; number=num if num!="ANY" else "UNKNOWN"
        else:
            if low in REF_FORMS: raise ValueError("REFERENCE_FORM_MISMARKED_AS_MENTION")
            entity=str(raw.get("entity_class") or "UNKNOWN").upper()
            number=str(raw.get("number") or "UNKNOWN").upper()
            if entity not in {"PERSON","NONPERSON","UNKNOWN"} or number not in {"SINGULAR","PLURAL","UNKNOWN"}:
                raise ValueError("MENTION_FEATURE_INVALID")
        start=offset; end=start+len(text); parts.append(text)
        mentions.append({"mention_id":mid,"text":text,"start":start,"end":end,
                         "entity_class":entity,"number":number,"is_reference":kind=="REFERENCE"})
        offset=end
    plain="".join(parts); starts=[0]
    for m in re.finditer(r"[.!?]\s+",plain): starts.append(m.end())
    for row in mentions:
        row["sentence_index"]=max(i for i,s in enumerate(starts) if s<=row["start"])
    ref=str(source.get("reference_id") or "").strip()
    if len([x for x in mentions if x["mention_id"]==ref and x["is_reference"]])!=1:
        raise ValueError("REFERENCE_ID_INVALID")
    graph=coref.compile_coreference_candidates([coref.Mention(**x) for x in mentions])
    if graph.get("status")!="COMPILED": raise ValueError("GRAPH_NOT_COMPILED")
    if any(isinstance(x,Mapping) and x.get("reference_id")==ref for x in graph.get("unresolved_references",[])):
        raise ValueError("TARGET_REFERENCE_UNRESOLVED")
    cands=sorted({str(x.get("antecedent_id") or "") for x in graph.get("candidate_edges",[])
                  if isinstance(x,Mapping) and x.get("reference_id")==ref})
    if not cands or any(not x for x in cands): raise ValueError("CANDIDATES_REQUIRED")
    return cands

def _projection(result:Mapping[str,Any])->dict[str,Any]:
    status=str(result.get("status") or ""); selected=result.get("selected_alternative")
    if status not in TERMINAL: raise ValueError("TERMINAL_STATUS_INVALID")
    if selected is not None and not isinstance(selected,str): raise ValueError("SELECTED_INVALID")
    if status=="DECIDED" and not selected: raise ValueError("DECIDED_WITHOUT_SELECTION")
    if status!="DECIDED" and selected is not None: raise ValueError("NONDECIDED_WITH_SELECTION")
    return {"schema":TERMINAL_PROJECTION_SCHEMA,"decision_status":status,"selected_alternative":selected}

def verify(source:Mapping[str,Any],observed:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(observed,Mapping) or observed.get("schema")!=OUTPUT_SCHEMA or observed.get("pass") is not True:
            raise ValueError("OUTPUT_INVALID")
        cands=_candidate_ids(source)
        problems=source.get("antecedent_decision_problems"); results=observed.get("typed_decision_results")
        if not isinstance(problems,Mapping) or set(problems)!=set(cands):
            raise ValueError("DECISION_PROBLEM_CANDIDATE_COVERAGE_INCOMPLETE")
        if not isinstance(results,Mapping) or set(results)!=set(cands):
            raise ValueError("DECISION_RESULT_CANDIDATE_COVERAGE_INCOMPLETE")
        terminals={}; derivations={}
        for cid in cands:
            p=problems[cid]; r=results[cid]
            if not isinstance(p,Mapping) or not isinstance(r,Mapping): raise ValueError("DECISION_ROW_INVALID:"+cid)
            ok,reason=decision_verify.verify(dict(p),dict(r))
            if ok is not True: raise ValueError("TYPED_DECISION_VERIFY_FAILED:"+cid+":"+str(reason))
            sig=_projection(r)
            terminals[cid]={"terminal_signature_complete":True,"terminal_signature":sig}
            derivations[cid]={"decision_problem_sha256":_sha(dict(p)),
                              "decision_result_sha256":_sha(dict(r)),
                              "terminal_projection_sha256":_sha(sig),
                              "producer_independent_decision_verification":True}
        if observed.get("antecedent_terminal_signatures")!=terminals:
            raise ValueError("DERIVED_TERMINAL_SIGNATURE_MISMATCH")
        if observed.get("terminal_signature_derivations")!=derivations:
            raise ValueError("DERIVATION_RECEIPT_MISMATCH")
        marked_source=deepcopy(dict(source)); marked_source["schema"]=marked_verify.INPUT_SCHEMA
        marked_source["antecedent_terminal_signatures"]=deepcopy(terminals)
        ambiguity_result=observed.get("ambiguity_result")
        checked=marked_verify.verify(marked_source,ambiguity_result)
        if checked.get("verified") is not True:
            raise ValueError("MARKED_AMBIGUITY_REVERIFY_FAILED:"+str(checked.get("reason") or ""))
        if observed.get("decision")!=(ambiguity_result or {}).get("decision"):
            raise ValueError("DECISION_PROJECTION_MISMATCH")
        if observed.get("candidate_antecedent_ids")!=cands or observed.get("candidate_count")!=len(cands):
            raise ValueError("CANDIDATE_BINDING_MISMATCH")
        if observed.get("model_dependency_count")!=0: raise ValueError("MODEL_DEPENDENCY_NONZERO")
        return {"schema":SCHEMA,"status":"PASS__DERIVED_TERMINAL_SIGNATURES_INDEPENDENTLY_REVERIFIED",
                "pass":True,"verified":True,"producer_independent":True,
                "candidate_count":len(cands),"terminal_signature_candidate_coverage_complete":True,
                "terminal_projection_complete_for_typed_decision_control":True,
                "mention_universe_complete_relative_to_marked_segment_contract":True,
                "open_world_plain_text_mention_completeness_claimed":False,
                "marked_ambiguity_verification":checked,
                "semantic_truth_authority":False,"policy_adequacy_authority":False,
                "terminal_authority":False}
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"verified":False,
                "producer_independent":True,"reason":type(exc).__name__+":"+str(exc),
                "terminal_signature_candidate_coverage_complete":False,
                "open_world_plain_text_mention_completeness_claimed":False,
                "semantic_truth_authority":False,"policy_adequacy_authority":False,
                "terminal_authority":False}
