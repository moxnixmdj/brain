from canonical.runtime.bounded_named_container_equivalence_v1 import compare


def test_gdpval_sample_size_calculation_equivalence():
    out = compare({
        "source_requirement": "Include your workings in a second tab titled ‘Sample Size Calculation’.",
        "rubric_criterion": "The workbook contains a worksheet named exactly 'Sample Size Calculation' (case-insensitive, ignoring surrounding spaces).",
    })
    assert out["status"] == "PASS__EQUIVALENT_NAMED_CONTAINER_REQUIREMENT"
    assert out["equivalent"] is True
    assert out["source"]["title"] == "sample size calculation"
    assert out["rubric"]["title"] == "sample size calculation"


def test_tab_sheet_worksheet_lexical_alias_only():
    out = compare({
        "source_requirement": 'Create a sheet named "Selected Sample".',
        "rubric_criterion": 'The spreadsheet has a tab titled exactly "Selected Sample".',
    })
    assert out["equivalent"] is True


def test_title_mismatch_is_not_equivalent():
    out = compare({
        "source_requirement": 'Create a worksheet named "A".',
        "rubric_criterion": 'The workbook contains a worksheet named exactly "B".',
    })
    assert out["status"] == "PASS__DISTINCT_NAMED_CONTAINER_REQUIREMENT"
    assert out["equivalent"] is False


def test_unquoted_general_paraphrase_stays_unknown():
    out = compare({
        "source_requirement": "Put the calculations on another page.",
        "rubric_criterion": "The workbook contains a worksheet named exactly 'Calculation'.",
    })
    assert out["status"] == "UNKNOWN__OUTSIDE_CHECKED_GRAMMAR"
    assert out["equivalent"] is None


def test_no_content_or_ordering_authority():
    out = compare({
        "source_requirement": "Include your workings in a second tab titled ‘Sample Size Calculation’.",
        "rubric_criterion": "The workbook contains a worksheet named exactly 'Sample Size Calculation'.",
    })
    assert out["equivalent"] is True
    assert out["content_requirement_authority"] is False
    assert out["ordering_authority"] is False
    assert out["general_paraphrase_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0


def test_rubric_without_named_container_stays_unknown():
    out = compare({
        "source_requirement": 'Create a sheet named "A".',
        "rubric_criterion": "The workbook is professionally formatted.",
    })
    assert out["status"] == "UNKNOWN__OUTSIDE_CHECKED_GRAMMAR"
