from unittest.mock import patch
from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v3 as v3

RAW="loss-absorbing cushion"
BASE={"pass":True,"status":"OPEN__COMPOSED_SOURCE_MEANING_WITH_NON_UNIQUE_REGCAP_CANDIDATES",
"candidate_discovery":{"pass":True},"mapped_concept_id":None,"fully_semantically_bound":False}

def test_identity_precedes_matrix():
    x=dict(BASE); x.update(mapped_concept_id="REGCAP::CCOB",fully_semantically_bound=True)
    with patch.object(v3.v2,"ground",return_value=x), patch.object(v3.ambiguity_v2,"plan_with_authenticated_matrix") as p:
        out=v3.ground(RAW,source_id="s",start=0,end=len(RAW),mapping_scope={"kind":"X"})
    assert out["status"]=="PASS__SOURCE_LOCAL_REGCAP_IDENTITY_PRECEDENCE"
    p.assert_not_called()

def test_candidate_route_forwards_minimum_discriminator():
    plan={"pass":False,"status":"OPEN__MINIMUM_POLICY_CHANGING_DISCRIMINATOR_READY",
    "authenticated_matrix_reused":True,"next_observation_id":"RELEASABILITY_CLASS",
    "minimum_worst_case_cost_units":2.0}
    with patch.object(v3.v2,"ground",return_value=BASE), patch.object(v3.ambiguity_v2,"plan_with_authenticated_matrix",return_value=plan):
        out=v3.ground(RAW,source_id="s",start=0,end=len(RAW),
        mapping_scope={"kind":"BOUND_REGCAP_RIVAL_SET","scope_complete":True})
    assert out["next_observation_id"]=="RELEASABILITY_CLASS"
    assert out["mapped_concept_id"] is None
    assert out["terminal_authority"] is False
