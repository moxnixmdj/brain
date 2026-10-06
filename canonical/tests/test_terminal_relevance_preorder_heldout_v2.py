from __future__ import annotations

from itertools import product

from canonical.runtime.terminal_relevance_preorder_factorization_v1 import (
    RelevancePreorderError,
    exhaustive_monotone_dominates,
    upper_set_dominates,
)
from canonical.runtime.utility_authority_or_behavioral_equivalence_v1 import (
    BehavioralLawError,
    utility_free_dominance_requires_equality,
)


def _preorders(items):
    reflexive={(x,x) for x in items}
    off=[(a,b) for a in items for b in items if a!=b]
    out=[]
    for mask in range(1<<len(off)):
        rel=set(reflexive)
        for i,pair in enumerate(off):
            if mask & (1<<i):
                rel.add(pair)
        transitive=True
        for a,b in rel:
            for c,d in rel:
                if b==c and (a,d) not in rel:
                    transitive=False
                    break
            if not transitive:
                break
        if transitive:
            out.append(rel)
    return out


def _quarter_laws(items):
    n=4
    out=[]
    for counts in product(range(n+1), repeat=len(items)):
        if sum(counts)==n:
            out.append({k:v/n for k,v in zip(items,counts)})
    return out


def test_all_three_state_preorders_agree_upper_sets_vs_monotone_integer_family_on_quarter_grid():
    items=("a","b","c")
    relations=_preorders(items)
    laws=_quarter_laws(items)
    assert len(relations)>1
    assert len(laws)==15
    checked=0
    for geq in relations:
        for brain in laws:
            for opus in laws:
                assert upper_set_dominates(brain,opus,items=items,geq=geq) == exhaustive_monotone_dominates(
                    brain,opus,items=items,geq=geq
                )
                checked+=1
    assert checked >= 3000


def test_invalid_nonreflexive_relation_fails_closed():
    items=("a","b")
    with pytest.raises(RelevancePreorderError):
        upper_set_dominates(
            {"a":0.5,"b":0.5},{"a":0.5,"b":0.5},
            items=items, geq={("a","a"),("a","b")}
        )


def test_invalid_nontransitive_relation_fails_closed():
    items=("a","b","c")
    geq={(x,x) for x in items}|{("a","b"),("b","c")}
    with pytest.raises(RelevancePreorderError):
        upper_set_dominates(
            {"a":1/3,"b":1/3,"c":1/3},{"a":1/3,"b":1/3,"c":1/3},
            items=items, geq=geq
        )


def test_malformed_probability_law_fails_closed():
    items=("a","b")
    geq={("a","a"),("b","b")}
    with pytest.raises(RelevancePreorderError):
        upper_set_dominates({"a":0.8,"b":0.8},{"a":0.5,"b":0.5},items=items,geq=geq)
    with pytest.raises(RelevancePreorderError):
        upper_set_dominates({"a":1.0},{"a":0.5,"b":0.5},items=items,geq=geq)


def test_behavioral_equality_dichotomy_on_all_three_state_quarter_laws():
    items=("a","b","c")
    laws=_quarter_laws(items)
    for brain in laws:
        for opus in laws:
            out=utility_free_dominance_requires_equality(brain,opus)
            same=all(brain[k]==opus[k] for k in items)
            assert out["laws_equal"] is same
            if same:
                assert out["separating_event"] is None
                assert out["utility_authority_required_for_nonidentical_dominance"] is False
            else:
                assert out["opus_strictly_better_on_indicator"] is True
                assert out["utility_authority_required_for_nonidentical_dominance"] is True


def test_behavioral_dichotomy_rejects_malformed_laws():
    with pytest.raises(BehavioralLawError):
        utility_free_dominance_requires_equality({"a":0.2},{"a":1.0})
    with pytest.raises(BehavioralLawError):
        utility_free_dominance_requires_equality({"a":1.1,"b":-0.1},{"a":1.0,"b":0.0})
