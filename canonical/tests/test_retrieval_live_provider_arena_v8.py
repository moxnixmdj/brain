from canonical.runtime import retrieval_live_provider_arena_v8 as a

a.validate_cases()
assert len(a.CASES)==7
assert len({x["case_id"] for x in a.CASES})==7
assert all(
    x["query_family"]=="TRANSLATED_TECHNICAL_ANCHOR_ONLY_V12"
    for x in a.CASES[:3]
)

query_repo={x["query"]:x["target_repository"] for x in a.CASES}
old_github=a.base.github
old_npm=a.bridge.npm_metadata
old_crates=a.bridge.crates_metadata

def fake_github(query,*,limit=10,timeout=20.0):
    return [query_repo[query]]

repo_by_package={
    "express":"expressjs/express",
    "webpack":"webpack/webpack",
    "reqwest":"seanmonstar/reqwest",
    "rayon":"rayon-rs/rayon",
}
def fake_npm(package_id,*,timeout=20.0,fetch=None):
    return {"package_id":package_id,"repository_url":"https://github.com/"+repo_by_package[package_id]}
def fake_crates(package_id,*,timeout=20.0,fetch=None):
    return {"package_id":package_id,"repository_url":"https://github.com/"+repo_by_package[package_id]}

try:
    a.base.github=fake_github
    a.bridge.npm_metadata=fake_npm
    a.bridge.crates_metadata=fake_crates
    out=a.run()
finally:
    a.base.github=old_github
    a.bridge.npm_metadata=old_npm
    a.bridge.crates_metadata=old_crates

assert out["case_count"]==7
assert out["usable_case_count"]==7
assert out["recovered_case_count"]==7
assert out["finite_residual_recovery_rate"]==1.0
assert out["miss_case_ids"]==[]
for row in out["observations"]:
    assert row["repository_hit"] is True
    if row["bridge"] is not None:
        assert row["bridge"]["bridge_match"] is True
        assert row["request_count"]==2
    else:
        assert row["request_count"]==1
assert out["open_world_completeness_claim"] is False
assert out["acceptance_credit_delta"]==0
assert out["execution_authority"] is False
print("test_retrieval_live_provider_arena_v8: PASS")
