from canonical.runtime import livebench_legacy15_pointwise_candidate_planner_v1 as p


def c(iid, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def test_joint_unsat_pair_is_reduced_to_constructive_singleton():
    out = p.plan_constraints([
        c(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=3,
            nth_paragraph=2,
            first_word="rock",
        ),
        c("keywords:forbidden_words", forbidden_words=["rock", "apple"]),
    ])
    assert out["status"] == "PASS_POINTWISE_CANDIDATE_PLAN"
    assert out["full_constraint_count"] == 2
    assert out["selected_constraint_count"] == 1
    assert out["certified_unsat_subsets_seen_before_selection"][0]["indices"] == [0, 1]


def test_required_forbidden_overlap_is_kept_as_jointly_constructive():
    out = p.plan_constraints([
        c("keywords:existence", keywords=["rock"]),
        c("keywords:forbidden_words", forbidden_words=["rock", "apple"]),
    ])
    assert out["status"] == "PASS_POINTWISE_CANDIDATE_PLAN"
    assert out["selected_constraint_count"] == 2


def test_two_disjoint_unsat_edges_force_drop_to_at_most_two_of_four():
    out = p.plan_constraints([
        c(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=3,
            nth_paragraph=2,
            first_word="rock",
        ),
        c("keywords:forbidden_words", forbidden_words=["rock", "apple"]),
        c("length_constraints:number_sentences", num_sentences=1, relation="less than"),
        c("startend:end_checker", end_phrase="Any other questions?"),
    ])
    assert out["status"] == "PASS_POINTWISE_CANDIDATE_PLAN"
    assert out["full_constraint_count"] == 4
    assert out["selected_constraint_count"] <= 2
    three_sets = {
        tuple(x["indices"])
        for x in out["certified_unsat_subsets_seen_before_selection"]
        if len(x["indices"]) == 3
    }
    assert three_sets == {(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)}
