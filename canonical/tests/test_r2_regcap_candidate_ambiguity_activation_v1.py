import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def test_regcap_candidate_ambiguity_activation_truth():
    a=json.loads((ROOT/"canonical/governance/R2_REGCAP_CANDIDATE_AMBIGUITY_CONTROL_ACTIVATION_20261009_V1.json").read_text())
    v=json.loads((ROOT/"canonical/verification/R2_REGCAP_CANDIDATE_AMBIGUITY_CONTROL_VERIFY_20261009_V1.json").read_text())
    assert a["verification"]["status"]==v["status"]
    assert a["new_closed_subproblem"]["new_state"].startswith("CLOSED_FOR_VERIFIED_BOUNDED")
    assert a["r2_truth_delta"]["primary_internal_unsolved_count_delta"]==0
    assert a["r2_truth_delta"]["primary_internal_unsolved_cell_remains"]=="FINANCE_SEMANTIC_ADEQUACY_TAIL"
    assert a["strict_externality"]["missing_context_or_observation_is_external_impossibility"] is False
    assert a["strict_externality"]["pending_clarification_or_acquisition_classification"]=="INTERNAL_UNSOLVED"
    assert a["semantic_truth_authority"] is False
    assert a["policy_adequacy_authority"] is False
    assert a["terminal_authority"] is False
    assert a["accounting"]["terminal_credit_delta"]==0
