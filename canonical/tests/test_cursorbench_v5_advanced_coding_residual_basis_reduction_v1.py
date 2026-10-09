import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_cursorbench_residual_basis_reduced_to_two():
    doc = json.loads((ROOT / "canonical/governance/CURSORBENCH_V5_ADVANCED_CODING_RESIDUAL_BASIS_REDUCTION_20261009_V1.json").read_text())
    reg = json.loads((ROOT / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json").read_text())
    assert doc["canonical_family_residuals"] == reg["family_to_residual_contracts"]["ADVANCED_AGENTIC_CODING"]
    assert doc["reduction"]["canonical_residual_count_before"] == 4
    assert doc["reduction"]["exact_contracts_discharged_by_reuse"] == 2
    assert doc["reduction"]["surviving_residual_count"] == 2
    assert doc["reduction"]["surviving_residual_ids"] == [
        "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
        "CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001",
    ]
    assert doc["accounting"]["acceptance_credit_delta"] == 0
    assert doc["accounting"]["terminal_credit_delta"] == 0
