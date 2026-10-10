from pathlib import Path

from canonical.runtime.root_theorem_live_binding_v1 import (
    git_blob_sha,
    validate_documents,
    validate_repo,
)

FORMULA = "FOR_ALL_w1_w2__pi(w1)=pi(w2)_IMPLIES_M(w1)=M(w2)"
MISSION_PATH = "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
THEOREM_PATH = "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json"
CARRIER_PATH = "canonical/governance/MISSION_SUFFICIENT_SEMANTIC_CARRIER_V1.json"
CLAIM_SCOPE_PATH = "canonical/governance/COVERAGE_COMPLETENESS_CLAIM_SCOPE_V1.json"
NAMESPACE_PATH = "canonical/governance/COVERAGE_ROOT_NAMESPACE_BRIDGE_V1.json"


def docs():
    mission = {"real_objective": "REAL_OBJECTIVE"}
    carrier = {
        "required_factorization": {"formula": FORMULA},
        "root_effect": {"new_semantic_root_required": False},
        "current_state": {"terminal_credit_delta": 0},
        "claim_scope": {
            "required_bindings": ["claim_id", "scope_sha256", "semantics_sha256"],
            "global_open_ended_mission_completion_derivable": False,
        },
    }
    theorem = {
        "terminal_objective_unchanged": "REAL_OBJECTIVE",
        "mission_objective_binding": {
            "path": MISSION_PATH,
            "git_blob_sha": "mission-sha",
            "real_objective": "REAL_OBJECTIVE",
        },
        "checkpoint_objective": {
            "role": "CURRENT_FRONTIER_CHECKPOINT_AND_ACCEPTANCE_LEDGER_ONLY",
        },
        "semantic_carrier_precondition": {
            "path": CARRIER_PATH,
            "formula": FORMULA,
            "claim_indexed": True,
            "required_claim_bindings": ["claim_id", "scope_sha256", "semantics_sha256"],
        },
    }
    claim_scope = {
        "mission": {"path": MISSION_PATH, "git_blob_sha": "mission-sha"},
        "root_theorem": {"path": THEOREM_PATH, "git_blob_sha": "theorem-sha"},
        "carrier_factorization": {
            "carrier_governance_path": CARRIER_PATH,
            "carrier_governance_git_blob_sha": "carrier-sha",
            "required_same_claim_bindings": ["claim_id", "scope_sha256", "semantics_sha256"],
            "global_open_ended_mission_completion_derivable": False,
        },
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
    binding = {
        "root_theorem": {"path": THEOREM_PATH, "git_blob_sha": "theorem-sha"},
        "mission_objective": {"git_blob_sha": "mission-sha"},
        "root_namespace_bridge": {"path": NAMESPACE_PATH, "git_blob_sha": "namespace-sha"},
        "semantic_carrier_precondition": {
            "path": CARRIER_PATH,
            "git_blob_sha": "carrier-sha",
            "runtime": {
                "path": "canonical/runtime/mission_carrier_factorization_v1.py",
                "git_blob_sha": "carrier-runtime-sha",
            },
            "tests": {
                "path": "canonical/tests/test_mission_carrier_factorization_v1.py",
                "git_blob_sha": "carrier-tests-sha",
            },
        },
        "claim_scope_precondition": {
            "path": CLAIM_SCOPE_PATH,
            "git_blob_sha": "claim-scope-sha",
        },
        "root_certificate_registry_precondition": {
            "registry_path": "canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json",
            "registry_git_blob_sha": "root-registry-sha",
            "current_pointer_path": "canonical/governance/CURRENT_COVERAGE_COMPLETENESS_ROOT_CERTIFICATES.json",
            "current_pointer_git_blob_sha": "root-registry-pointer-sha",
            "guard_path": "canonical/runtime/coverage_root_certificate_registry_guard_v1.py",
            "guard_git_blob_sha": "root-registry-guard-sha",
            "tests_path": "canonical/tests/test_coverage_root_certificate_registry_guard_v1.py",
            "tests_git_blob_sha": "root-registry-tests-sha",
            "semantic_receipt_verifier": {
                "path": "canonical/runtime/coverage_root_semantic_receipt_v1.py",
                "git_blob_sha": "semantic-receipt-sha",
                "tests_path": "canonical/tests/test_coverage_root_semantic_receipt_v1.py",
                "tests_git_blob_sha": "semantic-receipt-tests-sha",
            },
            "claim_alignment_tests": {
                "path": "canonical/tests/test_root_theorem_registry_claim_alignment_v1.py",
                "git_blob_sha": "registry-alignment-tests-sha",
            },
        },
        "falsifier": {
            "path": "canonical/runtime/root_theorem_falsifier_v1.py",
            "git_blob_sha": "falsifier-sha",
            "tests_path": "canonical/tests/test_root_theorem_falsifier_v1.py",
            "tests_git_blob_sha": "falsifier-tests-sha",
            "r4_binding_tests_path": "canonical/tests/test_root_theorem_r4_binding_coherence_v1.py",
            "r4_binding_tests_git_blob_sha": "r4-tests-sha",
        },
        "live_binding_validator": {
            "path": "canonical/runtime/root_theorem_live_binding_v1.py",
            "git_blob_sha": "live-validator-sha",
            "tests_path": "canonical/tests/test_root_theorem_live_binding_v1.py",
            "tests_git_blob_sha": "live-validator-tests-sha",
        },
        "accounting": {"terminal_credit_delta": 0},
    }
    authority = {
        "terminal_objective": "REAL_OBJECTIVE",
        "objective_precedence": {
            "authoritative_path": MISSION_PATH,
            "authoritative_git_blob_sha": "mission-sha",
            "real_objective": "REAL_OBJECTIVE",
        },
        "authoritative_sources": {
            "coverage_completeness_root_theorem_r1_r4": {
                "path": "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_LIVE_BINDING_V1.json",
                "git_blob_sha": "binding-sha",
            },
            "coverage_root_namespace_bridge": {
                "path": NAMESPACE_PATH,
                "git_blob_sha": "namespace-sha",
            },
            "coverage_completeness_claim_scope": {
                "path": CLAIM_SCOPE_PATH,
                "git_blob_sha": "claim-scope-sha",
            },
        },
    }
    return mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope


def check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope):
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
        carrier=carrier,
        carrier_blob_sha="carrier-sha",
        carrier_runtime_blob_sha="carrier-runtime-sha",
        carrier_tests_blob_sha="carrier-tests-sha",
        claim_scope=claim_scope,
        claim_scope_blob_sha="claim-scope-sha",
        falsifier_blob_sha="falsifier-sha",
        falsifier_tests_blob_sha="falsifier-tests-sha",
        r4_binding_tests_blob_sha="r4-tests-sha",
        registry_alignment_tests_blob_sha="registry-alignment-tests-sha",
        root_registry_blob_sha="root-registry-sha",
        root_registry_pointer_blob_sha="root-registry-pointer-sha",
        root_registry_guard_blob_sha="root-registry-guard-sha",
        root_registry_tests_blob_sha="root-registry-tests-sha",
        root_semantic_receipt_blob_sha="semantic-receipt-sha",
        root_semantic_receipt_tests_blob_sha="semantic-receipt-tests-sha",
        live_validator_blob_sha="live-validator-sha",
        live_validator_tests_blob_sha="live-validator-tests-sha",
    )


