from canonical.runtime import retrieval_live_provider_arena_v6 as a

a.validate()
assert a.CASE["target_repo"].casefold() not in " ".join(a.CASE["queries"]).casefold()
assert a.CASE["target_package"].casefold() not in " ".join(a.CASE["queries"]).casefold()
assert len(a.CASE["queries"])==4
assert a.CASE["strategy_id"]=="GITHUB_BEHAVIOR_LATTICE_V6"

print("test_retrieval_live_provider_arena_v6: PASS")
