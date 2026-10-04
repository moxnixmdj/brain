from canonical.runtime import livebench_union25_sound_lower_bound_hitting_set_v1 as h


def test_empty_clause_basis_has_zero_lower_bound():
    assert h.minimum_hitting_sets(["a", "b"], []) == ((),)


def test_overlapping_conflicts_share_one_failure():
    active = ["forbidden", "nth", "end"]
    clauses = [
        ["forbidden", "nth"],
        ["forbidden", "end"],
    ]
    assert h.minimum_hitting_sets(active, clauses) == (("forbidden",),)


def test_disjoint_sentence_singleton_adds_exactly_one_dimension():
    active = ["sentence", "forbidden", "nth", "end"]
    clauses = [
        ["sentence"],
        ["forbidden", "nth"],
        ["forbidden", "end"],
    ]
    assert h.minimum_hitting_sets(active, clauses) == (("forbidden", "sentence"),)


def test_exact_witness_attaining_lower_bound_proves_optimum():
    out = h.certify_exact_witness_optimality(
        ["sentence", "forbidden", "nth", "end"],
        [
            ["sentence"],
            ["forbidden", "nth"],
            ["forbidden", "end"],
        ],
        ["sentence", "forbidden"],
        exact_postvalidation=True,
        clause_soundness_bound=True,
    )
    assert out["minimum_unavoidable_failure_count"] == 2
    assert out["pointwise_maximum_pass_count_proved"] is True
    assert out["maximum_pass_count_if_proved"] == 2
    assert out["complete_incompatibility_map_required"] is False


def test_unknown_extra_incompatibility_fails_closed_via_postvalidation():
    out = h.certify_exact_witness_optimality(
        ["sentence", "forbidden", "nth", "end", "sections"],
        [
            ["sentence"],
            ["forbidden", "nth"],
            ["forbidden", "end"],
        ],
        ["sentence", "forbidden", "sections"],
        exact_postvalidation=True,
        clause_soundness_bound=True,
    )
    assert out["minimum_unavoidable_failure_count"] == 2
    assert out["exact_postvalidated_failure_count"] == 3
    assert out["pointwise_maximum_pass_count_proved"] is False


def test_unbound_soundness_or_postvalidation_never_gets_credit():
    kwargs = dict(
        active_ids=["a", "b"],
        unavoidable_loss_clauses=[["a", "b"]],
        exact_failed_ids=["a"],
    )
    assert not h.certify_exact_witness_optimality(
        **kwargs,
        exact_postvalidation=False,
        clause_soundness_bound=True,
    )["pointwise_maximum_pass_count_proved"]
    assert not h.certify_exact_witness_optimality(
        **kwargs,
        exact_postvalidation=True,
        clause_soundness_bound=False,
    )["pointwise_maximum_pass_count_proved"]


def test_failure_set_must_hit_every_sound_clause():
    out = h.certify_exact_witness_optimality(
        ["a", "b", "c"],
        [["a", "b"], ["c"]],
        ["a"],
        exact_postvalidation=True,
        clause_soundness_bound=True,
    )
    assert out["minimum_unavoidable_failure_count"] == 2
    assert out["hits_all_sound_clauses"] is False
    assert out["pointwise_maximum_pass_count_proved"] is False


def test_generic_theorem_regression():
    out = h.verify_theorem()
    assert out["status"] == "PASS__SOUND_LOWER_BOUND_PLUS_EXACT_WITNESS_THEOREM"
    assert out["deleted_proof_requirement"] == "COMPLETE_INCOMPATIBILITY_MAP"
