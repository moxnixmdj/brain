from __future__ import annotations
import copy
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

def current(evidence=None):
    return evaluate(load(REG), evidence or load(EVID), load(COMP), load(READY))

def test_current_authoritative_proof_forms_compile_without_semantic_downgrade():
    out=current()
    assert out["errors"] == [], out
    assert out["proved_predicate_count"] == 11, out
    assert out["open_predicate_count"] + out["blocked_predicate_count"] == 27, out
    assert out["receipt_saturation_complete"] is False, out
    assert [a["action_id"] for a in out["authorized_actions"]] == ["ACTION::SATURATE_EXISTING_RECEIPTS"], out
    assert out["terminal_promotion_allowed"] is False
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0

def test_delegation_universal_scope_certificate_is_load_bearing():
    ev=load(EVID)
    row=next(x for x in ev["claims"] if x["predicate_id"]=="DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
    row["scope_completeness"]["formal_completeness"]=False
    out=current(ev)
    assert "NONINDEPENDENT_EVIDENCE:DELEGATION_TERMINAL_SUCCESS_NONINFERIOR" in out["errors"] or \
           "UNIVERSAL_SCOPE_COMPLETENESS_NOT_ESTABLISHED:DELEGATION_TERMINAL_SUCCESS_NONINFERIOR" in out["errors"]

def test_recovery_stronger_proof_requires_independent_scope_complete_evidence():
    ev=load(EVID)
    row=next(x for x in ev["claims"] if x["predicate_id"]=="RECOVERY_TERMINAL_NONINFERIOR")
    row["independent_or_objective"]=False
    out=current(ev)
    assert "NONINDEPENDENT_EVIDENCE:RECOVERY_TERMINAL_NONINFERIOR" in out["errors"]

def test_unknown_proof_kind_still_fails_closed():
    ev=load(EVID)
    row=next(x for x in ev["claims"] if x["predicate_id"]=="RECOVERY_TERMINAL_NONINFERIOR")
    row["proof_kind"]="FUTURE_MAGIC"
    out=current(ev)
    assert "INVALID_PROOF_KIND:RECOVERY_TERMINAL_NONINFERIOR" in out["errors"]
