from decimal import Decimal
from canonical.runtime.mysterymechanism_intrinsic_noninferiority_certificate_v1 import (
    INTRINSIC_OPUS_SUCCESS_COUNT, DEPLOYED_OPUS_SUCCESS_COUNT, displayed_percent,
    evaluate_certificate,
)


def test_reference_arithmetic():
    assert INTRINSIC_OPUS_SUCCESS_COUNT == 109
    assert DEPLOYED_OPUS_SUCCESS_COUNT == 110
    assert displayed_percent(109) == Decimal("49.10")
    assert displayed_percent(110) == Decimal("49.55")


def test_fail_closed_and_threshold_mass():
    assert not evaluate_certificate({"route": "PUBLIC_EXAMPLES"}).passed
    p = {
        "route": "THRESHOLD_MASS", "task_count": 222, "same_private_population": True,
        "class_membership_mass_scope_complete": True,
        "brain_universal_success_on_certified_class": True, "same_task_contract": True,
        "same_scorer": True, "independently_verified": True,
        "guaranteed_private_success_mass": 109,
    }
    assert evaluate_certificate(p).passed
    p["guaranteed_private_success_mass"] = 108
    assert not evaluate_certificate(p).passed
