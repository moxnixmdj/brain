from __future__ import annotations

from typing import Any, Hashable, Mapping, Sequence

from canonical.runtime.terminal_distribution_outcome_order_v1 import (
    OutcomeOrderError,
    weakly_dominates,
)


class AdequatePolicySetError(ValueError):
    pass


def compile_adequate_policy_sets(
    *,
    worlds: Sequence[Hashable],
    policy_ids: Sequence[Hashable],
    brain_outcomes: Mapping[Hashable, Mapping[Hashable, Mapping[str, float]]],
    opus_outcomes: Mapping[Hashable, Mapping[str, float]],
    utilities: Mapping[str, Mapping[str, float]],
    hard_violation_risks: Mapping[str, Mapping[str, float]],
) -> dict[str, Any]:
    """Compile F(w): Brain-owned policies noninferior to Opus in each declared world.

    All semantic authority is supplied as input:
      - the declared finite world set,
      - Brain and Opus outcome distributions on one shared semantic outcome space,
      - frozen terminal utility and hard-risk functionals.

    This function owns only the mechanical set-comprehension/comparison step.
    """
    ws=tuple(worlds)
    ps=tuple(policy_ids)
    if not ws or len(set(ws)) != len(ws):
        raise AdequatePolicySetError("WORLDS_MUST_BE_NONEMPTY_UNIQUE")
    if not ps or len(set(ps)) != len(ps):
        raise AdequatePolicySetError("POLICIES_MUST_BE_NONEMPTY_UNIQUE")
    if not utilities:
        raise AdequatePolicySetError("NONEMPTY_UTILITY_FAMILY_REQUIRED")

    missing_opus=[w for w in ws if w not in opus_outcomes]
    if missing_opus:
        raise AdequatePolicySetError("OPUS_OUTCOME_MISSING:"+",".join(map(repr,missing_opus)))

    adequate: dict[Hashable, list[Hashable]]={}
    comparisons: dict[Hashable, dict[Hashable, dict[str, Any]]]={}

    for w in ws:
        if w not in brain_outcomes:
            raise AdequatePolicySetError("BRAIN_WORLD_OUTCOMES_MISSING:"+repr(w))
        missing_policy=[p for p in ps if p not in brain_outcomes[w]]
        if missing_policy:
            raise AdequatePolicySetError(
                "BRAIN_POLICY_OUTCOME_MISSING:"+repr(w)+":"+",".join(map(repr,missing_policy))
            )
        good=[]
        per_policy={}
        for p in ps:
            try:
                cmp=weakly_dominates(
                    brain_outcomes[w][p],
                    opus_outcomes[w],
                    utilities,
                    hard_violation_risks,
                )
            except OutcomeOrderError as exc:
                raise AdequatePolicySetError(
                    "OUTCOME_ORDER_INPUT_INVALID:"+repr(w)+":"+repr(p)+":"+str(exc)
                ) from exc
            per_policy[p]={
                "weakly_dominates":cmp.weakly_dominates,
                "utility_margins":[list(x) for x in cmp.utility_margins],
                "hard_risk_margins":[list(x) for x in cmp.hard_risk_margins],
            }
            if cmp.weakly_dominates:
                good.append(p)
        adequate[w]=good
        comparisons[w]=per_policy

    empty=[w for w in ws if not adequate[w]]
    return {
        "schema":"PROJECT_BRAIN_K6_ADEQUATE_POLICY_SET_COMPILER_V1",
        "status":"PASS" if not empty else "NO_TARGET_ADEQUATE_BRAIN_POLICY_IN_DECLARED_WORLD",
        "adequate_policy_sets":adequate,
        "empty_worlds":empty,
        "comparisons":comparisons,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }


if __name__=="__main__":
    import json
    out=compile_adequate_policy_sets(
        worlds=["w"],
        policy_ids=["p_good","p_bad"],
        brain_outcomes={
            "w":{
                "p_good":{"success":1.0,"failure":0.0},
                "p_bad":{"success":0.5,"failure":0.5},
            }
        },
        opus_outcomes={"w":{"success":0.9,"failure":0.1}},
        utilities={"success":{"success":1.0,"failure":0.0}},
        hard_violation_risks={},
    )
    print(json.dumps(out,sort_keys=True))
