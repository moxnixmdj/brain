from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/COMPOSITION_CURRENT_AUTHORITY_V8.json"
COUNTER=ROOT/"canonical/governance/COMPOSITION_COMPONENT_SCOPED_PROOF_NECESSITY_COUNTERMODEL_20261006_V1.json"
VERIFY=ROOT/"canonical/verification/COMPOSITION_COMPONENT_SCOPED_PROOF_NECESSITY_SPRITE_VERIFICATION_20261006_V1.json"

def load(p):
    return json.loads(p.read_text(encoding="utf-8"))

def test_parent_requirements_no_longer_require_internal_component_parity():
    a=load(AUTH)
    required=a["current_parent_composition_requirements"]
    assert required["terminal_comparison"]==[
        "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
        "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
    ]
    assert a["component_slice"]["no_longer_required_for_parent_composition_acceptance"] is True
    assert len(a["component_slice"]["open_component_receipt_chase_removed_from_parent_critical_path"])==7
    flat=json.dumps(required,sort_keys=True)
    assert "COMPOSITION_COMPONENT_SCOPED_PROOFS" not in flat

def test_truth_repair_is_independently_verified_and_preserves_separate_capabilities():
    a=load(AUTH); c=load(COUNTER); v=load(VERIFY)
    assert "STANDALONE_COMPONENT_PARITY_NOT_NECESSARY" in str(c["status"])
    assert str(v["status"]).startswith("INDEPENDENT_SPRITE_EXACT_BRANCH_BYTE_REPLAY_PASS")
    assert c["logical_result"]["falsified_necessity"].startswith("Every internal component")
    assert a["component_slice"]["preservation_rule"].startswith("IF_ANY_COMPONENT_IS_ITSELF_A_SEPARATE_USEFUL_TERMINAL_CAPABILITY")

def test_no_parent_credit_claimed():
    a=load(AUTH)
    assert a["accounting"]["terminal_credit_delta"]==0
    assert "NO_CLAIM_PARENT_COMPOSITION_IS_CURRENTLY_NONINFERIOR" in a["hard_nonclaims"]

if __name__=="__main__":
    test_parent_requirements_no_longer_require_internal_component_parity()
    test_truth_repair_is_independently_verified_and_preserves_separate_capabilities()
    test_no_parent_credit_claimed()
    print("test_composition_current_authority_v8: PASS")
