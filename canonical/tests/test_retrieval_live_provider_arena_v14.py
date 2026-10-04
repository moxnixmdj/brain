from canonical.runtime import retrieval_live_provider_arena_v14 as v14

def test_aliases_are_behavior_derived():
    q=v14.maven_behavior_queries("Java collections caching primitives utilities")
    joined=" ".join(q).casefold()
    assert "core libraries" in joined
    assert "cache" in joined
    assert "guava" not in joined

def test_json_and_logging_queries_expand():
    jq=" ".join(v14.maven_behavior_queries("Java JSON object data binding")).casefold()
    lq=" ".join(v14.maven_behavior_queries("Java logging facade API")).casefold()
    assert "json data binding" in jq
    assert "logging abstraction" in lq

def test_all_queries_hide_answer_key():
    v14.validate()

def test_union_is_monotonic():
    calls=[]
    old=v14.v13.base.github
    def fake(q,*,limit,timeout):
        calls.append(q)
        return ["a/b","c/d"] if len(calls)==1 else ["c/d","e/f"]
    v14.v13.base.github=fake
    try:
        repos,traces=v14.repo_union(["q1","q2"],limit_per_query=3,timeout=1)
    finally:
        v14.v13.base.github=old
    assert repos==["a/b","c/d","e/f"]
    assert len(traces)==2

def test_manifest_coordinate_parser_reused():
    xml="<project><parent><groupId>org.example</groupId><artifactId>parent</artifactId></parent><artifactId>child</artifactId></project>"
    assert v14.v13.parse_pom_coordinates(xml)==["org.example:child"]

if __name__=="__main__":
    test_aliases_are_behavior_derived()
    test_json_and_logging_queries_expand()
    test_all_queries_hide_answer_key()
    test_union_is_monotonic()
    test_manifest_coordinate_parser_reused()
    print("test_retrieval_live_provider_arena_v14: PASS")
