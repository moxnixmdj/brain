from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime import professional_quality_declared_system_subject_verify_v1 as subject_verify
from canonical.runtime import professional_quality_same_subject_composition_gate_v2 as gate

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
SUBJECT = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_P1_V4_DECLARED_SYSTEM_SUBJECT_20261010_V4.json"
WORKLIST = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_P1_V4_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V3.json"
GATE_GOV = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_SAME_SUBJECT_COMPOSITION_GATE_20261010_V2.json"
VERIFY = ROOT / "canonical/verification/PROFESSIONAL_QUALITY_V4_MULTISCOPE_SUBJECT_VERIFY_20261010_V1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def canonical_sha256(value) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def test_v4_subject_verifier_and_identity_are_current():
    subject = load(SUBJECT)
    assert subject["subject_sha256"] == canonical_sha256(subject["system_material"])
    out = subject_verify.verify(
        "canonical/governance/PROFESSIONAL_QUALITY_P1_V4_DECLARED_SYSTEM_SUBJECT_20261010_V4.json",
        repo_root=ROOT,
    )
    assert out["pass"] is True, out
    assert out["component_count"] == 14
    assert out["component_currentness_verified"] is True
    assert out["root_subject_binding_authority"] is False
    assert out["quality_authority"] is False
    assert out["terminal_authority"] is False


def test_v4_worklist_binds_current_subject_and_gate_with_zero_root_credit():
    work = load(WORKLIST)
    assert work["subject"]["git_blob_sha"] == git_blob_sha(SUBJECT)
    assert work["same_subject_gate"]["git_blob_sha"] == git_blob_sha(GATE_GOV)
    assert work["root_binding_count"] == 12
    assert work["roots_with_bounded_semantic_support"] == 12
    assert work["roots_with_bounded_execution_support"] == 12
    assert work["verified_root_subject_binding_count"] == 0
    assert all(row["same_subject_binding_status"] == "OPEN__NO_INDEPENDENT_ROOT_SUBJECT_BINDING_RECEIPT" for row in work["roots"])


def test_v2_gate_is_current_for_21_scopes_and_still_requires_real_bindings():
    out = gate.evaluate({"root_subject_bindings": []})
    assert out["status"] == "OPEN__SAME_SUBJECT_BINDINGS_REQUIRED", out
    assert out["pass"] is False
    assert out["scoped_root_count"] == 12
    assert out["scoped_admitted_scope_count"] == 21
    assert out["composition_admissible"] is False
    assert out["professional_quality_closed"] is False
    assert out["terminal_credit_delta"] == 0


def test_current_pointer_projects_v4_truth_without_live_promotion():
    current = load(CURRENT)
    assert current["router_path"] == "canonical/runtime/professional_quality_p1_router_v3.py"
    assert current["live_default"] is False

    candidate = current["r1_target_bound_router_v4_candidate"]
    assert candidate["full_v3_regression_equivalence_proved"] is True
    assert candidate["live_default"] is False

    subject = current["declared_system_subject"]
    assert subject["git_blob_sha"] == git_blob_sha(SUBJECT)
    assert subject["verification_git_blob_sha"] == git_blob_sha(VERIFY)
    assert subject["subject_sha256"] == "924ca9cb02980d19612b9e217b1354baa1a73990a5cd7060cc87975d1231783a"

    same = current["same_subject_composition"]
    assert same["governance_git_blob_sha"] == git_blob_sha(GATE_GOV)
    assert same["real_all_root_subject_bound"] is False
    assert same["composition_admissible"] is False

    frontier = current["same_subject_root_binding_frontier"]
    assert frontier["git_blob_sha"] == git_blob_sha(WORKLIST)
    assert frontier["verified_root_subject_binding_count"] == 0
    assert frontier["composition_admissible"] is False

    assert current["quality_authority"] is False
    assert current["terminal_authority"] is False
    assert current["terminal_credit_delta"] == 0
    assert current["leaf_coverage_projection"]["verified_global_leaf_count"] == 0
    assert current["leaf_coverage_projection"]["open_global_leaf_count"] == 24
