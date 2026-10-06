from canonical.runtime.m0_requirement_change_case_v1 import _canon,generate_case,execute_case,run_batch

def test_semantic_projection_ignores_derived_transform_kinds_alias():
    base={
        "subject":"Analyst","predicate":"preserve","object":"audit lineage",
        "polarity":"required","transform_kind":"artifact",
    }
    enriched={**base,"transform_kinds":["artifact"]}
    assert _canon([base])==_canon([enriched])

def test_requirement_change_batch_passes_fresh_synthetic_cases():
    out=run_batch(20261007,16)
    assert out["all_pass"] is True,out
    assert out["passed"]==16

def test_phase2_is_distinct_and_stale_requirements_are_not_retained():
    row=execute_case(generate_case(123456,0))
    assert row["pass"] is True,row
    assert row["requirements_changed"] is True
    assert row["stale_phase1_only_requirement_retained"] is False
    types=[x["type"] for x in row["objective_trace"]["events"]]
    assert "REQUIREMENT_CHANGE" in types
    assert "PLAN_REVISED" in types
    assert types[-1]=="TERMINAL"

def test_no_change_countermodel_fails():
    case=generate_case(654321,0)
    case["phase2"]=case["phase1"]
    row=execute_case(case)
    assert row["pass"] is False
    assert row["requirements_changed"] is False

def test_candidate_never_receives_hidden_oracle():
    case=generate_case(777,0)
    p1=case["phase1"]
    from canonical.runtime.m0_requirement_change_case_v1 import public_phase
    public=public_phase(case,1)
    assert "_oracle" not in public
    assert "raw_source" in public
    assert "_oracle" in p1
