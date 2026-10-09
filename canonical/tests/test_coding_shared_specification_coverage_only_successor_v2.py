import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_coding_spec_successor_is_coverage_only_and_zero_credit():
    doc = json.loads((ROOT / "canonical/governance/CODING_SHARED_SPECIFICATION_COVERAGE_ONLY_SUCCESSOR_20261009_V2.json").read_text())
    assert doc["current_registry_fact"]["registered_conditioned_policy_count"] == 1
    assert doc["current_registry_fact"]["registered_coding_policy_count"] == 0
    assert doc["current_exact_missing_objects"][0]["id"] == "CODING_V5_AUTHENTICATED_POSITIVE_ADEQUACY_CERTIFICATE_V1"
    assert "GENERAL_RELEVANCE_CLASSIFIER" in doc["deleted_as_current_missing_mechanisms"]
    assert doc["accounting"]["acceptance_credit_delta"] == 0
    assert doc["accounting"]["terminal_credit_delta"] == 0
