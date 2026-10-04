from canonical.runtime import retrieval_fresh_holdout_v20 as h
from canonical.runtime import retrieval_live_provider_arena_v1 as v1
from canonical.runtime import retrieval_live_provider_arena_v11 as v11

def test_holdout_is_fresh_against_prior_live_catalogs():
    prior={str(x["target"]).strip().casefold() for x in [*v1.TASKS,*v11.TASKS]}
    current={str(x["target"]).strip().casefold() for x in h.TASKS}
    assert len(current)==len(h.TASKS)
    assert current.isdisjoint(prior)

def test_answer_keys_do_not_leak_into_queries():
    h.validate()

def test_source_mix():
    providers={x["provider"] for x in h.TASKS}
    assert {"github","npm","crates","nuget","rubygems","packagist"} <= providers
    assert len(h.TASKS)>=14

if __name__=="__main__":
    test_holdout_is_fresh_against_prior_live_catalogs()
    test_answer_keys_do_not_leak_into_queries()
    test_source_mix()
    print("test_retrieval_fresh_holdout_v20: PASS")
