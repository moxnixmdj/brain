from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import p3_conditioned_policy_adequacy_registry_v1 as registry
from canonical.runtime import p3_robust_policy_adequacy_cegar_v1 as p3
from canonical.runtime.cursorbench_typed_acceptance_information_boundary_atom_v1 import (
    ATOM_ID as NO_HIDDEN_ATOM,
    RECEIPT_SCHEMA,
    VERIFY_SCHEMA,
    model_sha256,
)
from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import (
    ATOM_ID as TRANSFORM_ATOM,
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


def binding(root: Path, m, *, corrupt_verify=False):
    gov = root / "canonical/governance"
    ver = root / "canonical/verification"
    gov.mkdir(parents=True, exist_ok=True)
    ver.mkdir(parents=True, exist_ok=True)

    visible = ["c" * 64]
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "boundary_id": "boundary:integration",
        "subject_model_sha256": model_sha256(m),
        "declared_visible_input_sha256": visible,
        "preterminal_information_sources_complete": True,
        "model_derived_only_from_declared_visible_inputs": True,
        "hidden_verifier_access_before_terminal_authorization": False,
        "task_specific_solution_access_before_terminal_authorization": False,
        "boundary_frozen_before_terminal_authorization": True,
    }
    rp = gov / "info-boundary.json"
    rp.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

    verify = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": git_blob_sha(rp),
        "subject_model_sha256": model_sha256(m),
        "boundary_id": "boundary:integration",
        "declared_visible_input_sha256": visible,
        "pass": True,
        "independent_verified": True,
        "declared_visible_inputs_verified": True,
        "preterminal_information_source_completeness_verified": True,
        "model_derivation_boundary_verified": True,
        "hidden_verifier_access_absence_verified": not corrupt_verify,
        "task_specific_solution_access_absence_verified": True,
        "boundary_ordering_verified": True,
    }
    vp = ver / "info-boundary.verify.json"
    vp.write_text(json.dumps(verify, sort_keys=True), encoding="utf-8")

    return {
        "receipt": {
            "path": "canonical/governance/info-boundary.json",
            "git_blob_sha": git_blob_sha(rp),
        },
        "verification": {
            "path": "canonical/verification/info-boundary.verify.json",
            "git_blob_sha": git_blob_sha(vp),
        },
    }


def test_valid_boundary_auto_refines_exact_atom_without_other_membership_truth():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        m = model()
        b = binding(root, m)
        with patch.object(registry, "_REGISTRY", {}):
            out = registry.augment_problem(
                {
                    "decision_basis": ["BASE"],
                    "typed_acceptance_model": m,
                    "typed_acceptance_information_boundary_binding": b,
                },
                repo_root=root,
            )

    assert out["pass"] is True, out
    problem = out["problem"]
    assert TRANSFORM_ATOM in problem["decision_basis"]
    assert NO_HIDDEN_ATOM in problem["decision_basis"]
    assert {"op": "ATOM", "id": NO_HIDDEN_ATOM} in problem["formal_source_constraints"]
    assert {"op": "ATOM", "id": NO_HIDDEN_ATOM} in problem["proposed_refinements"]
    assert out["information_boundary_proved_atom_ids"] == [NO_HIDDEN_ATOM]
    assert set(out["proved_condition_atom_ids"]) == {TRANSFORM_ATOM, NO_HIDDEN_ATOM}
    assert out["membership_self_certified"] is False


def test_missing_boundary_binding_does_not_prove_hidden_access_atom():
    with patch.object(registry, "_REGISTRY", {}):
        out = registry.augment_problem(
            {
                "decision_basis": ["BASE"],
                "typed_acceptance_model": model(),
            }
        )
    assert out["pass"] is True, out
    assert NO_HIDDEN_ATOM not in out["problem"]["decision_basis"]
    assert out["information_boundary_proved_atom_ids"] == []
    assert out["structurally_proved_atom_ids"] == [TRANSFORM_ATOM]


def test_supplied_invalid_boundary_binding_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        m = model()
        b = binding(root, m, corrupt_verify=True)
        with patch.object(registry, "_REGISTRY", {}):
            out = registry.augment_problem(
                {
                    "decision_basis": ["BASE"],
                    "typed_acceptance_model": m,
                    "typed_acceptance_information_boundary_binding": b,
                },
                repo_root=root,
            )
    assert out["pass"] is False
    assert out["reason"] == "INFORMATION_BOUNDARY_ATOM_BINDING_INVALID"
    proof = out["detail"]["information_boundary_atom_proof"]
    assert proof["atom_truth_authorized"] is False
    assert "VERIFICATION_PREMISE_UNPROVED:hidden_verifier_access_absence_verified" in proof["errors"][0]


def test_boundary_binding_without_exact_typed_model_fails_closed():
    with patch.object(registry, "_REGISTRY", {}):
        out = registry.augment_problem(
            {
                "decision_basis": ["BASE"],
                "typed_acceptance_information_boundary_binding": {
                    "receipt": {},
                    "verification": {},
                },
            }
        )
    assert out["pass"] is False
    assert out["reason"] == "INFORMATION_BOUNDARY_BINDING_REQUIRES_TYPED_ACCEPTANCE_MODEL"


def test_p3_exposes_information_boundary_proof_without_terminal_authority():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        m = model()
        b = binding(root, m)
        old_root = p3.ROOT
        p3.ROOT = root
        try:
            with patch.object(registry, "_REGISTRY", {}):
                out = p3.solve(
                    {
                        "decision_basis": ["BASE"],
                        "typed_acceptance_model": m,
                        "typed_acceptance_information_boundary_binding": b,
                    }
                )
        finally:
            p3.ROOT = old_root

    assert out["pass"] is False
    assert out["reason"] == "POLICY_CONDITIONS_REQUIRED"
    info = out["conditioned_policy_adequacy_registry"]
    assert info["information_boundary_proved_atom_ids"] == [NO_HIDDEN_ATOM]
    assert NO_HIDDEN_ATOM in info["proved_condition_atom_ids"]
    assert info["membership_self_certified"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
