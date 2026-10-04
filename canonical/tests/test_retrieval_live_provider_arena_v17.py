from canonical.runtime import retrieval_live_provider_arena_v17 as v17

def test_queries_are_answer_key_blind():
    v17.validate()
    row=v17.row()
    target=v17.v11._norm(row["target"])
    for q in v17.v14.maven_behavior_queries(str(row["query"])):
        assert target not in v17.v11._norm(q)

def test_lineage_uses_only_discovered_artifact_id():
    calls=[]
    def fake(url,*,timeout):
        calls.append(url)
        return {"response":{"docs":[
            {"id":"tools.jackson.core:jackson-databind"},
            {"id":"com.fasterxml.jackson.core:jackson-databind"},
        ]}}
    old=v17.v13.base._url_json
    v17.v13.base._url_json=fake
    try:
        aliases,traces=v17.artifact_lineage(
            ["tools.jackson.core:jackson-databind"],timeout=1,limit=20
        )
    finally:
        v17.v13.base._url_json=old
    assert "com.fasterxml.jackson.core:jackson-databind" in aliases
    assert len(calls)==1
    assert 'jackson-databind' in traces[0]["query"]
    assert "com.fasterxml" not in traces[0]["query"]

def test_lineage_dedupes_artifact_ids():
    calls=[]
    def fake(url,*,timeout):
        calls.append(url)
        return {"response":{"docs":[]}}
    old=v17.v13.base._url_json
    v17.v13.base._url_json=fake
    try:
        v17.artifact_lineage(
            ["g1:alpha-artifact","g2:alpha-artifact","g3:beta-artifact"],
            timeout=1,limit=20
        )
    finally:
        v17.v13.base._url_json=old
    assert len(calls)==2

if __name__=="__main__":
    test_queries_are_answer_key_blind()
    test_lineage_uses_only_discovered_artifact_id()
    test_lineage_dedupes_artifact_ids()
    print("test_retrieval_live_provider_arena_v17: PASS")
