from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract


def test_every_nonwhitespace_source_segment_survives_as_acceptance_obligation():
    text = "Create a report. It must include revenue. Keep it under 500 words."
    out = compile_contract(
        text,
        source_id="user",
        routing_target_effects=["report.created"],
    )
    assert out["pass"] is True, out
    assert out["nonwhitespace_source_coverage_complete"] is True
    assert len(out["acceptance_contract"]["obligations"]) == 3
    reconstructed = "".join(
        text[a:b]
        for a, b in [row["span"] for row in out["acceptance_contract"]["obligations"]]
    )
    assert "Create a report." in reconstructed
    assert "It must include revenue." in reconstructed
    assert "Keep it under 500 words." in reconstructed


def test_coarse_routing_effect_cannot_delete_unrepresented_constraint():
    text = "Create a PDF. It must be under 1 MB."
    out = compile_contract(
        text,
        source_id="user",
        routing_target_effects=["pdf.created"],
    )
    assert out["pass"] is True
    assert out["routing_contract"]["success_authority"] is False
    segments = [x["text"] for x in out["acceptance_contract"]["obligations"]]
    assert "It must be under 1 MB." in segments
    assert all(x["acceptance_receipt_required"] for x in out["acceptance_contract"]["obligations"])


def test_explicit_requirement_index_adds_structure_but_does_not_replace_raw_obligation():
    text = "The workbook must include producer roster."
    out = compile_contract(
        text,
        source_id="user",
        routing_target_effects=["workbook.created"],
    )
    row = out["acceptance_contract"]["obligations"][0]
    assert row["structured_requirement_ids"]
    assert row["kind"] == "RAW_SOURCE_SEGMENT_ACCEPTANCE"
    assert row["acceptance_receipt_required"] is True


def test_semantic_goal_contract_is_optional_routing_aid_not_acceptance_authority():
    text = "Create a report. Keep it concise."
    import hashlib
    sha = hashlib.sha256(text.encode()).hexdigest()
    grounding = list(range(len(text)))
    semantic = {
        "status": "QUORUM_VERIFIED",
        "goal_sha256": sha,
        "target_effects": ["report.created"],
        "grounding": {"report.created": grounding},
    }
    out = compile_contract(
        text,
        source_id="user",
        routing_target_effects=["report.created"],
        semantic_goal_contract=semantic,
    )
    assert out["pass"] is True
    assert out["routing_contract"]["grounding"]["report.created"]
    assert out["acceptance_contract"]["raw_source_is_final_semantic_reference"] is True
    assert out["acceptance_contract"]["routing_effects_define_success"] is False


def test_mismatched_semantic_goal_contract_cannot_redefine_task():
    text = "Create a report."
    bad = {
        "status": "QUORUM_VERIFIED",
        "goal_sha256": "0" * 64,
        "target_effects": ["report.created"],
        "grounding": {"report.created": [0]},
    }
    out = compile_contract(
        text,
        source_id="user",
        routing_target_effects=["report.created"],
        semantic_goal_contract=bad,
    )
    assert out["pass"] is False
    assert any("SEMANTIC_GOAL_CONTRACT_HASH_MISMATCH" in x for x in out["errors"])
