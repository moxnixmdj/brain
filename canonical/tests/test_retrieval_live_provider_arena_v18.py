from canonical.runtime import retrieval_live_provider_arena_v18 as v18

def test_semver_ignores_rc_suffix_number():
    assert v18.semantic_version_key("jackson-databind-3.0.0-rc10")== (3,0,0)
    assert v18.semantic_version_key("release-2.18.4")== (2,18,4)

def test_representative_tags_use_real_major_lines():
    rows=[
        {"name":"jackson-databind-3.0.0-rc10","commit_sha":"a","source_page":1},
        {"name":"jackson-databind-3.0.0-rc9","commit_sha":"b","source_page":1},
        {"name":"jackson-databind-2.20.1","commit_sha":"c","source_page":2},
        {"name":"jackson-databind-2.19.4","commit_sha":"d","source_page":2},
    ]
    got=v18.representative_tags(rows,max_tags=12)
    majors={x["version_major"] for x in got}
    assert 3 in majors and 2 in majors
    assert 10 not in majors and 9 not in majors

def test_paginated_tags_stops_on_short_page():
    old=v18.v17.v13._github_json
    calls=[]
    def fake(url,timeout=1):
        calls.append(url)
        if "page=1" in url:
            return [{"name":"v3.0.0","commit":{"sha":"a"}}]*100
        if "page=2" in url:
            return [{"name":"v2.0.0","commit":{"sha":"b"}}]
        return []
    v18.v17.v13._github_json=fake
    try:
        rows=v18.paginated_tags("org/repo",timeout=1,max_pages=5,per_page=100)
    finally:
        v18.v17.v13._github_json=old
    assert len(calls)==2
    assert any(x["name"]=="v2.0.0" for x in rows)

def test_validate_answer_key_blind():
    v18.validate()

if __name__=="__main__":
    test_semver_ignores_rc_suffix_number()
    test_representative_tags_use_real_major_lines()
    test_paginated_tags_stops_on_short_page()
    test_validate_answer_key_blind()
    print("test_retrieval_live_provider_arena_v18: PASS")
