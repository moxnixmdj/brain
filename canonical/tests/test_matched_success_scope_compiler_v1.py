import hashlib
import json

from canonical.runtime.matched_success_scope_compiler_v1 import (
    INPUT_SCHEMA,
    REQUIRED,
    compile_scope,
)

A40 = "a" * 40
B40 = "b" * 40
A64 = "a" * 64
B64 = "b" * 64
C64 = "c" * 64
D64 = "d" * 64


def base():
    atoms = {k: sorted(v) for k, v in REQUIRED.items()}
    return {
        "schema": INPUT_SCHEMA,
        "freeze": {
            "generator_content_addressed": True,
            "generator_frozen_before_case_exposure": True,
            "post_freeze_beacon_or_equivalent_precommitted_randomness": True,
            "case_count_fixed_before_first_result": True,
            "scorer_content_addressed": True,
            "brain_runtime_content_addressed": True,
            "tool_authority_content_addressed": True,
            "target_interface_content_addressed": True,
            "no_case_replacement_after_exposure": True,
            "no_adaptive_case_selection": True,
            "no_result_dependent_scope_edit": True,
            "generator_git_blob_sha": A40,
            "scorer_git_blob_sha": B40,
            "brain_commit_sha": A40,
            "tool_authority_sha256": A64,
            "target_interface_sha256": B64,
            "fixed_case_count": 1,
        },
        "cases": [
            {
                "case_id": "ALL",
                "case_payload_sha256": C64,
                "case_initial_state_sha256": D64,
                "coverage": {
                    "independently_verified": True,
                    "receipt_sha256": A64,
                    "target_atoms": atoms,
                },
            }
        ],
    }


def test_complete_scope_passes():
    out = compile_scope(base())
    assert out["status"] == "PASS__FINITE_COMPLETE_CONTENT_ADDRESSED_MATCHED_SUCCESS_SCOPE"
    assert out["coverage_complete"] is True
    assert out["required_atom_count"] == 16
    assert len(out["case_manifest_sha256"]) == 64


def test_missing_atom_fails_closed():
    x = base()
    target = "AGENCY_MATCHED_SUCCESS_NONINFERIOR"
    x["cases"][0]["coverage"]["target_atoms"][target].pop()
    out = compile_scope(x)
    assert out["status"] == "FAIL_CLOSED"


def test_unknown_atom_fails_closed():
    x = base()
    target = "IF_SCOPE_BOUNDARY_NONINFERIOR"
    x["cases"][0]["coverage"]["target_atoms"][target].append("dimension:invented")
    out = compile_scope(x)
    assert out["status"] == "FAIL_CLOSED"


def test_adaptive_selection_fails_closed():
    x = base()
    x["freeze"]["no_adaptive_case_selection"] = False
    out = compile_scope(x)
    assert out["status"] == "FAIL_CLOSED"


def test_unverified_coverage_fails_closed():
    x = base()
    x["cases"][0]["coverage"]["independently_verified"] = False
    out = compile_scope(x)
    assert out["status"] == "FAIL_CLOSED"


def test_case_count_mismatch_fails_closed():
    x = base()
    x["freeze"]["fixed_case_count"] = 2
    out = compile_scope(x)
    assert out["status"] == "FAIL_CLOSED"


def test_manifest_binding():
    x = base()
    first = compile_scope(x)
    x["case_manifest_sha256"] = first["case_manifest_sha256"]
    second = compile_scope(x)
    assert second["status"] == "PASS__FINITE_COMPLETE_CONTENT_ADDRESSED_MATCHED_SUCCESS_SCOPE"
    x["cases"][0]["case_payload_sha256"] = B64
    third = compile_scope(x)
    assert third["status"] == "FAIL_CLOSED"
