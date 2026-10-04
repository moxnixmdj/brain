from canonical.runtime import retrieval_live_provider_arena_v17 as v17

def test_validate_answer_key_blind_queries():
    v17.validate()

def test_historical_coordinate_extraction_is_target_free():
    import inspect
    sig=str(inspect.signature(v17.historical_pom_coordinates))
    assert "target" not in sig
    sig2=str(inspect.signature(v17._tag_names))
    assert "target" not in sig2

def test_tag_deduplication():
    old=v17.v13._github_json
    try:
        v17.v13._github_json=lambda url,timeout=1:[
            {"name":"v3.0.0"},{"name":"v2.20.0"},{"name":"v2.20.0"}
        ] if "/tags?" in url else {}
        assert v17._tag_names("x/y",timeout=1)==["v3.0.0","v2.20.0"]
    finally:
        v17.v13._github_json=old

def test_historical_union_recovers_versioned_identity():
    old_tags=v17._tag_names
    old_file=v17._file_content
    try:
        v17._tag_names=lambda repo,timeout=1,per_page=100:["v3.0.0","v2.20.0"]
        docs={
            ("x/y","pom.xml","v3.0.0"):"""<project><groupId>tools.jackson.core</groupId><artifactId>jackson-databind</artifactId></project>""",
            ("x/y","pom.xml","v2.20.0"):"""<project><groupId>com.fasterxml.jackson.core</groupId><artifactId>jackson-databind</artifactId></project>""",
        }
        v17._file_content=lambda repo,path,ref,timeout=1:docs[(repo,path,ref)]
        coords,traces=v17.historical_pom_coordinates("x/y",timeout=1,max_tags=10)
        assert "tools.jackson.core:jackson-databind" in coords
        assert "com.fasterxml.jackson.core:jackson-databind" in coords
        assert len(traces)==2
    finally:
        v17._tag_names=old_tags
        v17._file_content=old_file

if __name__=="__main__":
    test_validate_answer_key_blind_queries()
    test_historical_coordinate_extraction_is_target_free()
    test_tag_deduplication()
    test_historical_union_recovers_versioned_identity()
    print("test_retrieval_live_provider_arena_v17: PASS")
