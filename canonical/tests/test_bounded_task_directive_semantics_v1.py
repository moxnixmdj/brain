from canonical.runtime.bounded_task_directive_semantics_v1 import parse_directive
from canonical.runtime.explicit_obligation_index_v2 import build_index


def test_simple_imperative_binds_action_and_opaque_tail():
    text = "Include metrics A1 and C1, which carry higher risk weightings."
    out = parse_directive(text)
    assert out["status"] == "RESOLVED_ONE_SIDED_DIRECTIVE_HEAD"
    d = out["directive"]
    assert d["action"] == "include"
    assert d["directive_tail"] == "metrics A1 and C1, which carry higher risk weightings"
    assert text[d["action_span"][0]:d["action_span"][1]].lower() == "include"
    assert text[d["directive_tail_span"][0]:d["directive_tail_span"][1]] == d["directive_tail"]
    assert out["semantic_completeness_claim"] is False
    assert out["coordination_split_performed"] is False


def test_coordinated_predicate_is_preserved_not_split():
    text = "Calculate variance and capture the result in column J."
    out = parse_directive(text)
    assert out["status"] == "RESOLVED_ONE_SIDED_DIRECTIVE_HEAD"
    assert out["directive"]["action"] == "calculate"
    assert out["directive"]["directive_tail"] == "variance and capture the result in column J"
    assert out["coordination_split_performed"] is False


def test_list_marker_span_and_action_span_are_source_bound():
    text = "- Ensure coverage across all Divisions and sub-Divisions."
    out = parse_directive(text)
    assert out["status"] == "RESOLVED_ONE_SIDED_DIRECTIVE_HEAD"
    assert text[slice(*out["list_marker_span"])] == "- "
    assert text[slice(*out["directive"]["action_span"])].lower() == "ensure"


def test_unknown_action_verb_remains_unresolved():
    out = parse_directive("Teleport the workbook to the reviewer.")
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "DIRECTIVE_VERB_OUTSIDE_BOUND_SET"


def test_dangling_list_parent_remains_unresolved():
    out = parse_directive("Create a workbook with three tabs:")
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "DIRECTIVE_REQUIRES_CONTINUATION_BINDING"


def test_semicolon_multi_clause_remains_unresolved():
    out = parse_directive("Create the workbook; send it to the reviewer.")
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "SEMICOLON_MULTI_CLAUSE_NOT_BOUND"


def test_v2_preserves_modal_channel_and_adds_directive_channel():
    text = "The report must include revenue.\nInclude costs and taxes."
    out = build_index(text, source_id="task-1")
    assert out["modal_obligation_count"] == 1
    assert out["directive_obligation_count"] == 1
    assert out["obligation_count"] == 2
    assert {x["kind"] for x in out["obligations"]} == {
        "MODAL_PREDICATE_ARGUMENT", "IMPERATIVE_DIRECTIVE_HEAD"
    }
    assert out["semantic_completeness_claim"] is False
    assert out["p2_membership_claim"] is False


def test_v2_unparsed_text_remains_unknown():
    out = build_index("Quarterly financial context and background.", source_id="task-1")
    assert out["obligation_count"] == 0
    assert len(out["unresolved_segments"]) == 1
    assert out["absence_of_indexed_obligation_proves_no_obligation"] is False
