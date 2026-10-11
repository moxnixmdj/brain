from pathlib import Path
import hashlib
import json

R=Path(__file__).resolve().parents[2]
def J(p): return json.loads((R/p).read_text())
def G(p):
    raw=(R/p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\\0"+raw).hexdigest()

p=J("canonical/CANONICAL_POINTER.json")
b=p["boot_requirements"]
assert "canonical/laws/CAPABILITY_TRANSFER_VS_COGNITION_OUTSOURCING_LAW_V1.md" in p["mandatory_laws"]
assert b["capability_transfer_vs_cognition_outsourcing_law_required"] is True
assert b["capability_transfer_ownership_gate_required"] is True
assert b["teacher_or_donor_runtime_cognition_forbidden"] is True
assert b["copied_or_rehosted_teacher_is_not_transfer"] is True
assert b["post_donor_removal_heldout_qualification_required"] is True
assert b["donor_provenance_must_persist_across_verified_episodes"] is True
assert b["donor_derived_skill_candidate_requires_exact_candidate_bound_transfer_record"] is True
assert b["donor_derived_skill_verifier_must_not_run_before_transfer_gate_pass"] is True
assert b["transfer_gate_pass_never_grants_reuse_by_itself"] is True
assert b["donor_derived_skill_requires_independent_skill_verification_after_transfer_gate"] is True
assert b["temporal_provenance_laundering_forbidden"] is True
assert b["external_contribution_three_way_classification_required"] is True
assert b["external_knowledge_must_be_non_authoritative_observation_or_evidence"] is True
assert b["external_knowledge_target_solving_policy_or_answer_forbidden"] is True
assert b["acquisition_donor_must_remain_transfer_gated_until_donor_deletion"] is True
assert b["runtime_cognition_provider_forbidden_regardless_of_label_hosting_or_cost"] is True
assert b["ambiguous_external_contribution_classification_fails_closed"] is True
s=J("canonical/governance/WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA_V3.json")
assert s["promotion_requires_transfer_gate_pass"] is True
d=J("canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V2.json")
assert d["fail_closed"] is True
promotion=(R/"canonical/runtime/ownership_promotion_compiler_v1.py").read_text(encoding="utf-8")
assert "ownership_promotion_cognition_provenance_gate_v1" in promotion
assert "cognition_provenance_gate.evaluate(s)" in promotion
assert "FAIL_CLOSED_K1_K2_K3_COGNITION_PROVENANCE" in promotion
cleanroom=(R/"canonical/runtime/final_terminal_cleanroom_gate_v1.py").read_text(encoding="utf-8")
assert "RUNTIME_COGNITION_NOT_MODEL_INDEPENDENT" in cleanroom
assert "EXTERNAL_MODEL_RUNTIME_DEPENDENCY_COUNT_NOT_ZERO" in cleanroom
assert "COPIED_OR_REHOSTED_TEACHER_NOT_EXPLICITLY_FALSE" in cleanroom
assert "OPERATIVE_SOLVER_ROLE_NOT_BRAIN_OWNED" in cleanroom
global_ownership=(R/"canonical/runtime/terminal_global_ownership_postconditions_reducer_v1.py").read_text(encoding="utf-8")
assert "DONOR_CLEANROOM_PROTOCOL_V2_NOT_BOUND" in global_ownership
assert "DONOR_CLEANROOM_RUNTIME_COGNITION_NOT_MODEL_INDEPENDENT" in global_ownership
assert "DONOR_CLEANROOM_EXTERNAL_MODEL_RUNTIME_DEPENDENCY_COUNT_NOT_ZERO" in global_ownership
assert "DONOR_CLEANROOM_COPIED_OR_REHOSTED_TEACHER_NOT_EXPLICITLY_FALSE" in global_ownership
kstar=(R/"canonical/runtime/terminal_kstar_promotion_bridge_v1.py").read_text(encoding="utf-8")
assert "GLOBAL_OWNERSHIP_RECEIPT_REDUCER_BLOB_STALE" in kstar
assert "GLOBAL_OWNERSHIP_ZERO_MODEL_PREDICATE_NOT_TRUE" in kstar
assert "zero_external_model_runtime_cognition_dependencies" in kstar

manifest=J("canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json")
mtp=manifest.get("terminal_predicates") or {}
mgp=manifest.get("global_ownership_postconditions") or {}
mdc=manifest.get("donor_deletion_cleanroom") or {}
if mtp.get("final_donor_deletion_cleanroom_pass") is True:
    evidence=mgp.get("evidence")
    evidence_blob=mgp.get("evidence_blob_sha")
    assert isinstance(evidence,str) and evidence
    assert evidence_blob==G(evidence)
    receipt=J(evidence)
    reducer_path="canonical/runtime/terminal_global_ownership_postconditions_reducer_v1.py"
    assert receipt.get("brain_reducer_blob_sha")==G(reducer_path)
    result=receipt.get("result") or {}
    predicates=result.get("terminal_predicates") or {}
    for name in (
        "final_donor_deletion_cleanroom_pass",
        "donor_deletion_protocol_v2_bound",
        "runtime_cognition_model_independent",
        "zero_external_model_runtime_cognition_dependencies",
        "copied_or_rehosted_teacher_absent",
        "runtime_dependency_inventory_complete",
    ):
        assert predicates.get(name) is True
else:
    assert mgp.get("current_authority") is False
    assert mgp.get("requalification_required") is True
    assert mdc.get("current_authority") is False
    assert mdc.get("requalification_required") is True
    assert mdc.get("required_protocol")=="canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V2.json"
    invalidation=mgp.get("invalidation")
    assert isinstance(invalidation,str) and (R/invalidation).is_file()
    assert mdc.get("invalidation")==invalidation

terminal_reducer=(R/"canonical/runtime/terminal_closure_reducer.py").read_text(encoding="utf-8")
assert "GLOBAL_OWNERSHIP_RECEIPT_REDUCER_BLOB_STALE" in terminal_reducer
assert "DONOR_AUTHORITY_REPOSITORY_ROOT_REQUIRED" in terminal_reducer
assert "GLOBAL_OWNERSHIP_ZERO_MODEL_PREDICATE_NOT_TRUE" in terminal_reducer

legacy=J("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
if (legacy.get("truth") or {}).get("donor_cleanroom")=="INDEPENDENT_PASS":
    assert mtp.get("final_donor_deletion_cleanroom_pass") is True
print("CAPABILITY_TRANSFER_STATIC_GOVERNANCE_PASS")
