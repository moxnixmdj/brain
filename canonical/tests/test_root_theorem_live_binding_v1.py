from copy import deepcopy
from pathlib import Path

from canonical.runtime.root_theorem_live_binding_v1 import (
    git_blob_sha,
    validate_documents,
    validate_repo,
)


def docs():
    mission = {
        "real_objective": "REAL_OBJECTIVE",
    }
    theorem = {
        "terminal_objective_unchanged": "REAL_OBJECTIVE",
        "mission_objective_binding": {
            "path": "canonical/governance/CURRENT_MISSION_OBJECTIVE.json",
            "git_blob_sha": "mission-sha",
            "real_objective": "REAL_OBJECTIVE",
        },
        "checkpoint_objective": {
            "role": "CURRENT_FRONTIER_CHECKPOINT_AND_ACCEPTANCE_LEDGER_ONLY",
        },
    }
    binding = {
        "root_theorem": {
            "path": "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json",
            "git_blob_sha": "theorem-sha",
        },
        "mission_objective": {"git_blob_sha": "mission-sha"},
        "accounting": {"terminal_credit_delta": 0},
    }
    authority = {
        "terminal_objective": "REAL_OBJECTIVE",
        "objective_precedence": {
            "authoritative_path": "canonical/governance/CURRENT_MISSION_OBJECTIVE.json",
            "authoritative_git_blob_sha": "mission-sha",
            "real_objective": "REAL_OBJECTIVE",
        },
        "authoritative_sources": {
            "coverage_completeness_root_theorem_r1_r4": {
                "path": "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_LIVE_BINDING_V1.json",
                "git_blob_sha": "binding-sha",
            }
        },
    }
    return mission, theorem, binding, authority


def check(mission, theorem, binding, authority):
    return validate_documents(
        mission=mission,
        mission_blob_sha="mission-sha",
        root_theorem=theorem,
        root_theorem_blob_sha="theorem-sha",
        binding=binding,
        binding_blob_sha="binding-sha",
        authority=authority,
    )


def test_minimal_valid_binding_passes_zero_credit():
    out = check(*docs())
    assert out["pass"] is True
    assert out["terminal_credit_delta"] == 0
    assert out["root_closed_claimed"] is False


def test_stale_authority_mission_blob_is_r4_failure():
    mission, theorem, binding, authority = docs()
    authority["objective_precedence"]["authoritative_git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, authority)
    assert out["pass"] is False
    assert "TERMINAL_AUTHORITY_MISSION_BLOB_STALE" in out["errors"]


def test_root_theorem_mission_binding_drift_fails():
    mission, theorem, binding, authority = docs()
    theorem["mission_objective_binding"]["git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, authority)
    assert "ROOT_THEOREM_MISSION_BLOB_STALE" in out["errors"]


def test_live_authority_missing_root_binding_fails():
    mission, theorem, binding, authority = docs()
    authority["authoritative_sources"] = {}
    out = check(mission, theorem, binding, authority)
    assert "LIVE_AUTHORITY_ROOT_BINDING_MISSING" in out["errors"]


def test_binding_to_old_root_blob_fails():
    mission, theorem, binding, authority = docs()
    binding["root_theorem"]["git_blob_sha"] = "old-root"
    out = check(mission, theorem, binding, authority)
    assert "BINDING_ROOT_BLOB_STALE" in out["errors"]


def test_binding_cannot_award_terminal_credit():
    mission, theorem, binding, authority = docs()
    binding["accounting"]["terminal_credit_delta"] = 1
    out = check(mission, theorem, binding, authority)
    assert "BINDING_ZERO_CREDIT_VIOLATION" in out["errors"]


def test_real_objective_drift_fails():
    mission, theorem, binding, authority = docs()
    theorem["terminal_objective_unchanged"] = "OLD_CHECKPOINT"
    out = check(mission, theorem, binding, authority)
    assert "ROOT_THEOREM_REAL_OBJECTIVE_DRIFT" in out["errors"]


def test_git_blob_sha_is_content_addressed():
    assert git_blob_sha(b"hello") == "b6fc4c620b67d95f953a5c1c1230aaab5db5a1b0"


def test_current_repo_live_binding_passes():
    root = Path(__file__).resolve().parents[2]
    out = validate_repo(root)
    assert out["pass"] is True, out
    assert out["terminal_credit_delta"] == 0
