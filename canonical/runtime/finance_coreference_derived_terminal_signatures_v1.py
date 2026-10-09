"""Derive Finance coreference terminal signatures from typed decision problems.

Bounded scope only: the mention universe is complete relative to the marked
segment contract. Candidate terminal signatures are not caller assertions;
they are derived by Brain-owned typed decision synthesis and independently
checked before entering the existing ambiguity controller.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import finance_marked_mention_universe_v1 as marked
from canonical.runtime import finance_coreference_ambiguity_control_v1 as ambiguity
from canonical.runtime import source_grounded_coreference as coref
from canonical.runtime.bound_capabilities import evidence_decision_synthesis as decision
from canonical.runtime.bound_capabilities import evidence_decision_verify as decision_verify

SCHEMA="PROJECT_BRAIN_FINANCE_DERIVED_TERMINAL_SIGNATURES_V1"
INPUT_SCHEMA="PROJECT_BRAIN_FINANCE_MARKED_COREFERENCE_TYPED_DECISION_SOURCE_V1"
TERMINAL_PROJECTION_SCHEMA="PROJECT_BRAIN_TYPED_DECISION_TERMINAL_PROJECTION_V1"

class DerivedTerminalSignatureError(ValueError): pass

def _canon(x:Any)->bytes:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def _sha(x:Any)->str: return sha256(_canon(x)).hexdigest()

def _mentions(source:Mapping[str,Any]):
    if not isinstance(source,Mapping) or source.get("schema")!=INPUT_SCHEMA:
        raise DerivedTerminalSignatureError("SOURCE_SCHEMA_INVALID")
    if source.get("domain")!="FINANCE":
        raise DerivedTerminalSignatureError("FINANCE_DOMAIN_MARKER_REQUIRED")
    if not str(source.get("source_id") or "").strip():
        raise DerivedTerminalSignatureError("SOURCE_ID_REQUIRED")
    if source.get("marked_mention_universe_complete") is not True:
        raise DerivedTerminalSignatureError("MARKED_MENTION_UNIVERSE_COMPLETENESS_REQUIRED")
    plain,rows=marked._compile_segments(source)
    ref=str(source.get("reference_id") or "").strip()
    if len([x for x in rows if x["mention_id"]==ref and x["is_reference"] is True])!=1:
        raise DerivedTerminalSignatureError("REFERENCE_ID_NOT_EXACT_MARKED_REFERENCE")
    graph=coref.compile_coreference_candidates([coref.Mention(**x) for x in rows])
    if graph.get("status")!="COMPILED":
        raise DerivedTerminalSignatureError("COREFERENCE_GRAPH_NOT_COMPILED")
    if any(isinstance(x,Mapping) and x.get("reference_id")==ref for x in graph.get("unresolved_references",[])):
        raise DerivedTerminalSignatureError("TARGET_REFERENCE_HAS_NO_BOUNDED_CANDIDATE_SET")
    cands=sorted({str(x.get("antecedent_id") or "") for x in graph.get("candidate_edges",[])
                  if isinstance(x,Mapping) and x.get("reference_id")==ref})
    if not cands or any(not x for x in cands):
        raise DerivedTerminalSignatureError("TARGET_REFERENCE_CANDIDATES_REQUIRED")
    return plain,rows,cands

def _projection(result:Mapping[str,Any])->dict[str,Any]:
    status=str(result.get("status") or "")
    selected=result.get("selected_alternative")
    if status not in decision.TERMINAL:
        raise DerivedTerminalSignatureError("TYPED_DECISION_TERMINAL_STATUS_INVALID")
    if selected is not None and not isinstance(selected,str):
        raise DerivedTerminalSignatureError("TYPED_DECISION_SELECTED_ALTERNATIVE_INVALID")
    if status=="DECIDED" and not selected:
        raise DerivedTerminalSignatureError("DECIDED_RESULT_REQUIRES_SELECTED_ALTERNATIVE")
    if status!="DECIDED" and selected is not None:
        raise DerivedTerminalSignatureError("NONDECIDED_RESULT_FORBIDS_SELECTED_ALTERNATIVE")
    return {"schema":TERMINAL_PROJECTION_SCHEMA,
            "decision_status":status,"selected_alternative":selected}

def compute(source:Mapping[str,Any])->dict[str,Any]:
    plain,mentions,cands=_mentions(source)
    problems=source.get("antecedent_decision_problems")
    if not isinstance(problems,Mapping) or set(problems)!=set(cands):
        raise DerivedTerminalSignatureError("DECISION_PROBLEM_CANDIDATE_COVERAGE_INCOMPLETE")
    results={}; terminals={}; derivations={}
    for cid in cands:
        problem=problems[cid]
        if not isinstance(problem,Mapping):
            raise DerivedTerminalSignatureError("DECISION_PROBLEM_NOT_OBJECT:"+cid)
        p=deepcopy(dict(problem))
        result=decision.synthesize(p)
        ok,reason=decision_verify.verify(p,result)
        if ok is not True:
            raise DerivedTerminalSignatureError("TYPED_DECISION_INDEPENDENT_VERIFICATION_FAILED:"+cid+":"+str(reason))
        if result.get("model_dependency_count")!=0:
            raise DerivedTerminalSignatureError("TYPED_DECISION_MODEL_DEPENDENCY_NONZERO:"+cid)
        sig=_projection(result)
        results[cid]=deepcopy(dict(result))
        terminals[cid]={"terminal_signature_complete":True,"terminal_signature":sig}
        derivations[cid]={
            "decision_problem_sha256":_sha(p),
            "decision_result_sha256":_sha(result),
            "terminal_projection_sha256":_sha(sig),
            "producer_independent_decision_verification":True,
        }
    observations=source.get("observations",[])
    if not isinstance(observations,Sequence) or isinstance(observations,(str,bytes,bytearray)):
        raise DerivedTerminalSignatureError("OBSERVATIONS_INVALID")
    case={
        "schema":ambiguity.INPUT_SCHEMA,"domain":"FINANCE",
        "source_id":str(source["source_id"]).strip(),"source_text":plain,
        "mention_universe_complete":True,"mentions":deepcopy(mentions),
        "reference_id":str(source["reference_id"]).strip(),
        "antecedent_terminal_signatures":deepcopy(terminals),
        "observations":deepcopy(list(observations)),
        "ambiguity_owner":str(source.get("ambiguity_owner") or "").strip().upper(),
    }
    amb=ambiguity.compute(case)
    return {
        "schema":SCHEMA,
        "status":"PASS__TERMINAL_SIGNATURES_DERIVED_FROM_INDEPENDENTLY_VERIFIED_TYPED_DECISIONS",
        "pass":True,"source_id":case["source_id"],
        "source_text_sha256":sha256(plain.encode()).hexdigest(),
        "reference_id":case["reference_id"],
        "candidate_antecedent_ids":cands,"candidate_count":len(cands),
        "typed_decision_results":results,
        "antecedent_terminal_signatures":terminals,
        "terminal_signature_derivations":derivations,
        "ambiguity_result":amb,"decision":deepcopy(dict(amb.get("decision") or {})),
        "mention_universe_complete_relative_to_marked_segment_contract":True,
        "terminal_signature_candidate_coverage_complete":True,
        "terminal_projection_complete_for_typed_decision_control":True,
        "open_world_plain_text_mention_completeness_claimed":False,
        "antecedent_identity_asserted":False,"semantic_truth_authority":False,
        "policy_adequacy_authority":False,"model_dependency_count":0,
        "terminal_authority":False,
    }

def run(args:Mapping[str,Any])->dict[str,Any]:
    try: return compute(args)
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "reason":type(exc).__name__+":"+str(exc),
                "terminal_signature_candidate_coverage_complete":False,
                "open_world_plain_text_mention_completeness_claimed":False,
                "antecedent_identity_asserted":False,"semantic_truth_authority":False,
                "policy_adequacy_authority":False,"terminal_authority":False}
