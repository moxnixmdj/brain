import hashlib
import json
from pathlib import Path

from canonical.runtime.cursorbench_typed_acceptance_failure_mode_completeness_atom_v1 import (
    RECEIPT_SCHEMA,
    VERIFY_SCHEMA,
    ATOM_ID,
    projection_sha256,
    verify,
)
from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import model_sha256

SHA64 = "1" * 64

def _model():
    return {
        "requirements": [{
            "id": "R1",
            "critical": True,
            "transform_kinds": ["selection"],
            "must_detect_failure_modes": ["custom_mode"],
            "builder_dependencies": ["raw:input"],
        }],
        "checks": [],
    }

def _blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def _binding(tmp_path: Path, model, *, mutate_receipt=None, mutate_verify=None):
    gov = tmp_path / "canonical/governance"
    ver = tmp_path / "canonical/verification"
    gov.mkdir(parents=True)
    ver.mkdir(parents=True)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "subject_model_sha256": model_sha256(model),
        "obligation_projection_sha256": projection_sha256(model),
        "mode_completeness_audit_id": "AUDIT",
        "producer_id": "producer",
        "authoritative_source_sha256": [SHA64],
        "every_material_independently_knowable_mode_bound": True,
        "generated_obligation_set_complete": True,
        "requirement_mode_scope_complete": True,
        "no_omitted_material_modes": True,
        "source_authority_complete": True,
    }
    if mutate_receipt:
        mutate_receipt(receipt)
    rp = gov / "modes.json"
    rp.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    verification = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": _blob(rp),
        "subject_model_sha256": model_sha256(model),
        "obligation_projection_sha256": projection_sha256(model),
        "mode_completeness_audit_id": receipt.get("mode_completeness_audit_id"),
        "producer_id": receipt.get("producer_id"),
        "independent_verifier_id": "verifier",
        "verification_method": "INDEPENDENT_AUDIT",
        "authoritative_source_sha256": receipt.get("authoritative_source_sha256"),
        "pass": True,
        "independent_verified": True,
        "authoritative_source_set_verified": True,
        "requirement_mode_scope_completeness_verified": True,
        "generated_obligation_set_completeness_verified": True,
        "omitted_material_mode_absence_verified": True,
        "source_authority_completeness_verified": True,
    }
    if mutate_verify:
        mutate_verify(verification)
    vp = ver / "modes_verify.json"
    vp.write_text(json.dumps(verification, sort_keys=True), encoding="utf-8")
    return {
        "receipt": {"path": "canonical/governance/modes.json", "git_blob_sha": _blob(rp)},
        "verification": {"path": "canonical/verification/modes_verify.json", "git_blob_sha": _blob(vp)},
    }

def test_missing_binding_is_open_not_truth():
    out = verify(_model(), None)
    assert out["pass"] is False
    assert out["status"].startswith("OPEN__")
    assert out["atom_truth_authorized"] is False

def test_valid_independent_completeness_audit_proves_only_atom(tmp_path):
    model = _model()
    out = verify(model, _binding(tmp_path, model), repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["atom_truth_authorized"] is True
    assert out["proved_constraint"]["id"] == ATOM_ID
    assert out["whole_policy_condition_proved"] is False
    assert out["whole_cursorbench_adequate"] is False
    assert out["terminal_authority"] is False

def test_producer_self_verification_rejected(tmp_path):
    model = _model()
    binding = _binding(
        tmp_path, model,
        mutate_verify=lambda v: v.__setitem__("independent_verifier_id", "producer"),
    )
    out = verify(model, binding, repo_root=tmp_path)
    assert out["pass"] is False
    assert "VERIFICATION_NOT_PRODUCER_INDEPENDENT" in out["errors"][0]

def test_incomplete_obligation_audit_rejected(tmp_path):
    model = _model()
    binding = _binding(
        tmp_path, model,
        mutate_receipt=lambda r: r.__setitem__("no_omitted_material_modes", False),
    )
    out = verify(model, binding, repo_root=tmp_path)
    assert out["pass"] is False
    assert "RECEIPT_PREMISE_UNPROVED:no_omitted_material_modes" in out["errors"][0]

def test_model_drift_rejected(tmp_path):
    model = _model()
    binding = _binding(tmp_path, model)
    drift = _model()
    drift["requirements"][0]["must_detect_failure_modes"].append("new_mode")
    out = verify(drift, binding, repo_root=tmp_path)
    assert out["pass"] is False

def test_critical_requirement_without_obligations_fails_closed():
    model = {
        "requirements": [{"id": "R", "critical": True, "transform_kinds": []}],
        "checks": [],
    }
    out = verify(model, None)
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__MODE_COMPLETENESS_MODEL_INVALID"
