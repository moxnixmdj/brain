from pathlib import Path

from canonical.runtime.root_theorem_r4_assurance_projection_v1 import project_repo


ROOT = Path(__file__).resolve().parents[2]


def current():
    return project_repo(ROOT)


def test_current_r4_is_open_not_self_certified():
    out = current()
    assert out["status"] == "OPEN__R4_EXACT_RESIDUAL_LOCALIZED", out
    assert out["pass"] is False
    assert out["r4_closed"] is False
    assert out["terminal_credit_delta"] == 0


def test_current_declared_representation_is_the_only_closed_gate():
    out = current()
    gates = out["gates"]
    assert gates["representation_closure"]["closed"] is True
    assert gates["proof_closure"]["closed"] is False
    assert gates["execution_closure"]["closed"] is False
    assert gates["adversarial_closure"]["closed"] is False


def test_current_r4_residual_is_exact_three_gate_tail():
    out = current()
    assert out["open_residuals"] == [
        "R4_ROOT_CERTIFICATE_COVERAGE_AND_PROOF_CLOSURE",
        "R4_ROOT_PROOF_TO_REALIZATION_EXECUTION_CLOSURE",
        "R4_INDEPENDENT_DOMAIN_ADVERSARIAL_CLOSURE",
    ]


def test_existing_assurance_kernel_is_reused_without_new_primitive():
    out = current()
    assert out["new_primitive_required"] is False
    assert out["assurance_terminal_authority"] is False
    assert out["hard_nonclaim"].startswith("REPRESENTATION_PASS_IS_CURRENT_DECLARED_REGISTRY_ONLY")
