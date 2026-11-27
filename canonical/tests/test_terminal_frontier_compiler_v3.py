from __future__ import annotations

import copy

import pytest

from canonical.runtime import terminal_frontier_compiler_v2 as v2
from canonical.runtime.terminal_frontier_compiler_v3 import (
    FrontierV3Error,
    compile_frontier,
    meta_envelope_obligations_v3,
)


def test_v5_and_v6_have_same_meta_count_but_different_identity():
    v5 = v2._load("canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V5.json")
    v6 = v2._load("canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V6.json")

    m5 = meta_envelope_obligations_v3(v5)
    m6 = meta_envelope_obligations_v3(v6)

    assert m5["open_count"] == 8
    assert m6["open_count"] == 8
    assert m5["identity_sha256"] != m6["identity_sha256"]

    assert m5["proof_basis_repairs"] == [
        "CREATIVE_TEXT_ARTIFACT_AND_DIAGRAM_OUTPUT"
    ]
    assert m5["performance_obligations"] == []

    assert m6["proof_basis_repairs"] == []
    assert m6["performance_obligations"] == [
        "CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META"
    ]


def test_v2_parser_reproduces_the_current_v6_identity_drop():
    v6 = v2._load("canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V6.json")
    old = v2.meta_envelope_obligations(v6)
    assert old["open_count"] == 7
    assert "performance_obligations" not in old


def test_v3_parser_matches_v6_declared_meta8():
    v6 = v2._load("canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V6.json")
    out = meta_envelope_obligations_v3(v6)
    assert out["open_count"] == v6["open_meta_obligation_accounting"][
        "total_open_meta_obligations"
    ]
    assert out["open_count"] == 8


def test_declared_meta_count_mismatch_fails_closed():
    v6 = v2._load("canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V6.json")
    broken = copy.deepcopy(v6)
    broken["open_meta_obligation_accounting"]["total_open_meta_obligations"] = 9
    with pytest.raises(
        FrontierV3Error,
        match="META_OPEN_COUNT_DISAGREES_WITH_ACTIVE_ROOT1_AUTHORITY",
    ):
        meta_envelope_obligations_v3(broken)


def test_duplicate_performance_identity_fails_closed():
    v6 = v2._load("canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V6.json")
    broken = copy.deepcopy(v6)
    broken["terminal_performance_obligations"] = [
        {
            "id": "CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META",
            "state": "OPEN",
        }
    ]
    with pytest.raises(
        FrontierV3Error,
        match="PERFORMANCE_OBLIGATION_IDENTITY_DUPLICATE",
    ):
        meta_envelope_obligations_v3(broken)


def test_current_frontier_uses_active_v6_and_preserves_creative_performance_identity():
    out = compile_frontier()
    meta = out["meta_envelope"]
    assert meta["active_version"] >= 6
    assert meta["open_count"] == 8
    assert meta["proof_basis_repairs"] == []
    assert meta["performance_obligations"] == [
        "CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META"
    ]
    assert len(meta["identity_sha256"]) == 64
    assert out["terminal"] is False


def test_identity_hash_changes_even_when_open_count_is_unchanged():
    v6 = v2._load("canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V6.json")
    original = meta_envelope_obligations_v3(v6)

    changed = copy.deepcopy(v6)
    changed["creative_diagram_performance_frontier"][
        "obligation"
    ] = "SAME_COUNT_DIFFERENT_OBLIGATION"
    mutated = meta_envelope_obligations_v3(changed)

    assert original["open_count"] == mutated["open_count"] == 8
    assert original["identity_sha256"] != mutated["identity_sha256"]
