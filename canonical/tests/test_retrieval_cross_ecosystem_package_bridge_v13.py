from canonical.runtime import retrieval_cross_ecosystem_package_bridge_v13 as a

a.validate()
assert a.parse_maven("<project><groupId>g</groupId><artifactId>a</artifactId></project>")==["g:a"]
assert a.parse_nuget("<Project><PropertyGroup><PackageId>X.Y</PackageId></PropertyGroup></Project>","x.csproj")==["X.Y"]
assert a.parse_nuget("<Project></Project>","src/Foo/Foo.csproj")==["Foo"]
assert a.parse_rubygems('spec.name = "faraday"')==["faraday"]
assert a.parse_composer('{"name":"guzzlehttp/guzzle"}')==["guzzlehttp/guzzle"]

orig_github=a.base.github
orig_bridge=a.bridge
try:
    def fake_github(q,*,limit=30,timeout=20.0):
        for row in a.CASES:
            if q in row["queries"]:
                return [row["target_repo"]]
        return []
    def fake_bridge(repo,ecosystem,timeout=20.0):
        row=next(x for x in a.CASES if x["target_repo"].casefold()==repo.casefold())
        return {"default_branch":"main","tree_truncated":False,"manifest_count":1,"manifest_rows":[],"package_identities":[row["target_package"]]}
    a.base.github=fake_github
    a.bridge=fake_bridge
    out=a.run()
finally:
    a.base.github=orig_github
    a.bridge=orig_bridge

assert out["repository_hit_count"]==8
assert out["verified_package_recovery_count"]==8
assert out["verified_package_recovery_rate"]==1.0
assert out["open_world_completeness_claim"] is False
print("test_retrieval_cross_ecosystem_package_bridge_v13: PASS")
