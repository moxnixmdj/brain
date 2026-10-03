from canonical.runtime import retrieval_live_provider_arena_v3 as a

a.validate_cases()

for row in a.CASES:
    target=row["target"].casefold()
    assert all(target not in q.casefold() for q in row["queries"])
    assert len(row["queries"])>=2

print("test_retrieval_live_provider_arena_v3: PASS")
