from canonical.runtime.livebench_union25_mandatory_loss_v1 import derive


def c(iid, **slots):
    return {"instruction_id": iid, "slots": slots}


def test_repeat_comma_is_exact_pairwise_impossibility():
    out = derive(
        [
            c("combination:repeat_prompt"),
            c("punctuation:no_comma"),
        ],
        prompt_to_repeat="alpha, beta",
    )
    assert [x["rule_id"] for x in out["mandatory_loss_rules"]] == [
        "REPEAT_PREFIX_COMMA_VS_NO_COMMA"
    ]
    assert derive(
        [c("combination:repeat_prompt"), c("punctuation:no_comma")],
        prompt_to_repeat="alpha beta",
    )["mandatory_loss_rule_count"] == 0


def test_lowercase_english_conflicts_with_both_frozen_section_splitters():
    for splitter in ("Section", "SECTION"):
        out = derive([
            c("detectable_format:multiple_sections", section_spliter=splitter, num_sections=3),
            c("change_case:english_lowercase"),
        ])
        assert any(
            x["rule_id"] == "LOWERCASE_ENGLISH_VS_SECTION_HEADING_CASE"
            for x in out["mandatory_loss_rules"]
        )


def test_uppercase_english_only_conflicts_with_mixed_case_section_splitter():
    mixed = derive([
        c("detectable_format:multiple_sections", section_spliter="Section", num_sections=2),
        c("change_case:english_capital"),
    ])
    upper = derive([
        c("detectable_format:multiple_sections", section_spliter="SECTION", num_sections=2),
        c("change_case:english_capital"),
    ])
    assert mixed["mandatory_loss_rule_count"] == 1
    assert upper["mandatory_loss_rule_count"] == 0


def test_uppercase_section_heading_forces_capital_word_floor():
    impossible = derive([
        c("detectable_format:multiple_sections", section_spliter="SECTION", num_sections=4),
        c("change_case:capital_word_frequency", capital_relation="less than", capital_frequency=4),
    ])
    assert impossible["mandatory_loss_rule_count"] == 1
    rule = impossible["mandatory_loss_rules"][0]
    assert rule["mandatory_capital_word_floor"] == 4
    assert rule["strict_upper_bound"] == 4

    possible_by_this_lower_bound = derive([
        c("detectable_format:multiple_sections", section_spliter="SECTION", num_sections=3),
        c("change_case:capital_word_frequency", capital_relation="less than", capital_frequency=4),
    ])
    assert possible_by_this_lower_bound["mandatory_loss_rule_count"] == 0
