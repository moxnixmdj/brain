from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from canonical.runtime.unified_cognitive_fabric_auto_route_refinement_v1 import (
    EXPECTED_STATE_COUNT,
    SUBJECT_ID,
    _blob_sha,
    verify_refinement,
)

ROOT = Path(__file__).resolve().parents[2]
CERT_REL = Path(
    "canonical/governance/"
    "UNIFIED_COGNITIVE_FABRIC_AUTO_ROUTE_REFINEMENT_CERTIFICATE_20261010_V1.json"
)
SPEC_REL = Path(
    "canonical/governance/"
    "UNIFIED_COGNITIVE_FABRIC_AUTO_ROUTE_ABSTRACT_MODEL_20261010_V1.json"
)
SUBJECT_REL = Path("canonical/runtime/unified_cognitive_fabric_v1.py")


def fixture(*, mutate_cert=None, mutate_model=None):
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    for rel in (CERT_REL, SPEC_REL, SUBJECT_REL):
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dst)

    model_path = root / SPEC_REL
    if mutate_model is not None:
        model = json.loads(model_path.read_text(encoding="utf-8"))
        mutate_model(model)
        model_path.write_text(
            json.dumps(model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    cert_path = root / CERT_REL
    cert = json.loads(cert_path.read_text(encoding="utf-8"))
    cert["abstract_spec"]["git_blob_sha"] = _blob_sha(model_path)
    cert["concrete_implementation"]["git_blob_sha"] = _blob_sha(root / SUBJECT_REL)
    if mutate_cert is not None:
        mutate_cert(cert)
    cert_path.write_text(
        json.dumps(cert, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return td, root, cert_path


def test_current_auto_route_model_matches_all_98304_states():
    td, root, cert = fixture()
    try:
        out = verify_refinement(
            root=root,
            certificate_path=cert,
            subject_id=SUBJECT_ID,
        )
        assert out["pass"] is True, out
        assert out["cases_checked"] == EXPECTED_STATE_COUNT == 98304
        assert out["mismatch_count"] == 0
        assert out["refinement_fact"] == "EXHAUSTIVE_FINITE_AUTO_ROUTE_MODEL_MATCH"
        assert out["terminal_credit_delta"] == 0
        assert out["liveness_preserved"] is False
    finally:
        td.cleanup()


def test_stale_concrete_blob_is_rejected_before_execution():
    td, root, cert = fixture(
        mutate_cert=lambda c: c["concrete_implementation"].__setitem__(
            "git_blob_sha", "0" * 40
        )
    )
    try:
        out = verify_refinement(root=root, certificate_path=cert, subject_id=SUBJECT_ID)
        assert out["pass"] is False
        assert "CONCRETE_IMPLEMENTATION_BLOB_SHA_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_stale_abstract_blob_is_rejected_before_execution():
    td, root, cert = fixture(
        mutate_cert=lambda c: c["abstract_spec"].__setitem__(
            "git_blob_sha", "0" * 40
        )
    )
    try:
        out = verify_refinement(root=root, certificate_path=cert, subject_id=SUBJECT_ID)
        assert out["pass"] is False
        assert "ABSTRACT_SPEC_BLOB_SHA_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_foreign_certificate_subject_is_rejected():
    td, root, cert = fixture(
        mutate_cert=lambda c: c.__setitem__("subject_id", "FOREIGN_SUBJECT")
    )
    try:
        out = verify_refinement(root=root, certificate_path=cert, subject_id=SUBJECT_ID)
        assert out["pass"] is False
        assert "CERTIFICATE_SUBJECT_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_abstract_signal_drift_is_rejected_even_when_rehashed():
    def mutate(model):
        model["boolean_route_signals"] = model["boolean_route_signals"][:-1]

    td, root, cert = fixture(mutate_model=mutate)
    try:
        out = verify_refinement(root=root, certificate_path=cert, subject_id=SUBJECT_ID)
        assert out["pass"] is False
        assert "ABSTRACT_MODEL_SIGNALS_INVALID" in out["errors"]
    finally:
        td.cleanup()


def test_abstract_state_count_drift_is_rejected_even_when_rehashed():
    td, root, cert = fixture(
        mutate_model=lambda m: m.__setitem__("exhaustive_state_count", 1)
    )
    try:
        out = verify_refinement(root=root, certificate_path=cert, subject_id=SUBJECT_ID)
        assert out["pass"] is False
        assert "ABSTRACT_MODEL_STATE_COUNT_INVALID" in out["errors"]
    finally:
        td.cleanup()


def test_nonzero_certificate_credit_is_rejected():
    td, root, cert = fixture(
        mutate_cert=lambda c: c.__setitem__("terminal_credit_delta", 1)
    )
    try:
        out = verify_refinement(root=root, certificate_path=cert, subject_id=SUBJECT_ID)
        assert out["pass"] is False
        assert "CERTIFICATE_NONZERO_CREDIT:terminal_credit_delta" in out["errors"]
    finally:
        td.cleanup()
