"""Deterministic evaluator-side synthesis dimension scorers and a strict
paired-dominance reducer.

Pre-exposure only. Creates no matched result and no execution authority.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from canonical.runtime.synthesis_matched_quality_metric_v1 import aggregate

SCHEMA="PROJECT_BRAIN_SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1"

def _count(x: Any, name: str) -> int:
    if isinstance(x,bool) or not isinstance(x,int) or x < 0:
        raise ValueError(f"INVALID_COUNT:{name}")
    return x

def _fraction(num: Any, den: Any, name: str) -> float:
    n=_count(num,f"{name}:num"); d=_count(den,f"{name}:den")
    if n>d:
        raise ValueError(f"COUNT_EXCEEDS_TOTAL:{name}")
    return 1.0 if d==0 else n/d

def score_dimensions(facts: Mapping[str,Any]) -> dict[str,float]:
    if not isinstance(facts,Mapping):
        raise ValueError("FACTS_NOT_MAPPING")
    total_material=_count(facts.get("total_material_claims"),"total_material_claims")
    supported=_fraction(facts.get("supported_material_claims"),total_material,"supported_material_claims")
    provenance=_fraction(facts.get("correctly_provenanced_material_claims"),total_material,"correctly_provenanced_material_claims")
    claim=min(supported,provenance)

    uncertainty=_fraction(
        facts.get("preserved_required_uncertainty_units"),
        facts.get("total_required_uncertainty_units"),
        "uncertainty",
    )
    audience=_fraction(
        facts.get("satisfied_audience_requirements"),
        facts.get("total_audience_requirements"),
        "audience",
    )
    fmt=_fraction(
        facts.get("satisfied_format_style_constraints"),
        facts.get("total_format_style_constraints"),
        "format_style",
    )
    budget=facts.get("output_budget_pass")
    if not isinstance(budget,bool):
        raise ValueError("OUTPUT_BUDGET_PASS_NOT_BOOL")
    compression=_fraction(
        facts.get("retained_decision_relevant_units"),
        facts.get("total_required_decision_relevant_units"),
        "compression",
    ) if budget else 0.0

    return {
        "claim_to_source_fidelity":claim,
        "uncertainty_and_disagreement_preservation":uncertainty,
        "audience_adaptation":audience,
        "format_and_style_constraints":fmt,
        "compression_without_decision_relevant_loss":compression,
    }

def score_case(facts: Mapping[str,Any]) -> dict[str,Any]:
    unsupported=_count(facts.get("unsupported_material_claims"),"unsupported_material_claims")
    components=score_dimensions(facts)
    out=aggregate(components,unsupported_material_claims=unsupported)
    return {
        "schema":SCHEMA,
        "components":components,
        "matched_quality":out["matched_quality"],
        "unsupported_material_claims":unsupported,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }

def strict_paired_dominance(
    brain: Mapping[str,Mapping[str,Any]],
    opus: Mapping[str,Mapping[str,Any]],
) -> dict[str,Any]:
    if not isinstance(brain,Mapping) or not isinstance(opus,Mapping):
        raise ValueError("PORTFOLIO_NOT_MAPPING")
    if not brain:
        raise ValueError("EMPTY_PORTFOLIO")
    if set(brain)!=set(opus):
        raise ValueError("CASE_ID_SET_MISMATCH")
    if len(brain)!=len(set(brain)):
        raise ValueError("DUPLICATE_CASE_ID")

    rows=[]
    worst=1.0
    for cid in sorted(brain):
        b=score_case(brain[cid])["matched_quality"]
        o=score_case(opus[cid])["matched_quality"]
        d=b-o
        worst=min(worst,d)
        rows.append({"case_id":cid,"brain":b,"opus":o,"delta":d})
    passed=worst>=0.0
    return {
        "schema":SCHEMA,
        "reducer":"STRICT_PAIRED_POINTWISE_DOMINANCE_V1",
        "case_count":len(rows),
        "rows":rows,
        "worst_case_delta":worst,
        "sufficient_noninferiority_pass":passed,
        "failure_is_negative_capability_verdict":False,
        "acceptance_credit_authorized":False,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }
