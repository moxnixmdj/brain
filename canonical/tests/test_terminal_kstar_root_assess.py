from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.bound_capabilities import terminal_kstar_root_assess as a

def _write(root:Path, rel:str, value):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value)+"\n",encoding="utf-8")

def _base(root:Path, truth):
    _write(root,a.AUTH,{"live_truth":{"tournament_failure_current_admitted_capability_deficit_count":0}})
    _write(root,a.U,{"single_live_primitive":"P","single_live_question":"Q","current_truth":truth})
    for rel in (a.ARCH,a.BRIDGE):
        _write(root,rel,{})
    p=root/a.REDUCER; p.parent.mkdir(parents=True,exist_ok=True); p.write_text("# reducer\n")

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
    assert doc["terminal_credit_claim"] is False

def test_kstar_assessor_never_invents_success_when_one_premise_open(tmp_path):
    _base(tmp_path,{
      "complete_declared_discriminator_quotient_scope_proved":True,
      "reachable_target_supported_unsplittable_policy_conflict_empty_proved":False,
      "scope_complete_parameterized_terminal_or_refinement_binding_proved":True})
    r=a.run({},tmp_path)
    assert r["outcome"]=="UNRESOLVED"
    assert r["u_empty"] is False

def test_kstar_assessor_emits_candidate_only_when_all_three_are_proved(tmp_path):
    _base(tmp_path,{
      "complete_declared_discriminator_quotient_scope_proved":True,
      "reachable_target_supported_unsplittable_policy_conflict_empty_proved":True,
      "scope_complete_parameterized_terminal_or_refinement_binding_proved":True})
    r=a.run({},tmp_path)
    doc=json.loads((tmp_path/a.RESULT).read_text())
    assert r["outcome"]=="SCOPE_COMPLETE_PROOF"
    assert doc["u_empty"] is True
    assert doc["terminal_credit_claim"] is False
    assert len(doc["source_bindings"])>=5
