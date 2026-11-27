from canonical.runtime import livebench_legacy15_lexical_closure_v1 as c
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


def _synthetic_words():
    words = list(q.SPECIAL_WORDS)
    i = 0
    while len(words) < q.EXPECTED_WORD_COUNT:
        word = _alpha_word(i)
        i += 1
        if word not in words:
            words.append(word)
    return tuple(words)


def test_keyword_carrier_theorem_holds_across_full_word_domain_shape():
    words = _synthetic_words()
    assert c._verify_keyword_carrier_theorem(words) == q.EXPECTED_WORD_COUNT


def test_all_192_signatures_match_semantic_unsat_kernel():
    rows = q.enumerate_signatures(_synthetic_words())
    assert len(rows) == c.EXPECTED_SIGNATURES

    unsat = 0
    sat = 0
    for row in rows:
        contracts = c._contracts(row)
        expected = c._expected_reasons(row)
        observed = c.feasibility.hard_unsat_reasons(contracts)
        assert observed == expected
        built = c.composer.compose_contracts(contracts)
        if expected:
            unsat += 1
            assert built["status"] == "PROVED_UNSAT"
            assert tuple(built["hard_unsat_reasons"]) == expected
        else:
            sat += 1
            assert built["status"] == "CANDIDATE_WITNESS"
            assert built["response"].strip()

    assert unsat == c.EXPECTED_UNSAT
    assert sat == c.EXPECTED_WITNESSES
