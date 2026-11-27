from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
FILES={
"sep":("canonical/governance/TARGET_BEHAVIOR_MECHANISM_SCOPE_SEPARATION_20261005_V1.json","251cac9c9f7892e26ca90f2f5118f31e1df02099"),
"collision":("canonical/governance/SYNTHESIS_LEAF_SCOPE_CONCURRENCY_CONFLICT_RECONCILIATION_20261005_V1.json","4b1b9c7149eb040447b8dd1665366eccfbca60f4"),
"cert":("canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json","dea9028f92f111ee3c8be71615fa4b02e8a8bfb6"),
"protocols":("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json","62394e5b7d221ec9f69c3458f669e40e253a9d09"),
"frontier":("canonical/governance/SIX_BENCHMARK_PROXY_SCOPE_REPAIR_FRONTIER_V3.json","2442af340f6445c1c8fbba7d770461a4e20a0378"),
}
FANOUT={"PROFESSIONAL_KNOWLEDGE_WORK","MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING","AGENTIC_SCIENTIFIC_RESEARCH"}
DIMS={
"claim-to-source fidelity","required evidence coverage","uncertainty/disagreement preservation",
"audience adaptation","format/style constraints","compression without decision-relevant loss"
}

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(root=ROOT):
    docs={}; errors=[]
    for key,(path,expected) in FILES.items():
        data=(root/path).read_bytes()
        got=blob(data)
        if got!=expected: errors.append(f"BLOB_DRIFT:{key}:{got}:{expected}")
        docs[key]=json.loads(data)
    return docs,errors

def evaluate(docs):
    errors=[]
    sep=docs["sep"]; cert=docs["cert"]; protocols=docs["protocols"]; frontier=docs["frontier"]; collision=docs["collision"]

    edges=[e for e in sep["current_frontier_audit"]["edges"] if e.get("behavior_id")=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"]
    if {e["family"] for e in edges}!=FANOUT: errors.append("SYNTHESIS_FANOUT_TARGET_AUDIT_SET_CHANGED")
    if any(e.get("mandatory_from_registry_incidence") is not False for e in edges): errors.append("SYNTHESIS_EDGE_BECAME_MANDATORY_WITHOUT_RECOMPUTE")
    if any(e.get("classification") not in {"TARGET_ENTAILMENT_NOT_PROVED_FOR_WHOLE_FAMILY","ADJACENT_NOT_ENTAILED","TARGET_ENTAILMENT_NOT_PROVED_FOR_CURRENT_FROZEN_SENTENCE"} for e in edges):
        errors.append("SYNTHESIS_EDGE_CLASSIFICATION_CHANGED")

    p=next((x for x in protocols["protocols"] if x.get("family")=="COMMUNICATION_AND_SYNTHESIS"),None)
    if not p: errors.append("COMMUNICATION_PROTOCOL_MISSING")
    else:
        if set(p.get("task_dimensions",[]))!=DIMS: errors.append("COMMUNICATION_TARGET_DIMENSIONS_CHANGED")
        if p.get("proof_mode")!="MATCHED_GROUNDED_SYNTHESIS_NONINFERIORITY": errors.append("COMMUNICATION_PROOF_MODE_CHANGED")

    if cert.get("target_scope_id")!="scope://opus55/SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR": errors.append("CERT_TARGET_CHANGED")
    if cert.get("coverage_complete") is not True or cert.get("coverage_relation")!="EXACT_UNION" or cert.get("scope_relation")!="PROVEN_STRONGER":
        errors.append("CERT_SCOPE_NOT_COMPLETE_STRONGER_EXACT_UNION")
    children=cert.get("children",[])
    if len(children)!=6: errors.append("CERT_DIMENSION_COUNT_CHANGED")
    if any(c.get("formal_completeness") is not True or c.get("all_admissible_target_inputs_proved") is not True for c in children):
        errors.append("CERT_CHILD_NOT_FORMALLY_COMPLETE_FOR_TARGET_INPUTS")

    roots=frontier.get("active_registry_scope_repair_roots",[])
    syn=[x for x in roots if x.get("id")=="SYNTHESIS_TYPED_INPUT_DOMAIN_SCOPE_COMPLETENESS"]
    if len(syn)!=1: errors.append("SYNTHESIS_WHOLE_LEAF_ROOT_NOT_EXACTLY_ONE")
    elif set(syn[0].get("fanout",[]))!=FANOUT: errors.append("SYNTHESIS_WHOLE_LEAF_ROOT_FANOUT_CHANGED")

    if collision.get("fail_closed_truth",{}).get("whole_behavior_leaf_input_domain_scope_complete") is not False:
        errors.append("COLLISION_NO_LONGER_FAILS_CLOSED_ON_WHOLE_LEAF")
    if collision.get("fail_closed_truth",{}).get("predicate_level_root3_scope_relation_closed") is not True:
        errors.append("PREDICATE_SCOPE_NO_LONGER_CLOSED")

    remaining=[x["id"] for x in roots if x.get("id")!="SYNTHESIS_TYPED_INPUT_DOMAIN_SCOPE_COMPLETENESS"]
    expected=[
      "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
      "CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001",
      "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001",
      "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
      "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
    ]
    if remaining!=expected: errors.append("REMAINING_SCOPE_ROOTS_CHANGED")

    return {
      "schema":"PROJECT_BRAIN_SYNTHESIS_WHOLE_LEAF_TARGET_OBLIGATION_CUT_DERIVATION_V1",
      "valid":not errors,
      "errors":errors,
      "whole_leaf_scope_complete":False,
      "whole_leaf_current_terminal_obligation":False if not errors else None,
      "predicate_target_scope_closed":True if not errors else None,
      "matched_performance_open":True,
      "scope_root_count_before":len(roots),
      "scope_root_count_after":len(remaining) if not errors else None,
      "remaining_scope_roots":remaining if not errors else None,
      "credit_delta":0,
    }

def derive(root=ROOT):
    docs,blob_errors=load(root)
    out=evaluate(docs)
    out["errors"]=blob_errors+out["errors"]
    out["valid"]=not out["errors"]
    out["exact_blob_binding"]=not blob_errors
    return out

if __name__=="__main__":
    print(json.dumps(derive(),indent=2,sort_keys=True))
