from canonical.runtime.source_aligned_analytic_generator_v1 import construct

def test_mixed_fields_generate_and_reverify():
    text='score must be at least 2. safe must be true. mode must equal "audit".'
    schema={
      "score":{"type":"integer","dimension":"score"},
      "safe":{"type":"boolean","dimension":"dimensionless"},
      "mode":{"type":"enum","dimension":"dimensionless"},
    }
    x=construct(text,source_id="t",field_schema=schema)
    assert x["pass"] is True,x
    assert x["candidate_values"]=={"mode":"audit","safe":True,"score":2}
    assert x["model_dependency_count"]==0
    assert x["external_proposal_dependency"] is False

def test_bounds_choose_satisfying_value():
    x=construct(
      "x must be at least 1.2. x must be at most 3.8.",
      source_id="b",field_schema={"x":{"type":"integer","dimension":"u"}},
    )
    assert x["pass"] is True,x
    assert x["candidate_values"]=={"x":2}

def test_contradiction_fails():
    x=construct(
      "x must equal 1. x must equal 2.",
      source_id="c",field_schema={"x":{"type":"number","dimension":"u"}},
    )
    assert x["pass"] is False
    assert x["status"]=="NO_SOUND_ANALYTIC_CANDIDATE"

def test_unresolved_normative_source_blocks():
    x=construct(
      "x should look excellent.",
      source_id="u",field_schema={"x":{"type":"number","dimension":"u"}},
    )
    assert x["pass"] is False
    assert x["status"]=="UNRESOLVED"

def test_unconstrained_declared_field_blocks():
    x=construct(
      "x must equal 1.",
      source_id="m",field_schema={
        "x":{"type":"number","dimension":"u"},
        "y":{"type":"boolean","dimension":"dimensionless"},
      },
    )
    assert x["pass"] is False
    assert x["status"]=="NO_SOUND_ANALYTIC_CANDIDATE"
