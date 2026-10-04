from collections import Counter

from canonical.runtime import livebench_legacy15_lexical_collision_signatures_v2 as q


def _alpha_word(i: int) -> str:
    chars = []
    n = i
    while True:
        chars.append(chr(ord("a") + (n % 26)))
        n //= 26
        if n == 0:
            break
    return "zzq" + "".join(reversed(chars))


def _synthetic_exact_size_domain():
    words = list(q.SPECIAL_WORDS)
    i = 0
    while len(words) < q.EXPECTED_WORD_COUNT:
        word = _alpha_word(i)
        i += 1
        if word not in words:
            words.append(word)
    return tuple(words)


def test_exact_reachable_signature_count_is_192_not_320():
    out = q.verify(_synthetic_exact_size_domain())
    assert out["exact_reachable_signature_count"] == 192
    assert out["prior_conservative_signature_bound"] == 320
    assert out["lexical_hard_unsat_signature_count"] == 155
    assert out["lexical_not_hard_unsat_signature_count"] == 37


def test_reachability_couples_special_nth_bit_to_same_forbidden_membership():
    rows = q.enumerate_signatures(_synthetic_exact_size_domain())
    for row in rows:
        nth = row["nth_word"]
        if nth in q.SPECIAL_WORDS:
            assert row["nth_in_forbidden"] == row["special_forbidden_membership"][nth]
        assert len(row["forbidden_words"]) == q.KEYWORD_COUNT
        assert len(set(row["forbidden_words"])) == q.KEYWORD_COUNT


def test_reachable_counts_are_16_for_special_nth_and_32_for_other_nth_per_end():
    rows = q.enumerate_signatures(_synthetic_exact_size_domain())
    counts = Counter((r["nth_category"], r["end_phrase"]) for r in rows)
    for nth in q.SPECIAL_WORDS:
        for end in q.END_PHRASES:
            assert counts[(nth, end)] == 16
    for end in q.END_PHRASES:
        assert counts[("ALL_OTHER", end)] == 32


def test_literal_parser_extracts_only_word_list_assignment():
    source = "WORD_LIST = ['alpha', 'beta']\nLANGUAGE_CODES = {'x': 'y'}\n"
    assert q._word_list_from_source(source) == ("alpha", "beta")
