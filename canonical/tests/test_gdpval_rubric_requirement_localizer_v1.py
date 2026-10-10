from canonical.runtime.gdpval_rubric_requirement_localizer_v1 import localize

def fixture():
    return {
        "status":"INDEXED_EXPLICIT_RUBRIC_ACCEPTANCE_CRITERIA",
        "tasks":[
            {
                "task_id":"t1",
                "criteria":[
                    {"criterion_id":"c1","criterion":"The workbook must include a summary table."},
                    {"criterion_id":"c2","criterion":"Include a reconciliation section."},
                    {"criterion_id":"c3","criterion":"Professional quality is excellent."},
                ],
            }
        ],
    }

def test_modal_and_imperative_localize_and_unknown_stays_open():
    out=localize(fixture())
    assert out["pass"] is True
    assert out["criterion_count"]==3
    assert out["resolved_requirement_count"]==2
    assert out["unresolved_criterion_count"]==1
    routes={x["criterion_id"]:x["route"] for x in out["resolved_requirements"]}
    assert routes["c1"]=="BOUNDED_MODAL_PREDICATE_ARGUMENT"
    assert routes["c2"]=="BOUNDED_IMPERATIVE_DIRECTIVE"
    assert out["unresolved_criteria"][0]["criterion_id"]=="c3"
    assert out["unresolved_criterion_is_irrelevant"] is False
    assert out["policy_adequacy_claim"] is False
    assert out["terminal_credit_delta"]==0

def test_bad_index_fails_closed():
    out=localize({"status":"WRONG","tasks":[]})
    assert out["pass"] is False
    assert out["status"]=="FAIL_CLOSED"

def test_unresolved_does_not_become_credit():
    x=fixture()
    x["tasks"][0]["criteria"]=[{"criterion_id":"u","criterion":"Overall quality and insightfulness."}]
    out=localize(x)
    assert out["resolved_requirement_count"]==0
    assert out["unresolved_criterion_count"]==1
    assert out["whole_task_semantic_completeness_claim"] is False
    assert out["terminal_authority"] is False
