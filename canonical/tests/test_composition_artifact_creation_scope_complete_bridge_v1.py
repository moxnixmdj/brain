#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "canonical/governance/COMPOSITION_ARTIFACT_CREATION_SCOPE_COMPLETE_BRIDGE_V1.json"
PROTOCOLS = ROOT / "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
MANIFEST = ROOT / "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"
REGISTRY = ROOT / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
PARTITION = ROOT / "canonical/verification/ARTIFACT_UNCOVERED_SCOPE_PARTITION_PROOF_20261002_V1.json"
LEDGER = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_component(s: str) -> str:
    return s.upper().replace(" ", "_")


def main() -> int:
    b = load(BRIDGE)
    p = load(PROTOCOLS)
    m = load(MANIFEST)
    r = load(REGISTRY)
    q = load(PARTITION)
    e = load(LEDGER)

    comp = next(x for x in p["protocols"] if x["family"] == "MULTI_CAPABILITY_COMPOSITION")
    art = next(x for x in p["protocols"] if x["family"] == "ARTIFACT_CREATION")
    assert "research+tool use+artifact creation" in comp["task_dimensions"]
    assert art["family"] == "ARTIFACT_CREATION"

    rows = [x for x in m["interfaces"] if x["component_id"] == "artifact creation"]
    assert len(rows) == 1
    assert rows[0]["interface_id"] == "research+tool use+artifact creation"
    assert rows[0]["required_properties"] == ["SCOPED_ACCEPTANCE_PROOF"]
    assert normalize_component(rows[0]["component_id"]) == "ARTIFACT_CREATION"

    family_contracts = r["family_to_residual_contracts"]["ARTIFACT_CREATION"]
    expected = {
        "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001",
        "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
    }
    assert set(family_contracts) == expected

    partition_contracts = {x["contract"] for x in q["frozen_contract_partition"]}
    assert partition_contracts == expected
    assert q["no_uncovered_contracted_leaf"] is True
    assert q["status"].startswith("PASS__FROZEN_CONTRACTED_ARTIFACT_SCOPE_PARTITIONS_COMPLETELY")
    assert "DOES_NOT_ASSERT_BRAIN_MEETS_AA_BRIEFCASE_1822_ELO" in q["exclusions"]
    assert "DOES_NOT_INHERIT_PUBLIC_BAR_PERFORMANCE_CREDIT" in q["exclusions"]

    row = next(x for x in e["claims"] if x.get("predicate_id") == "ARTIFACT_UNCOVERED_FORMAT_SCOPE_AUDIT")
    assert row["state"] == "PROVED"
    assert row["scope_complete"] is True
    assert row["independent_or_objective"] is True
    assert "ZERO" in row["performance_credit"]

    receipt = b["candidate_receipt"]
    assert receipt["component_id"] == "artifact creation"
    assert receipt["interface_id"] == "research+tool use+artifact creation"
    assert receipt["proved_properties"] == ["SCOPED_ACCEPTANCE_PROOF"]
    assert receipt["verified"] is False and receipt["independent"] is False
    assert receipt["contamination_clean"] is True and receipt["acceptance_scoped"] is True
    assert b["component_binding"]["normalized_component_id"] == "ARTIFACT_CREATION"
    assert b["expected_effect_after_independent_verification"]["projected_scoped_proved_components_after"] == 5
    assert b["expected_effect_after_independent_verification"]["projected_open_components_after"] == 7
    assert b["expected_effect_after_independent_verification"]["strict_opus55_acceptance_delta"] == 0
    assert b["acceptance_credit_delta"] == 0
    assert b["execution_authority"] is False
    assert b["promotion_authority"] is False
    assert b["fresh_reality_authority"] is False

    print("composition artifact-creation scope bridge candidate PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
