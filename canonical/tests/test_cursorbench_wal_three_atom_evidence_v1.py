from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime.independent_acceptance_model import assess
from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import (
    ATOM_ID as TRANSFORM_ATOM_ID,
    verify as verify_transform,
)
from canonical.runtime.cursorbench_typed_acceptance_source_coverage_atoms_v1 import (
    FAILURE_COMPLETENESS_ATOM_ID,
    TYPED_SEMANTICS_ATOM_ID,
    verify as verify_source,
)
from canonical.runtime.cursorbench_typed_acceptance_dependency_provenance_atom_v1 import (
    ATOM_ID as DEPENDENCY_ATOM_ID,
    verify as verify_dependency,
)

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "canonical" / "governance"
VER = ROOT / "canonical" / "verification"

MODEL_PATH = GOV / "CURSORBENCH_WAL_RECOVERY_TYPED_ACCEPTANCE_MODEL_20261009_V1.json"
SOURCE_PATH = GOV / "CURSORBENCH_WAL_RECOVERY_LOSSLESS_SOURCE_CONTRACT_20261009_V1.json"
SOURCE_RECEIPT_PATH = GOV / "CURSORBENCH_WAL_RECOVERY_SOURCE_COVERAGE_RECEIPT_20261009_V1.json"
DEP_RECEIPT_PATH = GOV / "CURSORBENCH_WAL_RECOVERY_DEPENDENCY_PROVENANCE_RECEIPT_20261009_V1.json"
SOURCE_VERIFY_PATH = VER / "CURSORBENCH_WAL_RECOVERY_SOURCE_COVERAGE_INDEPENDENT_VERIFICATION_20261009_V1.json"
DEP_VERIFY_PATH = VER / "CURSORBENCH_WAL_RECOVERY_DEPENDENCY_PROVENANCE_INDEPENDENT_VERIFICATION_20261009_V1.json"
AUDIT_PATH = VER / "CURSORBENCH_WAL_RECOVERY_TYPED_ACCEPTANCE_INDEPENDENT_AUDIT_20261009_V1.json"

BLOBS = {
    "source": "8cedc22b7c006d00a1ec863c49083b7a95876abe",
    "model": "68e2acec46f88ba3461cd277d4e79c6e8cbe50eb",
    "source_receipt": "118013f6add21526e6672c1753b7e7cc1f26515d",
    "source_verification": "fbf7b121a61429aa62d2100029ae63c6c07b09a2",
    "dependency_receipt": "8c48fa17e8d8b27fe75925403e5067968eef61a0",
    "dependency_verification": "cee18c733d26155ad32dada9e248b97dd26b6927",
    "audit": "9b77700a3f9b3712c9d7cb5d80b7beb46a71f9eb",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _source_binding():
    return {
        "source_contract": {
            "path": SOURCE_PATH.relative_to(ROOT).as_posix(),
            "git_blob_sha": BLOBS["source"],
        },
        "receipt": {
            "path": SOURCE_RECEIPT_PATH.relative_to(ROOT).as_posix(),
            "git_blob_sha": BLOBS["source_receipt"],
        },
        "verification": {
            "path": SOURCE_VERIFY_PATH.relative_to(ROOT).as_posix(),
            "git_blob_sha": BLOBS["source_verification"],
        },
    }


def _dependency_binding():
    return {
        "receipt": {
            "path": DEP_RECEIPT_PATH.relative_to(ROOT).as_posix(),
            "git_blob_sha": BLOBS["dependency_receipt"],
        },
        "verification": {
            "path": DEP_VERIFY_PATH.relative_to(ROOT).as_posix(),
            "git_blob_sha": BLOBS["dependency_verification"],
        },
    }


def test_wal_exact_model_proves_three_external_evidence_atoms_and_structural_atom():
    model = _load(MODEL_PATH)
    source = verify_source(model, _source_binding(), repo_root=ROOT)
    dependency = verify_dependency(model, _dependency_binding(), repo_root=ROOT)
    transform = verify_transform(model)

    assert source["pass"] is True, source
    assert set(source["proved_atom_ids"]) == {
        TYPED_SEMANTICS_ATOM_ID,
        FAILURE_COMPLETENESS_ATOM_ID,
    }
    assert dependency["pass"] is True, dependency
    assert dependency["atom_id"] == DEPENDENCY_ATOM_ID
    assert transform["pass"] is True, transform
    assert transform["atom_id"] == TRANSFORM_ATOM_ID


def test_wal_source_contract_is_lossless_and_independent_audit_is_bounded():
    source = _load(SOURCE_PATH)
    audit = _load(AUDIT_PATH)
    assert source["pass"] is True
    assert source["nonwhitespace_source_coverage_complete"] is True
    assert len(source["acceptance_contract"]["required_obligation_ids"]) == 35
    assert audit["pass"] is True
    assert audit["source_contract_replayed_exact"] is True
    assert audit["source_mapping_complete_and_literal"] is True
    assert audit["dependency_provenance_projection_verified"] is True
    assert audit["information_boundary_atom_claimed"] is False
    assert audit["hidden_verifier_or_solution_absence_claimed_by_this_audit"] is False


def test_wal_model_remains_fail_closed_on_separate_information_boundary_requirement():
    model = _load(MODEL_PATH)
    out = assess(model)
    assert out["pass"] is False
    assert out["terminal_submission_authorized_by_this_gate"] is False
    assert out["failed_requirements"] == ["R13_NO_TASK_SPECIFIC_CHEATING"]
