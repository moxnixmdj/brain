#!/usr/bin/env python3
import json, math, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/"governance"/"RELATIVE_ELO_ABSOLUTE_PROOF_NONTRANSPORT_V1.json"

def logit(p: float) -> float:
    assert 0.0 < p < 1.0
    return math.log(p/(1.0-p))

def check():
    x=json.loads(P.read_text())
    assert x["schema"]=="PROJECT_BRAIN_RELATIVE_ELO_ABSOLUTE_PROOF_NONTRANSPORT_V1"
    assert len(x["affected_predicates"])==3
    assert {p["predicate_id"] for p in x["affected_predicates"]}=={
        "PROWORK_GDPVAL_GE_1846",
        "PROWORK_AA_BRIEFCASE_GE_1822",
        "ARTIFACT_AA_BRIEFCASE_GE_1822",
    }

    # Countermodel for a Bradley-Terry style relative strength fit with a fixed anchor.
    # Same absolute-certificate state C, different unbound pairwise outcomes.
    # Strength difference is logit(win probability). The sign flips across 0.5.
    absolute_certificate={"all_declared_absolute_obligations": True}
    anchor_strength=0.0
    low_p=0.20
    high_p=0.80
    low_strength=anchor_strength+logit(low_p)
    high_strength=anchor_strength+logit(high_p)
    assert absolute_certificate=={"all_declared_absolute_obligations": True}
    assert low_strength < anchor_strength < high_strength
    assert low_strength != high_strength

    # Therefore absolute state alone does not determine even relative ordering,
    # much less a fixed anchored Elo threshold.
    th=x["theorem"]
    assert "CANNOT_LOGICALLY_ENTAIL_A_FIXED_ELO_THRESHOLD" in th["statement"]
    assert len(th["escape_hatches"])>=3

    rp=x["route_pruning"]
    assert "RELATIVE_SCORE_BRIDGE_STRONGER_PROOF" in rp["preserved"]
    assert "MATCHED_EMPIRICAL_COMPARISON" in rp["preserved"]
    assert "OWNER_RESULT" in rp["preserved"]
    assert "FORMAL_ENTAILMENT" in rp["not_globally_deleted"]
    assert all("WITHOUT_RELATIVE_SCORE_BRIDGE" in s for s in rp["conditionally_deleted_form"])

    assert x["relationship_to_private_surface_dominance"]["target_weakening"] is False
    assert all(v==0 for v in x["accounting"].values())
    assert x["execution_authority"] is False
    assert x["promotion_authority"] is False
    assert x["fresh_reality_authority"] is False
    print(json.dumps({
        "status":"PASS",
        "countermodel_low_strength":low_strength,
        "countermodel_high_strength":high_strength,
        "affected_predicates":3,
        "target_weakening":False,
        "acceptance_credit_delta":0
    },sort_keys=True))

if __name__=="__main__":
    check()
