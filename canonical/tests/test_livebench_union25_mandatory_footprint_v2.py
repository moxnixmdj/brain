from canonical.runtime import livebench_union25_mandatory_footprint_v1 as v1
from canonical.runtime.livebench_union25_mandatory_footprint_v2 import (
    strengthened_mandatory_footprint,
    proved_upper_bound_losses,
)


def c(iid, **slots):
    return {"instruction_id": iid, "slots": slots}


def test_separated_structural_letter_floors_add():
    contracts = [
        c("keywords:letter_frequency", letter="s", let_relation="less than", let_frequency=5),
        c("detectable_format:multiple_sections", section_spliter="SECTION", num_sections=2),
        c("detectable_content:postscript", postscript_marker="P.S."),
        c("startend:end_checker", end_phrase="Any other questions?"),
    ]

    old = v1.mandatory_footprint(contracts)
    new = strengthened_mandatory_footprint(contracts)

    # V1 deliberately used MAX: SECTION*2 -> 2, P.S. -> 1, ending -> 2.
    assert old["letter_frequency"]["mandatory_floor"] == 2

    # These fixed structural spans cannot alias, so their forced s counts add:
    # 2*SECTION (2) + P.S. (1) + "Any other questions?" (2) = 5.
    assert new["letter_frequency"]["separated_structural_floor"] == 5
    assert new["letter_frequency"]["mandatory_floor"] == 5

    losses = proved_upper_bound_losses(contracts)
    assert len(losses) == 1
    assert losses[0]["checker_id"] == "keywords:letter_frequency"
    assert losses[0]["mandatory_floor"] == 5
    assert losses[0]["strict_upper_bound"] == 5


def test_unlocated_existence_is_not_unsafely_added():
    contracts = [
        c("keywords:letter_frequency", letter="s", let_relation="less than", let_frequency=4),
        c("detectable_format:multiple_sections", section_spliter="SECTION", num_sections=2),
        c("keywords:existence", keywords=["sassy"]),
    ]
    fp = strengthened_mandatory_footprint(contracts)

    # Structural sum is 2. "sassy" forces 3 s characters, but existence may
    # share placement with other material, so V2 conservatively takes MAX=3.
    assert fp["letter_frequency"]["separated_structural_floor"] == 2
    assert fp["letter_frequency"]["unlocated_max_floor"] == 3
    assert fp["letter_frequency"]["mandatory_floor"] == 3
    assert proved_upper_bound_losses(contracts) == ()


def test_section_multiplicity_remains_additive_for_keyword_frequency():
    contracts = [
        c("keywords:frequency", keyword="section", relation="less than", frequency=3),
        c("detectable_format:multiple_sections", section_spliter="Section", num_sections=3),
    ]
    fp = strengthened_mandatory_footprint(contracts)
    assert fp["keyword_frequency"]["separated_structural_floor"] == 3
    assert fp["keyword_frequency"]["mandatory_floor"] == 3
    assert len(proved_upper_bound_losses(contracts)) == 1


def test_no_frequency_contracts_preserve_none_shape():
    contracts = [
        c("detectable_content:postscript", postscript_marker="P.P.S"),
        c("startend:end_checker", end_phrase="Is there anything else I can help with?"),
    ]
    fp = strengthened_mandatory_footprint(contracts)
    assert fp["keyword_frequency"]["mandatory_floor"] is None
    assert fp["letter_frequency"]["mandatory_floor"] is None
    assert fp["capital_word_frequency"]["mandatory_floor"] is None
