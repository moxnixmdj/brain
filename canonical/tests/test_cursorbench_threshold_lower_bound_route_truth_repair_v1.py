import json
from pathlib import Path

from canonical.runtime.benchmark_witness_elimination_compiler_v3 import evaluate_certificate

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "canonical/governance/CURSORBENCH_THRESHOLD_LOWER_BOUND_ROUTE_TRUTH_REPAIR_20261009_V1.json"
REG = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
READY = ROOT / "canonical/governance/OPUS55_PUBLIC_BAR_SCORE_READINESS_MATRIX_V1.json"
NONID = ROOT / "canonical/governance/CURSORBENCH_4_0_PUBLIC_SCORE_ROUTE_NONIDENTIFIABILITY_20261009_V1.json"

SHA = "1" * 40
BIND = {"path": "canonical/verification/synthetic-threshold-proof.json", "git_blob_sha": SHA}

def proof(claim_id, scope, *, claim_value=None, target_value=None):
    row = {
        "claim_id": claim_id,
        "status": "PROVED_EXACT",
        "proof_type": "DETERMINISTIC_DERIVATION",
        "target_scope": scope,
        "evidence_class": "DETERMINISTIC_FORMAL_PROOF",
        "target_tuple_binding": dict(BIND),
        "receipts": [dict(BIND)],
    }
    if claim_value is not None:
        row["claim_value"] = claim_value
    if target_value is not None:
        row["target_value"] = target_value
    return row

def threshold_spec(lower=0.578):
    return {
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "exact_target_tuple_bound": True,
        "target_tuple_binding": dict(BIND),
        "certificate": {
            "type": "THRESHOLD_LOWER_BOUND",
            "receipts": [dict(BIND)],
            "evaluator_relation": {
                "status": "PROVED_EXACT",
                "relation_type": "EXACT_IDENTITY",
                "target_scope": "FROZEN_TARGET_EVALUATOR_HARNESS_FALLBACK",
                "evidence_class": "EXACT_FROZEN_TARGET_HARNESS",
                "target_tuple_binding": dict(BIND),
                "receipts": [dict(BIND)],
            },
            "proved_lower_bound": lower,
            "target_threshold": 0.578,
            "premise_proofs": {
                "SCORE_DECOMPOSITION_EXACT": proof(
                    "SCORE_DECOMPOSITION_EXACT", "FROZEN_TARGET_SCORING_RULE"
                ),
                "LOWER_BOUND_GE_TARGET": proof(
                    "LOWER_BOUND_GE_TARGET",
                    "FROZEN_TARGET_SCORE_THRESHOLD",
                    claim_value=lower,
                    target_value=0.578,
                ),
            },
        },
    }

def test_fixed_bar_can_close_by_threshold_lower_bound_without_whole_scope_adequacy():
    doc = json.loads(DOC.read_text(encoding="utf-8"))
    registry = json.loads(REG.read_text(encoding="utf-8"))
    row = next(x for x in registry["predicates"] if x["id"] == "CODING_CURSORBENCH_GE_57_8")
    assert row["kind"] == "PUBLIC_FIXED_BAR"
    assert row["acceptance"] == "CursorBench 4.0 >= 57.8%"

    out = evaluate_certificate(threshold_spec())
    assert out.admissible is True, out
    assert out.reason == "THRESHOLD_SOUNDLY_IMPLIED"

    # The admitted certificate contains neither of the stronger-route premises.
    premises = threshold_spec()["certificate"]["premise_proofs"]
    assert "UNIVERSAL_SUCCESS" not in premises
    assert "HIDDEN_SCOPE_UPPER_BOUND" not in premises

    assert "UNIVERSAL_SUCCESS" in doc["logic"]["not_required_by_threshold_route"]
    assert "COMPLETE_POSITIVE_ADEQUACY_COVER_OF_EVERY_CURSORBENCH_CONTEXT" in doc["logic"]["not_required_by_threshold_route"]

def test_below_threshold_is_rejected():
    out = evaluate_certificate(threshold_spec(0.577))
    assert out.admissible is False
    assert out.reason == "PROVED_LOWER_BOUND_BELOW_TARGET"

def test_current_threshold_route_is_not_falsely_marked_ready():
    doc = json.loads(DOC.read_text(encoding="utf-8"))
    ready = json.loads(READY.read_text(encoding="utf-8"))
    nonid = json.loads(NONID.read_text(encoding="utf-8"))

    row = next(x for x in ready["rows"] if x["surface"] == "CursorBench 4.0")
    assert row["scorer"] == "NOT_BOUND"
    assert row["score_producing_route_ready"] is False
    assert nonid["answer"].startswith("NO__")
    assert doc["current_route_state"]["threshold_route"] == "OPEN_BLOCKED"
    assert doc["current_route_state"]["current_score_producing_route_ready"] is False
    assert doc["accounting"]["acceptance_credit_delta"] == 0
    assert doc["accounting"]["terminal_credit_delta"] == 0
