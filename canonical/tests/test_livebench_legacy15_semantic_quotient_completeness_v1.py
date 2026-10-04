from canonical.runtime import livebench_legacy15_semantic_quotient_completeness_v1 as q


def _letters(n: int) -> str:
    out = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(ord("a") + r) + out
    return out


def _synthetic_words():
    fixed = ["other", "anything", "can", "help", "section"]
    banned = {
        "any", "questions", "is", "there", "else", "i", "with", "p", "s",
        *fixed,
    }
    out = list(fixed)
    i = 0
    while len(out) < 1525:
        w = "zz" + _letters(i)
        i += 1
        if w not in banned and w not in out:
            out.append(w)
    return out


def test_special_components_are_exactly_isolated():
    got = q.verify_special_component_isolation()
    assert got[q.JSON_ID] == sorted([q.EXIST, q.FORBIDDEN])
    assert got[q.REPEAT] == sorted([q.EXIST, q.TITLE])
    assert got[q.TWO] == sorted([q.EXIST, q.FORBIDDEN, q.TITLE])


def test_numeric_domain_counts_are_exact():
    got = q.numeric_domain_certificate()
    assert got["word_thresholds"]["exact_relation_threshold_pairs"] == 802
    assert got["sentence_thresholds"]["exact_relation_threshold_pairs"] == 40
    assert len(got["nth_paragraph_index_pairs"]) == 15


def test_lexical_basis_reduces_to_only_true_unshielded_collisions():
    got = q.lexical_basis(_synthetic_words())
    assert got.word_count == 1525
    assert set(got.end_collisions) == {"other", "anything", "can", "help"}
    assert set(got.section_collisions) == {"section"}
    assert got.postscript_collisions == ()
    assert got.required_forbidden_carrier_total is True


def test_full_certificate_is_fail_closed_but_complete_before_promotion():
    got = q.verify(_synthetic_words())
    assert got["status"] == "PASS__FULL_PUBLIC_GENERATOR_ACTIVE15_SEMANTIC_QUOTIENT_COMPLETE"
    assert got["factors"]["structural_identity_factor"]["compatible_set_count"] == 928
    assert got["distribution_dependence"] is False
    assert got["acceptance_credit"] is False
