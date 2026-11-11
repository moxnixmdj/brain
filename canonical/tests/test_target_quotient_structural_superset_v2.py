from canonical.runtime.target_quotient_structural_superset_v2 import (
    SupersetCertificateError,
    certify_structural_superset,
    require_terminal_sufficient,
)


def full(**overrides):
    args = {
        "target_subset_receipt_verified": True,
        "superset_semantics_complete": True,
        "superset_dominance_verified": True,
        "condition_composition_closure_verified": True,
        "resource_safety_authority_nonregression_verified": True,
        "donor_independent_ownership_verified": True,
    }
    args.update(overrides)
    return certify_structural_superset(**args)


def test_interface_never_accepts_exact_target_membership():
    cert = full()
    assert not hasattr(cert, "target_members")
    assert not hasattr(cert, "target")
    assert require_terminal_sufficient(cert).startswith("PASS__")


def test_verified_subset_receipt_is_load_bearing():
    cert = full(target_subset_receipt_verified=False)
    assert cert.terminal_sufficient is False
    try:
        require_terminal_sufficient(cert)
    except SupersetCertificateError as exc:
        assert str(exc) == "SUPERSET_ROUTE_PREMISE_MISSING"
    else:
        raise AssertionError("expected fail closed")


def test_every_superset_premise_is_load_bearing():
    fields = [
        "superset_semantics_complete",
        "superset_dominance_verified",
        "condition_composition_closure_verified",
        "resource_safety_authority_nonregression_verified",
        "donor_independent_ownership_verified",
    ]
    for field in fields:
        assert full(**{field: False}).terminal_sufficient is False


def test_non_boolean_receipt_rejected():
    try:
        certify_structural_superset(
            target_subset_receipt_verified=1,
            superset_semantics_complete=True,
            superset_dominance_verified=True,
            condition_composition_closure_verified=True,
            resource_safety_authority_nonregression_verified=True,
            donor_independent_ownership_verified=True,
        )
    except SupersetCertificateError as exc:
        assert str(exc) == "BOOLEAN_PROOF_FLAGS_REQUIRED"
    else:
        raise AssertionError("expected fail closed")
