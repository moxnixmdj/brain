from canonical.runtime.explicit_obligation_index_v1 import build_index


def test_simple_explicit_requirement_is_indexed_with_global_spans():
    text = "Context note. The workbook must include producer roster."
    out = build_index(text, source_id="task")
    assert out["obligation_count"] == 1, out
    row = out["obligations"][0]
    assert row["semantic_graph"]["subject"] == "The workbook"
    assert row["semantic_graph"]["predicate"] == "include"
    assert row["semantic_graph"]["object"] == "producer roster"
    s, e = row["semantic_graph"]["object_span"]
    assert text[s:e] == "producer roster"


def test_explicit_prohibition_is_indexed():
    text = "The workbook must not include conflicting estimates."
    out = build_index(text, source_id="standards")
    assert out["obligation_count"] == 1
    assert out["obligations"][0]["semantic_graph"]["polarity"] == "PROHIBITED"


def test_conditional_requirement_preserves_condition():
    text = "If multiple sizing methods disagree, the workbook must show reconciliation."
    out = build_index(text, source_id="task")
    assert out["obligation_count"] == 1, out
    cond = out["obligations"][0]["condition"]
    assert cond["relation"] == "CONDITION_IF"
    s, e = cond["span"]
    assert text[s:e] == "multiple sizing methods disagree"


def test_compound_clause_is_unresolved_not_guessed():
    text = "The workbook must include pricing and explain margins."
    out = build_index(text, source_id="task")
    assert out["obligation_count"] == 0
    assert len(out["unresolved_segments"]) == 1


def test_pronoun_clause_is_unresolved_not_resolved_by_context():
    text = "A pricing workbook exists. It must include source vintage."
    out = build_index(text, source_id="task")
    assert out["obligation_count"] == 0
    assert len(out["unresolved_segments"]) >= 1


def test_plain_narrative_does_not_create_false_obligation():
    text = "The source pool contains historical pricing data."
    out = build_index(text, source_id="task")
    assert out["obligation_count"] == 0
    assert out["absence_of_indexed_obligation_proves_no_obligation"] is False
