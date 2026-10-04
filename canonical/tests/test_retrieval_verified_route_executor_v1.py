from canonical.runtime import retrieval_verified_route_executor_v1 as x

def action(route,query="Java collections caching utilities"):
    return {
        "action":"VERIFIED_RECOVERY_ROUTE",
        "action_id":"A1",
        "source_id":"MAVEN_CENTRAL_SEARCH",
        "provider_route":"MAVEN_CENTRAL_SEARCH",
        "strategy_id":route,
        "query":query,
        "answer_key_identity_permitted":False,
    }

def test_multiquery_compiles_children():
    out=x.execute(action("MULTI_QUERY_DECOMPOSITION"),timeout=1)
    assert out["status"]=="CHILD_QUERY_ACTIONS_COMPILED"
    assert len(out["child_query_actions"])>=2
    assert all(r["candidate_authority"]=="CANDIDATE_ONLY" for r in out["child_query_actions"])

def test_answer_key_policy_required():
    a=action("MULTI_QUERY_DECOMPOSITION")
    a["answer_key_identity_permitted"]=True
    try:
        x.execute(a,timeout=1)
        raise AssertionError("answer-key policy bypassed")
    except ValueError as e:
        assert "ANSWER_KEY_IDENTITY_POLICY_REQUIRED" in str(e)

def test_graph_dispatch_candidate_only():
    old_union=x.v14.repo_union
    old_graph=x.v16.graph_snowball
    old_pom=x.v13.repository_pom_coordinates
    try:
        x.v14.repo_union=lambda queries,limit_per_query=10,timeout=1:(["seed/repo"],[])
        x.v16.graph_snowball=lambda query,seeds,timeout=1,max_seed_repos=8,max_links_per_seed=24:(["linked/repo"],[])
        x.v13.repository_pom_coordinates=lambda repo,timeout=1,max_poms=20:(
            ["com.example:thing"] if repo=="linked/repo" else [],{"repository":repo,"pom_files":[]}
        )
        out=x.execute(action("BEHAVIOR_CONTEXT_CANDIDATE_GRAPH_SNOWBALL"),timeout=1)
        assert [c["candidate_id"] for c in out["candidates"]]==["com.example:thing"]
        assert out["candidates"][0]["sufficiency_status"]=="UNVERIFIED"
        assert out["nonexistence_claim_authorized"] is False
    finally:
        x.v14.repo_union=old_union
        x.v16.graph_snowball=old_graph
        x.v13.repository_pom_coordinates=old_pom

def test_history_dispatch_candidate_only():
    old_union=x.v14.repo_union
    old_hist=x.v18.historical_coordinates
    try:
        x.v14.repo_union=lambda queries,limit_per_query=10,timeout=1:(["repo/a"],[])
        x.v18.historical_coordinates=lambda repo,timeout=1,max_pages=3,max_per_major=2,max_poms=20:{
            "repository":repo,"coordinates":["old.group:artifact"],"selected_tags":[],"probes":[]
        }
        out=x.execute(action("VERSION_LINE_HISTORY_IDENTITY_BRIDGE","Java JSON object data binding"),timeout=1)
        assert [c["candidate_id"] for c in out["candidates"]]==["old.group:artifact"]
        assert out["execution_authority"] is False
        assert out["promotion_authority"] is False
    finally:
        x.v14.repo_union=old_union
        x.v18.historical_coordinates=old_hist

def test_unverified_route_rejected():
    try:
        x.execute(action("MAGIC_ROUTE"),timeout=1)
        raise AssertionError("unverified route accepted")
    except ValueError as e:
        assert "UNVERIFIED_ROUTE_FORBIDDEN" in str(e)

if __name__=="__main__":
    test_multiquery_compiles_children()
    test_answer_key_policy_required()
    test_graph_dispatch_candidate_only()
    test_history_dispatch_candidate_only()
    test_unverified_route_rejected()
    print("test_retrieval_verified_route_executor_v1: PASS")
