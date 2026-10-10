from canonical.runtime.requirement_graph_kernel import (
    build_test_obligations,
    compile_requirement_contract,
    requirement_mutation_score,
    validate_requirement_output_reachability,
    compile_structured_method_contract,
)


def base_requirements():
    return [
        {
            "id":"REQ-A",
            "critical":True,
            "dependencies":[],
            "children":[],
            "open_questions":[],
            "clauses":[{"id":"REQ-A-C1","keyword":"MUST","covered_by_scenarios":["A-OK"]}],
            "scenarios":[{"id":"A-OK","given":["raw A"],"when":["transform A"],"then":["observable A"]}],
        },
        {
            "id":"REQ-B",
            "critical":True,
            "dependencies":["REQ-A"],
            "children":[],
            "open_questions":[],
            "clauses":[{"id":"REQ-B-C1","keyword":"MUST","covered_by_scenarios":["B-OK"]}],
            "scenarios":[{"id":"B-OK","given":["A output"],"when":["transform B"],"then":["observable B"]}],
        },
    ]


def test_valid_graph_and_obligations_pass():
    r=base_requirements()
    out=compile_requirement_contract(r, expected_required_ids=["REQ-A","REQ-B"])
    assert out["pass"] is True
    assert len(out["test_obligations"]["obligations"]) == 2


def test_omitted_required_node_fails():
    r=base_requirements()[1:]
    out=compile_requirement_contract(r, expected_required_ids=["REQ-A","REQ-B"])
    assert out["pass"] is False
    assert any(d["code"]=="required-node-omitted" for d in out["graph"]["diagnostics"])


def test_open_question_fails():
    r=base_requirements()
    r[0]["open_questions"]=["what does A mean?"]
    assert compile_requirement_contract(r, expected_required_ids=["REQ-A","REQ-B"])["pass"] is False


def test_cycle_fails():
    r=base_requirements()
    r[0]["dependencies"]=["REQ-B"]
    assert compile_requirement_contract(r, expected_required_ids=["REQ-A","REQ-B"])["pass"] is False


def test_normative_clause_requires_scenario_coverage():
    r=base_requirements()
    r[0]["clauses"][0]["covered_by_scenarios"]=[]
    assert compile_requirement_contract(r, expected_required_ids=["REQ-A","REQ-B"])["pass"] is False


def test_requirement_mutations_all_killed():
    out=requirement_mutation_score(base_requirements())
    assert out["total"] >= 6
    assert out["kill_fraction"] == 1.0
    assert out["survived"] == 0
    assert out["pass"] is True


def test_spent_saccr_shortcut_missing_supervisory_duration_output_path_fails():
    requirements=base_requirements()+[{
        "id":"SUPERVISORY_DURATION","critical":True,"dependencies":[],"children":[],"open_questions":[],
        "clauses":[{"id":"SD-C1","keyword":"MUST","covered_by_scenarios":["SD-OK"]}],
        "scenarios":[{"id":"SD-OK","given":["dates"],"when":["derive duration"],"then":["duration"]}],
    }]
    nodes=[
        {"id":"req-a","requirement_id":"REQ-A"},
        {"id":"req-b","requirement_id":"REQ-B"},
        {"id":"sd","requirement_id":"SUPERVISORY_DURATION"},
        {"id":"shortcut"},{"id":"out"},
    ]
    edges=[
        {"from":"req-a","to":"shortcut"},
        {"from":"req-b","to":"shortcut"},
        {"from":"shortcut","to":"out"},
    ]
    out=validate_requirement_output_reachability(
        requirements, calculation_nodes=nodes, calculation_edges=edges, outputs=["out"]
    )
    assert out["pass"] is False
    assert "SUPERVISORY_DURATION:NO_OUTPUT_PATH" in out["uncovered"]


def test_corrected_saccr_requirement_lineage_reaches_output():
    requirements=base_requirements()
    nodes=[
        {"id":"req-a","requirement_id":"REQ-A"},
        {"id":"req-b","requirement_id":"REQ-B"},
        {"id":"mid"},{"id":"out"},
    ]
    edges=[
        {"from":"req-a","to":"mid"},
        {"from":"req-b","to":"mid"},
        {"from":"mid","to":"out"},
    ]
    out=compile_structured_method_contract(
        requirements,
        expected_required_ids=["REQ-A","REQ-B"],
        calculation_nodes=nodes,
        calculation_edges=edges,
        outputs=["out"],
    )
    assert out["pass"] is True


def test_cad_local_only_graph_fails_global_requirements():
    requirements=[
        {"id":"LOCAL_DIM"},{"id":"GLOBAL_TOPOLOGY"},{"id":"GLOBAL_ENVELOPE"}
    ]
    nodes=[
        {"id":"local","requirement_id":"LOCAL_DIM"},
        {"id":"topo","requirement_id":"GLOBAL_TOPOLOGY"},
        {"id":"env","requirement_id":"GLOBAL_ENVELOPE"},
        {"id":"out"},
    ]
    edges=[{"from":"local","to":"out"}]
    out=validate_requirement_output_reachability(
        requirements, calculation_nodes=nodes, calculation_edges=edges, outputs=["out"]
    )
    assert out["pass"] is False
    assert "GLOBAL_TOPOLOGY:NO_OUTPUT_PATH" in out["uncovered"]
    assert "GLOBAL_ENVELOPE:NO_OUTPUT_PATH" in out["uncovered"]


def test_output_reachability_fails_closed_on_cycle_dangling_and_unjustified_exclusion():
    requirements=[{"id":"R"}]
    nodes=[{"id":"r","requirement_id":"R"},{"id":"a"},{"id":"out"}]
    edges=[{"from":"r","to":"a"},{"from":"a","to":"r"},{"from":"ghost","to":"out"}]
    out=validate_requirement_output_reachability(
        requirements,
        calculation_nodes=nodes,
        calculation_edges=edges,
        outputs=["out"],
        exclusions=[{"requirement_id":"R","justification":""}],
    )
    assert out["pass"] is False
    codes={d["code"] for d in out["diagnostics"]}
    assert "calculation-cycle" in codes
    assert "dangling-calculation-edge" in codes
    assert "empty-exclusion-justification" in codes
