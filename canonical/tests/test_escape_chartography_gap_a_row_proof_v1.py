from canonical.runtime import escape_progress_shared_gap_audit_v5 as v5


def test_chartography_real_public_runner_row_proof_closes_exactly_one_current_row():
    bindings = {
        "CHARTOGRAPHY_TOOLS_GE_89": {
            "proof": {
                "path": "canonical/governance/ESCAPE_ROW_PROOF_CHARTOGRAPHY_TOOLS_GE_89_20261010_V1.json",
                "git_blob_sha": "423417e35cfb834bc390ab7147c80eaa4ff26a94",
            },
            "independent_verification": {
                "path": "canonical/verification/ESCAPE_ROW_PROOF_CHARTOGRAPHY_TOOLS_GE_89_INDEPENDENT_VERIFY_20261010_V1.json",
                "git_blob_sha": "0ae60b111159e9093cac07af526a68be8d9811be",
            },
        }
    }
    out = v5.audit_repo(row_proof_bindings=bindings)
    assert out["pass"] is True, out
    assert out["cc_r3_proved"] is False
    assert out["currentness_errors"] == []
    assert out["authenticated_current_row_proof_count"] == 1
    assert out["binding_path"].endswith("_V8.json")
    assert out["manifest_path"].endswith("_V4.json")

    v4 = out["v4_audit"]
    assert v4["authenticated_row_proof_count"] == 1
    structural = v4["structural_audit"]
    assert structural["closed_row_count"] == 1
    assert structural["open_row_count"] == 12
    rows = {row["obligation_id"]: row for row in structural["rows"]}
    assert rows["CHARTOGRAPHY_TOOLS_GE_89"]["closed"] is True
    assert rows["CHARTOGRAPHY_TOOLS_GE_89"]["missing_predicates"] == []
    assert all(
        row["closed"] is False
        for oid, row in rows.items()
        if oid != "CHARTOGRAPHY_TOOLS_GE_89"
    )


def test_chartography_row_proof_does_not_claim_threshold_or_terminal_credit():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    evidence = json.loads(
        (root / "canonical/evidence/CHARTOGRAPHY_QWEN3VL4B_ZERO_CASE_PREFLIGHT_RUN_38040901506_20261010_V1.json").read_text()
    )
    verify = json.loads(
        (root / "canonical/verification/ESCAPE_ROW_PROOF_CHARTOGRAPHY_TOOLS_GE_89_INDEPENDENT_VERIFY_20261010_V1.json").read_text()
    )
    assert evidence["observed_result"]["observed_outcome"] == "PUBLIC_RUNNER_FEASIBLE"
    assert evidence["safety"]["terminal_or_benchmark_cases_consumed"] == 0
    assert evidence["accounting"]["acceptance_credit_delta"] == 0
    assert evidence["accounting"]["terminal_credit_delta"] == 0
    assert verify["acceptance_authority"] is False
    assert verify["terminal_authority"] is False
