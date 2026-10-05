"""Current 8-target x 14-witness zero-reality totalization.

Binds the existing independently verified 8-target normalization to the exact
current 14/38 proved witness ledger. This layer deliberately assigns zero
semantic, metric, or scope credit. Its purpose is to prove whether direct reuse
from the normalized witness catalog alone closes anything after the two newest
proved witnesses (LiveBench and Unknown-Domain V8) are admitted.

No terminal case, benchmark response, hidden comparator output, or fresh reality
is consumed.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime.brain_witness_normalization_verifier_v3 import evaluate as verify_witnesses

ROOT=Path(__file__).resolve().parents[2]
TARGETS=ROOT/"canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json"
TARGET_VERIFY=ROOT/"canonical/verification/OPUS55_MATCHED_TARGET_NORMALIZATION_V3_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
WITNESSES=ROOT/"canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V3.json"
EVIDENCE=ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
ROOT3=ROOT/"canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V5.json"

SCHEMA="PROJECT_BRAIN_CURRENT_WITNESS_TARGET_TOTALIZATION_V3"

def blob(p:Path)->str:
    b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def fail(*errors:str)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
      "errors":sorted(set(errors)),"acceptance_credit_delta":0,
      "family_credit_delta":0,"capability_credit_delta":0,
      "ownership_credit_delta":0,"new_reality_units_consumed":0,
      "execution_authority":False,"promotion_authority":False,
      "fresh_reality_authority":False}

def totalize(target_doc:Mapping[str,Any], target_verify:Mapping[str,Any],
             witness_doc:Mapping[str,Any], evidence:Mapping[str,Any],
             root3:Mapping[str,Any], *, evidence_blob_sha:str)->dict[str,Any]:
    errors=[]
    if not str(target_verify.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("TARGET_NORMALIZATION_NOT_INDEPENDENT_PASS")
    if target_verify.get("verified",{}).get("current_live_target_set_exact") is not True:
        errors.append("TARGET_SET_NOT_PREVIOUSLY_VERIFIED_EXACT")
    wv=verify_witnesses(evidence,witness_doc,evidence_blob_sha)
    if wv.get("pass") is not True:
        errors.append("CURRENT_WITNESS_NORMALIZATION_INVALID")
    if wv.get("witness_count")!=14:
        errors.append("WITNESS_COUNT_NOT_14")

    targets=target_doc.get("targets",[])
    witnesses=witness_doc.get("witnesses",[])
    if not isinstance(targets,list) or len(targets)!=8: errors.append("TARGET_COUNT_NOT_8")
    if not isinstance(witnesses,list) or len(witnesses)!=14: errors.append("WITNESS_COUNT_NOT_14_DOC")

    current7=set(root3.get("shared_matched_scope_targets",[]))
    current7_ids={x.get("predicate_id") if isinstance(x,Mapping) else x for x in current7}
    # shared_matched_scope_targets in V5 is a list of strings; tolerate rows fail-closed.
    current7_ids={x for x in current7_ids if isinstance(x,str)}
    expected8=set(current7_ids)|{"SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"}
    actual8={x.get("predicate_id") for x in targets if isinstance(x,Mapping)}
    if expected8!=actual8:
        errors.append("CURRENT_MATCHED_TARGET_SET_DRIFT:"+repr(sorted(actual8^expected8)))

    proved={x.get("predicate_id") for x in evidence.get("claims",[])
            if isinstance(x,Mapping) and x.get("state")=="PROVED"}
    overlap=actual8 & proved
    if overlap:
        errors.append("PROVED_TARGET_STILL_IN_LIVE_SET:"+repr(sorted(overlap)))

    atoms=metrics=positive_atoms=positive_metrics=positive_edges=0
    target_rows=[]
    for i,t in enumerate(targets if isinstance(targets,list) else []):
        if not isinstance(t,Mapping): errors.append(f"TARGET_{i}_INVALID"); continue
        ar=t.get("atom_sources",[]); mr=t.get("metric_requirement_sources",[])
        if not isinstance(ar,list) or not isinstance(mr,list):
            errors.append(f"TARGET_{i}_NORMALIZATION_INVALID"); continue
        atoms+=len(ar); metrics+=len(mr)
        target_rows.append(t.get("predicate_id"))

    witness_rows=[]
    for i,w in enumerate(witnesses if isinstance(witnesses,list) else []):
        if not isinstance(w,Mapping): errors.append(f"WITNESS_{i}_INVALID"); continue
        a=w.get("normalized_target_atoms",[])
        m=w.get("normalized_metric_bounds",{})
        e=w.get("semantic_implications",[])
        if not isinstance(a,list): errors.append(f"WITNESS_{i}_ATOMS_INVALID"); a=[]
        if not isinstance(m,Mapping): errors.append(f"WITNESS_{i}_METRICS_INVALID"); m={}
        if not isinstance(e,list): errors.append(f"WITNESS_{i}_EDGES_INVALID"); e=[]
        positive_atoms+=len(a); positive_metrics+=len(m); positive_edges+=len(e)
        witness_rows.append(w.get("witness_id"))
    if positive_atoms: errors.append("POSITIVE_ATOM_BINDING_PRESENT")
    if positive_metrics: errors.append("POSITIVE_METRIC_BINDING_PRESENT")
    if positive_edges: errors.append("POSITIVE_SEMANTIC_EDGE_PRESENT")
    if errors: return fail(*errors)

    pairs=[{"target_predicate_id":t,"witness_id":w,"direct_semantic_binding":False,
            "verified_scope_relation":False,"implies_target":False}
           for t in target_rows for w in witness_rows]
    return {
      "schema":SCHEMA,
      "status":"PASS__CURRENT_8X14_SURFACE_TOTALIZED__ZERO_DIRECT_REUSE_CLOSURES__ZERO_CREDIT",
      "pass":True,"target_count":8,"witness_count":14,"pair_count":len(pairs),
      "target_atom_occurrence_count":atoms,"target_metric_occurrence_count":metrics,
      "positive_atom_binding_count":0,"positive_metric_binding_count":0,
      "positive_semantic_edge_count":0,"closed_target_count":0,"residual_target_count":8,
      "target_results":[{"predicate_id":t,"closed_by_current_normalized_witness_reuse":False,
        "reason":"NO_DECLARED_POSITIVE_SEMANTIC_OR_METRIC_BINDING_AND_NO_VERIFIED_SCOPE_RELATION_IN_CURRENT_14_WITNESS_NORMALIZATION"}
        for t in target_rows],
      "pairs":pairs,
      "logical_consequence":"THE_CURRENT_NORMALIZED_14_WITNESS_CATALOG_ALONE_CLOSES_NONE_OF_THE_8_STILL_OPEN_MATCHED_TARGETS__THIS_DOES_NOT_PROVE_NO_OTHER_SEMANTIC_OR_SCOPE_CERTIFICATE_EXISTS",
      "next":"SEARCH_ONLY_FOR_NEW_CONTENT_ADDRESSED_SEMANTIC_BINDING_OR_EXACT_SUPERSET_SCOPE_CERTIFICATES_TRIGGERED_BY_THE_TWO_NEW_WITNESSES__DO_NOT_REPEAT_OLD_12_WITNESS_SEARCH",
      "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
      "ownership_credit_delta":0,"new_reality_units_consumed":0,
      "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
      "errors":[]
    }

def main()->int:
    td=json.loads(TARGETS.read_text()); tv=json.loads(TARGET_VERIFY.read_text())
    wd=json.loads(WITNESSES.read_text()); ev=json.loads(EVIDENCE.read_text())
    r3=json.loads(ROOT3.read_text())
    out=totalize(td,tv,wd,ev,r3,evidence_blob_sha=blob(EVIDENCE))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("pass") is True else 1

if __name__=="__main__": raise SystemExit(main())
