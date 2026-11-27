from canonical.runtime.semantic_observational_equivalence_cut_v1 import (
    exact_finite_theorem_summary,
    observational_equivalence_classes,
    optimal_query_cut,
    two_query_zero_residual_example,
    unsplittable_counterexample,
    zero_residual_semantic_information,
)

def test_unsplittable_worlds_preserve_one_irreducible_bit():
    out=unsplittable_counterexample()
    assert out["zero_residual_semantic_information"] is False
    assert out["irreducible_persistent_states"]==2
    assert out["irreducible_persistent_bits"]==1
    assert out["equivalence_classes"]==(("w0","w1"),)

def test_two_queries_remove_two_bits_exactly():
    out=two_query_zero_residual_example()
    assert out["b0"]["persistent_states"]==4
    assert out["b0"]["persistent_bits"]==2
    assert out["b1"]["persistent_states"]==2
    assert out["b1"]["persistent_bits"]==1
    assert out["b2"]["persistent_states"]==1
    assert out["b2"]["persistent_bits"]==0
    assert out["b2"]["zero_residual_semantic_information"] is True
    assert out["full"]["zero_residual_semantic_information"] is True

def test_common_policy_per_unsplittable_cell_gives_zero_bits():
    worlds=("a0","a1","b0","b1")
    policies=("pa","pb")
    adequate={
        "a0":("pa",),"a1":("pa",),
        "b0":("pb",),"b1":("pb",),
    }
    queries={
        "q":{"a0":"A","a1":"A","b0":"B","b1":"B"}
    }
    assert zero_residual_semantic_information(worlds,policies,adequate,queries) is True

def test_pairwise_overlap_without_whole_cell_common_policy_is_not_enough():
    worlds=("w0","w1","w2")
    policies=("p1","p2","p3")
    adequate={
        "w0":("p1","p2"),
        "w1":("p2","p3"),
        "w2":("p1","p3"),
    }
    queries={"q":{"w0":"same","w1":"same","w2":"same"}}
    out=exact_finite_theorem_summary(worlds,policies,adequate,queries)
    assert out["irreducible_persistent_states"]==2
    assert out["irreducible_persistent_bits"]==1

def test_adaptive_query_tree_can_use_branch_specific_second_queries():
    worlds=("w0","w1","w2","w3")
    policies=("p0","p1","p2","p3")
    adequate={w:(f"p{i}",) for i,w in enumerate(worlds)}
    queries={
        "root":{"w0":"L","w1":"L","w2":"R","w3":"R"},
        "left":{"w0":0,"w1":1,"w2":0,"w3":0},
        "right":{"w0":0,"w1":0,"w2":0,"w3":1},
    }
    out=optimal_query_cut(worlds,policies,adequate,queries,2)
    assert out["persistent_states"]==1
    assert out["persistent_bits"]==0

def test_observational_equivalence_uses_all_admissible_queries_not_role_labels():
    worlds=("vision_case","reasoning_case","action_case")
    queries={
        "q0":{
            "vision_case":"x",
            "reasoning_case":"x",
            "action_case":"y",
        },
        "q1":{
            "vision_case":1,
            "reasoning_case":1,
            "action_case":2,
        },
    }
    classes=observational_equivalence_classes(worlds,queries)
    assert ("reasoning_case","vision_case") in classes
    assert ("action_case",) in classes
