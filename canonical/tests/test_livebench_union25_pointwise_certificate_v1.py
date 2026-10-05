from canonical.runtime.livebench_union25_pointwise_certificate_v1 import certify
from canonical.runtime.livebench_union25_semantic_unsat_kernel_v1 import prove_unsat


def c(iid, **slots):
    return {"instruction_id": iid, "slots": slots}


def test_case_mode_section_pair_closes_next_cardinality_subset():
    contracts = [
        c("change_case:english_lowercase"),
        c("detectable_format:multiple_sections", section_spliter="Section", num_sections=2),
    ]
    proof = prove_unsat(contracts)
    assert proof["jointly_unsatisfiable"] is True
    assert any(
        e["rule_id"] == "LOWERCASE_ENGLISH_VS_SECTION_HEADING_CASE"
        for e in proof["hard_unsat_evidence"]
    )

    out = certify(contracts, [True, False])
    assert out["pointwise_optimal"] is True
    assert out["required_next_cardinality_subset_count"] == 1
    assert out["semantically_verified_unsat_subset_count"] == 1


def test_strengthened_additive_floor_can_close_four_checker_optimum():
    contracts = [
        c("keywords:letter_frequency", letter="s", let_relation="less than", let_frequency=5),
        c("detectable_format:multiple_sections", section_spliter="SECTION", num_sections=2),
        c("detectable_content:postscript", postscript_marker="P.S."),
        c("startend:end_checker", end_phrase="Any other questions?"),
    ]
    proof = prove_unsat(contracts)
    assert proof["jointly_unsatisfiable"] is True
    assert any(
        e["rule_id"]
        == "LETTER_FREQUENCY_STRICT_UPPER_BOUND_BELOW_STRENGTHENED_MANDATORY_FLOOR"
        for e in proof["hard_unsat_evidence"]
    )

    # A candidate satisfying the other three checkers is then pointwise optimal:
    # the only next-cardinality subset is the impossible all-four conjunction.
    out = certify(contracts, [False, True, True, True])
    assert out["pointwise_optimal"] is True
    assert out["required_next_cardinality_subset_count"] == 1
    assert out["unresolved_subset_indices"] == []


def test_active15_unsat_proofs_are_preserved():
    contracts = [
        c(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=2,
            nth_paragraph=1,
            first_word="alpha",
        ),
        c("keywords:forbidden_words", forbidden_words=["alpha"]),
    ]
    proof = prove_unsat(contracts)
    assert proof["jointly_unsatisfiable"] is True
    assert any(
        e["rule_id"] == "NTH_FIRST_WORD_IS_FORBIDDEN_WORD"
        for e in proof["hard_unsat_evidence"]
    )
    assert certify(contracts, [True, False])["pointwise_optimal"] is True


def test_unknown_pair_fails_closed_not_sat():
    contracts = [
        c("keywords:letter_frequency", letter="a", let_relation="at least", let_frequency=5),
        c("detectable_format:multiple_sections", section_spliter="Section", num_sections=2),
    ]
    proof = prove_unsat(contracts)
    assert proof["jointly_unsatisfiable"] is False
    assert proof["status"].startswith("UNKNOWN")

    out = certify(contracts, [True, False])
    assert out["pointwise_optimal"] is False
    assert out["status"].startswith("FAIL_CLOSED")
    assert out["unresolved_subset_indices"] == [[0, 1]]
