from copy import deepcopy
import json
from pathlib import Path

import pytest

from canonical.runtime.sub100mb_learned_state_gate_v1 import (
    LearnedStateAuditError,
    evaluate,
)

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "canonical/governance/SUB100MB_ACCEPTED5_ZERO_LEARNED_STATE_AUDIT_V1.json"


def load():
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def test_current_accepted_five_are_zero_learned_state():
    out = evaluate(load())
    assert out["pass"] is True
    assert out["family_count"] == 5
    assert out["zero_learned_state_family_count"] == 5
    assert out["persistent_learned_state_bytes"] == 0
    assert out["remaining_budget_bytes"] == 100_000_000
    assert out["terminal_hypothesis_proved"] is False


def test_hidden_external_learned_provider_fails_closed():
    doc = load()
    doc["families"][0]["external_learned_capability_provider_required"] = True
    with pytest.raises(LearnedStateAuditError, match="EXTERNAL_LEARNED_PROVIDER_REQUIRED"):
        evaluate(doc)


def test_incomplete_dependency_inventory_fails_closed():
    doc = load()
    doc["families"][0]["dependency_inventory_complete_for_scoped_capability"] = False
    with pytest.raises(LearnedStateAuditError, match="DEPENDENCY_INVENTORY_INCOMPLETE"):
        evaluate(doc)


def test_budget_overrun_is_reported_not_hidden():
    doc = load()
    doc["families"][0]["persistent_learned_state_bytes"] = 100_000_001
    doc["result"]["persistent_learned_state_bytes_required_by_audited_accepted_routes"] = 100_000_001
    doc["result"]["accepted_families_with_zero_persistent_learned_state"] = 4
    doc["result"]["within_100mb_learned_state_budget"] = False
    out = evaluate(doc)
    assert out["pass"] is False
    assert out["persistent_learned_state_bytes"] == 100_000_001
    assert out["remaining_budget_bytes"] == -1


def test_forged_summary_bytes_are_rejected():
    doc = load()
    doc["result"]["persistent_learned_state_bytes_required_by_audited_accepted_routes"] = 1
    with pytest.raises(LearnedStateAuditError, match="RESULT_LEARNED_BYTES_MISMATCH"):
        evaluate(doc)
