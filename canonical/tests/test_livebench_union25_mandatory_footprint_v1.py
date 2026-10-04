from canonical.runtime.livebench_union25_mandatory_footprint_v1 import (
    mandatory_footprint,
    proved_upper_bound_losses,
)


def c(iid, **slots):
    return {"instruction_id": iid, "slots": slots}


def test_keyword_floor_from_end_phrase():
    contracts = [
        c("keywords:frequency", keyword="help", relation="less than", frequency=1),
        c("startend:end_checker", end_phrase="Is there anything else I can help with?"),
    ]
    fp = mandatory_footprint(contracts)
    assert fp["keyword_frequency"]["mandatory_floor"] == 1
    losses = proved_upper_bound_losses(contracts)
    assert losses[0]["rule_id"].startswith("KEYWORD_FREQUENCY_")


def test_keyword_floor_from_repeated_section_marker():
    contracts = [
        c("keywords:frequency", keyword="section", relation="less than", frequency=2),
        c("detectable_format:multiple_sections", section_spliter="Section", num_sections=2),
    ]
    assert mandatory_footprint(contracts)["keyword_frequency"]["mandatory_floor"] == 2
    assert len(proved_upper_bound_losses(contracts)) == 1


def test_letter_floor_from_pps_marker():
    contracts = [
        c("keywords:letter_frequency", letter="p", let_relation="less than", let_frequency=2),
        c("detectable_content:postscript", postscript_marker="P.P.S"),
    ]
    assert mandatory_footprint(contracts)["letter_frequency"]["mandatory_floor"] == 2
    assert len(proved_upper_bound_losses(contracts)) == 1


def test_letter_floor_from_uppercase_section_repetition():
    contracts = [
        c("keywords:letter_frequency", letter="e", let_relation="less than", let_frequency=3),
        c("detectable_format:multiple_sections", section_spliter="SECTION", num_sections=3),
    ]
    assert mandatory_footprint(contracts)["letter_frequency"]["mandatory_floor"] == 3
    assert len(proved_upper_bound_losses(contracts)) == 1


def test_existence_obligation_uses_max_not_unsafe_sum():
    contracts = [
        c("keywords:frequency", keyword="a", relation="less than", frequency=3),
        c("keywords:existence", keywords=["damage", "apple"]),
    ]
    fp = mandatory_footprint(contracts)
    # damage contains two non-overlapping /a/i matches; apple contains one.
    assert fp["keyword_frequency"]["mandatory_floor"] == 2
    assert len(proved_upper_bound_losses(contracts)) == 0


def test_capital_floor_from_uppercase_section_tokens():
    contracts = [
        c("change_case:capital_word_frequency", capital_relation="less than", capital_frequency=4),
        c("detectable_format:multiple_sections", section_spliter="SECTION", num_sections=4),
    ]
    fp = mandatory_footprint(contracts)
    assert fp["capital_word_frequency"]["mandatory_floor"] == 4
    assert len(proved_upper_bound_losses(contracts)) == 1
