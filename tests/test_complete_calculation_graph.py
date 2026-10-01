from canonical.runtime.complete_calculation_graph import validate

def test_complete_graph_passes():
    m = {"requirements":[{"id":"R1"},{"id":"R2"}],
      "nodes":[{"id":"r1","requirement_id":"R1"},{"id":"r2","requirement_id":"R2"},{"id":"mid"},{"id":"out"}],
      "edges":[{"from":"r1","to":"mid"},{"from":"r2","to":"mid"},{"from":"mid","to":"out"}],
      "outputs":["out"], "exclusions":[]}
    assert validate(m)["pass"] is True

def test_spent_saccr_shortcut_fails_when_duration_factor_has_no_consumer():
    m={"requirements":[{"id":"NOTIONAL"},{"id":"SUPERVISORY_DURATION"},{"id":"MATURITY_FACTOR"},{"id":"SUPERVISORY_FACTOR"}],
       "nodes":[{"id":"n","requirement_id":"NOTIONAL"},{"id":"sd","requirement_id":"SUPERVISORY_DURATION"},{"id":"mf","requirement_id":"MATURITY_FACTOR"},{"id":"sf","requirement_id":"SUPERVISORY_FACTOR"},{"id":"shortcut"},{"id":"out"}],
       "edges":[{"from":"n","to":"shortcut"},{"from":"mf","to":"shortcut"},{"from":"sf","to":"shortcut"},{"from":"shortcut","to":"out"}],
       "outputs":["out"],"exclusions":[]}
    out=validate(m)
    assert out["pass"] is False
    assert "SUPERVISORY_DURATION:NO_OUTPUT_PATH" in out["uncovered"]

def test_corrected_saccr_lineage_passes():
    m={"requirements":[{"id":"NOTIONAL"},{"id":"SUPERVISORY_DURATION"},{"id":"MATURITY_FACTOR"},{"id":"SUPERVISORY_FACTOR"}],
       "nodes":[{"id":"n","requirement_id":"NOTIONAL"},{"id":"sd","requirement_id":"SUPERVISORY_DURATION"},{"id":"mf","requirement_id":"MATURITY_FACTOR"},{"id":"sf","requirement_id":"SUPERVISORY_FACTOR"},{"id":"effective_notional"},{"id":"addon"},{"id":"out"}],
       "edges":[{"from":"n","to":"effective_notional"},{"from":"sd","to":"effective_notional"},{"from":"mf","to":"effective_notional"},{"from":"effective_notional","to":"addon"},{"from":"sf","to":"addon"},{"from":"addon","to":"out"}],
       "outputs":["out"],"exclusions":[]}
    assert validate(m)["pass"] is True

def test_cad_local_only_fails_global_requirements():
    m={"requirements":[{"id":"LOCAL_DIM"},{"id":"GLOBAL_TOPOLOGY"},{"id":"GLOBAL_ENVELOPE"}],
       "nodes":[{"id":"local","requirement_id":"LOCAL_DIM"},{"id":"topo","requirement_id":"GLOBAL_TOPOLOGY"},{"id":"env","requirement_id":"GLOBAL_ENVELOPE"},{"id":"out"}],
       "edges":[{"from":"local","to":"out"}],"outputs":["out"],"exclusions":[]}
    out=validate(m)
    assert out["pass"] is False
    assert "GLOBAL_TOPOLOGY:NO_OUTPUT_PATH" in out["uncovered"]
    assert "GLOBAL_ENVELOPE:NO_OUTPUT_PATH" in out["uncovered"]

def test_cycle_and_dangling_fail_closed():
    m={"requirements":[{"id":"R"}],"nodes":[{"id":"r","requirement_id":"R"},{"id":"a"},{"id":"out"}],
       "edges":[{"from":"r","to":"a"},{"from":"a","to":"r"},{"from":"ghost","to":"out"}],"outputs":["out"],"exclusions":[]}
    out=validate(m)
    assert out["pass"] is False
    assert "CYCLE_DETECTED" in out["errors"]
    assert any(x.startswith("DANGLING_EDGE") for x in out["errors"])

def test_explicit_justified_exclusion_is_allowed():
    m={"requirements":[{"id":"R"}],"nodes":[],"edges":[],"outputs":[],
       "exclusions":[{"requirement_id":"R","justification":"Not applicable under declared task contract."}]}
    out=validate(m)
    assert out["pass"] is True
    assert out["explicitly_excluded"]==["R"]
