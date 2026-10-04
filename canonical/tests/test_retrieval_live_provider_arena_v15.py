from canonical.runtime import retrieval_live_provider_arena_v15 as v15

def test_queries_are_answer_key_blind():
    v15.validate()

def test_guava_hierarchy_queries_are_generic():
    qs=v15.guava_behavior_queries("Java collections caching primitives utilities")
    j=" ".join(qs).casefold()
    assert "core libraries" in j
    assert "guava" not in j
    assert "google" not in j

def test_github_url_canonicalization():
    assert v15.github_repo_from_url("https://github.com/google/guava")== "google/guava"
    assert v15.github_repo_from_url("https://github.com/google/guava/blob/master/README.md")== "google/guava"
    assert v15.github_repo_from_url("https://example.com/google/guava") is None

def test_version_line_branch_selection():
    old=v15.v13._github_json
    def fake(url,*,timeout):
        return [
          {"name":"feature/x","commit":{"sha":"x"}},
          {"name":"3.x","commit":{"sha":"3"}},
          {"name":"2.x","commit":{"sha":"2"}},
          {"name":"2.22","commit":{"sha":"22"}},
        ]
    v15.v13._github_json=fake
    try:rows=v15.version_line_branches("a/b",timeout=1,max_branches=8)
    finally:v15.v13._github_json=old
    assert [x[0] for x in rows][:2]==["2.x","3.x"]
    assert "2.22" in [x[0] for x in rows]

def test_root_pom_coordinate_uses_existing_parser():
    import base64
    xml=b"<project><groupId>com.example</groupId><artifactId>thing</artifactId></project>"
    old=v15.v13._github_json
    v15.v13._github_json=lambda url,timeout:{"encoding":"base64","content":base64.b64encode(xml).decode()}
    try:coords=v15.root_pom_coordinate("a/b","2.x",timeout=1)
    finally:v15.v13._github_json=old
    assert coords==["com.example:thing"]

if __name__=="__main__":
    test_queries_are_answer_key_blind()
    test_guava_hierarchy_queries_are_generic()
    test_github_url_canonicalization()
    test_version_line_branch_selection()
    test_root_pom_coordinate_uses_existing_parser()
    print("test_retrieval_live_provider_arena_v15: PASS")
