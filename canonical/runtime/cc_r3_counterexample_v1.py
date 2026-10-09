"""Claim-bound CC_R3 counterexample finder.

For the active checkpoint claim, OPEN/UNKNOWN frozen acceptance predicates retain
both PASS and FAIL completions in B_plus. G_minus requires all mandatory
terminal predicates to be satisfied. Therefore any still-open acceptance family
constructs a witness in B_plus - G_minus.

This is an epistemic terminal-closure counterexample, not a claim that the real
system necessarily fails that family. It grants zero terminal credit.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id

SCHEMA="PROJECT_BRAIN_CC_R3_COUNTEREXAMPLE_V1"
EXPECTED_CLAIM_ID="fda1409a94d983f61888f08f3df99cad50dc36edc3f5feb01b6df20e31156eaa"


def evaluate(claim_doc: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    claim=(claim_doc or {}).get("claim") if isinstance(claim_doc, Mapping) else None
    if not isinstance(claim, Mapping):
        return {"status":"FAIL_CLOSED","errors":["CLAIM_MISSING"],"terminal_credit_delta":0}
    errors=[]
    if claim.get("claim_id") != EXPECTED_CLAIM_ID or compute_claim_id(claim) != EXPECTED_CLAIM_ID:
        errors.append("CLAIM_ID_OR_CORE_BINDING_MISMATCH")
    semantics=(claim_doc or {}).get("semantics_descriptor") or {}
    if semantics.get("b_plus_rule") != "OPEN_OR_UNKNOWN_FROZEN_ACCEPTANCE_PREDICATE_RETAINS_BOTH_PASS_AND_FAIL_COMPLETIONS_UNTIL_PROVED":
        errors.append("B_PLUS_RULE_DRIFT")
    if semantics.get("g_minus_rule") != "ONLY_COMPLETIONS_SATISFYING_ALL_MANDATORY_TERMINAL_PREDICATES_ARE_DEFINITELY_GOOD":
        errors.append("G_MINUS_RULE_DRIFT")
    if manifest.get("expected_family_count") != 19 or manifest.get("actual_family_count") != 19:
        errors.append("FROZEN_FAMILY_UNIVERSE_DRIFT")
    families=manifest.get("families")
    if not isinstance(families,list) or len(families)!=19:
        errors.append("FAMILY_LIST_INVALID")
        families=[]
    if errors:
        return {"status":"FAIL_CLOSED","errors":errors,"terminal_credit_delta":0}

    open_rows=[]
    for row in families:
        if not isinstance(row,Mapping):
            continue
        state=row.get("opus55_acceptance_state")
        unresolved=row.get("unresolved")
        if state != "PASS" or (isinstance(unresolved,list) and unresolved):
            open_rows.append({
                "family_id":row.get("id"),
                "opus55_acceptance_state":state,
                "unresolved":list(unresolved or []),
            })

    if not open_rows:
        return {
            "schema":SCHEMA,
            "status":"NO_R3_COUNTEREXAMPLE_FROM_FROZEN_ACCEPTANCE_STATES__U_EMPTY_NOT_PROVED",
            "claim_id":EXPECTED_CLAIM_ID,
            "witness":None,
            "terminal_credit_delta":0,
        }

    witness=open_rows[0]
    return {
        "schema":SCHEMA,
        "status":"CC_R3_COUNTEREXAMPLE_CURRENT_EPISTEMIC_ENVELOPE",
        "claim_id":EXPECTED_CLAIM_ID,
        "root_id":"CC_R3_TERMINAL_CLOSURE_V1",
        "witness":{
            **witness,
            "b_plus_membership_reason":"OPEN_ACCEPTANCE_RETAINS_FAIL_COMPLETION",
            "not_in_g_minus_reason":"G_MINUS_REQUIRES_ALL_MANDATORY_TERMINAL_PREDICATES_SATISFIED",
        },
        "open_family_count":len(open_rows),
        "u_empty":False,
        "cc_r3_proved":False,
        "terminal_credit_delta":0,
        "nonclaim":"DOES_NOT_PROVE_REAL_SYSTEM_FAILURE__PROVES_CURRENT_R3_CLOSURE_IS_FALSE_UNDER_FROZEN_EPISTEMIC_ENVELOPE",
    }
