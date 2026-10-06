from __future__ import annotations

import hashlib
import json

from canonical.runtime.matched_success_semantic_coupling_contract_v3 import (
    INPUT_SCHEMA,
    compile_coupling_v3,
)


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def b(label: str) -> str:
    return hashlib.sha1(label.encode()).hexdigest()


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


def make_run(class_id, role, upstream, shape, terminal, success):
    record = {
        "class_id": class_id,
        "run_role": role,
        "upstream_semantic_sha256": upstream,
        "upstream_shape_sha256": shape,
        "terminal_semantic_sha256": terminal,
        "success": success,
    }
    run_sha = digest(record)
    return {
        "upstream_semantic_sha256": upstream,
        "upstream_shape_sha256": shape,
        "terminal_semantic_sha256": terminal,
        "success": success,
        "run_semantics_sha256": run_sha,
        "receipt": {
            "path": f"canonical/verification/{class_id}_{role}.json",
            "git_blob_sha": b(f"{class_id}:{role}"),
            "independent_or_objective": True,
            "class_id": class_id,
            "run_role": role,
            "run_semantics_sha256": run_sha,
            "upstream_semantic_sha256": upstream,
            "terminal_semantic_sha256": terminal,
            "success": success,
        },
    }


def bind_details(class_id, row, details):
    details_sha = digest(details)
    row["details"] = details
    row["details_sha256"] = details_sha
    row["details_receipt"] = {
        "path": f"canonical/verification/{class_id}_details.json",
        "git_blob_sha": b(f"{class_id}:details"),
        "independent_or_objective": True,
        "class_id": class_id,
        "details_sha256": details_sha,
    }


def make_row(class_id, i, *, terminal=None):
    upstream = h(f"{class_id}:true")
    decoy = h(f"{class_id}:decoy")
    shape = h(f"{class_id}:shape")
    terminal = terminal or h(f"{class_id}:terminal")
    row = {
        "class_id": class_id,
        "true_run": make_run(
            class_id, "true", upstream, shape, terminal, True
        ),
        "ablated_run": make_run(
            class_id,
            "ablated",
            decoy,
            shape,
            h(f"{class_id}:ablated-terminal"),
            False,
        ),
        "rescue_run": make_run(
            class_id, "rescue", upstream, shape, terminal, True
        ),
    }
    return row, upstream, terminal


def base():
    rows = []

    cid = "AGENCY_THREE_TOOL_LONG_HORIZON"
    row, upstream, terminal = make_row(cid, 0)
    bind_details(
        cid,
        row,
        {
            "distinct_action_type_count": 3,
            "learned_early_value_sha256": upstream,
            "final_recall_sha256": upstream,
            "intervening_component_boundaries": 2,
            "early_value_replayed_to_final_stage": False,
            "oversight_requested_after_start": False,
        },
    )
    rows.append(row)

    cid = "INSTRUCTION_CHANGE_CONTROL"
    row, upstream, terminal = make_row(cid, 1)
    lineage = h(cid + ":lineage")
    bind_details(
        cid,
        row,
        {
            "prechange_semantic_sha256": upstream,
            "prechange_task_lineage_sha256": lineage,
            "postchange_task_lineage_sha256": lineage,
            "mutation_sha256": h(cid + ":mutation"),
            "revised_output_semantic_sha256": terminal,
            "stale_prechange_output_passes_postchange": False,
            "revised_output_passes_postchange": True,
        },
    )
    rows.append(row)

    for cid in (
        "RESEARCH_TOOL_ARTIFACT",
        "DELEGATION_SYNTHESIS_ARTIFACT",
    ):
        row, upstream, terminal = make_row(cid, 2)
        synthesis = h(cid + ":synthesis")
        bind_details(
            cid,
            row,
            {
                "producer_projection_sha256": upstream,
                "synthesis_bound_upstream_sha256": upstream,
                "synthesis_projection_sha256": synthesis,
                "artifact_bound_upstream_sha256": synthesis,
                "artifact_semantic_sha256": terminal,
            },
        )
        rows.append(row)

    cid = "BROWSER_MEMORY_RECOVERY"
    row, upstream, terminal = make_row(cid, 4)
    bind_details(
        cid,
        row,
        {
            "early_browser_projection_sha256": upstream,
            "retained_memory_sha256": upstream,
            "recovered_state_semantic_sha256": terminal,
            "observable_failure_injected": True,
            "recovery_passes": True,
            "goal_relevant_state_preserved": True,
        },
    )
    rows.append(row)

    cid = "CODING_DEBUG_TOOL_DISCOVERY"
    row, upstream, terminal = make_row(cid, 5)
    bind_details(
        cid,
        row,
        {
            "premutation_solution_sha256": upstream,
            "mutated_failure_sha256": h(cid + ":mutated"),
            "repaired_output_semantic_sha256": terminal,
            "debug_localizes_injected_failure": True,
            "tool_route_admissible": True,
            "repaired_output_passes_original_oracle": True,
        },
    )
    rows.append(row)

    cid = "CROSS_CAPABILITY_HANDOFF_ROLLBACK"
    upstream = h(cid + ":pre")
    row, _, _ = make_row(cid, 6, terminal=upstream)
    # Rebuild intervention so its true upstream is exactly the pre-state.
    shape = h(cid + ":shape")
    row["true_run"] = make_run(cid, "true", upstream, shape, upstream, True)
    row["ablated_run"] = make_run(
        cid,
        "ablated",
        h(cid + ":decoy"),
        shape,
        h(cid + ":bad-terminal"),
        False,
    )
    row["rescue_run"] = make_run(
        cid, "rescue", upstream, shape, upstream, True
    )
    bind_details(
        cid,
        row,
        {
            "pre_mutation_state_sha256": upstream,
            "mutated_state_sha256": h(cid + ":mutated"),
            "post_rollback_state_sha256": upstream,
            "state_restoration_independently_verified": True,
        },
    )
    rows.append(row)

    return {"schema": INPUT_SCHEMA, "classes": rows}


