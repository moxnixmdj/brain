from canonical.runtime.matched_coding_debug_tool_discovery_fresh_v1 import (
    CASE_COUNT,
    FAMILIES,
    derive_hidden_case,
    discover_patch,
    execute_case,
    run_fresh_batch,
)

BEACON_A = "PREEXPOSURE-TEST-BEACON-A-0123456789abcdef"
BEACON_B = "PREEXPOSURE-TEST-BEACON-B-fedcba9876543210"


def test_hidden_generation_is_deterministic_and_beacon_sensitive():
    a1 = derive_hidden_case(BEACON_A, 0)
    a2 = derive_hidden_case(BEACON_A, 0)
    b = derive_hidden_case(BEACON_B, 0)
    assert a1 == a2
    assert a1["case_payload_sha256"] != b["case_payload_sha256"]
    assert a1["hidden_holdout_sha256"] != b["hidden_holdout_sha256"]


def test_four_ordinals_cover_four_predeclared_structural_families():
    got = [derive_hidden_case(BEACON_A, i)["hidden_spec"]["family_id"] for i in range(CASE_COUNT)]
    assert got == list(FAMILIES)


def test_candidate_patch_selection_never_needs_hidden_spec():
    for i in range(CASE_COUNT):
        hidden = derive_hidden_case(BEACON_A, i)
        patch = discover_patch(hidden["public_rows"])
        assert patch["status"] == "EXACT_PUBLIC_TEST_PATCH_FOUND"
        assert patch["family_id"] == hidden["hidden_spec"]["family_id"]


def test_fresh_cases_execute_end_to_end():
    for i in range(CASE_COUNT):
        row = execute_case(BEACON_A, i)
        assert row["pass"] is True, row
        assert row["candidate_visible_hidden_spec"] is False
        assert row["initial_test_failed"] is True
        assert row["tool_discovery"]["selected_tool"] == "generic_patch_search"
        assert row["public_test_after_patch_pass"] is True
        assert row["hidden_holdout"]["pass"] is True
        assert row["git_diff_check_pass"] is True
        assert row["coding_finish_gate"]["pass"] is True


def test_batch_passes_and_payloads_are_unique():
    out = run_fresh_batch(BEACON_A)
    assert out["all_pass"] is True, out
    assert out["passed"] == CASE_COUNT
    assert len(set(out["case_payload_sha256s"])) == CASE_COUNT


def test_objective_trace_preserves_coding_debug_tool_discovery_chain():
    row = execute_case(BEACON_A, 2)
    kinds = [x["type"] for x in row["objective_trace"]["events"]]
    assert kinds == [
        "CODE_REVISION", "TEST_RESULT", "DEBUG", "TOOL_DISCOVERY",
        "CODE_REVISION", "TEST_RESULT", "TERMINAL",
    ]
    assert row["objective_trace"]["events"][1]["pass"] is False
    assert row["objective_trace"]["events"][2]["failure_observed"] is True
    assert row["objective_trace"]["events"][5]["hidden_holdout_pass"] is True
    assert row["objective_trace"]["events"][-1]["success"] is True
