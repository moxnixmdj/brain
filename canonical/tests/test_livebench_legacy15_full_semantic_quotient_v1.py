from canonical.runtime import livebench_legacy15_full_semantic_quotient_v1 as q
from canonical.runtime import livebench_legacy15_lexical_collision_signatures_v2 as lexical


def _alpha_code(i: int) -> str:
    # Fixed-width base-26, letters only.
    chars = []
    n = i
    for _ in range(5):
        chars.append(chr(ord("a") + (n % 26)))
        n //= 26
    return "q" + "".join(reversed(chars))


def _synthetic_exact_shape_words() -> tuple[str, ...]:
    # The quotient combinator depends on exact cardinality, uniqueness,
    # ASCII-alpha shape, and presence of the four special end-phrase words.
    rows = list(lexical.SPECIAL_WORDS)
    i = 0
    while len(rows) < lexical.EXPECTED_WORD_COUNT:
        word = _alpha_code(i)
        i += 1
        if word not in rows:
            rows.append(word)
    return tuple(rows)


def test_exact_subject_bindings_still_match():
    got = q._verify_bindings(q._root())
    assert got == q.EXPECTED_BLOBS


def test_public_domain_and_special_branch_isolation():
    domain = q._verify_public_domain_constants()
    assert domain["word_relation_threshold_cases"] == 802
    assert domain["sentence_relation_threshold_cases"] == 40
    assert domain["nth_position_pairs"] == 15
    assert domain["mandatory_word_upper_bound"] < 100

    isolation = q._verify_conflict_isolation()
    assert isolation["compatible_id_sets"] == 928
    assert isolation["repeat_prompt_id_sets"] == 4
    assert isolation["json_id_sets"] == 4
    assert isolation["two_response_id_sets"] == 8


def test_complete_pointwise_optimum_quotient_has_exact_53068_cells():
    words = _synthetic_exact_shape_words()
    signatures = lexical.enumerate_signatures(words)
    assert len(signatures) == 192

    out = q._verify_optimum_quotient(signatures)
    assert out["complete_pointwise_optimum_quotient_cells"] == 53068
    assert out["loss_histogram"] == {
        "0": 15503,
        "1": 31499,
        "2": 6066,
    }
    assert out["maximum_unavoidable_checker_losses"] == 2


def test_multiple_lexical_collisions_share_one_forbidden_loss():
    words = _synthetic_exact_shape_words()
    signatures = lexical.enumerate_signatures(words)
    sig = next(
        row
        for row in signatures
        if row["nth_in_forbidden"] and q._end_collision(row)
    )
    ids = {q.FORBIDDEN, q.NTH, q.END}
    dropped = q._sacrificed_ids(ids, sig, q.ABSENT_CLASS)
    assert dropped == (q.FORBIDDEN,)
    assert len(ids) - len(dropped) == 2


def test_sentence_and_lexical_defects_are_independent_two_checker_losses():
    words = _synthetic_exact_shape_words()
    signatures = lexical.enumerate_signatures(words)
    sig = next(row for row in signatures if row["nth_in_forbidden"])
    ids = {q.FORBIDDEN, q.NTH, q.END, q.SENTENCES}
    dropped = q._sacrificed_ids(ids, sig, "LESS_THAN_ONE")
    assert set(dropped) == {q.FORBIDDEN, q.SENTENCES}
    assert len(ids) - len(dropped) == 2


def test_no_defect_means_full_pointwise_pass_count():
    words = _synthetic_exact_shape_words()
    signatures = lexical.enumerate_signatures(words)
    sig = next(
        row
        for row in signatures
        if not row["nth_in_forbidden"] and not q._end_collision(row)
    )
    ids = {q.FORBIDDEN, q.NTH, q.END, q.SENTENCES}
    dropped = q._sacrificed_ids(ids, sig, "AT_LEAST")
    assert dropped == ()
    assert len(ids) - len(dropped) == len(ids)
