import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERLAY = "canonical/governance/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V5_LIVEBENCH_UNION25_OVERLAY.json"

def test_union25_overlay_strictly_supersedes_active15_as_livebench_target():
    x = json.loads((ROOT / OVERLAY).read_text(encoding="utf-8"))
    d = x["verified_delta"]
    assert d["full_registry_family_count"] == 25
    assert d["compatible_structural_sets_1_to_5"] == 14559
    assert d["active15_full_cross_cases"] == 712704
    assert d["active15_exact_pointwise_matches"] == 712704
    assert d["active15_acceptance_credit"] == 0
    assert x["scheduler_override"]["supersede_base_livebench_strategy"] is True
    assert "FULL_PINNED_REGISTRY25" in x["scheduler_override"]["strategy"]
    assert "ACTIVE15_ONLY_ACCEPTANCE_REDUCTION" in x["scheduler_override"]["stop"]

def test_overlay_grants_no_credit_or_authority():
    x = json.loads((ROOT / OVERLAY).read_text(encoding="utf-8"))
    assert x["accounting"]["acceptance_credit_delta"] == 0
    assert x["accounting"]["family_credit_delta"] == 0
    assert x["accounting"]["capability_credit_delta"] == 0
    assert x["accounting"]["ownership_credit_delta"] == 0
    assert x["execution_authority"] is False
    assert x["promotion_authority"] is False
    assert x["fresh_reality_authority"] is False
