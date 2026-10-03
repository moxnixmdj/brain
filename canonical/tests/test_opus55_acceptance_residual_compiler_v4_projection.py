from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.opus55_acceptance_residual_compiler_v3 import evaluate

ROOT = Path(__file__).resolve().parents[2]

def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

REG="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EVID="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
COMP="canonical/reasoning/2026-10-02_EXACT_OPUS55_ZERO_COST_COMPARATOR_ROUTE_RECONCILIATION_V1.json"
READY="canonical/governance/OPUS55_PUBLIC_BAR_SCORE_READINESS_MATRIX_V1.json"

def test_current_post_tool_discovery_projection():
    out=evaluate(load(REG),load(EVID),load(COMP),load(READY))
    assert out["errors"] == [], out
    assert out["proved_predicate_count"] == 12, out
    assert out["open_predicate_count"] + out["blocked_predicate_count"] == 26, out
    assert out["receipt_saturation_complete"] is False, out
    assert [a["action_id"] for a in out["authorized_actions"]] == ["ACTION::SATURATE_EXISTING_RECEIPTS"], out
    assert out["terminal_promotion_allowed"] is False
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0

def test_tool_discovery_universal_scope_compiles_as_load_bearing():
    ev=load(EVID)
    row=next(x for x in ev["claims"] if x["predicate_id"]=="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
    assert row["state"] == "PROVED"
    assert row["proof_kind"] == "ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS"
    assert row["scope_completeness"]["all_admissible_target_inputs_proved"] is True
    out=evaluate(load(REG),ev,load(COMP),load(READY))
    assert "NONINDEPENDENT_EVIDENCE:TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" not in out["errors"], out
    assert "UNIVERSAL_SCOPE_COMPLETENESS_NOT_ESTABLISHED:TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" not in out["errors"], out
