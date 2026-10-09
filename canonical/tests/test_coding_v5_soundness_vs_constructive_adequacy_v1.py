import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/"canonical/governance/CODING_V5_TERMINAL_SOUNDNESS_VS_CONSTRUCTIVE_ADEQUACY_SEPARATION_20261009_V1.json"

def terminal_sound(submits_bad_candidate: bool) -> bool:
    return not submits_bad_candidate

def positive_adequacy(eventual_success: bool) -> bool:
    return eventual_success

def test_terminal_soundness_does_not_imply_positive_adequacy():
    d=json.loads(DOC.read_text(encoding="utf-8"))
    never_submit_sound=terminal_sound(False)
    never_submit_adequate=positive_adequacy(False)
    assert never_submit_sound is True
    assert never_submit_adequate is False
    assert d["observed_contract_structure"]["constructive_total_solver_bound"] is False
    assert d["observed_contract_structure"]["exhaustive_candidate_search_bound"] is False
    assert d["observed_contract_structure"]["termination_to_solution_theorem_bound"] is False
    assert d["formal_separation"]["proposition"]=="TERMINAL_SOUNDNESS_GATE_DOES_NOT_IMPLY_POSITIVE_ALL_MEMBERS_ADEQUACY"
    assert d["current_route_implication"]["formal_all_members_from_completion_contract_alone"]=="INVALID"
    assert d["current_route_implication"]["one_wal_success_sufficient"] is False
    assert d["accounting"]["acceptance_credit_delta"]==0
    assert d["accounting"]["terminal_credit_delta"]==0

if __name__=="__main__":
    test_terminal_soundness_does_not_imply_positive_adequacy()
    print("PASS 1/1")
