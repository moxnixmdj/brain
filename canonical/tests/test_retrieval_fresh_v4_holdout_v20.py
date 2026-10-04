from canonical.runtime import retrieval_fresh_v4_holdout_v20 as v20

def test_validate():
    v20.validate()

def test_targets_are_new_vs_v11():
    from canonical.runtime import retrieval_live_provider_arena_v11 as v11
    old={v11._norm(x["target"]) for x in v11.TASKS}
    new={v11._norm(x["target"]) for x in v20.TASKS}
    assert old.isdisjoint(new)

def test_v4_plan_is_answer_key_blind():
    for row in v20.TASKS:
        plan=v20.ep.compile_authorized_plan(
            root=v20.root(),
            query_actions=[v20.query_action(row)],
            sources=[v20.source_row(row)],
        )
        t=v20.v11._norm(row["target"])
        assert not v20.identity_leaked(plan,t)

if __name__=="__main__":
    test_validate();test_targets_are_new_vs_v11();test_v4_plan_is_answer_key_blind()
    print("test_retrieval_fresh_v4_holdout_v20: PASS")
