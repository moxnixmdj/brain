from canonical.runtime.terminal_adaptive_minimum_action_policy_v1 import (
    Action, compile_frontier, next_actions, priority, strictly_dominates
)

def A(action_id, targets, t, p, **kw):
    return Action(action_id, frozenset(targets), t, p, **kw)

def test_zero_probability_deleted():
    x=A("dead", {"P1"}, 1, 0.0)
    out=compile_frontier([x])
    assert out["deleted_probability_zero"] == ["dead"]
    assert out["ranked_known_probability"] == []

def test_unknown_probability_preserved_not_invented():
    x=A("owner_wait", {"P1"}, 3, None)
    out=compile_frontier([x])
    assert out["unknown_probability_preserved"][0]["action_id"] == "owner_wait"
    assert out["unknown_probability_preserved"][0]["priority"] is None

def test_fresh_reality_filtered_before_authority():
    z=A("zero", {"P1"}, 2, 1.0, zero_reality=True)
    r=A("fresh", {"P2"}, 1, 1.0, zero_reality=False)
    out=compile_frontier([z,r], allow_fresh_reality=False)
    ids=[x["action_id"] for x in out["ranked_known_probability"]]
    assert ids == ["zero"]

def test_dominance_requires_same_reality_class_and_known_bounds():
    sup=A("sup", {"P1","P2"}, 2, 0.8)
    sub=A("sub", {"P1"}, 3, 0.8)
    assert strictly_dominates(sup, sub)
    out=compile_frontier([sup,sub])
    assert out["dominated"] == ["sub"]

def test_unknown_never_dominates_known():
    u=A("u", {"P1","P2"}, 1, None)
    k=A("k", {"P1"}, 2, 0.5)
    assert not strictly_dominates(u,k)
    out=compile_frontier([u,k])
    assert not out["dominated"]

def test_priority_rewards_fanout_and_deletion():
    a=A("a", {"P1"}, 10, 1.0, downstream_action_deletion=1)
    b=A("b", {"P1","P2"}, 10, 1.0, downstream_action_deletion=2)
    assert priority(b) > priority(a)

def test_correlation_penalty_reduces_priority():
    a=A("a", {"P1"}, 10, 1.0, correlation_penalty=0)
    b=A("b", {"P2"}, 10, 1.0, correlation_penalty=1)
    assert priority(a) > priority(b)

def test_next_actions_parallel_tie():
    a=A("a", {"P1"}, 10, 1.0)
    b=A("b", {"P2"}, 10, 1.0)
    out=compile_frontier([a,b])
    assert next_actions(out) == ["a","b"]

def test_inadmissible_excluded():
    x=A("x", {"P1"}, 1, 1.0, admissible=False)
    out=compile_frontier([x])
    assert out["inadmissible"] == ["x"]
    assert next_actions(out) == []
