from canonical.runtime.synthesis_dimension_scorers_and_strict_reducer_v1 import score_dimensions,score_case,strict_paired_dominance
import pytest

BASE={
 "total_material_claims":4,
 "supported_material_claims":4,
 "correctly_provenanced_material_claims":4,
 "unsupported_material_claims":0,
 "total_required_uncertainty_units":2,
 "preserved_required_uncertainty_units":2,
 "total_audience_requirements":2,
 "satisfied_audience_requirements":2,
 "total_format_style_constraints":3,
 "satisfied_format_style_constraints":3,
 "total_required_decision_relevant_units":5,
 "retained_decision_relevant_units":5,
 "output_budget_pass":True,
}

def test_perfect_scores_one():
    s=score_case(BASE)
    assert s["matched_quality"]==1.0
    assert all(v==1.0 for v in s["components"].values())

def test_unsupported_claim_hard_zero():
    x=dict(BASE); x["unsupported_material_claims"]=1
    assert score_case(x)["matched_quality"]==0.0

def test_dimension_fraction_and_noncompensation():
    x=dict(BASE); x["preserved_required_uncertainty_units"]=1
    s=score_case(x)
    assert s["components"]["uncertainty_and_disagreement_preservation"]==0.5
    assert s["matched_quality"]==0.5

def test_budget_failure_zeroes_compression():
    x=dict(BASE); x["output_budget_pass"]=False
    assert score_case(x)["matched_quality"]==0.0

def test_empty_denominator_is_vacuous_one():
    x=dict(BASE)
    x["total_required_uncertainty_units"]=0
    x["preserved_required_uncertainty_units"]=0
    assert score_dimensions(x)["uncertainty_and_disagreement_preservation"]==1.0

def test_invalid_counts_fail_closed():
    x=dict(BASE); x["supported_material_claims"]=5
    with pytest.raises(ValueError):
        score_case(x)

def test_strict_reducer_passes_pointwise_noninferiority():
    weak=dict(BASE); weak["preserved_required_uncertainty_units"]=1
    out=strict_paired_dominance(
      {"a":BASE,"b":BASE},
      {"a":weak,"b":BASE},
    )
    assert out["sufficient_noninferiority_pass"] is True
    assert out["worst_case_delta"]==0.0

def test_strict_reducer_failure_not_negative_verdict():
    weak=dict(BASE); weak["preserved_required_uncertainty_units"]=1
    out=strict_paired_dominance(
      {"a":weak},
      {"a":BASE},
    )
    assert out["sufficient_noninferiority_pass"] is False
    assert out["failure_is_negative_capability_verdict"] is False

def test_case_mismatch_rejected():
    with pytest.raises(ValueError):
        strict_paired_dominance({"a":BASE},{"b":BASE})
