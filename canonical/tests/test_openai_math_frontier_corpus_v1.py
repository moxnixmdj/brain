from __future__ import annotations

from canonical.runtime.openai_math_frontier_corpus_v1 import (
    SOURCE_SNAPSHOT_SCHEMA,
    compile_snapshot,
)

SHA = "1" * 40

def snapshot():
    return {
        "schema": SOURCE_SNAPSHOT_SCHEMA,
        "source_repository": "openai/math",
        "source_commit_sha": SHA,
        "reported_facts": {
            "manuscripts": 722,
            "families": 372,
            "approx_problems": 4000,
            "average_pro_thinking_hours_per_result": 3,
            "model_identity_disclosed": False,
        },
        "artifact_census": {
            "comparator_challenge_pairs": 405,
            "reasoning_summary_pdfs": 10,
            "formalization_source_entries": 162,
        },
        "source_artifact_bindings": [
            {"path": "README.md", "git_blob_sha": SHA},
            {"path": "CONTENTS.md", "git_blob_sha": SHA},
            {"path": "lean/formalization.yaml", "git_blob_sha": SHA},
            {"path": "lean/ComparatorChallenges/README.md", "git_blob_sha": SHA},
        ],
        "public_solution_exposure": True,
        "direct_target_identity_relation": False,
    }

def test_valid_public_corpus_compiles_with_zero_credit():
    out = compile_snapshot(snapshot())
    assert out["status"].startswith("PASS__")
    assert out["artifact_census"]["comparator_challenge_pairs"] == 405
    assert out["terminal_relation"]["direct_target_identity_proved"] is False
    assert out["terminal_credit_delta"] == 0
    assert out["capability_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False

def test_disclosed_model_identity_claim_fails_closed():
    s = snapshot()
    s["reported_facts"]["model_identity_disclosed"] = True
    out = compile_snapshot(s)
    assert out["status"] == "FAIL_CLOSED"
    assert "MODEL_IDENTITY_MUST_REMAIN_UNDISCLOSED" in out["errors"]

def test_missing_comparator_readme_binding_fails_closed():
    s = snapshot()
    s["source_artifact_bindings"] = [
        x for x in s["source_artifact_bindings"]
        if x["path"] != "lean/ComparatorChallenges/README.md"
    ]
    out = compile_snapshot(s)
    assert out["status"] == "FAIL_CLOSED"
    assert any(e.startswith("MISSING_REQUIRED_SOURCE_BINDINGS:") for e in out["errors"])

def test_public_exposure_cannot_be_laundered_away():
    s = snapshot()
    s["public_solution_exposure"] = False
    out = compile_snapshot(s)
    assert out["status"] == "FAIL_CLOSED"
    assert "PUBLIC_SOLUTION_EXPOSURE_MUST_BE_TRUE" in out["errors"]

def test_direct_target_identity_assertion_fails_closed():
    s = snapshot()
    s["direct_target_identity_relation"] = True
    out = compile_snapshot(s)
    assert out["status"] == "FAIL_CLOSED"
    assert "DIRECT_TARGET_IDENTITY_RELATION_MUST_BE_FALSE" in out["errors"]

def test_bad_commit_sha_fails_closed():
    s = snapshot()
    s["source_commit_sha"] = "not-a-sha"
    out = compile_snapshot(s)
    assert out["status"] == "FAIL_CLOSED"
    assert "SOURCE_COMMIT_SHA_MUST_BE_SHA40" in out["errors"]
