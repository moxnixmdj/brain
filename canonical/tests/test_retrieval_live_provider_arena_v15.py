from canonical.runtime import retrieval_live_provider_arena_v15 as v15

def test_atomic_queries_are_answer_key_blind():
    for row in v15.rows():
        target=v15.v11._norm(row["target"])
        basename=target.rsplit(":",1)[-1]
        for q in v15.atomic_behavior_queries(str(row["query"])):
            nq=v15.v11._norm(q)
            assert target not in nq
            assert basename not in nq

def test_collections_atomic_queries_reduce_conjunction_pressure():
    qs=v15.atomic_behavior_queries("Java collections caching primitives utilities")
    joined=" | ".join(qs).casefold()
    assert "java core libraries" in joined
    assert "java caching library" in joined
    assert "guava" not in joined

def test_json_atomic_queries_expand_without_target_name():
    qs=v15.atomic_behavior_queries("Java JSON object data binding")
    joined=" | ".join(qs).casefold()
    assert "java json data binding" in joined
    assert "java object mapping json" in joined
    assert "jackson" not in joined

def test_maven_artifact_lineage_uses_only_discovered_artifact_id():
    calls=[]
    def fake(url,*,timeout):
        calls.append(url)
        if "jackson-databind" in url:
            return {"response":{"docs":[
                {"id":"tools.jackson.core:jackson-databind"},
                {"id":"com.fasterxml.jackson.core:jackson-databind"},
            ]}}
        return {"response":{"docs":[]}}
    old=v15.v13.base._url_json
    v15.v13.base._url_json=fake
    try:
        aliases,traces=v15.maven_artifact_lineage(
            ["tools.jackson.core:jackson-databind"],timeout=1,max_queries=4,limit=20
        )
    finally:
        v15.v13.base._url_json=old
    assert "com.fasterxml.jackson.core:jackson-databind" in aliases
    assert traces[0]["artifact_id"]=="jackson-databind"
    assert len(calls)==1

def test_lineage_dedupes_artifact_queries():
    count=0
    def fake(url,*,timeout):
        nonlocal count
        count+=1
        return {"response":{"docs":[]}}
    old=v15.v13.base._url_json
    v15.v13.base._url_json=fake
    try:
        v15.maven_artifact_lineage(
            ["g1:alpha","g2:alpha","g3:beta"],timeout=1,max_queries=10,limit=20
        )
    finally:
        v15.v13.base._url_json=old
    assert count==2

if __name__=="__main__":
    test_atomic_queries_are_answer_key_blind()
    test_collections_atomic_queries_reduce_conjunction_pressure()
    test_json_atomic_queries_expand_without_target_name()
    test_maven_artifact_lineage_uses_only_discovered_artifact_id()
    test_lineage_dedupes_artifact_queries()
    print("test_retrieval_live_provider_arena_v15: PASS")