def test_valid_binding_passes_zero_credit():
    out = check(*docs())
    assert out["pass"] is True
    assert out["terminal_credit_delta"] == 0
    assert out["root_closed_claimed"] is False
    assert out["claim_completeness_closed_claimed"] is False
    assert out["carrier_factorization_closed_claimed"] is False
    assert out["global_mission_completion_derivable"] is False


def test_stale_mission_blob_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    authority["objective_precedence"]["authoritative_git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "TERMINAL_AUTHORITY_MISSION_BLOB_STALE" in out["errors"]


def test_old_root_blob_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["root_theorem"]["git_blob_sha"] = "old"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_ROOT_BLOB_STALE" in out["errors"]


def test_zero_credit_is_required():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["accounting"]["terminal_credit_delta"] = 1
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_ZERO_CREDIT_VIOLATION" in out["errors"]


def test_missing_namespace_ref_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding.pop("root_namespace_bridge")
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_ROOT_NAMESPACE_PATH_DRIFT" in out["errors"]


def test_missing_namespace_authority_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    authority["authoritative_sources"].pop("coverage_root_namespace_bridge")
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "LIVE_AUTHORITY_ROOT_NAMESPACE_MISSING" in out["errors"]


def test_legacy_equivalence_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    namespace_bridge["legacy_namespaces"]["LEGACY_ESCAPE_POLICY_ADEQUACY"]["equivalent_to_ccrt_roots"] = ["R2"]
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "ROOT_NAMESPACE_LEGACY_ESCAPE_POLICY_ADEQUACY_EQUIVALENCE_FORBIDDEN" in out["errors"]


def test_carrier_formula_drift_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    theorem["semantic_carrier_precondition"]["formula"] = "WEAKER_FORMULA"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "ROOT_THEOREM_CARRIER_FORMULA_DRIFT" in out["errors"]


def test_carrier_must_be_claim_indexed():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    theorem["semantic_carrier_precondition"]["claim_indexed"] = False
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "ROOT_THEOREM_CARRIER_NOT_CLAIM_INDEXED" in out["errors"]


def test_carrier_blob_drift_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["semantic_carrier_precondition"]["git_blob_sha"] = "old-carrier"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_CARRIER_BLOB_STALE" in out["errors"]


def test_carrier_runtime_blob_drift_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["semantic_carrier_precondition"]["runtime"]["git_blob_sha"] = "old-runtime"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_CARRIER_RUNTIME_BLOB_STALE" in out["errors"]


def test_carrier_tests_blob_drift_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["semantic_carrier_precondition"]["tests"]["git_blob_sha"] = "old-tests"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_CARRIER_TESTS_BLOB_STALE" in out["errors"]


def test_carrier_cannot_request_new_root():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    carrier["root_effect"]["new_semantic_root_required"] = True
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "CARRIER_NEW_ROOT_VIOLATION" in out["errors"]


def test_claim_scope_root_blob_drift_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    claim_scope["root_theorem"]["git_blob_sha"] = "stale-root"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "CLAIM_SCOPE_ROOT_BLOB_STALE" in out["errors"]


def test_claim_scope_carrier_blob_drift_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    claim_scope["carrier_factorization"]["carrier_governance_git_blob_sha"] = "stale-carrier"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "CLAIM_SCOPE_CARRIER_BLOB_STALE" in out["errors"]


def test_live_authority_claim_scope_binding_drift_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    authority["authoritative_sources"]["coverage_completeness_claim_scope"]["git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "LIVE_AUTHORITY_CLAIM_SCOPE_BLOB_STALE" in out["errors"]


def test_stale_falsifier_blob_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["falsifier"]["git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_FALSIFIER_BLOB_STALE" in out["errors"]


def test_stale_r4_binding_tests_blob_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["falsifier"]["r4_binding_tests_git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_R4_TESTS_BLOB_STALE" in out["errors"]


def test_stale_live_validator_blob_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["live_binding_validator"]["git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_LIVE_VALIDATOR_BLOB_STALE" in out["errors"]


def test_stale_live_validator_tests_blob_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["live_binding_validator"]["tests_git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_LIVE_VALIDATOR_TESTS_BLOB_STALE" in out["errors"]


def test_git_blob_sha():
    assert git_blob_sha(b"hello") == "b6fc4c620b67d95f953a5c1c1230aaab5db5a1b0"


def test_current_repo_binding_passes():
    root = Path(__file__).resolve().parents[2]
    out = validate_repo(root)
    assert out["pass"] is True, out
    assert out["terminal_credit_delta"] == 0
    assert out["claim_completeness_closed_claimed"] is False
    assert out["carrier_factorization_closed_claimed"] is False
    assert out["global_mission_completion_derivable"] is False


def test_stale_semantic_receipt_checker_blob_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["root_certificate_registry_precondition"]["semantic_receipt_verifier"]["git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_ROOT_SEMANTIC_RECEIPT_BLOB_STALE" in out["errors"]


def test_stale_root_registry_guard_blob_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["root_certificate_registry_precondition"]["guard_git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_ROOT_REGISTRY_GUARD_BLOB_STALE" in out["errors"]


def test_stale_registry_alignment_tests_blob_fails():
    mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope = docs()
    binding["root_certificate_registry_precondition"]["claim_alignment_tests"]["git_blob_sha"] = "stale"
    out = check(mission, theorem, binding, namespace_bridge, authority, carrier, claim_scope)
    assert "BINDING_REGISTRY_ALIGNMENT_TESTS_BLOB_STALE" in out["errors"]
