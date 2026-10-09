from pathlib import Path

from canonical.runtime.root_theorem_r4_assurance_projection_v2 import project_repo

ROOT = Path(__file__).resolve().parents[2]


def test_v2_consumes_bound_root_registry_without_promoting_unknown():
    out = project_repo(ROOT)
    assert out["status"] == "OPEN__R4_ROOT_REGISTRY_BOUND__EXACT_ROOT_PROOFS_AND_TRUST_TAIL_OPEN", out
    assert out["root_registry"]["pass"] is True
    assert out["gates"]["proof_closure"]["registry_bound"] is True
    assert out["gates"]["proof_closure"]["root_status_vector"] == ["UNKNOWN", "UNKNOWN", "UNKNOWN"]
    assert out["gates"]["proof_closure"]["closed"] is False
    assert out["r4_closed"] is False
    assert out["terminal_credit_delta"] == 0


def test_missing_registry_residual_is_replaced_by_exact_root_proof_residual():
    out = project_repo(ROOT)
    assert "R4_ROOT_CERTIFICATE_COVERAGE_AND_PROOF_CLOSURE" not in out["open_residuals"]
    assert out["open_residuals"] == [
        "R4_R1_R2_R3_EXACT_ROOT_PROOF_CLOSURE",
        "R4_ROOT_PROOF_TO_REALIZATION_EXECUTION_CLOSURE",
        "R4_INDEPENDENT_DOMAIN_ADVERSARIAL_CLOSURE",
    ]
