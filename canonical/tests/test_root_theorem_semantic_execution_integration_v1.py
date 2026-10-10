import json
import tempfile
from pathlib import Path

from canonical.runtime import root_theorem_falsifier_v1 as rt


def _write_control_plane(root: Path, slots):
    gov = root / "canonical/governance"
    gov.mkdir(parents=True, exist_ok=True)
    registry = {
        "active_claim": {"claim_id": "a" * 64},
        "certificate_slots": slots,
    }
    (gov / "COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json").write_text(
        json.dumps(registry), encoding="utf-8"
    )
    (gov / "CURRENT_MISSION_OBJECTIVE.json").write_text(
        json.dumps({
            "authoritative_source": {"path": "canonical/governance/REAL_MISSION.json"}
        }),
        encoding="utf-8",
    )
    (gov / "REAL_MISSION.json").write_text("{}", encoding="utf-8")
    (root / "canonical/CANONICAL_POINTER.json").write_text(
        json.dumps({"canonical_generation": "GEN1"}), encoding="utf-8"
    )
    return registry


def _proved(root_id):
    return {
        "root_id": root_id,
        "status": "PROVED_CURRENT",
        "certificate": {"path": "cert.json", "git_blob_sha": "same"},
        "semantic_verifier": {"path": "verifier.py", "git_blob_sha": "same"},
        "independent_verification": {"path": "receipt.json", "git_blob_sha": "same"},
    }


def _patch_paths(monkeypatch, root):
    monkeypatch.setattr(rt, "REPO_ROOT", root)
    monkeypatch.setattr(
        rt,
        "ROOT_REGISTRY_PATH",
        root / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json",
    )
    monkeypatch.setattr(
        rt,
        "MISSION_PATH",
        root / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json",
    )
    monkeypatch.setattr(
        rt,
        "CANONICAL_POINTER_PATH",
        root / "canonical/CANONICAL_POINTER.json",
    )
    monkeypatch.setattr(rt, "_git_blob_sha", lambda path: "same")


def test_canonical_r4_authority_rejects_semantically_rejected_proved_slot(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_control_plane(root, [_proved("CC_R1_REALITY_CONTAINMENT_V1")])
        _patch_paths(monkeypatch, root)
        monkeypatch.setattr(
            rt,
            "validate_root_registry",
            lambda *args, **kwargs: {
                "pass": True,
                "status": "PASS__ROOT_CERTIFICATE_REGISTRY",
                "errors": [],
                "r4_proof_closure": True,
            },
        )
        seen = []

        def reject(root, slot, active_claim):
            seen.append(slot["root_id"])
            return {"pass": False, "status": "FAIL_CLOSED", "errors": ["SEMANTIC_FALSE"]}

        monkeypatch.setattr(rt, "validate_semantic_root_slot", reject)
        out = rt.evaluate_canonical_registry_authority()

        assert seen == ["CC_R1_REALITY_CONTAINMENT_V1"]
        assert out["authorized"] is False
        assert out["status"] == "R4_CANONICAL_REGISTRY_INVALID"
        assert any("PROVED_SLOT_SEMANTIC_RECEIPT_INVALID" in e for e in out["registry"]["errors"])


def test_canonical_r4_authority_executes_semantic_verifier_for_every_proved_slot(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        roots = [
            "CC_R1_REALITY_CONTAINMENT_V1",
            "CC_R2_MISSION_SOUNDNESS_V1",
            "CC_R3_TERMINAL_CLOSURE_V1",
        ]
        _write_control_plane(root, [_proved(x) for x in roots])
        _patch_paths(monkeypatch, root)
        monkeypatch.setattr(
            rt,
            "validate_root_registry",
            lambda *args, **kwargs: {
                "pass": True,
                "status": "PASS__ROOT_CERTIFICATE_REGISTRY",
                "errors": [],
                "r4_proof_closure": True,
            },
        )
        seen = []

        def accept(root, slot, active_claim):
            seen.append(slot["root_id"])
            return {"pass": True, "status": "PASS__EXECUTABLE_SEMANTIC_ROOT_CERTIFICATE_VERIFICATION", "errors": []}

        monkeypatch.setattr(rt, "validate_semantic_root_slot", accept)
        out = rt.evaluate_canonical_registry_authority()

        assert seen == roots
        assert out["authorized"] is True
        assert out["status"] == "PASS_CANONICAL_ROOT_CERTIFICATE_AUTHORITY"


def test_open_zero_proved_registry_does_not_execute_semantic_verifier(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_control_plane(root, [])
        _patch_paths(monkeypatch, root)
        monkeypatch.setattr(
            rt,
            "validate_root_registry",
            lambda *args, **kwargs: {
                "pass": True,
                "status": "PASS__ROOT_CERTIFICATE_REGISTRY",
                "errors": [],
                "r4_proof_closure": False,
            },
        )
        monkeypatch.setattr(
            rt,
            "validate_semantic_root_slot",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
        )
        out = rt.evaluate_canonical_registry_authority()

        assert out["authorized"] is False
        assert out["status"] == "R4_CANONICAL_ROOT_CERTIFICATES_OPEN"
