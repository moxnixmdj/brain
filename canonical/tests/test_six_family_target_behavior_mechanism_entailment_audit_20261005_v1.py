from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime.target_behavior_mechanism_entailment_gate_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "canonical/governance/SIX_FAMILY_TARGET_BEHAVIOR_MECHANISM_ENTAILMENT_AUDIT_20261005_V1.json"


def test_current_six_family_entailment_audit_passes_fail_closed_gate() -> None:
    doc = json.loads(AUDIT.read_text())
    out = evaluate(doc)
    assert out["status"] == "PASS", out
    assert out["errors"] == []
    assert out["edge_count"] == 11
    assert out["mandatory_admissible_count"] == 1


def test_only_computer_browser_grounding_is_currently_mandatory() -> None:
    doc = json.loads(AUDIT.read_text())
    out = evaluate(doc)
    mandatory = [
        (row["family"], row["behavior_id"])
        for row in out["rows"]
        if row["admissible_as_mandatory"]
    ]
    assert mandatory == [
        ("COMPUTER_AND_BROWSER_USE", "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001")
    ]


def test_nonmandatory_edges_do_not_grant_credit_or_authority() -> None:
    out = evaluate(json.loads(AUDIT.read_text()))
    assert out["acceptance_credit_delta"] == 0
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False
    assert out["incremental_spend_usd"] == 0
