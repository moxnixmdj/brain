from canonical.runtime.requirement_acceptance_compiler import compile_requirements
from canonical.runtime import independent_acceptance_model as iam


def test_every_owned_transform_kind_compiles_nonempty():
    rows=[
        {"id": f"R_{kind}", "critical": True, "transform_kinds": [kind],
         "builder_dependencies": ["raw:input", f"builder:{kind}"]}
        for kind in sorted(iam.OBLIGATIONS)
    ]
    out=compile_requirements(rows)
    assert out["status"]=="COMPILED"
    assert out["requirement_count"]==len(iam.OBLIGATIONS)
    for plan in out["plans"]:
        assert plan["required_failure_modes"]
        assert len(plan["counterexample_templates"])==len(plan["required_failure_modes"])


def test_rank23_transform_vocabulary_compiles():
    rows=[
        {"id":"R1","transform_kinds":["aggregate","artifact"]},
        {"id":"R2","transform_kinds":["geometry_reconstruction","selection"]},
        {"id":"R3","transform_kinds":["state_transition"]},
    ]
    out=compile_requirements(rows)
    assert out["status"]=="COMPILED"
    by_id={x["requirement_id"]:x for x in out["plans"]}
    assert "component_omission" in by_id["R1"]["required_failure_modes"]
    assert "topology" in by_id["R2"]["required_failure_modes"]
    assert "failure_recovery" in by_id["R3"]["required_failure_modes"]


def test_unknown_transform_fails_closed():
    out=compile_requirements([{"id":"R","transform_kinds":["magic_semantics"]}])
    assert out["status"]=="FAIL_CLOSED"
    assert any(x.startswith("UNKNOWN_TRANSFORM_KINDS:R:") for x in out["errors"])


def test_critical_empty_transform_fails_closed():
    out=compile_requirements([{"id":"R","critical":True,"transform_kinds":[]}])
    assert out["status"]=="FAIL_CLOSED"


def test_explicit_failure_mode_is_preserved():
    out=compile_requirements([{
        "id":"R","transform_kinds":["artifact"],
        "must_detect_failure_modes":["custom_visible_failure"]
    }])
    assert out["status"]=="FAIL_CLOSED"  # no generic template may be invented
    assert any("COUNTEREXAMPLE_TEMPLATE_MISSING" in x for x in out["errors"])
