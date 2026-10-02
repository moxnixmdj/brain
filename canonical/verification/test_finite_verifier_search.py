from canonical.runtime.finite_verifier_search import exhaustive_acceptance_search

def test_unique_candidate():
    r = exhaustive_acceptance_search(["a","b","c"], lambda x: x == "b")
    assert r.status == "UNIQUE_ACCEPTED_CANDIDATE"
    assert r.passing == ("b",)

def test_ambiguity_preserved():
    r = exhaustive_acceptance_search([1,2,3,4], lambda x: x % 2 == 0)
    assert r.status == "MULTIPLE_ACCEPTED_CANDIDATES__AMBIGUITY_PRESERVED"
    assert r.passing == (2,4)

def test_no_candidate():
    r = exhaustive_acceptance_search([1,2], lambda x: False)
    assert r.status == "NO_ACCEPTED_CANDIDATE_IN_DECLARED_UNIVERSE"

def test_bound_fail_closed():
    r = exhaustive_acceptance_search([1,2], lambda x: True, max_candidates=1)
    assert r.status == "BOUND_EXCEEDED"
    assert r.complete_over_declared_universe is False

# PR verification trigger: runtime behavior unchanged.
