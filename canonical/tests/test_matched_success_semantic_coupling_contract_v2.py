from canonical.runtime.matched_success_semantic_coupling_contract_v2 import (
    INPUT_SCHEMA,
    compile_coupling,
)


def h(ch):
    return ch * 64


def receipt(ch):
    return {"receipt_sha256": h(ch), "independent_or_objective": True}


def base_row(class_id, n):
    true_up = h(chr(ord("a") + n))
    decoy = h(chr(ord("h") + n))
    terminal = h(chr(ord("o") + n))
    return {
        "class_id": class_id,
        "true_run": {
            "upstream_semantic_sha256": true_up,
            "terminal_semantic_sha256": terminal,
            "success": True,
            "receipt": receipt(chr(ord("a") + n)),
        },
        "ablated_run": {
            "upstream_semantic_sha256": decoy,
            "terminal_semantic_sha256": h(chr(ord("v") + n)),
            "success": False,
            "receipt": receipt(chr(ord("b") + n)),
        },
        "rescue_run": {
            "upstream_semantic_sha256": true_up,
            "terminal_semantic_sha256": terminal,
            "success": True,
            "receipt": receipt(chr(ord("c") + n)),
        },
        "details": {},
    }


def base():
    classes = []

    r = base_row("AGENCY_THREE_TOOL_LONG_HORIZON", 0)
    learned = h("d")
    r["details"] = {
        "distinct_action_type_count": 3,
        "learned_early_value_sha256": learned,
        "final_recall_sha256": learned,
        "intervening_component_boundaries": 2,
        "early_value_replayed_to_final_stage": False,
        "oversight_requested_after_start": False,
    }
    classes.append(r)

    r = base_row("INSTRUCTION_CHANGE_CONTROL", 1)
    lineage = h("e")
    r["details"] = {
        "prechange_task_lineage_sha256": lineage,
        "postchange_task_lineage_sha256": lineage,
        "mutation_sha256": h("f"),
        "stale_prechange_output_passes_postchange": False,
        "revised_output_passes_postchange": True,
    }
    classes.append(r)

    for i, cid in enumerate(
        ["RESEARCH_TOOL_ARTIFACT", "DELEGATION_SYNTHESIS_ARTIFACT"],
        start=2,
    ):
        r = base_row(cid, i)
        producer = h("1")
        synthesis = h("2")
        r["details"] = {
            "producer_projection_sha256": producer,
            "synthesis_bound_upstream_sha256": producer,
            "synthesis_projection_sha256": synthesis,
            "artifact_bound_upstream_sha256": synthesis,
        }
        classes.append(r)

    r = base_row("BROWSER_MEMORY_RECOVERY", 4)
    early = h("3")
    r["details"] = {
        "early_browser_projection_sha256": early,
        "retained_memory_sha256": early,
        "observable_failure_injected": True,
        "recovery_passes": True,
        "goal_relevant_state_preserved": True,
    }
    classes.append(r)

    r = base_row("CODING_DEBUG_TOOL_DISCOVERY", 5)
    r["details"] = {
        "premutation_solution_sha256": h("4"),
        "mutated_failure_sha256": h("5"),
        "debug_localizes_injected_failure": True,
        "tool_route_admissible": True,
        "repaired_output_passes_original_oracle": True,
    }
    classes.append(r)

    r = base_row("CROSS_CAPABILITY_HANDOFF_ROLLBACK", 6)
    pre = h("6")
    r["details"] = {
        "pre_mutation_state_sha256": pre,
        "mutated_state_sha256": h("7"),
        "post_rollback_state_sha256": pre,
        "state_restoration_independently_verified": True,
    }
    classes.append(r)

    return {"schema": INPUT_SCHEMA, "classes": classes}


def row(doc, class_id):
    return next(x for x in doc["classes"] if x["class_id"] == class_id)


def test_valid_interventional_certificate_passes():
    out = compile_coupling(base())
    assert out["status"] == "PASS__INTERVENTIONAL_SEMANTIC_COUPLING_CONTRACT"
    assert out["class_count"] == 7
    assert out["receipt_acknowledgement_only_sufficient"] is False


def test_ack_only_false_positive_is_rejected_when_ablation_still_passes():
    x = base()
    row(x, "RESEARCH_TOOL_ARTIFACT")["ablated_run"]["success"] = True
    out = compile_coupling(x)
    assert out["status"] == "FAIL_CLOSED"


def test_memory_replay_to_final_stage_is_rejected():
    x = base()
    row(x, "AGENCY_THREE_TOOL_LONG_HORIZON")["details"][
        "early_value_replayed_to_final_stage"
    ] = True
    out = compile_coupling(x)
    assert out["status"] == "FAIL_CLOSED"


def test_unrelated_requirement_change_case_is_rejected():
    x = base()
    row(x, "INSTRUCTION_CHANGE_CONTROL")["details"][
        "postchange_task_lineage_sha256"
    ] = h("9")
    out = compile_coupling(x)
    assert out["status"] == "FAIL_CLOSED"


def test_hash_ack_without_artifact_semantic_binding_is_rejected():
    x = base()
    row(x, "DELEGATION_SYNTHESIS_ARTIFACT")["details"][
        "artifact_bound_upstream_sha256"
    ] = h("8")
    out = compile_coupling(x)
    assert out["status"] == "FAIL_CLOSED"


def test_rollback_ack_without_real_state_restore_is_rejected():
    x = base()
    row(x, "CROSS_CAPABILITY_HANDOFF_ROLLBACK")["details"][
        "post_rollback_state_sha256"
    ] = h("0")
    out = compile_coupling(x)
    assert out["status"] == "FAIL_CLOSED"


def test_rescue_must_restore_true_semantics():
    x = base()
    row(x, "BROWSER_MEMORY_RECOVERY")["rescue_run"][
        "terminal_semantic_sha256"
    ] = h("9")
    out = compile_coupling(x)
    assert out["status"] == "FAIL_CLOSED"
