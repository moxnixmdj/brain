from canonical.runtime import retrieval_live_provider_arena_v13 as v13

def test_qualifier_removed_before_tokenization():
    q="fast Python linter formatter static analysis in:name,description,readme"
    toks=v13._words(q)
    assert "in" not in [x.casefold() for x in toks]
    assert "name" not in [x.casefold() for x in toks]
    assert "description" not in [x.casefold() for x in toks]

def test_platform_anchor_is_preserved():
    row=next(x for x in v13.selected_rows() if x["episode_id"]=="GITHUB_PY_LINTER")
    qs=v13.generated_queries(row)
    assert qs
    assert any("Python" in q for q in qs)
    assert all(v13.GITHUB_QUALIFIER in q for q in qs)

def test_russian_bridge_is_answer_key_blind():
    row=next(x for x in v13.selected_rows() if x["episode_id"]=="GITHUB_RU_NLP")
    qs=v13.generated_queries(row)
    assert any("Russian" in q and ("morphology" in q or "NLP" in q) for q in qs)
    target=v13.v11._norm(row["target"])
    basename=target.rsplit("/",1)[-1]
    assert all(target not in v13.v11._norm(q) for q in qs)
    assert all(basename not in v13.v11._norm(q) for q in qs)

def test_npm_morphology_adds_execution():
    row=next(x for x in v13.selected_rows() if x["episode_id"]=="NPM_PROCESS_EXEC")
    qs=v13.generated_queries(row)
    assert any("execution" in q.casefold() for q in qs)

def test_pom_coordinate_direct_and_parent_group():
    direct="""<project><groupId>com.example</groupId><artifactId>thing</artifactId></project>"""
    inherited="""<project><parent><groupId>org.example</groupId><artifactId>parent</artifactId></parent><artifactId>child</artifactId></project>"""
    assert v13.parse_pom_coordinates(direct)==["com.example:thing"]
    assert v13.parse_pom_coordinates(inherited)==["org.example:child"]

def test_pom_unresolved_property_rejected():
    xml="""<project><groupId>${project.groupId}</groupId><artifactId>child</artifactId></project>"""
    assert v13.parse_pom_coordinates(xml)==[]

def test_all_generated_queries_hide_answer_key():
    v13.validate()

def test_simple_union_monotonic():
    calls=[]
    def provider(q,*,limit,timeout):
        calls.append(q)
        return ["a","b"] if len(calls)==1 else ["b","c"]
    out=v13._run_simple(["q1","q2"],provider,limit=5,timeout=1)
    assert out["candidate_ids"]==["a","b","c"]
    assert out["failed_request_count"]==0

if __name__=="__main__":
    test_qualifier_removed_before_tokenization()
    test_platform_anchor_is_preserved()
    test_russian_bridge_is_answer_key_blind()
    test_npm_morphology_adds_execution()
    test_pom_coordinate_direct_and_parent_group()
    test_pom_unresolved_property_rejected()
    test_all_generated_queries_hide_answer_key()
    test_simple_union_monotonic()
    print("test_retrieval_live_provider_arena_v13: PASS")
