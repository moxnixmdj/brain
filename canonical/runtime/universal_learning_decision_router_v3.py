from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import universal_learning_contract_v1 as v1
from canonical.runtime import universal_active_transfer_learner_v2 as v2
from canonical.runtime import structural_transfer_v3 as transfer
from canonical.runtime import decision_discriminator_v3 as decision

SCHEMA="PROJECT_BRAIN_UNIVERSAL_LEARNING_DECISION_ROUTER_V3"

def route(*,goal:str,verified_coverage:Any,required_facts:Iterable[Any],verified_facts:Iterable[Any],transfer_mappings:Sequence[Mapping[str,Any]],hypotheses:Sequence[Mapping[str,Any]],actions:Sequence[Mapping[str,Any]]):
    base=v1.route_input(verified_coverage=verified_coverage)
    coverage=transfer.apply(verified_facts=verified_facts,mappings=transfer_mappings)
    delta=v2.minimum_novelty_delta(required_facts=required_facts,verified_facts=coverage["verified_facts"])
    common={
        "schema":SCHEMA,
        "trusted_execution_authorized":False,
        "promotion_authorized":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "novelty_delta":delta,
        "transfer_coverage":coverage,
    }
    if base["route"]=="USE_VERIFIED_CAPABILITY" and not delta["missing"]:
        return {
            **common,
            "route":"USE_VERIFIED_CAPABILITY",
            "trusted_execution_authorized":True,
            "reason":"V1_VERIFIED_COVERAGE_AND_ZERO_POST_TRANSFER_NOVELTY_DELTA",
            "recommended_action":None,
            "next_action":None,
        }
    suff=decision.sufficient(hypotheses)
    if suff["sufficient"]:
        return {
            **common,
            "route":"DECISION_SUFFICIENT_UNVERIFIED_MODEL",
            "reason":suff["reason"],
            "recommended_action":suff["action"],
            "next_action":None,
        }
    ranked=decision.rank(hypotheses=hypotheses,actions=actions)
    if ranked:
        return {
            **common,
            "route":"LEARN",
            "reason":"DECISION_RELEVANT_SAFE_DISCRIMINATOR_AVAILABLE",
            "recommended_action":None,
            "next_action":ranked[0],
            "ranked_discriminators":ranked,
        }
    return {
        **common,
        "route":"ABSTAIN_OR_REQUEST_DISCRIMINATOR",
        "reason":"NO_SAFE_POSITIVE_DECISION_GAIN_DISCRIMINATOR_AND_NO_DECISION_SUFFICIENCY",
        "recommended_action":None,
        "next_action":None,
    }
