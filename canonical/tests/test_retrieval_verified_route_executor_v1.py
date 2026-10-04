from pathlib import Path
from canonical.runtime import retrieval_verified_route_executor_v1 as x

def test_forbids_answer_key_fields():
    try:
        x.execute_request(
            root=Path("."),
            query_action={"action_id":"q","source_id":"GITHUB_REPOSITORY_SEARCH","query":"behavior","target":"secret/repo"},
            source={"source_id":"GITHUB_REPOSITORY_SEARCH","provider":"github"},
        )
        raise AssertionError("target field accepted")
    except ValueError as e:
        assert "ANSWER_KEY_FIELD_FORBIDDEN" in str(e)

def test_executes_frozen_plan_without_target(monkeypatch=None):
    old_plan=x.entrypoint.compile_authorized_plan
    old_provider=x.v11.PROVIDERS["github"]
    try:
        x.entrypoint.compile_authorized_plan=lambda **kwargs:{
            "status":"PASS__AUTHORIZED_EMPIRICAL_PLAN_WITH_VERIFIED_RECOVERY_PORTFOLIO",
            "plan":{"actions":[
                {"action":"QUERY_SOURCE","action_id":"raw","source_id":"GITHUB_REPOSITORY_SEARCH","strategy_id":"RAW","query":"terminal fuzzy search"},
                {"action":"VERIFIED_RECOVERY_ROUTE","action_id":"multi","source_id":"GITHUB_REPOSITORY_SEARCH","strategy_id":"MULTI_QUERY_DECOMPOSITION","query":"terminal fuzzy search","requires_prior_miss_of":["raw"]},
            ]},
        }
        x.v11.PROVIDERS["github"]=lambda q,limit=20,timeout=1:["alpha/repo","beta/repo"]
        out=x.execute_request(
            root=Path("."),
            query_action={"action_id":"q","source_id":"GITHUB_REPOSITORY_SEARCH","query":"terminal fuzzy search"},
            source={"source_id":"GITHUB_REPOSITORY_SEARCH","provider":"github"},
            timeout=1,
        )
        assert out["status"]=="LIVE_FROZEN_V19_ROUTE_MEASUREMENT_COMPLETE"
        assert out["planned_action_count"]==2
        assert len(out["events"])==2
        assert out["answer_key_identity_used"] is False
        assert "alpha/repo" in out["candidate_ids"]
        assert all(e["answer_key_identity_used"] is False for e in out["events"])
    finally:
        x.entrypoint.compile_authorized_plan=old_plan
        x.v11.PROVIDERS["github"]=old_provider

def test_multilingual_bridge_uses_only_request_variants():
    row={
        "query":"日本語 形態素解析 Python",
        "language_variants":[{"text":"Japanese morphological analysis Python","language":"en"}],
    }
    qs=x._multilingual_queries(row,"github")
    joined=" ".join(qs).casefold()
    assert "japanese" in joined
    assert "morphological" in joined
    assert len(qs)>=2

def test_maven_route_uses_manifest_bridge_not_answer_key():
    old=x.v13.maven_behavior_bridge
    try:
        x.v13.maven_behavior_bridge=lambda q,timeout=1:{
            "coordinates":["org.example:artifact"],
            "search_traces":[],
            "repository_manifest_traces":[],
        }
        out=x._maven_manifest_bridge("Java behavior",timeout=1,deep=False)
        assert out["candidate_ids"]==["org.example:artifact"]
    finally:
        x.v13.maven_behavior_bridge=old

if __name__=="__main__":
    test_forbids_answer_key_fields()
    test_executes_frozen_plan_without_target()
    test_multilingual_bridge_uses_only_request_variants()
    test_maven_route_uses_manifest_bridge_not_answer_key()
    print("test_retrieval_verified_route_executor_v1: PASS")
