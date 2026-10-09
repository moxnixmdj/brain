import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
THM=ROOT/"canonical/governance/CODING_ROBUST_FINITE_MULTI_INTERPRETATION_CONSTRUCTIVE_ADEQUACY_THEOREM_20261009_V1.json"

def test_theorem_has_seven_load_bearing_premises_and_no_target_transfer():
    t=json.loads(THM.read_text(encoding="utf-8"))
    atoms=[x["id"] for x in t["condition"]["args"]]
    assert len(atoms)==7 and len(set(atoms))==7
    assert t["adequacy"]["adequate_for_every_member"] is True
    assert t["adequacy"]["constructive_liveness"] is True
    assert t["adequacy"]["robust_to_semantic_ambiguity"] is True
    assert t["adequacy"]["unique_semantic_interpretation_required"] is False
    assert t["boundary"]["interpretation_set_completeness_self_certified"] is False
    assert t["boundary"]["target_membership_self_certified"] is False
    assert t["boundary"]["arbitrary_cursorbench_membership_proved"] is False
    assert t["boundary"]["whole_cursorbench_cover_proved"] is False
    assert t["accounting"]["terminal_credit_delta"]==0

def test_single_interpretation_is_declared_special_case():
    t=json.loads(THM.read_text(encoding="utf-8"))
    assert t["relation_to_existing_regions"]["finite_exact_oracle_region"]=="STRICT_SPECIAL_CASE_AT_INTERPRETATION_COUNT_ONE"
