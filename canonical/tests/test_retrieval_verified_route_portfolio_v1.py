from pathlib import Path
from canonical.runtime import retrieval_verified_route_portfolio_v1 as p
from canonical.runtime import global_retrieval_entrypoint_v4 as e

def _maven():
    return (
        [{
            "action_id":"Q1",
            "source_id":"MAVEN_CENTRAL_SEARCH",
            "provider_route":"MAVEN_CENTRAL_SEARCH",
            "query":"Java JSON object data binding behavior",
            "strategy_id":"BEHAVIOR_ANCHOR",
        }],
        [{
            "source_id":"MAVEN_CENTRAL_SEARCH",
            "ecosystem":"MAVEN",
            "upstream_group":"MAVEN_CENTRAL_API",
        }],
    )

def test_maven_gets_verified_fallbacks():
    q,s=_maven()
    out=p.compile_portfolio(q,s)
    routes={x["strategy_id"] for x in out["actions"]}
    assert "MULTI_QUERY_DECOMPOSITION" in routes
    assert "BEHAVIOR_CONTEXT_CANDIDATE_GRAPH_SNOWBALL" in routes
    assert "REPOSITORY_MANIFEST_BRIDGE" in routes
    assert "DEEP_MANIFEST_INSPECTION" in routes
    assert "VERSION_LINE_HISTORY_IDENTITY_BRIDGE" in routes
    assert out["answer_key_identity_permitted"] is False

def test_target_identity_absent_from_generated_actions():
    q,s=_maven()
    target="com.fasterxml.jackson.core:jackson-databind"
    out=p.compile_portfolio(q,s)
    text=str(out).casefold()
    assert target.casefold() not in text
    assert "answer_key_identity_permitted': false" in text or '"answer_key_identity_permitted": false' in text

def test_non_maven_repo_gets_graph_not_history():
    q=[{
        "action_id":"Q2","source_id":"GITHUB_REPOSITORY_SEARCH",
        "query":"fast Python linter formatter static analysis",
    }]
    s=[{"source_id":"GITHUB_REPOSITORY_SEARCH","kind":"repository"}]
    routes={x["strategy_id"] for x in p.compile_portfolio_actions(q,s)}
    assert "BEHAVIOR_CONTEXT_CANDIDATE_GRAPH_SNOWBALL" in routes
    assert "VERSION_LINE_HISTORY_IDENTITY_BRIDGE" not in routes

def test_multilingual_signal_gets_bridge():
    q=[{
        "action_id":"Q3","source_id":"GITHUB_REPOSITORY_SEARCH",
        "query":"обработка русского языка морфология Python",
        "script":"CYRILLIC",
    }]
    s=[{"source_id":"GITHUB_REPOSITORY_SEARCH","kind":"repository"}]
    routes={x["strategy_id"] for x in p.compile_portfolio_actions(q,s)}
    assert "CROSS_LANGUAGE_TECHNICAL_BRIDGE" in routes

def test_entrypoint_v4_compiles_portfolio():
    root=Path(__file__).resolve().parents[2]
    q,s=_maven()
    out=e.compile_authorized_plan(root=root,query_actions=q,sources=s)
    assert out["status"]=="PASS__AUTHORIZED_EMPIRICAL_PLAN_WITH_VERIFIED_RECOVERY_PORTFOLIO",out
    routes={x["strategy_id"] for x in out["route_portfolio"]["actions"]}
    assert "VERSION_LINE_HISTORY_IDENTITY_BRIDGE" in routes
    assert out["plan"]["open_world_nonexistence_claim_authorized"] is False
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False

if __name__=="__main__":
    test_maven_gets_verified_fallbacks()
    test_target_identity_absent_from_generated_actions()
    test_non_maven_repo_gets_graph_not_history()
    test_multilingual_signal_gets_bridge()
    test_entrypoint_v4_compiles_portfolio()
    print("test_retrieval_verified_route_portfolio_v1: PASS")