def row(doc, class_id):
    return next(x for x in doc["classes"] if x["class_id"] == class_id)


def test_valid_content_bound_interventional_shape_passes_candidate_compiler():
    out = compile_coupling_v3(base())
    assert out["status"] == (
        "PASS__CONTENT_BOUND_INTERVENTIONAL_SEMANTIC_COUPLING_V3"
    )
    assert out["class_count"] == 7
    assert out["independent_receipt_bytes_verified"] is False
    assert out["independent_exact_receipt_verification_required"] is True


def test_run_field_change_under_old_digest_fails_closed():
    x = base()
    r = row(x, "BROWSER_MEMORY_RECOVERY")["true_run"]
    r["terminal_semantic_sha256"] = h("fabricated-terminal")
    out = compile_coupling_v3(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "RUN_SEMANTICS_SHA256_MISMATCH" in out["errors"][0]


def test_recomputed_run_digest_under_old_receipt_fails_closed():
    x = base()
    cid = "BROWSER_MEMORY_RECOVERY"
    r = row(x, cid)["true_run"]
    r["terminal_semantic_sha256"] = h("fabricated-terminal")
    r["run_semantics_sha256"] = digest(
        {
            "class_id": cid,
            "run_role": "true",
            "upstream_semantic_sha256": r["upstream_semantic_sha256"],
            "upstream_shape_sha256": r["upstream_shape_sha256"],
            "terminal_semantic_sha256": r["terminal_semantic_sha256"],
            "success": r["success"],
        }
    )
    out = compile_coupling_v3(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "RUN_SEMANTICS_SHA256_MISMATCH" in out["errors"][0]


def test_details_change_under_old_digest_fails_closed():
    x = base()
    d = row(x, "CODING_DEBUG_TOOL_DISCOVERY")["details"]
    d["debug_localizes_injected_failure"] = False
    out = compile_coupling_v3(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "DETAILS_SHA256_MISMATCH" in out["errors"][0]


def test_recomputed_details_digest_under_old_receipt_fails_closed():
    x = base()
    r = row(x, "CODING_DEBUG_TOOL_DISCOVERY")
    r["details"]["debug_localizes_injected_failure"] = False
    r["details_sha256"] = digest(r["details"])
    out = compile_coupling_v3(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "DETAILS_SHA256_MISMATCH" in out["errors"][0]


def test_same_semantic_decoy_fails_closed():
    x = base()
    cid = "RESEARCH_TOOL_ARTIFACT"
    r = row(x, cid)
    true = r["true_run"]
    r["ablated_run"] = make_run(
        cid,
        "ablated",
        true["upstream_semantic_sha256"],
        true["upstream_shape_sha256"],
        h(cid + ":different-terminal"),
        False,
    )
    out = compile_coupling_v3(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "DECOY_NOT_SEMANTICALLY_DISTINCT" in out["errors"][0]


def test_different_shape_decoy_fails_closed():
    x = base()
    cid = "RESEARCH_TOOL_ARTIFACT"
    r = row(x, cid)
    r["ablated_run"] = make_run(
        cid,
        "ablated",
        h(cid + ":decoy2"),
        h(cid + ":wrong-shape"),
        h(cid + ":different-terminal"),
        False,
    )
    out = compile_coupling_v3(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "UPSTREAM_SHAPE_MISMATCH" in out["errors"][0]


def test_details_projection_must_anchor_to_intervention():
    x = base()
    r = row(x, "RESEARCH_TOOL_ARTIFACT")
    r["details"]["producer_projection_sha256"] = h("unrelated-producer")
    r["details_sha256"] = digest(r["details"])
    r["details_receipt"]["details_sha256"] = r["details_sha256"]
    out = compile_coupling_v3(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "PRODUCER_NOT_BOUND_TO_TRUE_UPSTREAM" in out["errors"][0]


def test_receipt_binding_requires_exact_class_and_role():
    x = base()
    r = row(x, "AGENCY_THREE_TOOL_LONG_HORIZON")["true_run"]
    r["receipt"]["run_role"] = "rescue"
    out = compile_coupling_v3(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "RUN_ROLE_MISMATCH" in out["errors"][0]


def test_independence_flag_is_required_but_not_claimed_as_byte_verification():
    x = base()
    r = row(x, "AGENCY_THREE_TOOL_LONG_HORIZON")["details_receipt"]
    r["independent_or_objective"] = False
    out = compile_coupling_v3(x)
    assert out["status"] == "FAIL_CLOSED"
