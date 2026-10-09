from canonical.runtime.coverage_root_namespace_guard_v1 import (
    classify_root_claim,
    validate_bridge_document,
)


def test_direct_ccrt_root_can_close():
    out = classify_root_claim({
        "source_namespace": "CCRT",
        "source_root": "R2",
        "asserted_ccrt_root": "R2",
        "relation": "EQUIVALENT",
    })
    assert out["pass"] is True
    assert out["can_close_ccrt_root"] is True


def test_legacy_root2_cannot_equal_ccrt_r2():
    out = classify_root_claim({
        "source_namespace": "LEGACY_ESCAPE_POLICY_ADEQUACY",
        "source_root": "ROOT2",
        "asserted_ccrt_root": "R2",
        "relation": "EQUIVALENT",
    })
    assert out["pass"] is False
    assert out["can_close_ccrt_root"] is False


def test_legacy_root2_may_support_ccrt_r3_without_closing():
    out = classify_root_claim({
        "source_namespace": "LEGACY_ESCAPE_POLICY_ADEQUACY",
        "source_root": "ROOT2",
        "asserted_ccrt_root": "R3",
        "relation": "SUPPORTS",
    })
    assert out["pass"] is True
    assert out["can_close_ccrt_root"] is False


def test_legacy_root3_cannot_equal_ccrt_r3():
    out = classify_root_claim({
        "source_namespace": "LEGACY_EFFECT_FINALITY",
        "source_root": "ROOT3",
        "asserted_ccrt_root": "R3",
        "relation": "EQUIVALENT",
    })
    assert out["pass"] is False


def test_legacy_root3_may_support_ccrt_r1():
    out = classify_root_claim({
        "source_namespace": "LEGACY_EFFECT_FINALITY",
        "source_root": "ROOT3",
        "asserted_ccrt_root": "R1",
        "relation": "SUPPORTS",
    })
    assert out["pass"] is True
    assert out["can_close_ccrt_root"] is False


def test_unnamespaced_claim_fails_closed():
    out = classify_root_claim({
        "source_root": "R3",
        "asserted_ccrt_root": "R3",
        "relation": "EQUIVALENT",
    })
    assert out["pass"] is False


def test_bridge_rejects_legacy_equivalence():
    bridge = {
        "theorem_namespace": {
            "id": "CCRT",
            "roots": {"R1": "", "R2": "", "R3": "", "R4": ""},
        },
        "legacy_namespaces": {
            "LEGACY_ESCAPE_POLICY_ADEQUACY": {
                "equivalent_to_ccrt_roots": ["R2"],
                "can_close_ccrt_root_by_label_identity": False,
            },
            "LEGACY_EFFECT_FINALITY": {
                "equivalent_to_ccrt_roots": [],
                "can_close_ccrt_root_by_label_identity": False,
            },
        },
    }
    out = validate_bridge_document(bridge)
    assert out["pass"] is False


def test_valid_bridge_passes():
    bridge = {
        "theorem_namespace": {
            "id": "CCRT",
            "roots": {"R1": "", "R2": "", "R3": "", "R4": ""},
        },
        "legacy_namespaces": {
            "LEGACY_ESCAPE_POLICY_ADEQUACY": {
                "equivalent_to_ccrt_roots": [],
                "can_close_ccrt_root_by_label_identity": False,
            },
            "LEGACY_EFFECT_FINALITY": {
                "equivalent_to_ccrt_roots": [],
                "can_close_ccrt_root_by_label_identity": False,
            },
        },
    }
    out = validate_bridge_document(bridge)
    assert out["pass"] is True
    assert out["terminal_credit_delta"] == 0
