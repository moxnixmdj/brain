from canonical.runtime import retrieval_registry_miss_recovery_v12 as a

a.validate()
assert len(a.CASES)==12
assert len({x["provider"] for x in a.CASES})==7

orig=dict(a.PROVIDERS)
try:
    def make(provider):
        def f(query,*,limit=50,timeout=20.0):
            for row in a.CASES:
                if row["provider"]==provider and query in row["queries"]:
                    return [row["target"]] if row["episode_id"] in {"NPM_PROCESS_EXEC","CRATE_ERROR","HF_TEXT2TEXT","NUGET_JSON","RUBY_HTTP","PHP_HTTP"} else ["wrong/example"]
            return []
        return f
    for p in list(a.PROVIDERS):
        a.PROVIDERS[p]=make(p)
    out=a.run()
finally:
    a.PROVIDERS.clear();a.PROVIDERS.update(orig)

assert out["baseline_case_count"]==12
assert out["usable_case_count"]==12
assert out["recovered_case_count"]==6
assert out["recovery_rate"]==0.5
assert out["open_world_completeness_claim"] is False
assert out["execution_authority"] is False
print("test_retrieval_registry_miss_recovery_v12: PASS")
