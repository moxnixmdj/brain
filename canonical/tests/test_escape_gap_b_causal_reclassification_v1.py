from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_gap_b_causal_reclassification_preserves_frozen_universe_and_collapses_active_gap_b():
    v2 = load("canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json")
    v3 = load("canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V3.json")
    current = load("canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json")
    binding = load("canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V7.json")

    old = {row["obligation_id"]: row["route_group"] for row in v2["rows"]}
    new = {row["obligation_id"]: row["route_group"] for row in v3["rows"]}
    assert set(old) == set(new)
    changed = {oid for oid in old if old[oid] != new[oid]}
    assert changed == {"PROWORK_GDPVAL_GE_1846", "CHARTOGRAPHY_TOOLS_GE_89"}
    assert all(new[oid] == "GAP_A_ACQUISITION_TOTALITY" for oid in changed)

    assert sum(x == "GAP_A_ACQUISITION_TOTALITY" for x in new.values()) == 12
    assert sum(x == "GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS" for x in new.values()) == 1
    assert new["TB_SCIENCE_GE_58_7"] == "GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"

    rows = {row["residual_id"]: row for row in current["classifications"]}
    gap_a = rows["ESCAPE_GAP_A_ACQUISITION_TOTALITY"]
    gap_b = rows["ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"]
    assert gap_a["successor_count"] == 12
    assert gap_b["successor_count"] == 1
    assert gap_b["active_gap_b_count"] == 0
    assert gap_b["active_gap_b_rows"] == []
    assert gap_b["parked_rows"] == ["TB_SCIENCE_GE_58_7"]

    assert binding["current_successor_manifest"]["path"].endswith("_V3.json")
    assert binding["current_successor_manifest"]["gap_a_count"] == 12
    assert binding["current_successor_manifest"]["gap_b_count"] == 1
    assert binding["shared_gaps"]["GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"]["current_active_obligation_count"] == 0


def test_reclassification_is_zero_credit_and_does_not_fake_row_closure():
    proof = load("canonical/governance/ESCAPE_GAP_B_CAUSAL_RECLASSIFICATION_20261010_V1.json")
    assert proof["derived"]["successor_active_gap_b_count"] == 0
    assert proof["derived"]["successor_parked_gap_b_rows"] == ["TB_SCIENCE_GE_58_7"]
    assert "NO_GAP_A_ROW_PROOF" in proof["hard_nonclaims"]
    assert proof["accounting"]["acceptance_credit_delta"] == 0
    assert proof["accounting"]["terminal_credit_delta"] == 0
