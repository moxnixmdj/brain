from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.bound_capabilities import terminal_kstar_root_assess as a

def _write(root:Path, rel:str, value):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value)+"\n",encoding="utf-8")

def _gblob(path:Path):
    import hashlib
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _base(root:Path, truth, *, with_p3=False):
    _write(root,a.AUTH,{"live_truth":{"tournament_failure_current_admitted_capability_deficit_count":0}})
    _write(root,a.U,{"single_live_primitive":"P","single_live_question":"Q","current_truth":truth})
    for rel in (a.ARCH,a.BRIDGE):
        _write(root,rel,{})
    p=root/a.REDUCER; p.parent.mkdir(parents=True,exist_ok=True); p.write_text("# reducer\n")
    if with_p3:
        cut={
          "concrete_u_witness":{"behavior_id":"EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"},
          "exact_causal_synthesis_result":{
            "frontier_component_count":8,
            "architectures_evaluated":256,
            "classification":"NEW_PRIMITIVE_REQUIRED"
          },
          "first_principles_collapse":{
            "unified_effect":"P3_SCOPE_COMPLETE_GROUNDED_AUDIENCE_CONDITIONED_POLICY_DOMINANCE",
            "build_target_count":1
          }
        }
        _write(root,a.P3CUT,cut)
        cut_binding={"path":a.P3CUT,"git_blob_sha":_gblob(root/a.P3CUT)}
        _write(root,a.P3VERIFY,{
          "status":"PASS__EXACT_EIGHT_COMPONENT_FRONTIER_EXHAUSTED",
          "subject":{"causal_cut":cut_binding},
          "verification":{
            "pass":True,
            "architectures_evaluated":256,
            "all_subsets_exhausted":True,
            "classification":"NEW_PRIMITIVE_REQUIRED",
            "unified_missing_effect":"P3_SCOPE_COMPLETE_GROUNDED_AUDIENCE_CONDITIONED_POLICY_DOMINANCE"
          }
        })

def test_kstar_assessor_fails_closed_on_missing_scope(tmp_path):
    _base(tmp_path,{
      "complete_declared_discriminator_quotient_scope_proved":False,
      "reachable_target_supported_unsplittable_policy_conflict_empty_proved":False,
      "scope_complete_parameterized_terminal_or_refinement_binding_proved":False})
    r=a.run({},tmp_path)
    assert r["outcome"]=="UNRESOLVED"
    doc=json.loads((tmp_path/a.RESULT).read_text())
    assert doc["u_empty"] is False
    assert len(doc["missing_premises"])==3
    assert r["smallest_verified_constructive_residual"] is None
    assert doc["terminal_credit_claim"] is False

def test_kstar_assessor_refines_generic_open_root_to_verified_p3_residual(tmp_path):
    _base(tmp_path,{
      "complete_declared_discriminator_quotient_scope_proved":False,
      "reachable_target_supported_unsplittable_policy_conflict_empty_proved":False,
      "scope_complete_parameterized_terminal_or_refinement_binding_proved":False},with_p3=True)
    r=a.run({},tmp_path)
    assert r["outcome"]=="UNRESOLVED"
    assert r["smallest_verified_constructive_residual"]=="P3_SCOPE_COMPLETE_GROUNDED_AUDIENCE_CONDITIONED_POLICY_DOMINANCE"
    doc=json.loads((tmp_path/a.RESULT).read_text())
    p3=doc["smallest_constructive_residual_witness"]["current_smallest_verified_constructive_residual"]
    assert p3["architectures_evaluated"]==256
    assert p3["scope_boundary"].startswith("EXACT_OVER_DECLARED_EIGHT_COMPONENT")
    assert doc["terminal_credit_claim"] is False

def test_kstar_assessor_rejects_unverified_or_drifted_p3_refinement(tmp_path):
    _base(tmp_path,{
      "complete_declared_discriminator_quotient_scope_proved":False,
      "reachable_target_supported_unsplittable_policy_conflict_empty_proved":False,
      "scope_complete_parameterized_terminal_or_refinement_binding_proved":False},with_p3=True)
    verify=json.loads((tmp_path/a.P3VERIFY).read_text())
    verify["verification"]["architectures_evaluated"]=255
    _write(tmp_path,a.P3VERIFY,verify)
    r=a.run({},tmp_path)
    assert r["smallest_verified_constructive_residual"] is None

def test_kstar_assessor_never_invents_success_when_one_premise_open(tmp_path):
    _base(tmp_path,{
      "complete_declared_discriminator_quotient_scope_proved":True,
      "reachable_target_supported_unsplittable_policy_conflict_empty_proved":False,
      "scope_complete_parameterized_terminal_or_refinement_binding_proved":True},with_p3=True)
    r=a.run({},tmp_path)
    assert r["outcome"]=="UNRESOLVED"
    assert r["u_empty"] is False
    assert r["smallest_verified_constructive_residual"]=="P3_SCOPE_COMPLETE_GROUNDED_AUDIENCE_CONDITIONED_POLICY_DOMINANCE"

def test_kstar_assessor_emits_candidate_only_when_all_three_are_proved(tmp_path):
    _base(tmp_path,{
      "complete_declared_discriminator_quotient_scope_proved":True,
      "reachable_target_supported_unsplittable_policy_conflict_empty_proved":True,
      "scope_complete_parameterized_terminal_or_refinement_binding_proved":True},with_p3=True)
    r=a.run({},tmp_path)
    doc=json.loads((tmp_path/a.RESULT).read_text())
    assert r["outcome"]=="SCOPE_COMPLETE_PROOF"
    assert doc["u_empty"] is True
    assert doc["terminal_credit_claim"] is False
    assert len(doc["source_bindings"])>=7
