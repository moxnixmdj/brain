from canonical.runtime import retrieval_live_provider_arena_v17 as v17

def test_version_key():
    assert v17.version_key("jackson-databind-2.20.0")[0]==2
    assert v17.version_key("v3.0.1")[0]==3
    assert v17.version_key("release")==(None,None,None)

def test_representative_tags_preserve_major_diversity():
    rows=[
        {"name":"v3.1.0","commit_sha":"a"},
        {"name":"v3.0.0","commit_sha":"b"},
        {"name":"v2.20.0","commit_sha":"c"},
        {"name":"v2.19.0","commit_sha":"d"},
        {"name":"v1.9.0","commit_sha":"e"},
    ]
    got=v17.representative_tags(rows,max_tags=12)
    majors={x["version_major"] for x in got}
    assert {1,2,3}.issubset(majors)

def test_history_route_is_target_parameter_free():
    import inspect
    for fn in (v17.tags,v17.representative_tags,v17.current_pom_paths,v17.historical_coordinates):
        assert "target" not in str(inspect.signature(fn)).casefold()

def test_validate_answer_key_blind():
    v17.validate()

def test_historical_coordinates_unions_current_and_old():
    old_paths=v17.current_pom_paths
    old_tags=v17.tags
    old_file=v17.file_at_ref
    try:
        v17.current_pom_paths=lambda repo,timeout=1,max_poms=20:(
            ["pom.xml"],
            {"pom_files":[{"path":"pom.xml","coordinates":["tools.example:thing"]}]}
        )
        v17.tags=lambda repo,timeout=1,per_page=100:[
            {"name":"v3.0.0","commit_sha":"a"},
            {"name":"v2.9.0","commit_sha":"b"},
        ]
        docs={
            "v3.0.0":"<project><groupId>tools.example</groupId><artifactId>thing</artifactId></project>",
            "v2.9.0":"<project><groupId>com.example</groupId><artifactId>thing</artifactId></project>",
        }
        v17.file_at_ref=lambda repo,path,ref,timeout=1:docs.get(ref,"")
        coords,trace=v17.historical_coordinates("org/repo",timeout=1)
    finally:
        v17.current_pom_paths=old_paths
        v17.tags=old_tags
        v17.file_at_ref=old_file
    assert "tools.example:thing" in coords
    assert "com.example:thing" in coords
    assert len(trace["selected_tags"])>=2

if __name__=="__main__":
    test_version_key()
    test_representative_tags_preserve_major_diversity()
    test_history_route_is_target_parameter_free()
    test_validate_answer_key_blind()
    test_historical_coordinates_unions_current_and_old()
    print("test_retrieval_live_provider_arena_v17: PASS")
