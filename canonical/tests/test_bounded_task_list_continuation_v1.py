from canonical.runtime.bounded_task_list_continuation_v1 import bind_continuations


def test_binds_contiguous_bullet_children_to_parent():
    text = "Create a workbook with two tabs:\n- Summary\n- Details\n"
    out = bind_continuations(text)
    assert out["status"] == "BOUND"
    assert out["block_count"] == 1
    assert out["child_item_count"] == 2
    block = out["blocks"][0]
    assert block["parent"]["action"] == "create"
    assert [x["item"] for x in block["children"]] == ["Summary", "Details"]
    assert block["structural_relation_only"] is True
    assert block["semantic_completeness_claim"] is False


def test_supports_compact_repeated_dash_markers():
    text = "Include the following entities:\n--CB Cash Italy\n--IB Debt Markets Luxembourg\n"
    out = bind_continuations(text)
    assert out["child_item_count"] == 2
    assert [x["marker"] for x in out["blocks"][0]["children"]] == ["--", "--"]


def test_source_spans_round_trip_exactly():
    text = "Prepare two deliverables:\n1. Report\n2. Workbook\n"
    out = bind_continuations(text)
    block = out["blocks"][0]
    p = block["parent"]
    assert text[p["action_span"][0]:p["action_span"][1]].lower() == "prepare"
    for child in block["children"]:
        assert text[child["item_span"][0]:child["item_span"][1]] == child["item"]


def test_non_contiguous_non_list_line_stops_block():
    text = "Create the following:\n- A\nContext sentence\n- B\n"
    out = bind_continuations(text)
    assert out["child_item_count"] == 1
    assert out["blocks"][0]["children"][0]["item"] == "A"


def test_no_colon_no_parent_binding():
    text = "Create the workbook.\n- Summary\n"
    out = bind_continuations(text)
    assert out["status"] == "NO_BOUND_CONTINUATIONS"
    assert out["child_item_count"] == 0


def test_unknown_parent_verb_does_not_bind():
    text = "Teleport the following files:\n- A\n- B\n"
    out = bind_continuations(text)
    assert out["block_count"] == 0


def test_semicolon_parent_fails_closed_by_nonbinding():
    text = "Create this; then include:\n- A\n"
    out = bind_continuations(text)
    assert out["block_count"] == 0


def test_never_claims_p2_or_semantic_completeness():
    out = bind_continuations("Include these:\n* One\n")
    assert out["p2_membership_claim"] is False
    assert out["semantic_completeness_claim"] is False
    assert out["terminal_authority"] is False
