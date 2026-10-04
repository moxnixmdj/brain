"""REVOKED: the original V2 universal proof is false.

The historical promoted blob 2400dba7f763fc16dc65c31512ccd9eee8be82fb
treated ADD2 true-support role swapping as output-equivalent. That is true over
real arithmetic but false under the frozen scorer's exact Python binary64
comparison. Keep this module fail-closed so no caller can accidentally reuse the
revoked theorem.

Use unknown_domain_direct_v2_add2_float_counterexample_v1.py for the exact
witness and unknown_domain_direct_v3_universal_proof_v1.py for the repaired
zero-credit proof candidate.
"""
from __future__ import annotations

from canonical.runtime import unknown_domain_direct_v2_add2_float_counterexample_v1 as counterexample

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V2_UNIVERSAL_PROOF_V1_REVOKED"


def prove(root=None):
    witness = counterexample.reproduce()
    assert witness["status"] == "COUNTEREXAMPLE_REPRODUCED__V2_UNIVERSAL_PASS_FALSE"
    return {
        "schema": SCHEMA,
        "status": "FAIL__V2_UNIVERSAL_CLAIM_FALSIFIED_BY_EXACT_ADD2_BINARY64_COUNTEREXAMPLE",
        "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "historical_false_proof_blob": "2400dba7f763fc16dc65c31512ccd9eee8be82fb",
        "counterexample": witness,
        "fresh_reality_required_for_THIS_frozen_generator_claim": None,
        "production_execution_information_gain": None,
        "hard_nonclaims": [
            "NO_ACCEPTANCE_PROMOTION_FROM_V2_UNIVERSAL_PROOF",
            "NO_CLAIM_THAT_81_OF_81_SAMPLE_PASS_IMPLIES_UNIVERSAL_COMPLETENESS",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "terminal_cases_consumed": 0,
            "production_cases_generated": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(prove(), indent=2, sort_keys=True))
