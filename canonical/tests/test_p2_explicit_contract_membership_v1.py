import json

from canonical.runtime.p2_explicit_contract_membership_v1 import compile_membership
from canonical.runtime.p2_strong_quality_visible_certifier_v4 import certify
from canonical.runtime.p2_explicit_contract_membership_v1 import P2


def raw_source(extra_task=None):
    task = {
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
    }
    if extra_task:
        task.update(extra_task)
    return json.dumps({"contract": P2, "task": task}, separators=(",", ":"))


def quality_binding():
    return {
        # A forged caller membership flag should be irrelevant to v4.
        "lossless_p2_membership_proved": False,
        "lossless_p2_membership_receipt": "",
        "baseline_layout_nonobscuring": True,
        "baseline_layout_receipt": "l1",
        "mechanics_only_baseline_equals_empty_p2_plan": True,
        "mechanics_only_baseline_equivalence_receipt": "b-empty",
        "ablation_rescue_semantics_bound_to_certifier_policy": True,
        "ablation_rescue_semantics_receipt": "a1",
        "native_mechanical_gate_required": False,
        "explicit_rubric_equivalent_to_p2_objective": True,
        "rubric_equivalence_receipt": "r1",
    }


def test_strict_explicit_source_gets_recomputed_membership():
    out = compile_membership(raw_source(), source_id="task")
    assert out["pass"] is True, out
    assert out["membership_receipt"].startswith("P2MEM:")


def test_wrapper_ignores_caller_membership_flag_and_recomputes_it():
    out = certify({
        "raw_p2_source": raw_source(),
        "raw_p2_source_id": "task",
        "quality_binding": quality_binding(),
    })
    assert out["pass"] is True, out
    assert out["membership_self_assertion_permitted"] is False
    assert out["membership"]["pass"] is True


def test_extra_task_dimension_blocks_membership():
    out = compile_membership(
        raw_source({"hidden_priority": "CEO preference"}),
        source_id="task",
    )
    assert out["pass"] is False
    assert "TASK_KEYS_NOT_EXACT_P2_BASIS" in out["errors"]


def test_extra_evidence_text_blocks_membership_as_outside_contract_semantics():
    raw = json.dumps({
        "contract": P2,
        "task": {
            "audience": "executive",
            "required_topics": ["T1"],
            "evidence": [{"fact_id": "F1", "text": "load bearing prose"}],
            "edit_candidates": [{
                "id": "E1", "analysis_kind": "quantify", "topic": "T1",
                "claims": ["F1"], "intended_audience": "executive", "cost": 1,
            }],
            "edit_budget": 1,
        },
    })
    out = compile_membership(raw, source_id="task")
    assert out["pass"] is False
    assert any(x.startswith("EVIDENCE_ROW_KEYS_INVALID") for x in out["errors"])


def test_duplicate_fact_id_fails_closed():
    raw = json.dumps({
        "contract": P2,
        "task": {
            "audience": "executive",
            "required_topics": ["T1"],
            "evidence": [{"fact_id": "F1"}, {"fact_id": "F1"}],
            "edit_candidates": [{
                "id": "E1", "analysis_kind": "quantify", "topic": "T1",
                "claims": ["F1"], "intended_audience": "executive", "cost": 1,
            }],
            "edit_budget": 1,
        },
    })
    out = compile_membership(raw, source_id="task")
    assert out["pass"] is False
    assert "FACT_ID_DUPLICATE:F1" in out["errors"]


def test_wrapper_blocks_nonmember_source_before_quality_certifier():
    out = certify({
        "raw_p2_source": raw_source({"extra_dimension": "x"}),
        "raw_p2_source_id": "task",
        "quality_binding": quality_binding(),
    })
    assert out["pass"] is False
    assert "LOSSLESS_P2_MEMBERSHIP_RECOMPUTE_FAILED" in out["errors"]
