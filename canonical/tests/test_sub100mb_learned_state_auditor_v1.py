import hashlib

from canonical.runtime.sub100mb_learned_state_auditor_v1 import (
    MAX_LEARNED_BYTES_EXCLUSIVE,
    audit_manifest,
    audit_state_root,
    theoretical_parameter_capacity,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _base_manifest():
    return {
        "schema": "PROJECT_BRAIN_LEARNED_STATE_MANIFEST_V1",
        "capsule_id": "test-capsule",
        "inventory_complete": True,
        "dependency_closure_complete": True,
        "same_capsule_for_all_predicates": True,
        "frozen_acceptance_predicate_count": 38,
        "artifacts": [],
        "runtime_providers": [],
    }


def test_under_budget_counts_exact_learned_bytes():
    m = _base_manifest()
    m["artifacts"] = [
        {
            "path": "kernel.bin",
            "sha256": "0" * 64,
            "bytes": 99_999_999,
            "classification": "LEARNED",
            "learned_kind": "MODEL_WEIGHTS",
        }
    ]
    x = audit_manifest(m)
    assert x["learned_bytes"] == 99_999_999
    assert x["under_budget"] is True
    assert x["manifest_mechanically_complete"] is True


def test_exactly_100mb_fails_strict_bound():
    m = _base_manifest()
    m["artifacts"] = [
        {
            "path": "kernel.bin",
            "sha256": "0" * 64,
            "bytes": MAX_LEARNED_BYTES_EXCLUSIVE,
            "classification": "LEARNED",
            "learned_kind": "MODEL_WEIGHTS",
        }
    ]
    x = audit_manifest(m)
    assert x["under_budget"] is False
    assert "LEARNED_STATE_BUDGET_EXCEEDED" in x["reasons"]


def test_data_fit_state_cannot_hide_as_nonlearned():
    m = _base_manifest()
    m["artifacts"] = [
        {
            "path": "router.json",
            "sha256": "0" * 64,
            "bytes": 12,
            "classification": "NONLEARNED",
            "deterministic_or_static": True,
            "fit_or_optimized_from_data": True,
        }
    ]
    x = audit_manifest(m)
    assert x["manifest_mechanically_complete"] is False
    assert any("MISCLASSIFIED_AS_NONLEARNED" in r for r in x["reasons"])


def test_external_general_reasoning_provider_is_forbidden():
    m = _base_manifest()
    m["runtime_providers"] = [
        {
            "role": "REMOTE_GENERAL_REASONING_MODEL",
            "external": True,
            "learned_general_reasoning": True,
            "supplies_missing_target_capability": True,
        }
    ]
    x = audit_manifest(m)
    assert x["manifest_mechanically_complete"] is False
    assert any("FORBIDDEN_PROVIDER_ROLE" in r for r in x["reasons"])


def test_exact_state_root_verifies_bytes_and_inventory(tmp_path):
    learned = b"tiny-learned-kernel"
    static = b'{"rule":"deterministic"}'
    (tmp_path / "kernel.bin").write_bytes(learned)
    (tmp_path / "rules.json").write_bytes(static)

    m = _base_manifest()
    m["artifacts"] = [
        {
            "path": "kernel.bin",
            "sha256": _sha(learned),
            "bytes": len(learned),
            "classification": "LEARNED",
            "learned_kind": "MODEL_WEIGHTS",
        },
        {
            "path": "rules.json",
            "sha256": _sha(static),
            "bytes": len(static),
            "classification": "NONLEARNED",
            "deterministic_or_static": True,
            "fit_or_optimized_from_data": False,
        },
    ]

    x = audit_state_root(tmp_path, m)
    assert x["exact_state_root_verified"] is True
    assert x["learned_bytes"] == len(learned)
    assert x["actual_state_file_count"] == 2


def test_undeclared_state_file_fails_closed(tmp_path):
    data = b"declared"
    (tmp_path / "kernel.bin").write_bytes(data)
    (tmp_path / "hidden.bin").write_bytes(b"not-declared")

    m = _base_manifest()
    m["artifacts"] = [
        {
            "path": "kernel.bin",
            "sha256": _sha(data),
            "bytes": len(data),
            "classification": "LEARNED",
            "learned_kind": "MODEL_WEIGHTS",
        }
    ]

    x = audit_state_root(tmp_path, m)
    assert x["exact_state_root_verified"] is False
    assert "UNDECLARED_STATE_FILE:hidden.bin" in x["reasons"]


def test_planning_only_parameter_capacity():
    assert theoretical_parameter_capacity(16) == 50_000_000
    assert theoretical_parameter_capacity(8) == 100_000_000
    assert theoretical_parameter_capacity(4) == 200_000_000
