from pathlib import Path

from canonical.runtime.root_theorem_live_binding_v1 import (
    git_blob_sha,
    validate_documents,
    validate_repo,
)


def docs():
    mission = {"real_objective": "REAL_OBJECTIVE"}
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
        "root_namespace_bridge": {
            "path": "canonical/governance/COVERAGE_ROOT_NAMESPACE_BRIDGE_V1.json",
            "git_blob_sha": "namespace-sha",
        },
        "accounting": {"terminal_credit_delta": 0},
    }
    namespace_bridge = {
        "theorem_namespace": {
            "id": "CCRT",
            "roots": {"R1": "", "R2": "", "R3": "", "R4": ""},
        },
        "legacy_namespaces": {
            "LEGACY_ESCAPE_POLICY_ADEQUACY": {
                "equivalent_to_ccrt_roots": [],
                "can_close_ccrt_root_by_label_identity": False,
            },
            "LEGACY_EFFECT_FINALITY": {
                "equivalent_to_ccrt_roots": [],
                "can_close_ccrt_root_by_label_identity": False,
            },
        },
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
            },
            "coverage_root_namespace_bridge": {
                "path": "canonical/governance/COVERAGE_ROOT_NAMESPACE_BRIDGE_V1.json",
                "git_blob_sha": "namespace-sha",
            },
        },
    }
    return mission, theorem, binding, namespace_bridge, authority


def check(mission, theorem, binding, namespace_bridge, authority):
    return validate_documents(
        mission=mission,
        mission_blob_sha="mission-sha",
        root_theorem=theorem,
        root_theorem_blob_sha="theorem-sha",
        binding=binding,
        binding_blob_sha="binding-sha",
        namespace_bridge=namespace_bridge,
        namespace_bridge_blob_sha="namespace-sha",
        authority=authority,
    )


def test_valid_binding_passes_zero_credit():
    out = check(*docs())
    assert out["pass"] is True
    assert out["terminal_credit_delta"] == 0
    assert out["root_closed_claimed"] is False


def test_stale_mission_blob_fails():
    mission, theorem, binding, namespace_bridge, authority = docs()
    authority["objective_precedence"]["authoritative_git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, namespace_bridge, authority)
    assert "TERMINAL_AUTHORITY_MISSION_BLOB_STALE" in out["errors"]


def test_old_root_blob_fails():
    mission, theorem, binding, namespace_bridge, authority = docs()
    binding["root_theorem"]["git_blob_sha"] = "old"
    out = check(mission, theorem, binding, namespace_bridge, authority)
    assert "BINDING_ROOT_BLOB_STALE" in out["errors"]


def test_zero_credit_is_required():
    mission, theorem, binding, namespace_bridge, authority = docs()
    binding["accounting"]["terminal_credit_delta"] = 1
    out = check(mission, theorem, binding, namespace_bridge, authority)
    assert "BINDING_ZERO_CREDIT_VIOLATION" in out["errors"]


def test_missing_namespace_ref_fails():
    mission, theorem, binding, namespace_bridge, authority = docs()
    binding.pop("root_namespace_bridge")
    out = check(mission, theorem, binding, namespace_bridge, authority)
    assert "BINDING_ROOT_NAMESPACE_PATH_DRIFT" in out["errors"]


def test_missing_namespace_authority_fails():
    mission, theorem, binding, namespace_bridge, authority = docs()
    authority["authoritative_sources"].pop("coverage_root_namespace_bridge")
    out = check(mission, theorem, binding, namespace_bridge, authority)
    assert "LIVE_AUTHORITY_ROOT_NAMESPACE_MISSING" in out["errors"]


def test_legacy_equivalence_fails():
    mission, theorem, binding, namespace_bridge, authority = docs()
    namespace_bridge["legacy_namespaces"]["LEGACY_ESCAPE_POLICY_ADEQUACY"]["equivalent_to_ccrt_roots"] = ["R2"]
    out = check(mission, theorem, binding, namespace_bridge, authority)
    assert "ROOT_NAMESPACE_LEGACY_ESCAPE_POLICY_ADEQUACY_EQUIVALENCE_FORBIDDEN" in out["errors"]


def test_git_blob_sha():
    assert git_blob_sha(b"hello") == "b6fc4c620b67d95f953a5c1c1230aaab5db5a1b0"


def test_current_repo_binding_passes():
    root = Path(__file__).resolve().parents[2]
    out = validate_repo(root)
    assert out["pass"] is True, out
