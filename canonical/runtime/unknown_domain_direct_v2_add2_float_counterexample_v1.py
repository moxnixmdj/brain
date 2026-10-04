"""Exact zero-production counterexample to the frozen Unknown-Domain V2 universal proof.

This does not consume a terminal/production population. It instantiates the
already-public frozen generator with a fixed synthetic beacon and evaluator
secret, then runs the exact frozen V2 candidate through the exact frozen
harness/scorer. The witness exposes a binary64 role-order defect in ADD2.
"""
from __future__ import annotations

from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V2_ADD2_FLOAT_COUNTEREXAMPLE_V1"
BEACON = "COUNTEREXAMPLE-BEACON-00000000"
SECRET = b"COUNTEREXAMPLE-SECRET-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ"
TRANSFER_INDEX = 4

EXPECTED = {
    "candidate_terminal_consequence": 7.335613344468422,
    "gold_terminal_consequence": 7.335613344468421,
    "true_r0_feature_id": "udir_b_c45fa39ebb3052",
    "true_r1_feature_id": "udir_b_0e54d03c56ba67",
}


def reproduce() -> dict:
    # Private generator core is intentional: no production authority is
    # requested or consumed. Namespace matches the frozen production shape.
    packet = generator._generate(
        beacon=BEACON,
        evaluator_secret=SECRET,
        namespace="UDIR",
    )
    visible = packet["visible_cases"][TRANSFER_INDEX]
    hidden = packet["hidden_records"][TRANSFER_INDEX]
    result = harness.execute_case(
        candidate_step=candidate.step,
        case_visible=visible,
        hidden_record=hidden,
    )
    scorer = result["scorer_result"]
    action = result["candidate_terminal_action"]

    true_map = hidden["domain_mapping"]
    assert hidden["latent_primitive_program"]["op"] == "ADD2"
    assert true_map["r0"] == EXPECTED["true_r0_feature_id"]
    assert true_map["r1"] == EXPECTED["true_r1_feature_id"]
    assert action["support_feature_ids"] == sorted(true_map.values())
    assert action["terminal_consequence"] == EXPECTED["candidate_terminal_consequence"]
    assert hidden["gold_terminal_consequence"] == EXPECTED["gold_terminal_consequence"]
    assert action["terminal_consequence"] != hidden["gold_terminal_consequence"]
    assert scorer["pass"] is False
    assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in scorer["errors"]

    return {
        "schema": SCHEMA,
        "status": "COUNTEREXAMPLE_REPRODUCED__V2_UNIVERSAL_PASS_FALSE",
        "beacon": BEACON,
        "synthetic_evaluator_secret_sha256_only": __import__("hashlib").sha256(SECRET).hexdigest(),
        "transfer_index": TRANSFER_INDEX,
        "primitive": "ADD2",
        "true_mapping": true_map,
        "candidate_terminal_consequence": action["terminal_consequence"],
        "gold_terminal_consequence": hidden["gold_terminal_consequence"],
        "binary64_delta": action["terminal_consequence"] - hidden["gold_terminal_consequence"],
        "scorer_errors": scorer["errors"],
        "production_authority_used": False,
        "terminal_or_production_cases_consumed": 0,
        "acceptance_credit_delta": 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(reproduce(), indent=2, sort_keys=True))
