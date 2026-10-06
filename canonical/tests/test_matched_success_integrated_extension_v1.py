from canonical.runtime.matched_success_integrated_extension_v1 import (
    REPETITIONS,
    TARGET_BY_ATOM,
    generate_cases,
    scope_input,
)
from canonical.runtime.matched_success_scope_compiler_v1 import compile_scope

A40 = "a" * 40
B40 = "b" * 40
A64 = "a" * 64
B64 = "b" * 64

def test_rehearsal_generation_is_deterministic_and_complete():
    a = generate_cases("REHEARSAL_COMMITMENT", "REHEARSAL_BEACON")
    b = generate_cases("REHEARSAL_COMMITMENT", "REHEARSAL_BEACON")
    assert a == b
    assert len(a) == 64
    assert len({x["case_id"] for x in a}) == 64
    counts = {}
    for row in a:
        counts[row["primary_atom"]] = counts.get(row["primary_atom"], 0) + 1
    assert set(counts) == set(TARGET_BY_ATOM)
    assert set(counts.values()) == {REPETITIONS}

def test_different_beacon_changes_case_payloads():
    a = generate_cases("REHEARSAL_COMMITMENT", "BEACON_A")
    b = generate_cases("REHEARSAL_COMMITMENT", "BEACON_B")
    assert [x["case_id"] for x in a] == [x["case_id"] for x in b]
    assert [x["case_payload_sha256"] for x in a] != [x["case_payload_sha256"] for x in b]

def test_scope_compiler_rejects_self_certified_rehearsal_manifest():
    doc = scope_input(
        "REHEARSAL_COMMITMENT",
        "REHEARSAL_BEACON",
        generator_git_blob_sha=A40,
        scorer_git_blob_sha=B40,
        brain_commit_sha=A40,
        tool_authority_sha256=A64,
        target_interface_sha256=B64,
    )
    out = compile_scope(doc)
    assert out["status"] == "FAIL_CLOSED"
    assert "COVERAGE_NOT_VERIFIED" in out["errors"][0]


def test_no_cross_case_history_is_embedded_in_initial_state():
    rows = generate_cases("REHEARSAL_COMMITMENT", "REHEARSAL_BEACON")
    assert all(row["case_initial_state"]["cross_case_memory"] is None for row in rows)
    assert all(row["case_initial_state"]["result_history"] == [] for row in rows)
    assert len({row["case_initial_state"]["mutable_namespace"] for row in rows}) == 64


def test_scope_input_has_no_caller_authority_to_mark_coverage_verified():
    doc = scope_input(
        "REHEARSAL_COMMITMENT",
        "REHEARSAL_BEACON",
        generator_git_blob_sha=A40,
        scorer_git_blob_sha=B40,
        brain_commit_sha=A40,
        tool_authority_sha256=A64,
        target_interface_sha256=B64,
    )
    assert all(
        case["coverage"]["independently_verified"] is False
        for case in doc["cases"]
    )
    assert all(
        case["coverage"]["receipt_sha256"] == "0" * 64
        for case in doc["cases"]
    )
