from canonical.runtime import livebench_union25_language_exception_carrier_v2 as c


def test_exact_detector_bucket_repairs_v1_gap():
    assert c.detector_latin_bucket_count("ABCxyz") == 6
    assert c.detector_latin_bucket_count("[\\]^_`") == 6
    assert c.detector_latin_bucket_count("[][][][]") == 8
    assert c.required_carrier_count("[][][][]") == 17


def test_carrier_strictly_dominates_exact_cleaning_bucket():
    samples = [
        "",
        "ABCxyz",
        "[\\]^_`",
        "[][][][]",
        "P.S.+",
        "<<9000001>>",
        "*-* [] 9000001?",
        '"SECTION 1"',
    ]
    for sample in samples:
        n = c.required_carrier_count(sample)
        assert n > 2 * c.detector_latin_bucket_count(sample)
        out = c.inject_before_suffix(sample)
        assert out.count(c.PRIVATE_USE_CARRIER) == n
        assert len(out) < c.DETECTOR_MAX_TEXT_LENGTH


def test_carrier_is_syntax_and_case_neutral():
    inv = c.static_invariants()
    assert inv["codepoint"] == "U+E000"
    assert inv["detector_latin_bucket_gap_count"] == 6
    assert inv["regexp_word_delta_per_char"] == 0
    assert inv["ascii_letter_delta_per_char"] == 0
    assert inv["cased_character_delta_per_char"] == 0
    assert inv["structural_punctuation_delta_per_char"] == 0


def test_static_proof_remains_zero_credit_until_runtime_gate():
    out = c.verify()
    assert out["status"].endswith("INDEPENDENT_LANGDETECT_PROFILE_AND_EXCEPTION_GATE_PENDING")
    assert out["acceptance_credit"] is False
    assert out["family_credit"] is False
    assert out["capability_credit"] is False
    assert out["ownership_credit"] is False
