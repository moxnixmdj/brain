import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
T=ROOT/"canonical/governance/CURSORBENCH_TYPED_SPECIALIST_TARGET_MEMBERSHIP_TRANSFER_FALSIFICATION_20261009_V1.json"

SOURCES={
 "owner_access_boundary":("canonical/governance/CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json","d58c41a8e93fc95df6667e955e291b3f36c8942f"),
 "public_contract_hidden_scope_falsification":("canonical/governance/PRIVATE_CODING_PUBLIC_CONTRACT_HIDDEN_SCOPE_UPPER_BOUND_FALSIFICATION_20261008_V1.json","3b56bc5bfb6457659c9a238e9669bcd8ba866585"),
 "observable_scope_receipt":("canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V1.json","7401589da3b30954104145dc4959e534ab8cd641"),
 "real_spent_typed_acceptance_witness":("canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_REAL_EVIDENCE_SPENT_CONTEXT_RECONCILIATION_20261009_V1.json","06c6df3be8b065b106038da32de4e268be9a7521"),
 "route_b_policy_coalescence":("canonical/governance/CURSORBENCH_ROUTE_B_POLICY_COALESCENCE_DISJUNCTION_TRUTH_REPAIR_20261009_V1.json","2342783490431bc36ba98d81606326192ad2fa69"),
}

def blob(path):
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode()+b"\0"+data)
    return h.hexdigest()

def load(rel):
    return json.loads((ROOT/rel).read_text())

def test_exact_sources_and_current_truth_are_bound():
    t=json.loads(T.read_text())
    for key,(rel,sha) in SOURCES.items():
        assert blob(ROOT/rel)==sha
        assert t["exact_sources"][key]["path"]==rel
        assert t["exact_sources"][key]["git_blob_sha"]==sha

    owner=load(SOURCES["owner_access_boundary"][0])
    assert "PRIVATE_AND_HELDOUT_TASKS_STAY_PRIVATE" in owner["owner_facts"]
    assert "NO_PUBLIC_SUBMISSION_INTERFACE_API_CONTAINER_CLI_OR_SIMILAR_FOR_THIRD_PARTY_SYSTEMS" in owner["owner_facts"]

    witness=load(SOURCES["real_spent_typed_acceptance_witness"][0])
    d=witness["deduction"]
    assert d["typed_acceptance_atom_mechanisms_have_real_non_synthetic_same_model_witness"] is True
    assert d["hidden_cursorbench_task_membership_proved"] is False
    assert d["transfer_from_this_terminal_bench_context_to_all_cursorbench_v5_contexts_proved"] is False

    scope=load(SOURCES["observable_scope_receipt"][0])
    assert scope["scope_complete"] is True
    assert scope["positive_adequacy_cover_closed"] is False

def test_public_plus_spent_witness_does_not_entail_target_membership_or_universal_transfer():
    t=json.loads(T.read_text())
    f=t["formal_nonentailment"]
    e=f["countermodel_existential"]
    assert e["P"] is True and e["W"] is True and e["E"] is False

    u=f["countermodel_universal_transfer"]
    assert u["P"] is True and u["W"] is True and u["A"] is False
    m0,m1=u["witness_world_pair"]
    assert m0["public_owner_facts_identical"] is True
    assert m1["public_owner_facts_identical"] is True
    assert m0["hidden_context_atoms"]["SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1"] is True
    assert m1["hidden_context_atoms"]["SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1"] is False
    for atom in t["five_atom_region"]:
        if atom=="SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1":
            continue
        assert m0["hidden_context_atoms"][atom] == m1["hidden_context_atoms"][atom] == True

def test_scheduler_deletes_only_the_unsound_transfer_shortcut():
    t=json.loads(T.read_text())
    r=t["route_effect"]
    assert r["generic_public_metadata_transfer_route"]=="FALSIFIED"
    assert r["actual_private_context_membership_route"].startswith("EVENT_DRIVEN_ONLY")
    assert r["scope_completeness_status"].startswith("PRESERVED_CLOSED")
    assert r["positive_adequacy_cover_status"]=="OPEN"
    assert r["active_internal_successor"]=="CODING_SPEC_SCOPE_COMPLETE_AUTHENTICATED_POLICY_ADEQUACY_COVER"
    assert t["accounting"]["terminal_credit_delta"]==0
    assert t["promotion_authority"] is False
    assert t["terminal_authority"] is False
