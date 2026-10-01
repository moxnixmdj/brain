from canonical.runtime.independent_acceptance_model import assess

def test_correlated_recompute_is_rejected():
    model = {
        "requirements": [{
            "id": "R1", "critical": True,
            "transform_kinds": ["aggregate"],
            "builder_dependencies": ["raw:inputs", "semantic:interpretation-A"],
        }],
        "checks": [{
            "id": "same-recompute", "covers": ["R1"],
            "provenance": "same_formula",
            "dependencies": ["raw:inputs", "semantic:interpretation-A"],
            "detects": ["aggregation_formula"],
        }],
    }
    out = assess(model)
    assert out["pass"] is False
    assert out["failed_requirements"] == ["R1"]

def test_shared_raw_inputs_do_not_break_independence():
    modes = [
        "component_omission","component_mapping","weight_or_factor",
        "correlation_or_interaction","unit_or_scale","aggregation_formula"
    ]
    model = {
        "requirements": [{
            "id": "R", "transform_kinds": ["aggregate"],
            "builder_dependencies": ["raw:portfolio", "builder:formula-A"],
        }],
        "checks": [{
            "id": "alt", "covers": ["R"], "provenance": "independent_oracle",
            "dependencies": ["raw:portfolio", "oracle:formula-B"],
            "detects": modes,
        }],
    }
    out = assess(model)
    assert out["pass"] is True

def test_missing_global_geometry_checks_blocks():
    model = {
        "requirements": [{
            "id": "G", "transform_kinds": ["geometry_reconstruction"],
            "builder_dependencies": ["raw:drawing", "builder:cad-construction"],
        }],
        "checks": [{
            "id": "local", "covers": ["G"], "provenance": "independent_oracle",
            "dependencies": ["raw:drawing", "oracle:local-dimension-probe"],
            "detects": ["watertightness"],
        }],
    }
    out = assess(model)
    r = out["requirements"][0]
    assert out["pass"] is False
    assert "global_mass_property" in r["uncovered"]
    assert "topology" in r["uncovered"]
    assert "envelope" in r["uncovered"]
    assert "curvature" in r["uncovered"]

def test_counterexample_templates_emitted():
    model = {
        "requirements": [{
            "id": "S", "transform_kinds": ["selection"],
            "builder_dependencies": ["raw:records"],
        }],
        "checks": [],
    }
    out = assess(model)
    r = out["requirements"][0]
    assert r["counterexample_templates"]
    assert any(x["failure_mode"] == "missing_value" for x in r["counterexample_templates"])
