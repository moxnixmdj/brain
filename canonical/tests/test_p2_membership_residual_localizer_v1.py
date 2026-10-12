import json

from canonical.runtime.p2_membership_residual_localizer_v1 import localize
from canonical.runtime.p2_explicit_contract_membership_v1 import P2


def valid():
    return {
        "contract": P2,
        "task": {
            "audience": "executive",
            "required_topics": ["T1"],
            "evidence": [{"fact_id": "F1"}],
            "edit_candidates": [{
                "id": "E1",
                "analysis_kind": "quantify",
                "topic": "T1",
                "claims": ["F1"],
                "intended_audience": "executive",
                "cost": 1,
            }],
            "edit_budget": 1,
        },
    }


def test_exact_explicit_context_passes():
    out = localize(json.dumps(valid()), source_id="task")
    assert out["membership_proved"] is True
    assert out["first_residual_class"] is None


def test_extra_task_dimension_is_localized_not_dropped():
    x = valid()
    x["task"]["producer_roster"] = ["A", "B"]
    out = localize(json.dumps(x), source_id="task")
    assert out["membership_proved"] is False
    assert out["first_residual_class"] == "POTENTIALLY_LOAD_BEARING_EXTRA_SEMANTICS"
    assert out["first_residual"]["path"] == "task.producer_roster"
    assert "IRRELEVANT" in out["next_action"]


def test_missing_audience_is_named_exactly():
    x = valid()
    del x["task"]["audience"]
    out = localize(json.dumps(x), source_id="task")
    assert out["first_residual_class"] == "MISSING_P2_SEMANTIC_FIELD"
    assert out["first_residual"]["path"] == "task.audience"


def test_extra_evidence_semantics_are_not_silently_projected():
    x = valid()
    x["task"]["evidence"][0]["source_vintage"] = "2026-Q3"
    out = localize(json.dumps(x), source_id="task")
    assert out["first_residual_class"] == "POTENTIALLY_LOAD_BEARING_EXTRA_SEMANTICS"
    assert out["first_residual"]["path"] == "task.evidence[0].source_vintage"


def test_free_form_source_becomes_raw_to_typed_residual():
    out = localize(
        "Prepare an executive workbook using all current pricing sources.",
        source_id="task",
    )
    assert out["status"] == "UNRESOLVED"
    assert out["first_residual_class"] == "RAW_TO_TYPED_P2_SEMANTIC_COMPILATION"
    assert out.get("semantic_omission_leaves_context_unresolved", True) is True


def test_declared_structural_preflight_failure_dominates_semantic_work():
    manifest = {
        "sources": [{
            "source_id": "pricing.xlsx",
            "required": True,
            "parsed": False,
            "content_sha256": "abc",
            "parser_receipt": "r",
            "authority_rank": 0,
        }],
        "required_dimension_ids": ["pricing"],
        "dimensions": [{
            "dimension_id": "pricing",
            "source_ids": ["pricing.xlsx"],
            "coverage_receipt": "c",
        }],
        "required_convention_ids": [],
        "conventions": [],
    }
    out = localize(
        json.dumps(valid()),
        source_id="task",
        structural_manifest=manifest,
    )
    assert out["status"] == "BLOCKED"
    assert out["first_residual_class"] == "DECLARED_STRUCTURAL_PREFLIGHT_FAILURE"
