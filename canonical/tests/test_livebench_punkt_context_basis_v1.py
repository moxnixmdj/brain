from itertools import islice

from canonical.runtime import livebench_punkt_context_basis_v1 as q
from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp


def test_punkt_basis_count_is_exact():
    out = q.verify()
    assert out["status"].startswith("PASS__147924_EXACT_REDUCED_PUNKT_CONTEXTS")
    assert out["sentence_context_id_sets"] == 285
    assert out["punkt_context_count"] == 147924


def test_sentence_less_than_one_is_not_a_construction_context():
    for label, n, relation in q.SENTENCE_CONTEXTS:
        assert not (relation == "less than" and n == 1)


def test_only_general_sentence_compatible_families_are_modeled():
    for ids in q.sentence_id_sets():
        assert comp.SENTENCES in ids
        assert comp.PARAGRAPHS not in ids
        assert comp.JSON_ID not in ids
        assert comp.REPEAT not in ids
        assert comp.TWO not in ids


def test_word_context_has_only_no_pad_vs_positive_pad_shapes():
    assert q.WORD_CONTEXTS == (
        ("NO_PADDING", 100, "less than"),
        ("POSITIVE_PADDING", 100, "at least"),
    )
    assert q.param.CONSERVATIVE_UNPADDED_WORD_UPPER_BOUND < 100


def test_basis_iterator_emits_contracts_with_sentence_checker():
    sample = list(islice(q.iter_contexts(), 128))
    assert len(sample) == 128
    for contracts in sample:
        ids = {c["instruction_id"] for c in contracts}
        assert comp.SENTENCES in ids
        sentence = next(c for c in contracts if c["instruction_id"] == comp.SENTENCES)
        slots = sentence["slots"]
        assert slots["relation"] == "at least" or slots["num_sentences"] == 2
