from __future__ import annotations

from canonical.runtime.terminal_dependency_falsifier_v1 import (
    ATTACK_FAMILIES,
    falsify,
)


def graph():
    return {
        "nodes": [
            {
                "id": "HASH_BOUND",
                "kind": "LEAF",
                "status": "PROVED",
                "note": "deterministic content-addressed binding",
            },
            {
                "id": "route",
                "kind": "ROUTE",
                "lifecycle": "IMPLEMENTED",
                "creditable": False,
                "terminal_authority": False,
                "implementation": {
                    "path": "canonical/runtime/route.py",
                    "git_blob_sha": "a" * 40,
                },
                "refinement": {
                    "status": "UNRESOLVED",
                    "certificate": None,
                    "verification_receipt": None,
                },
                "live_authority_status": "UNRESOLVED",
                "note": "fixture",
            },
        ]
    }


def _row(out, node_id, family):
    return next(
        row
        for row in out["rows"]
        if row["node_id"] == node_id and row["family"] == family
    )


def test_attack_family_set_contains_implementation_refinement_mismatch():
    assert "IMPLEMENTATION_REFINEMENT_MISMATCH" in ATTACK_FAMILIES
    assert "ADAPTIVE_SELECTION" in ATTACK_FAMILIES
    assert "CAUSAL_CONFOUNDING" in ATTACK_FAMILIES


def test_unbound_implemented_route_surfaces_refinement_mismatch():
    out = falsify(graph())
    row = _row(out, "route", "IMPLEMENTATION_REFINEMENT_MISMATCH")
    assert row["applicability"] == "APPLICABLE"
    assert row["disposition"] == "OPEN"
    assert "NO_VERIFIED_EXECUTABLE_REFINEMENT_RECEIPT" in row["reason"]


def test_content_addressed_route_version_drift_is_marked_guard_covered():
    out = falsify(graph())
    row = _row(out, "route", "VERSION_DRIFT")
    assert row["applicability"] == "APPLICABLE"
    assert row["disposition"] == "COVERED_BY_BOUND_GUARD"


def test_irrelevant_statistical_attack_can_be_explicitly_not_applicable():
    out = falsify(
        graph(),
        attack_profiles={
            "HASH_BOUND": {
                "ADAPTIVE_SELECTION": "NOT_APPLICABLE",
                "PROXY_MEASUREMENT": "NOT_APPLICABLE",
                "CAUSAL_CONFOUNDING": "NOT_APPLICABLE",
            }
        },
    )
    for family in (
        "ADAPTIVE_SELECTION",
        "PROXY_MEASUREMENT",
        "CAUSAL_CONFOUNDING",
    ):
        row = _row(out, "HASH_BOUND", family)
        assert row["disposition"] == "NOT_APPLICABLE"


def test_unspecified_applicability_remains_unknown_not_passed():
    out = falsify(graph())
    row = _row(out, "HASH_BOUND", "TIMING")
    assert row["applicability"] == "UNKNOWN"
    assert row["disposition"] == "UNKNOWN_APPLICABILITY"


def test_falsifier_never_claims_open_world_closure():
    out = falsify(graph())
    assert out["pass"] is True
    assert out["generator_coverage_proved"] is False
    assert out["closure_proved"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0


def test_invalid_attack_profile_fails_closed():
    out = falsify(
        graph(),
        attack_profiles={"HASH_BOUND": {"TIMING": "PROBABLY"}},
    )
    assert out["pass"] is False
    assert out["reason"] == "ATTACK_PROFILE_INVALID"
    assert out["closure_proved"] is False
