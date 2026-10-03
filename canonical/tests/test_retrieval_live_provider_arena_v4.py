from canonical.runtime import retrieval_live_provider_arena_v4 as a

a.validate_cases()
assert len(a.CASES)==5
for row in a.CASES:
    assert row["target"].casefold() not in row["query"].casefold()
    assert row["strategy_id"]=="DEEP_WINDOW_50_V4"

print("test_retrieval_live_provider_arena_v4: PASS")
