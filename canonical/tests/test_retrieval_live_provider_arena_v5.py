from canonical.runtime import retrieval_live_provider_arena_v5 as a

a.validate_cases()
assert len(a.CASES)==5
for row in a.CASES:
    q=row["query"].casefold()
    assert row["target_repo"].casefold() not in q
    assert row["target_package"].casefold() not in q
    assert row["strategy_id"]=="CROSS_ECOSYSTEM_REPO_BRIDGE_V5"

print("test_retrieval_live_provider_arena_v5: PASS")
