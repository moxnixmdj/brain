"""Live-main P3 V5/V6 failure regression: requirements must not disappear."""
from copy import deepcopy

from canonical.runtime.p3_real_context_v3_admission_v5 import evaluate as v5
from canonical.runtime.p3_real_context_v3_admission_v6 import evaluate as v6
from canonical.runtime.p3_required_claim_grounded_realization_cell_v3 import evaluate as required
from canonical.tests.test_p3_real_context_v3_admission_v5 import base, req, opt, ev


def two_required():
    return {"context_id":"C1","v3_input":base([
        req("A","Revenue growth is 12."),
        req("B","Margin rate is 8."),
    ],[
        ev("E1","Report states Revenue growth is 12."),
        ev("E2","Report states Margin rate is 8."),
    ])}


def test_normal_structural_route_still_passes():
    out=v6(two_required())
    assert out["pass"] is True,out
    assert out["route"]=="MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1",out
    assert out["terminal_credit_delta"]==0


def test_positive_numeric_required_v3_still_passes():
    p={"context_id":"C2","v3_input":base([
        req("A","Revenue growth is at least 10.")
    ],[ev("E","Report states Revenue growth is 12.")])}
    out=v6(p)
    assert out["pass"] is True,out
    assert out["route"]=="REQUIRED_SUPPORT_V4_REALIZATION_CELL_V2",out
    assert out["terminal_credit_delta"]==0


def test_weighted_objective_binds_order_even_for_all_mandatory_claims():
    p=two_required()
    p["objective_weights"]={"A":1,"B":100}
    for engine in (v5,v6):
        out=engine(deepcopy(p))
        assert out["pass"] is True,out
        assert out["route"]=="EXPLICIT_WEIGHTED_SALIENCE_CELL_V1",out
        assert out["claim_order"]==["B","A"],out
        assert out["terminal_credit_delta"]==0


def test_bad_weight_objectives_never_fall_through_to_structural():
    p=two_required()
    for bad in (None,[],{"A":1},{"A":1,"B":"100"}):
        for engine in (v5,v6):
            out=engine({**deepcopy(p),"objective_weights":bad})
            assert out["pass"] is False,(bad,out)
            assert out["reason"] in ("OBJECTIVE_WEIGHTS_INVALID","OBJECTIVE_WEIGHTS_UNSATISFIED"),(bad,out)
            assert out["terminal_authority"] is False


def test_unmodeled_input_contract_requirements_fail_all_positive_routes():
    cases=[
        ("outer","UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS", lambda p: p.update({"must_translate":"German"})),
        ("schema","V3_INPUT_SCHEMA_INVALID",lambda p:p["v3_input"].update({"schema":"FORGED"})),
        ("public","UNMODELED_V3_INPUT_FIELDS",lambda p:p["v3_input"].update({"mandatory_policy":True})),
        ("task","UNMODELED_TASK_REQUIREMENTS",lambda p:p["v3_input"]["task"].update({"must_translate":"German"})),
        ("claim","UNMODELED_CLAIM_REQUIREMENTS",lambda p:p["v3_input"]["task"]["claims"][0].update({"must_not_show":True})),
        ("evidence","UNMODELED_EVIDENCE_REQUIREMENTS",lambda p:p["v3_input"]["task"]["evidence"][0].update({"authority_condition":"human_review"})),
        ("audience","AUDIENCE_PROFILE_SEMANTICS_UNMODELED",lambda p:p["v3_input"]["task"]["audience_profile"].update({"profile_id":"GERMAN_ONLY"})),
        ("profile","UNMODELED_AUDIENCE_PROFILE_FIELDS",lambda p:p["v3_input"]["task"]["audience_profile"].update({"must_translate":"German"})),
        ("render","UNMODELED_RENDER_REQUIREMENTS",lambda p:p["v3_input"]["task"]["audience_profile"]["constraints"].update({"language":"de"})),
        ("order","UNMODELED_RENDER_REQUIREMENTS",lambda p:p["v3_input"]["task"]["audience_profile"]["constraints"].update({"item_order":"WEIGHT_DESC"})),
        ("titles","CONFLICTING_TITLE_REQUIREMENTS",lambda p:(p["v3_input"]["task"].update({"title":"First"}),p["v3_input"]["task"]["audience_profile"].update({"title":"Second"}))),
    ]
    for label,reason,mutate in cases:
        p=two_required()
        mutate(p)
        for engine in (v6,v5):
            out=engine(deepcopy(p))
            assert out["pass"] is False,(label,out)
            assert out["reason"]==reason,(label,out)
            assert out["terminal_credit_delta"]==0
            assert out["u_subtraction_authority"] is False


def test_direct_required_v3_has_same_syntactic_guard():
    cases=[
        ("schema","V3_INPUT_SCHEMA_INVALID",lambda x:x.update({"schema":"FORGED"})),
        ("task","UNMODELED_TASK_REQUIREMENTS",lambda x:x["task"].update({"must_translate":"German"})),
        ("audience","AUDIENCE_PROFILE_SEMANTICS_UNMODELED",lambda x:x["task"]["audience_profile"].update({"profile_id":"GERMAN_ONLY"})),
        ("render","UNMODELED_RENDER_REQUIREMENTS",lambda x:x["task"]["audience_profile"]["constraints"].update({"language":"de"})),
    ]
    for label,reason,mutate in cases:
        public=deepcopy(two_required()["v3_input"])
        mutate(public)
        out=required({"v3_input":public})
        assert out["pass"] is False,(label,out)
        assert out["reason"]==reason,(label,out)
        assert out["terminal_credit_delta"]==0


def test_optional_weighted_path_still_selects_high_weight_claim():
    p={"context_id":"C3","v3_input":base([
        req("A","Revenue growth is 12."),opt("B","Margin rate is 8.")
    ],[
        ev("E1","Report states Revenue growth is 12."),
        ev("E2","Report states Margin rate is 8.")
    ]),"objective_weights":{"A":1,"B":10}}
    out=v6(p)
    assert out["pass"] is True,out
    assert out["route"]=="EXPLICIT_WEIGHTED_SALIENCE_CELL_V1"
    assert out["terminal_credit_delta"]==0
