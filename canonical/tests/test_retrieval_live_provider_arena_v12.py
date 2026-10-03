from canonical.runtime import retrieval_live_provider_arena_v12 as v12

def test_query_variants_are_answer_key_blind():
    v12.validate_tasks()
    for row in v12.selected_tasks():
        target=v12.v11._norm(row["target"])
        basename=target.rsplit("/",1)[-1].rsplit(":",1)[-1]
        qs=v12.query_variants(row)
        assert qs
        assert len(qs)<=6
        for q in qs:
            nq=v12.v11._norm(q)
            assert target not in nq
            if len(basename)>=4:
                assert basename not in nq

def test_multilingual_variants_preserve_native_script():
    row=next(x for x in v12.selected_tasks() if x["episode_id"]=="GITHUB_ZH_SEGMENTATION")
    qs=v12.query_variants(row)
    assert any("中文" in q or "分词" in q for q in qs)
    assert all("in:name,description,readme" in q for q in qs)

def test_registry_variants_compress_behavior():
    row=next(x for x in v12.selected_tasks() if x["episode_id"]=="MAVEN_JSON_BIND")
    qs=v12.query_variants(row)
    assert any(len(q.split()) < len(row["query"].split()) for q in qs)

def test_union_is_monotonic_and_late_hit_counts():
    row=next(x for x in v12.selected_tasks() if x["episode_id"]=="NPM_PROCESS_EXEC")
    calls=[]
    target=v12.v11._norm(row["target"])
    def fake_provider(query,*,limit,timeout):
        calls.append(query)
        if len(calls)==2:
            return ["irrelevant",target]
        return ["irrelevant"]
    old=v12.v11.PROVIDERS[row["provider"]]
    v12.v11.PROVIDERS[row["provider"]]=fake_provider
    try:
        event=v12._run_provider_group([(1,row)],timeout=1.0)[0]
    finally:
        v12.v11.PROVIDERS[row["provider"]]=old
    assert event["target_hit"] is True
    assert target in event["candidate_ids"]
    assert event["candidate_ids"].count("irrelevant")==1
    assert event["request_count"]==len(v12.query_variants(row))
    assert event["answer_key_used_for_query_generation"] is False

def test_failed_one_variant_does_not_fail_episode():
    row=next(x for x in v12.selected_tasks() if x["episode_id"]=="NPM_PROCESS_EXEC")
    n={"i":0}
    def fake_provider(query,*,limit,timeout):
        n["i"]+=1
        if n["i"]==1:
            raise TimeoutError("retry")
        return ["something"]
    old=v12.v11.PROVIDERS[row["provider"]]
    v12.v11.PROVIDERS[row["provider"]]=fake_provider
    try:
        event=v12._run_provider_group([(1,row)],timeout=1.0)[0]
    finally:
        v12.v11.PROVIDERS[row["provider"]]=old
    assert event["status"]=="SUCCESS"
    assert event["failed_request_count"]==1

if __name__=="__main__":
    test_query_variants_are_answer_key_blind()
    test_multilingual_variants_preserve_native_script()
    test_registry_variants_compress_behavior()
    test_union_is_monotonic_and_late_hit_counts()
    test_failed_one_variant_does_not_fail_episode()
    print("test_retrieval_live_provider_arena_v12: PASS")
