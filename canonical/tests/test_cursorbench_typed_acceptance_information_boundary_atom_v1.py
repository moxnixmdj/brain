from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime.cursorbench_typed_acceptance_information_boundary_atom_v1 import (
    ATOM_ID,
    RECEIPT_SCHEMA,
    VERIFY_SCHEMA,
    model_sha256,
    verify,
)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def model():
    return {
        "requirements": [
            {
                "id": "R1",
                "critical": True,
                "transform_kinds": ["artifact"],
                "must_detect_failure_modes": ["bad_output"],
            }
        ],
        "checks": [],
    }


def write_binding(root: Path, m, *, receipt_mut=None, verify_mut=None):
    gov = root / "canonical/governance"
    ver = root / "canonical/verification"
    gov.mkdir(parents=True, exist_ok=True)
    ver.mkdir(parents=True, exist_ok=True)

    visible = ["a" * 64, "b" * 64]
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "boundary_id": "boundary:clean-1",
        "subject_model_sha256": model_sha256(m),
        "declared_visible_input_sha256": visible,
        "preterminal_information_sources_complete": True,
        "model_derived_only_from_declared_visible_inputs": True,
        "hidden_verifier_access_before_terminal_authorization": False,
        "task_specific_solution_access_before_terminal_authorization": False,
        "boundary_frozen_before_terminal_authorization": True,
    }
    if receipt_mut:
        receipt_mut(receipt)
    receipt_path = gov / "boundary.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

    verification = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": git_blob_sha(receipt_path),
        "subject_model_sha256": model_sha256(m),
        "boundary_id": receipt.get("boundary_id"),
        "declared_visible_input_sha256": visible,
        "pass": True,
        "independent_verified": True,
        "declared_visible_inputs_verified": True,
        "preterminal_information_source_completeness_verified": True,
        "model_derivation_boundary_verified": True,
        "hidden_verifier_access_absence_verified": True,
        "task_specific_solution_access_absence_verified": True,
        "boundary_ordering_verified": True,
    }
    if verify_mut:
        verify_mut(verification)
    verification_path = ver / "boundary.verify.json"
    verification_path.write_text(
        json.dumps(verification, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "receipt": {
            "path": "canonical/governance/boundary.json",
            "git_blob_sha": git_blob_sha(receipt_path),
        },
        "verification": {
            "path": "canonical/verification/boundary.verify.json",
            "git_blob_sha": git_blob_sha(verification_path),
        },
    }


def test_missing_binding_is_open_not_atom_truth(tmp_path):
    m = model()
    out = verify(m, None, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["status"] == "OPEN__PREVERIFIER_INFORMATION_BOUNDARY_BINDING_REQUIRED"
    assert out["atom_truth_authorized"] is False
    assert out["evidence_missing"] is True


def test_exact_independent_boundary_proves_only_hidden_access_atom(tmp_path):
    m = model()
    binding = write_binding(tmp_path, m)
    out = verify(m, binding, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["atom_truth_authorized"] is True
    assert out["atom_id"] == ATOM_ID
    assert out["proved_constraint"] == {"op": "ATOM", "id": ATOM_ID}
    assert out["other_condition_atoms_proved"] == []
    assert out["whole_policy_condition_proved"] is False
    assert out["whole_cursorbench_adequate"] is False


def test_receipt_for_different_model_fails_closed(tmp_path):
    m = model()
    other = model()
    other["requirements"][0]["transform_kinds"] = ["aggregate"]
    binding = write_binding(tmp_path, other)
    out = verify(m, binding, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__INFORMATION_BOUNDARY_ATOM_UNPROVED"
    assert "RECEIPT_MODEL_DIGEST_MISMATCH" in out["errors"][0]


def test_receipt_cannot_self_assert_hidden_access_absence(tmp_path):
    m = model()
    binding = write_binding(
        tmp_path,
        m,
        receipt_mut=lambda r: r.__setitem__(
            "hidden_verifier_access_before_terminal_authorization", True
        ),
    )
    out = verify(m, binding, repo_root=tmp_path)
    assert out["pass"] is False
    assert "RECEIPT_PREMISE_UNPROVED:hidden_verifier_access_before_terminal_authorization" in out["errors"][0]


def test_independent_verification_must_verify_absence(tmp_path):
    m = model()
    binding = write_binding(
        tmp_path,
        m,
        verify_mut=lambda v: v.__setitem__(
            "hidden_verifier_access_absence_verified", False
        ),
    )
    out = verify(m, binding, repo_root=tmp_path)
    assert out["pass"] is False
    assert "VERIFICATION_PREMISE_UNPROVED:hidden_verifier_access_absence_verified" in out["errors"][0]


def test_task_specific_solution_access_is_separate_load_bearing_check(tmp_path):
    m = model()
    binding = write_binding(
        tmp_path,
        m,
        receipt_mut=lambda r: r.__setitem__(
            "task_specific_solution_access_before_terminal_authorization", True
        ),
    )
    out = verify(m, binding, repo_root=tmp_path)
    assert out["pass"] is False
    assert "RECEIPT_PREMISE_UNPROVED:task_specific_solution_access_before_terminal_authorization" in out["errors"][0]


def test_verification_must_bind_exact_receipt_blob(tmp_path):
    m = model()
    binding = write_binding(tmp_path, m)
    p = tmp_path / "canonical/governance/boundary.json"
    receipt = json.loads(p.read_text(encoding="utf-8"))
    receipt["boundary_id"] = "mutated-after-verification"
    p.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    binding["receipt"]["git_blob_sha"] = git_blob_sha(p)
    out = verify(m, binding, repo_root=tmp_path)
    assert out["pass"] is False
    assert "VERIFICATION_SUBJECT_BLOB_MISMATCH" in out["errors"][0]


def test_symlink_escape_is_rejected(tmp_path):
    m = model()
    binding = write_binding(tmp_path, m)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    link = tmp_path / "canonical/governance/escape.json"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        return
    binding["receipt"] = {
        "path": "canonical/governance/escape.json",
        "git_blob_sha": git_blob_sha(outside),
    }
    out = verify(m, binding, repo_root=tmp_path)
    assert out["pass"] is False
    assert "BOUND_SYMLINK_FORBIDDEN" in out["errors"][0]
