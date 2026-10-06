import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MATRIX=ROOT/"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"
GOV=ROOT/"canonical/governance/G_ROUTE_FIVE_GENERATOR_DOMINANCE_RECONCILIATION_20261007_V1.json"

EXPECTED_GENERATOR_FAMILIES={
    "LONG_HORIZON_MEMORY_AND_CONTINUITY",
    "SUBAGENT_DELEGATION_AND_COORDINATION",
    "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
    "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
    "EXACT_SYMBOLIC_COMPUTATION",
}

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_matrix_summary_is_derived_from_current_rows():
    d=load(MATRIX)
    rows=d.get("families") or d.get("rows") or d.get("capabilities") or []
    verified={x["family"] for x in rows if x["status"]=="VERIFIED_OWNED_EQUAL_OR_BETTER"}
    components={x["family"] for x in rows if x["status"]=="OWNED_COMPONENT_NOT_FULL_FAMILY"}
    assert verified==EXPECTED_GENERATOR_FAMILIES
    assert set(d["summary"]["verified_owned_equal_or_better_capabilities"])==verified
    assert set(d["summary"]["owned_components_not_full_family"])==components
    assert d["postwave_acceptance_summary"]["verified_owned_family_count"]==len(verified)==5

def test_g_reconciliation_binds_exact_five_structural_generators():
    d=load(GOV)
    rows=d["generator_reconciliation"]
    assert len(rows)==5
    assert {x["family"] for x in rows}==EXPECTED_GENERATOR_FAMILIES
    assert all(x["state"]=="VERIFIED_OWNED_EQUAL_OR_BETTER" for x in rows)
    assert d["k6_role"]["preproof_generic_implementation_generator"] is False
    assert d["k6_role"]["owned_operator"] is True
    assert d["k6_role"]["certificate_form_logically_mandatory"] is False

def test_g_route_remains_fail_closed_on_transfer_and_generation():
    d=load(GOV)
    residual={x["id"] for x in d["remaining_g_route_requirements"]}
    assert residual=={
        "G_TARGET_GENERATION_COMPLETENESS",
        "G_DOMINANCE_PRESERVING_TRANSFER",
        "G_SEMANTIC_CERTIFICATE_CLOSURE",
        "G_RESOURCE_SAFETY_AUTHORITY_TRANSFER",
        "G_L2_DONOR_INDEPENDENT_EFFECT_TOTALITY",
    }
    assert "NO_CLAIM_G_GENERATOR_CLOSURE_IS_PROVED" in d["hard_nonclaims"]
    assert d["promotion_authority"] is False
    assert d["execution_authority"] is False
    assert d["fresh_reality_authority"] is False
    assert any("ROOT3_EFFECT_TOTALITY_FALSIFICATION" in x for x in d["next_tournament"])
    assert any("K6_ONLY_IF_NONDOMINATED" in x for x in d["next_tournament"])

def test_zero_credit_from_reconciliation():
    d=load(GOV)
    assert all(v==0 for v in d["accounting"].values())
