#!/usr/bin/env python3
from canonical.runtime.finance_index_weighted_lower_bound_reducer_v1 import (
    aggregate_interval, classify, minimum_additional_component_sets
)

def close(a,b,eps=1e-9):
    return abs(a-b) <= eps

def test_weights_and_empty_bounds():
    lo,hi=aggregate_interval({})
    assert close(lo,0)
    assert close(hi,100)
    assert classify({})["state"]=="OPEN"

def test_exact_threshold():
    b={
      "BUSINESS_KNOWLEDGE":61,
      "AGENTIC_KNOWLEDGE_WORK":61,
      "REASONING":61,
      "AGENTIC_TOOL_USE":61,
      "LONG_CONTEXT":61,
      "NON_HALLUCINATION":61,
    }
    r=classify(b)
    assert r["state"]=="PROVED"
    assert close(r["lower"],61)

def test_componentwise_route_is_sufficient_but_not_required():
    # Two perfect 30%-weight components contribute 60. One extra weighted point closes.
    b={"BUSINESS_KNOWLEDGE":100,"AGENTIC_KNOWLEDGE_WORK":100,"REASONING":5}
    r=classify(b)
    assert r["state"]=="PROVED"
    assert close(r["lower"],61)

def test_missing_components_are_not_assumed_good():
    b={"BUSINESS_KNOWLEDGE":100,"AGENTIC_KNOWLEDGE_WORK":100}
    r=classify(b)
    assert r["state"]=="OPEN"
    assert close(r["lower"],60)
    assert close(r["residual"],1)

def test_interval_falsification():
    b={k:[0,50] for k in [
      "BUSINESS_KNOWLEDGE","AGENTIC_KNOWLEDGE_WORK","REASONING",
      "AGENTIC_TOOL_USE","LONG_CONTEXT","NON_HALLUCINATION"
    ]}
    r=classify(b)
    assert r["state"]=="IMPOSSIBLE_ON_BOUND_INPUTS"
    assert close(r["upper"],50)

def test_minimum_cut_scheduler_is_only_possibility_not_credit():
    b={"BUSINESS_KNOWLEDGE":100,"AGENTIC_KNOWLEDGE_WORK":100}
    sets=minimum_additional_component_sets(b)
    assert sets
    assert all(len(x["components"])==1 for x in sets)

def test_invalid_bounds_fail_closed():
    try:
        aggregate_interval({"REASONING":[90,80]})
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
