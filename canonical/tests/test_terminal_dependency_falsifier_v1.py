from __future__ import annotations

from canonical.runtime.terminal_dependency_falsifier_v1 import analyze_graph


def graph():
    return {
        "leaves": [
            {
                "id": "hash",
                "kind": "IMPLEMENTATION_IDENTITY",
                "status": "PROVED",
                "failure_families": ["VERSION_DRIFT"],
            },
            {
                "id": "local-refine",
                "kind": "EXECUTABLE_REFINEMENT",
                "status": "UNRESOLVED",
                "failure_families": ["IMPLEMENTATION_REFINEMENT_MISMATCH"],
            },
            {
                "id": "terminal-refine",
                "kind": "EXECUTABLE_REFINEMENT",
                "status": "UNRESOLVED",
                "failure_families": [
                    "COMPOSITION_MISMATCH",
                    "NOVEL_DIMENSION",
                    "IMPLEMENTATION_REFINEMENT_MISMATCH",
                ],
            },
        ],
        "routes": [
            {
                "id": "local",
                "terminal_load_bearing": False,
                "creditable": False,
                "dependency_leaf_ids": ["local-refine"],
            },
            {
                "id": "terminal",
                "terminal_load_bearing": True,
                "creditable": False,
                "dependency_leaf_ids": ["terminal-refine"],
            },
        ],
    }


def test_terminal_load_bearing_refinement_is_ranked_highest():
    out = analyze_graph(graph())
    assert out["pass"] is True
    assert out["highest_dominance_unresolved_leaf"] == "terminal-refine"


def test_irrelevant_statistical_family_is_not_invented():
    out = analyze_graph(graph())
    assert all(
        x["family"] != "ADAPTIVE_SELECTION"
        for x in out["unresolved_obligations"]
    )


def test_unknown_family_is_not_silently_passed():
    raw = graph()
    raw["leaves"][1]["failure_families"].append("MAGIC")
    out = analyze_graph(raw)
    assert {"leaf_id": "local-refine", "family": "MAGIC"} in out["unknown_applicability"]


def test_falsifier_never_claims_open_world_closure_or_terminal_credit():
    out = analyze_graph(graph())
    assert out["open_world_closure"] is False
    assert out["generator_coverage_proved"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
