def common_policy(adequate, policy):
    if not adequate: raise ValueError("EMPTY_CELL")
    return all(policy in set(ps) for ps in adequate.values())

def positive_bypass_example():
    true={"w0":{"p","x"},"w1":{"p","y"}}
    assert common_policy(true,"p")
    return {"policy":"p","full_sets_needed_for_success":False}

def negative_completeness_countermodel():
    known_lower={"w0":{"a"},"w1":{"b"}}
    true={"w0":{"a","q"},"w1":{"b","q"}}
    assert not set.intersection(*(set(x) for x in known_lower.values()))
    assert common_policy(true,"q")
    return {
      "lower_bound_sets_have_no_common_policy":True,
      "true_sets_have_hidden_common_policy":True,
      "separator_necessity_from_lower_bounds_only_is_unsound":True,
    }

def verify():
    a=positive_bypass_example()
    b=negative_completeness_countermodel()
    assert a["full_sets_needed_for_success"] is False
    assert b["separator_necessity_from_lower_bounds_only_is_unsound"] is True
    return {"positive_existential_bypass":True,
            "negative_claim_requires_completeness":True,
            "terminal_credit_delta":0}

if __name__=="__main__":
    import json; print(json.dumps(verify(),sort_keys=True))
