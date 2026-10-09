import json
from pathlib import Path

from canonical.runtime import p3_conditioned_policy_adequacy_registry_v1 as registry

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "canonical/governance/CODING_SHARED_SPECIFICATION_COVERAGE_ONLY_SUCCESSOR_20261009_V3.json"

SPECIALIST = "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"
EXPECTED_ATOMS = {
    "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1",
    "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1",
    "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1",
    "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1",
    "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1",
}

def test_v3_reconciles_registry_truth_without_closing_v5_or_whole_cover():
    doc = json.loads(DOC.read_text(encoding="utf-8"))
    catalog = registry.catalog()
    by_id = {row["policy_id"]: row for row in catalog["policies"]}

    assert catalog["policy_count"] == 2
    assert SPECIALIST in by_id
    assert doc["current_registry_fact"]["registered_conditioned_policy_count"] == 2
    assert doc["current_registry_fact"]["registered_coding_specialist_policy_count"] == 1
    assert doc["current_registry_fact"]["coding_positive_adequacy_edge_available_from_registry"] is True
    assert doc["current_registry_fact"]["v5_common_policy_certificate_registered"] is False

    condition = by_id[SPECIALIST]["condition"]
    assert condition["op"] == "AND"
    assert {row["id"] for row in condition["args"]} == EXPECTED_ATOMS
    assert set(doc["specialist_edge"]["condition_atoms"]) == EXPECTED_ATOMS
    assert doc["specialist_edge"]["registry_presence_proves_membership"] is False
    assert doc["specialist_edge"]["hidden_cursorbench_task_membership_proved"] is False

    assert "FIRST_REAL_SOURCE_POSITIVE_CODING_ADEQUACY_EDGE" in doc["reduction"]["deleted_as_missing_object"]
    assert "CODING_V5_AUTHENTICATED_POSITIVE_ADEQUACY_CERTIFICATE_V1" in doc["reduction"]["still_open"]
    assert doc["reduction"]["global_selector_work_ready"] is False
    assert doc["reduction"]["local_specialist_reuse_ready_if_condition_truth_is_source_authorized"] is True

    assert doc["accounting"]["acceptance_credit_delta"] == 0
    assert doc["accounting"]["terminal_credit_delta"] == 0
