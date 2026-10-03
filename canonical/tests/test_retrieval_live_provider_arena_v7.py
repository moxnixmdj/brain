from canonical.runtime import retrieval_live_provider_arena_v7 as a

a.validate_tasks()
assert len(a.TASKS)==18
assert len({x["case_id"] for x in a.TASKS})==13

for row in a.TASKS:
    assert str(row["target"]).casefold() not in str(row["query"]).casefold()

for case in ("XLANG_COMPUTER_VISION","XLANG_MACHINE_LEARNING","XLANG_ASYNC_WEB_API"):
    rows=[x for x in a.TASKS if x["case_id"]==case]
    assert len(rows)==2
    assert {x["query_family"] for x in rows}=={
        "NATIVE_ONLY_V11","NATIVE_PLUS_TECHNICAL_ANCHOR_V11"
    }

# Deterministic transport stub: each frozen query returns its answer-key target.
query_target={x["query"]:x["target"] for x in a.TASKS}
old=dict(a.PROVIDERS)
def fake(query,*,limit=10,timeout=20.0):
    return [query_target[query]]
try:
    for key in list(a.PROVIDERS):
        a.PROVIDERS[key]=fake
    out=a.run()
finally:
    a.PROVIDERS.clear(); a.PROVIDERS.update(old)

assert out["event_count"]==18
assert out["unique_labeled_case_count"]==13
assert out["usable_event_count"]==18
assert out["target_hit_event_count"]==18
assert out["target_hit_case_count"]==13
assert out["finite_case_union_recall"]==1.0
assert out["open_world_completeness_claim"] is False
assert out["acceptance_credit_delta"]==0
assert out["execution_authority"] is False

print("test_retrieval_live_provider_arena_v7: PASS")
