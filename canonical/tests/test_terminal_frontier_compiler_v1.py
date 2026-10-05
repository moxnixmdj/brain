from __future__ import annotations

import json

import pytest

from canonical.runtime.terminal_frontier_compiler_v1 import (
    FrontierCompileError,
    _validate_activation,
    acceptance_identity,
    compile_frontier,
    frontier_epoch,
    git_blob_sha,
    root_partition,
    terminal_finality,
)


def test_current_frontier_compiles_from_exact_predicate_identity():
    out = compile_frontier()
    assert out["acceptance"]["proved_atomic"] == 14
    assert out["acceptance"]["unresolved_atomic"] == 24
    assert len(out["proved_predicates"]) == 14
    assert len(out["unresolved_predicates"]) == 24
    assert out["root1_positive_gap_count"] == 0
    assert out["root2_touching_count"] == 18
    assert out["root3_touching_count"] == 9
    assert (
        set(out["root1_positive_predicates"])
        | set(out["root2_touching"])
        | set(out["root3_touching"])
        == set(out["unresolved_predicates"])
    )
    assert out["meta_envelope"]["active_version"] >= 5
    assert out["meta_envelope"]["open_count"] >= 1
    assert out["zero_reality_cut"]["active_version"] >= 12
    assert out["terminal"] is False


def test_current_activation_verifications_are_epoch_bound():
    out = compile_frontier()
    paths = set(out["component_blobs"])
    assert "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json" in paths
    assert out["meta_envelope"]["verification_path"] in paths
    assert out["zero_reality_cut"]["verification_path"] in paths


def test_equal_counts_with_wrong_predicate_identity_fail_closed():
    registry = {"predicates": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}
    evidence = {"claims": [{"predicate_id": "a", "state": "PROVED"}]}
    acceptance = {"total_atomic": 3, "proved_atomic": 1, "unresolved_atomic": 2}
    with pytest.raises(FrontierCompileError, match="ROOT_PARTITION_IDENTITY_DRIFT"):
        acceptance_identity(registry, evidence, acceptance, {"b", "x"})


def test_activation_requires_content_bound_passing_verification(tmp_path):
    (tmp_path / "canonical/governance").mkdir(parents=True)
    (tmp_path / "canonical/verification").mkdir(parents=True)

    subject_path = "canonical/governance/SUBJECT.json"
    verification_path = "canonical/verification/VERIFY.json"
    (tmp_path / subject_path).write_text(
        json.dumps({"schema": "SUBJECT", "value": 1}, indent=2) + "\n"
    )
    subject_sha = git_blob_sha(subject_path, tmp_path)

    verification = {
        "schema": "VERIFY",
        "status": "CONNECTOR_RECOMPUTATION_PASS",
        "subject": {"path": subject_path, "git_blob_sha": subject_sha},
        "errors": [],
    }
    (tmp_path / verification_path).write_text(json.dumps(verification, indent=2) + "\n")
    verification_sha = git_blob_sha(verification_path, tmp_path)

    activation = {
        "status": "ACTIVE__TEST",
        "scheduling_authority": True,
        "subject": {"path": subject_path, "git_blob_sha": subject_sha},
        "verification": {
            "path": verification_path,
            "git_blob_sha": verification_sha,
        },
    }
    _, subject, _, verified = _validate_activation("ACTIVATION.json", activation, tmp_path)
    assert subject["value"] == 1
    assert "PASS" in verified["status"]

    verification["status"] = "FAIL_CLOSED"
    (tmp_path / verification_path).write_text(json.dumps(verification, indent=2) + "\n")
    activation["verification"]["git_blob_sha"] = git_blob_sha(verification_path, tmp_path)
    with pytest.raises(FrontierCompileError, match="ACTIVATION_VERIFICATION_NOT_PASS"):
        _validate_activation("ACTIVATION.json", activation, tmp_path)


def test_meta_obligation_blocks_false_38_of_38_finality():
    acceptance = {
        "accepted_families": 19,
        "total_families": 19,
        "proved_atomic": 38,
        "total_atomic": 38,
        "unresolved_atomic": 0,
    }
    assert terminal_finality(
        acceptance, root1_positive_gap_count=0, meta_open_count=1
    ) is False
    assert terminal_finality(
        acceptance, root1_positive_gap_count=0, meta_open_count=0
    ) is True


def test_root_partition_mixed_predicates_count_on_both_sides():
    part = {
        "unresolved_total": 4,
        "root1_positive_gap_count": 0,
        "root2_only_count": 1,
        "root3_only_count": 1,
        "root2_and_root3_count": 2,
        "root1_only": [],
        "root2_only": ["a"],
        "root3_only": ["b"],
        "root2_and_root3": ["c", "d"],
    }
    r1, r2, r3, residual = root_partition(part)
    assert r1 == set()
    assert r2 == {"a", "c", "d"}
    assert r3 == {"b", "c", "d"}
    assert residual == {"a", "b", "c", "d"}


def test_frontier_epoch_changes_on_any_bound_component():
    a = {"x": "1" * 40, "y": "2" * 40}
    b = dict(a)
    b["y"] = "3" * 40
    assert frontier_epoch(a) != frontier_epoch(b)


def test_git_blob_sha_uses_real_nul_separator(tmp_path):
    payload = b"abc"
    (tmp_path / "x").write_bytes(payload)
    expected = hashlib.sha1(b"blob 3\0abc").hexdigest()
    assert git_blob_sha("x", tmp_path) == expected
