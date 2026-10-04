import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "canonical/governance/ROOT1_SUBSTRATE_OWNERSHIP_CUT_V1.json"


def load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_zero_credit_and_zero_terminal_reality():
    x = load()
    assert x["accounting"]["incremental_spend_usd"] == 0
    assert x["accounting"]["new_terminal_cases_exposed"] == 0
    assert x["accounting"]["terminal_cases_consumed"] == 0
    assert x["accounting"]["ownership_credit_delta"] == 0
    assert x["authority"]["execution"] is False
    assert x["authority"]["promotion"] is False


def test_external_provider_negative_control_is_mandatory():
    x = load()
    arch = x["ownership_architecture"]
    assert "MUST_NOT_ALREADY_SATISFY" in arch["required_negative_control"]
    assert "CAUSALLY_NECESSARY" in arch["required_causal_result"]
    assert "HIDDEN_STANDALONE_TARGET_CAPABILITY_PROVIDER" in arch["provider_boundary"]


def test_whole_donor_mirroring_is_not_terminal_ownership():
    x = load()
    repair = x["truth_repair"]
    assert repair["current_route_utility"].startswith("VALID_AS_CONTENT_ADDRESSED_DONOR_PROVENANCE")
    assert "DOES_NOT_ESTABLISH_BRAIN_OWNERSHIP" in repair["current_route_terminal_limitation"]
    assert any("55_6_GB_WHOLE_DONOR_STORAGE" in item for item in x["work_deleted"])


def test_lora_clue_is_not_overclaimed():
    x = load()
    clue = x["white_box_clue"]
    assert "LOCALIZATION_AND_HARVEST_CLUE" in clue["admissible_use"]
    assert "NOT_ASSUMED_TO_REMAIN_EXACTLY_LOW_RANK" in clue["hard_nonclaim"]


def test_minimum_route_requires_ablation_and_configured_pass():
    x = load()
    actions = x["ranked_next_actions"]
    assert any("RAW_SUBSTRATE_NEGATIVE_CONTROL" in item for item in actions)
    assert any("MINIMUM_RESOURCE_SUBSTRATE" in item for item in actions)
