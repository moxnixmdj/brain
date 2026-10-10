from canonical.runtime.independent_acceptance_model import assess

def test_spent_cad_local_only_acceptance_is_killed():
    model={
      "requirements":[{
        "id":"CAD_GLOBAL_SOLID",
        "critical":True,
        "transform_kinds":["geometry_reconstruction"],
        "builder_dependencies":["raw:drawing","semantic:local-feature-interpretation","builder:cad-construction"],
      }],
      "checks":[{
        "id":"local-watertight-check",
        "covers":["CAD_GLOBAL_SOLID"],
        "provenance":"independent_oracle",
        "dependencies":["raw:drawing","oracle:watertightness"],
        "detects":["watertightness"],
      }],
    }
    out=assess(model)
    assert out["pass"] is False
    uncovered=set(out["requirements"][0]["uncovered"])
    assert {"global_mass_property","topology","envelope","curvature"} <= uncovered

def test_spent_kg_shared_semantic_acceptance_is_killed():
    model={
      "requirements":[{
        "id":"KG_SELECTION_RECONCILIATION",
        "critical":True,
        "transform_kinds":["selection","entity_reconciliation","hierarchy_closure"],
        "builder_dependencies":["raw:records","semantic:record-precedence-and-identity"],
      }],
      "checks":[{
        "id":"builder-semantic-recompute",
        "covers":["KG_SELECTION_RECONCILIATION"],
        "provenance":"same_semantic_interpretation",
        "dependencies":["raw:records","semantic:record-precedence-and-identity"],
        "detects":["ordering_precedence","identifier_variant","transitive_or_superclass_closure"],
      }],
    }
    out=assess(model)
    assert out["pass"] is False
    assert out["requirements"][0]["independent_checks"] == ()

def test_spent_saccr_shared_formula_acceptance_is_killed():
    model={
      "requirements":[{
        "id":"SACCR_COMPLETE_CALCULATION_GRAPH",
        "critical":True,
        "transform_kinds":["aggregate","numeric_formula"],
        "builder_dependencies":["raw:portfolio","semantic:saccr-rule-selection","builder:formula-graph-A"],
      }],
      "checks":[{
        "id":"same-formula-recompute",
        "covers":["SACCR_COMPLETE_CALCULATION_GRAPH"],
        "provenance":"same_formula",
        "dependencies":["raw:portfolio","builder:formula-graph-A"],
        "detects":["aggregation_formula","unit_or_scale"],
      }],
    }
    out=assess(model)
    assert out["pass"] is False
    assert out["requirements"][0]["independent_checks"] == ()

def test_precommitted_bun_builder_policy_checks_are_killed():
    model={
      "requirements":[{
        "id":"BUN_PUBLIC_RELEASE_POLICY_ENVELOPE",
        "critical":True,
        "must_detect_failure_modes":["policy_or_semantic_variant"],
        "builder_dependencies":["raw:instruction","raw:visibility-policy","semantic:release-policy-interpretation"],
      }],
      "checks":[{
        "id":"candidate-self-test",
        "covers":["BUN_PUBLIC_RELEASE_POLICY_ENVELOPE"],
        "provenance":"builder_derived",
        "dependencies":["raw:instruction","semantic:release-policy-interpretation"],
        "detects":["baseline_functional_output"],
      }],
    }
    out=assess(model)
    assert out["pass"] is False
    assert out["requirements"][0]["uncovered"] == ("policy_or_semantic_variant",)
