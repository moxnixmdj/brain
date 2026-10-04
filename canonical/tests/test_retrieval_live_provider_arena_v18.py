from canonical.runtime import retrieval_live_provider_arena_v18 as v18

def test_semver_ignores_rc_suffix_digits():
    assert v18.semantic_version_from_tag("jackson-databind-3.0.0-rc10")== (3,0,0)
    assert v18.semantic_version_from_tag("jackson-databind-2.20.1")== (2,20,1)
    assert v18.semantic_version_from_tag("v1.2")== (1,2,None)

def test_major_line_selection_preserves_old_major():
    tags=[
        {"name":"x-3.0.0-rc10","version_major":3},
        {"name":"x-3.0.0-rc9","version_major":3},
        {"name":"x-3.0.0-rc8","version_major":3},
        {"name":"x-2.20.1","version_major":2},
        {"name":"x-2.19.4","version_major":2},
        {"name":"x-1.9.0","version_major":1},
    ]
    selected=v18.select_version_line_tags(tags,max_per_major=1)
    assert [x["version_major"] for x in selected[:3]]==[3,2,1]

def test_validate_answer_key_blind_queries():
    v18.validate()

def test_history_functions_are_target_parameter_free():
    import inspect
    for fn in [v18.list_tags,v18.select_version_line_tags,v18.historical_coordinates]:
        assert "target" not in str(inspect.signature(fn))

def test_historical_coords_cross_major_lines():
    old_list=v18.list_tags
    old_paths=v18.repository_pom_paths
    old_pom=v18.pom_at_ref
    try:
        v18.list_tags=lambda repo,timeout=1,max_pages=3:[
            {"name":"jackson-databind-3.0.0-rc10","version_major":3},
            {"name":"jackson-databind-2.20.1","version_major":2},
        ]
        v18.repository_pom_paths=lambda repo,timeout=1,max_poms=20:["pom.xml"]
        docs={
            "jackson-databind-3.0.0-rc10":"<project><groupId>tools.jackson.core</groupId><artifactId>jackson-databind</artifactId></project>",
            "jackson-databind-2.20.1":"<project><groupId>com.fasterxml.jackson.core</groupId><artifactId>jackson-databind</artifactId></project>",
        }
        v18.pom_at_ref=lambda repo,path,ref,timeout=1:docs[ref]
        out=v18.historical_coordinates("FasterXML/jackson-databind",timeout=1,max_per_major=1)
        assert "tools.jackson.core:jackson-databind" in out["coordinates"]
        assert "com.fasterxml.jackson.core:jackson-databind" in out["coordinates"]
    finally:
        v18.list_tags=old_list
        v18.repository_pom_paths=old_paths
        v18.pom_at_ref=old_pom

if __name__=="__main__":
    test_semver_ignores_rc_suffix_digits()
    test_major_line_selection_preserves_old_major()
    test_validate_answer_key_blind_queries()
    test_history_functions_are_target_parameter_free()
    test_historical_coords_cross_major_lines()
    print("test_retrieval_live_provider_arena_v18: PASS")
