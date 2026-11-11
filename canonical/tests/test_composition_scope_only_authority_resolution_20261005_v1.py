from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MANIFEST = "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"
AUTHORITY = "canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json"
CERT = "canonical/governance/COMPOSITION_SCOPE_ONLY_AUTHORITY_RESOLUTION_20261005_V1.json"

EXPECTED = {
    MANIFEST: "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
    AUTHORITY: "5bb089582a5bc2ee4a44143c8d3a11e919fecdff",
}


def blob(rel: str) -> str:
    b = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_scope_only_is_inadmissible_under_current_pinned_authority():
    for rel, expected in EXPECTED.items():
        assert blob(rel) == expected, (rel, blob(rel), expected)

    manifest = load(MANIFEST)
    authority = load(AUTHORITY)
    cert = load(CERT)

    assert manifest["isolated_component_interface_count"] == 12
    assert all(
        row["required_properties"] == ["SCOPED_ACCEPTANCE_PROOF"]
        for row in manifest["interfaces"]
    )
    assert (
        manifest["next"]
        == "BIND_ONLY_INDEPENDENT_CONTAMINATION_CLEAN_ACCEPTANCE_SCOPED_RECEIPTS_TO_THE_12_LITERAL_INTERFACES__RERUN_COMPONENT_PROOF_SLICER__NO_ACCEPTANCE_OR_FAMILY_CREDIT_FROM_REPRESENTATION_ALONE"
    )
    assert (
        authority["hard_rules"][0]
        == "ONLY_INDEPENDENT_CONTAMINATION_CLEAN_ACCEPTANCE_SCOPED_CURRENT_SOURCE_RECEIPTS_GRANT_COMPONENT_CREDIT"
    )

    theorem = cert["theorem"]
    assert theorem["result"] == "RESOLVED_NO_UNDER_CURRENT_PINNED_AUTHORITY"
    assert cert["scheduler_effect_if_independently_verified"]["current_safe_component_credit"] == "UNCHANGED_4_OF_12"
    assert cert["important_scope"]["authority_relative"] is True
    assert cert["important_scope"]["not_an_eternal_semantic_claim"] is True
    assert cert["acceptance_credit_delta"] == 0
    assert cert["fresh_reality_authority"] is False
