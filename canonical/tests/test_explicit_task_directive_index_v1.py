from canonical.runtime.explicit_task_directive_index_v1 import build_index, classify_segment


def test_direct_imperative_binds_action_and_payload():
    out = classify_segment("Create an Excel workbook with three tabs.")
    assert out["status"] == "RESOLVED"
    assert out["kind"] == "IMPERATIVE_DIRECTIVE"
    assert out["action_head"] == "create"
    assert out["opaque_payload"].startswith("an Excel workbook")


def test_numbered_directive_is_positive():
    out = classify_segment("2. Calculate the required sample size based on a 90% confidence level.")
    assert out["status"] == "RESOLVED"
    assert out["action_head"] == "calculate"


def test_please_directive_is_positive():
    out = classify_segment("Please prepare Bob and Lisa Smith's Individual tax return form 1040.")
    assert out["status"] == "RESOLVED"
    assert out["action_head"] == "prepare"


def test_explicit_assignment_is_positive_but_payload_remains_opaque():
    out = classify_segment("You have been tasked with preparing a detailed amortization schedule.")
    assert out["status"] == "RESOLVED"
    assert out["kind"] == "EXPLICIT_TASK_ASSIGNMENT"
    assert out["action_head"] is None


def test_your_task_assignment_is_positive():
    out = classify_segment("Your task is to create a concise board memo.")
    assert out["status"] == "RESOLVED"
    assert out["kind"] == "EXPLICIT_TASK_ASSIGNMENT"


def test_modal_is_reserved_to_existing_semantic_route():
    out = classify_segment("The report should include a summary.")
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "MODAL_ROUTE_RESERVED"


def test_descriptive_text_remains_unknown():
    out = classify_segment("A descriptive sentence about the engagement.")
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "OUTSIDE_EXPLICIT_DIRECTIVE_GRAMMAR"


def test_index_binds_exact_source_spans_without_completeness_claim():
    source = "Create a workbook. A descriptive sentence. Submit the workbook."
    out = build_index(source, source_id="T1")
    assert out["directive_count"] == 2
    assert out["semantic_completeness_claim"] is False
    assert out["absence_of_indexed_directive_proves_no_directive"] is False
    for row in out["directives"]:
        s, e = row["segment_span"]
        assert source[s:e]
        ps, pe = row["opaque_payload_span"]
        assert source[ps:pe].strip() == row["opaque_payload"].strip()
