from copy import deepcopy

import pytest

from canonical.runtime.unknown_domain_direct_production_reducer_v1 import ReductionError, reduce_result

TRANSFER = "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE"
ABSTAIN = "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"
DIGEST = "9dd08aab9d79e6bbf2552d15c405b8de526478c3a505e2397455150d372164cb"
CLAIM = "refs/heads/unknown-domain-direct-claims/" + DIGEST


def _precommit():
    return {
        "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_REDUCTION_PRECOMMIT_V2",
        "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "acceptance_reduction": {
            "required_result_schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_RESULT_V1",
            "required_result_status": "PRODUCTION_PASS",
            "required_target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
            "required_authority_claim_id": CLAIM,
            "required_claim_create_http_status": 201,
            "required_claim_uniqueness_source": "ATOMIC_CREATE_RESPONSE",
            "required_execution_lease_sha256": DIGEST,
            "required_production_cases_generated": 27,
            "required_case_result_count": 27,
            "required_unique_case_ids": 27,
            "required_leaf_counts": {TRANSFER: 12, ABSTAIN: 15},
            "required_abstention_class_balance": {"IDENTIFIABLE": 5, "NONIDENTIFIABLE": 5, "UNDERSPECIFIED": 5},
            "required_transfer_leaf_pass": True,
            "required_abstention_leaf_pass": True,
            "required_all_27_cases_pass": True,
            "required_every_case_scorer_pass": True,
            "max_probe_count_per_case": 2,
            "required_persistent_learned_bytes": 0,
            "required_external_frontier_model_calls": 0,
            "required_external_learned_capability_calls": 0,
            "required_incremental_spend_usd": 0,
            "required_raw_hidden_records_persisted": False,
            "required_raw_evaluator_secret_persisted": False,
            "required_raw_beacon_persisted": False,
            "required_replay_allowed": False,
            "required_replacement_allowed": False,
            "required_result_promotion_authority": False,
            "required_separate_independent_reduction": True,
        },
    }


def _result():
    rows = []
    for i in range(12):
        rows.append({
            "case_id": f"t{i}",
            "leaf_id": TRANSFER,
            "probe_count": 2,
            "scorer_result": {"case_id": f"t{i}", "leaf_id": TRANSFER, "pass": True},
        })
    classes = ["IDENTIFIABLE"] * 5 + ["NONIDENTIFIABLE"] * 5 + ["UNDERSPECIFIED"] * 5
    for i, cls in enumerate(classes):
        rows.append({
            "case_id": f"a{i}",
            "leaf_id": ABSTAIN,
            "probe_count": 1,
            "scorer_result": {"case_id": f"a{i}", "leaf_id": ABSTAIN, "case_class": cls, "pass": True},
        })
    return {
        "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_RESULT_V1",
        "status": "PRODUCTION_PASS",
        "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "authority_claim_id": CLAIM,
        "claim_response_ref": CLAIM,
        "claim_create_http_status": 201,
        "claim_uniqueness_source": "ATOMIC_CREATE_RESPONSE",
        "execution_lease_sha256": DIGEST,
        "production_cases_generated": 27,
        "case_results": rows,
        "aggregate": {
            "case_count": 27,
            "transfer_leaf_pass": True,
            "abstention_leaf_pass": True,
            "all_27_cases_pass": True,
            "class_balance": {"IDENTIFIABLE": 5, "NONIDENTIFIABLE": 5, "UNDERSPECIFIED": 5},
        },
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "incremental_spend_usd": 0,
        "raw_hidden_records_persisted": False,
        "raw_evaluator_secret_persisted": False,
        "raw_beacon_persisted": False,
        "replay_allowed": False,
        "replacement_allowed": False,
        "promotion_authority": False,
        "separate_independent_reduction_required": True,
    }


def test_exact_frozen_pass_surface_reduces_to_local_proof_candidate():
    receipt = reduce_result(_precommit(), _result())
    assert receipt["acceptance_promotion_eligible"] is True
    assert receipt["production_cases_verified"] == 27
    assert receipt["acceptance_credit_delta"] == 0


@pytest.mark.parametrize(
    "mutator",
    [
        lambda r: r.__setitem__("claim_create_http_status", 422),
        lambda r: r.__setitem__("execution_lease_sha256", "0" * 64),
        lambda r: r["case_results"][0]["scorer_result"].__setitem__("pass", False),
        lambda r: r["case_results"][0].__setitem__("probe_count", 3),
        lambda r: r.__setitem__("raw_hidden_records_persisted", True),
        lambda r: r["aggregate"].__setitem__("all_27_cases_pass", False),
    ],
)
def test_any_frozen_condition_violation_fails_closed(mutator):
    result = deepcopy(_result())
    mutator(result)
    with pytest.raises(ReductionError):
        reduce_result(_precommit(), result)
