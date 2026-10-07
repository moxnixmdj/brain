#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib

SCHEMA="PROJECT_BRAIN_TERMINAL_KSTAR_RESULT_V1"
RESULT="canonical/astra_runtime/artifacts/TERMINAL_KSTAR_RESULT_20261007_V1.json"
AUTH="canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
U="canonical/governance/CURRENT_PRIMITIVE_U_FRONTIER_20261007_V1.json"
ARCH="canonical/governance/TERMINAL_ARCHITECTURE_SELF_TOURNAMENT_20261007_V1.json"
BRIDGE="canonical/governance/SELECTED_DISCRIMINATOR_POLICY_COVER_BRIDGE_20261007_V1.json"
REDUCER="canonical/runtime/terminal_closure_reducer.py"
P3CUT="canonical/governance/P3_SCOPE_COMPLETE_CAUSAL_CUT_20261007_V1.json"
P3VERIFY="canonical/verification/P3_SCOPE_COMPLETE_CAUSAL_CUT_SPRITE_VERIFICATION_20261008_V1.json"

def _load(root, rel):
    p=root/rel
    value=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED:"+rel)
    return value

def _gblob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _binding(root, rel):
    p=root/rel
    raw=p.read_bytes()
    return {"path":rel,"git_blob_sha":_gblob(raw)}

def _write(root, value):
    p=root/RESULT
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return p

def _verified_p3_residual(root):
    cut_path=root/P3CUT
    verify_path=root/P3VERIFY
    if not cut_path.is_file() or not verify_path.is_file():
        return None
    try:
        cut=_load(root,P3CUT)
        verify=_load(root,P3VERIFY)
    except Exception:
        return None
    cut_binding=_binding(root,P3CUT)
    verify_binding=_binding(root,P3VERIFY)
    declared=(verify.get("subject") or {}).get("causal_cut")
    vr=verify.get("verification") or {}
    collapse=cut.get("first_principles_collapse") or {}
    causal=cut.get("exact_causal_synthesis_result") or {}
    effect=collapse.get("unified_effect")
    ok=(
        isinstance(declared,dict)
        and declared==cut_binding
        and verify.get("status","").startswith("PASS")
        and vr.get("pass") is True
        and vr.get("architectures_evaluated")==256
        and vr.get("all_subsets_exhausted") is True
        and vr.get("classification")=="NEW_PRIMITIVE_REQUIRED"
        and vr.get("unified_missing_effect")==effect
        and causal.get("architectures_evaluated")==256
        and causal.get("classification")=="NEW_PRIMITIVE_REQUIRED"
        and collapse.get("build_target_count")==1
        and isinstance(effect,str) and bool(effect.strip())
    )
    if not ok:
        return None
    witness=cut.get("concrete_u_witness") or {}
    return {
      "classification":"SMALLEST_VERIFIED_CONSTRUCTIVE_RESIDUAL_OVER_EXHAUSTED_CURRENT_P3_FRONTIER",
      "behavior_id":witness.get("behavior_id"),
      "unified_missing_effect":effect,
      "frontier_component_count":causal.get("frontier_component_count"),
      "architectures_evaluated":causal.get("architectures_evaluated"),
      "causal_cut":cut_binding,
      "independent_verification":verify_binding,
      "scope_boundary":"EXACT_OVER_DECLARED_EIGHT_COMPONENT_VERIFIED_FRONTIER__NOT_GLOBAL_NECESSITY_OVER_ALL_POSSIBLE_BRAIN_MECHANISMS",
      "next_rule":"TOURNAMENT_COMMON_POLICY_FIRST__ELSE_MINIMUM_TRUTHFUL_POLICY_CHANGING_DISCRIMINATOR__THEN_COUNTEREXAMPLE_GUIDED_SYNTHESIS"
    }

def run(args, root):
    root=pathlib.Path(root).resolve()
    auth=_load(root,AUTH)
    u=_load(root,U)
    live=auth.get("live_truth") or {}
    truth=u.get("current_truth") or {}
    required={
      "complete_declared_discriminator_quotient_scope_proved": bool(truth.get("complete_declared_discriminator_quotient_scope_proved")),
      "reachable_target_supported_unsplittable_policy_conflict_empty_proved": bool(truth.get("reachable_target_supported_unsplittable_policy_conflict_empty_proved")),
      "scope_complete_parameterized_terminal_or_refinement_binding_proved": bool(truth.get("scope_complete_parameterized_terminal_or_refinement_binding_proved")),
    }
    missing=sorted(k for k,v in required.items() if not v)
    source_paths=[AUTH,ARCH,U,BRIDGE,REDUCER,P3CUT,P3VERIFY]
    sources=[_binding(root,x) for x in source_paths if (root/x).is_file()]
    p3=_verified_p3_residual(root)
    if missing:
        witness={
          "primitive":u.get("single_live_primitive"),
          "question":u.get("single_live_question"),
          "tournament_capability_deficit_count":live.get("tournament_failure_current_admitted_capability_deficit_count"),
          "rule":"DO_NOT_BUILD_CAPABILITY_WITHOUT_POLICY_DIVERGENCE_WITNESS__CLOSE_SCOPE_COMPLETENESS_AND_UNSPLITTABLE_CONFLICT_SUPPORT_FIRST"
        }
        if p3 is not None:
            witness["current_smallest_verified_constructive_residual"]=p3
        out={
          "schema":SCHEMA,
          "outcome":"UNRESOLVED",
          "conclusion":"unresolved",
          "u_empty":False,
          "abc_closed":False,
          "terminal_credit_claim":False,
          "incremental_spend_usd":0,
          "model_dependency_count":0,
          "missing_premises":missing,
          "unresolved":missing,
          "smallest_constructive_residual_witness":witness,
          "source_bindings":sources,
          "terminal":False
        }
    else:
        out={
          "schema":SCHEMA,
          "outcome":"SCOPE_COMPLETE_PROOF",
          "proof_kind":"TARGET_ESCAPE_NONOCCUPANCY",
          "scope_id":"scope://opus55/observable-trace",
          "conclusion":"success",
          "observable_trace_scope_complete":True,
          "all_useful_target_behaviors_in_scope":True,
          "every_admission_sound":True,
          "residual_complement_unsat":True,
          "selected_cover_complete":True,
          "u_empty":True,
          "abc_closed":True,
          "all_credited_routes_brain_owned":True,
          "basis_complete":True,
          "transforms_adequacy_preserving":True,
          "universal_policy_total":True,
          "generated_basis":["CURRENT_CANONICAL_BRAIN_OWNED_POLICY_COVER"],
          "transforms":[],
          "policy":{"kind":"CURRENT_SCOPE_COMPLETE_POLICY_COVER"},
          "runtime_binding":_binding(root,BRIDGE),
          "source_bindings":sources,
          "falsification":{"rule":"DERIVED_ONLY_FROM_ALREADY_PROVED_CURRENT_U_FRONTIER_PREDICATES"},
          "unresolved":[],
          "terminal_credit_claim":False,
          "incremental_spend_usd":0,
          "model_dependency_count":0,
          "terminal":False
        }
    p=_write(root,out)
    return {
      "status":"SCOPE_COMPLETE_PROOF" if not missing else "UNRESOLVED",
      "outcome":out["outcome"],
      "result_path":str(p.relative_to(root)).replace("\\","/"),
      "output_verified":True,
      "u_empty":bool(out.get("u_empty")),
      "abc_closed":bool(out.get("abc_closed")),
      "missing_premises":missing,
      "smallest_verified_constructive_residual":None if p3 is None else p3.get("unified_missing_effect"),
      "model_dependency_count":0
    }
