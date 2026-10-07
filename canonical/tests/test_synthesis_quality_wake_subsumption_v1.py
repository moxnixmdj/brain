from copy import deepcopy

from canonical.runtime.synthesis_quality_wake_subsumption_v1 import (
    _load,
    verify_documents,
    verify_repository,
)


def test_bound_repository_proves_quality_wake_subsumption():
    out=verify_repository()
    assert out["pass"] is True,out
    assert out["separate_synthesis_quality_target_wake_required"] is False
    assert len(out["target_dimensions"])==6


def test_missing_scope_dimension_fails_closed():
    docs=deepcopy(_load())
    docs["scope"]["children"]=docs["scope"]["children"][:-1]
    out=verify_documents(docs)
    assert out["pass"] is False
    assert "SYNTHESIS_SCOPE_DIMENSION_SET_DRIFT" in out["errors"]


def test_missing_required_coverage_ceiling_fails_closed():
    docs=deepcopy(_load())
    docs["v2"]["theorem"]["quality_coordinates"]["selected_required_claim_coverage"]=0
    out=verify_documents(docs)
    assert out["pass"] is False
    assert "V2_REQUIRED_COVERAGE_CEILING_MISSING" in out["errors"]


def test_uncertainty_ceiling_drift_fails_closed():
    docs=deepcopy(_load())
    docs["v3"]["theorem"]["matched_quality_coordinates"]["uncertainty_and_disagreement_preservation"]=0
    out=verify_documents(docs)
    assert out["pass"] is False
    assert "V3_UNCERTAINTY_CEILING_MISSING" in out["errors"]


def test_v3_independent_replay_drift_fails_closed():
    docs=deepcopy(_load())
    docs["v3_verify"]["replay"]["direct_function_replay"]["tests_passed"]=6
    out=verify_documents(docs)
    assert out["pass"] is False
    assert "V3_REPLAY_COUNT_DRIFT" in out["errors"]


def test_metric_identity_truth_repair_is_load_bearing():
    docs=deepcopy(_load())
    docs["metric_truth"]["truth_repair"]["delete_only"]="OTHER"
    out=verify_documents(docs)
    assert out["pass"] is False
    assert "MATCHED_QUALITY_IDENTITY_STILL_TREATED_AS_AXIOM" in out["errors"]
