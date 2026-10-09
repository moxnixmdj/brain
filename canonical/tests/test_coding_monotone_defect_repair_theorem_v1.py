import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
THM=ROOT/"canonical/governance/CODING_MONOTONE_DEFECT_REPAIR_CONSTRUCTIVE_ADEQUACY_THEOREM_20261009_V1.json"

def test_theorem_has_six_load_bearing_premises_and_ranking_proof():
    t=json.loads(THM.read_text(encoding="utf-8"))
    atoms=[x["id"] for x in t["condition"]["args"]]
    assert len(atoms)==6 and len(set(atoms))==6
    assert t["adequacy"]["constructive_liveness"] is True
    assert t["adequacy"]["adaptive_candidate_generation"] is True
    assert t["adequacy"]["predeclared_finite_candidate_set_required"] is False
    assert t["proof"]["ranking_function"]=="R_C_EQUALS_CARDINALITY_OF_THE_TRUE_DEFECT_SET_OF_C"
    assert t["boundary"]["target_membership_self_certified"] is False
    assert t["boundary"]["whole_cursorbench_cover_proved"] is False
    assert t["accounting"]["terminal_credit_delta"]==0
