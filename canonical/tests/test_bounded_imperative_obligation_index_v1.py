from canonical.runtime.bounded_imperative_predicate_argument_semantics_v1 import parse_imperative
from canonical.runtime.explicit_obligation_index_v1 import build_index as build_v1
from canonical.runtime.explicit_obligation_index_v2 import build_index as build_v2


def test_direct_imperatives_resolve_with_source_spans():
    cases = [
        ("Include metrics A1 and C1.", "include", "metrics A1 and C1"),
        ("- Create a new spreadsheet titled Sample.", "create", "a new spreadsheet titled Sample"),
        ("Please prepare the report.", "prepare", "the report"),
        ("Also mention the ZOPA.", "mention", "the ZOPA"),
    ]
    for text, predicate, obj in cases:
        out = parse_imperative(text)
        assert out["status"] == "RESOLVED", out
        g = out["semantic_graph"]
        assert g["subject"] == "IMPLICIT_ADDRESSEE"
        assert g["subject_span"] is None
        assert g["predicate"] == predicate
        assert g["object"] == obj
        ps, pe = g["predicate_span"]
        os, oe = g["object_span"]
        assert text[ps:pe].lower() == predicate
        assert text[os:oe] == obj


def test_ambiguous_or_incomplete_imperatives_fail_closed_or_unresolved():
    bad = [
        "Select a sample and indicate sampled rows.",
        "Use is common in this context.",
        "Teleport the workbook.",
        "Create a new spreadsheet titled Sample:",
        "Report Overview",
        "Review and testing are important.",
    ]
    for text in bad:
        assert parse_imperative(text)["status"] != "RESOLVED"


def test_v2_preserves_v1_modal_obligation_and_adds_imperative_route():
    text = "The operator must archive the record. Include the receipt in the report."
    v1 = build_v1(text, source_id="T")
    v2 = build_v2(text, source_id="T")
    modal_v1 = [x for x in v1["obligations"]]
    modal_v2 = [x for x in v2["obligations"] if x["route"] == "MODAL"]
    imp_v2 = [x for x in v2["obligations"] if x["route"] == "IMPERATIVE"]
    assert len(modal_v1) == 1
    assert len(modal_v2) == 1
    assert modal_v2[0]["semantic_graph"] == modal_v1[0]["semantic_graph"]
    assert len(imp_v2) == 1
    assert imp_v2[0]["semantic_graph"]["predicate"] == "include"


def test_v2_remains_one_sided_and_never_claims_completeness():
    out = build_v2("Create the report. This paragraph is semantically unresolved.", source_id="T")
    assert out["obligation_count"] == 1
    assert out["unresolved_segments"]
    assert out["one_sided_sound_discovery"] is True
    assert out["absence_of_indexed_obligation_proves_no_obligation"] is False
    assert out["semantic_completeness_claim"] is False


def test_multi_predicate_command_is_not_laundered_into_single_obligation():
    out = build_v2("Select the rows and indicate them in column K.", source_id="T")
    assert out["obligation_count"] == 0
    assert out["unresolved_segments"]
