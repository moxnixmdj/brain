from canonical.runtime.requirement_graph_kernel import (
    build_test_obligations,
    compile_requirement_contract,
    requirement_mutation_score,
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
