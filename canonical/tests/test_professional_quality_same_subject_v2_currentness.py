from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime import professional_quality_same_subject_composition_gate_v2 as gate

ROOT = Path(__file__).resolve().parents[2]

CURRENT = ROOT / "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
SUBJECT = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_P1_V3_DECLARED_SYSTEM_SUBJECT_20261010_V2.json"
WORKLIST = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_P1_V3_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V2.json"
GATE_GOV = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_SAME_SUBJECT_COMPOSITION_GATE_20261010_V2.json"
REGISTRY = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"
VERIFY = ROOT / "canonical/verification/PROFESSIONAL_QUALITY_SAME_SUBJECT_COMPOSITION_GATE_V2_CURRENT_VERIFY_20261010_V1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def canonical_sha256(value) -> str:
    data = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def test_v2_declared_subject_identity_is_current_and_self_consistent():
    subject = load(SUBJECT)
    assert subject["subject_sha256"] == canonical_sha256(subject["system_material"])
    assert subject["subject_id"] == "PROFESSIONAL_QUALITY_P1_V3_INTEGRATED_SYSTEM_20261010_V2"

    for component in subject["system_material"]["components"]:
        path = ROOT / component["path"]
        assert path.is_file(), component
        assert git_blob_sha(path) == component["git_blob_sha"], component


def test_v2_worklist_matches_current_21_scope_registry_without_binding_credit():
    work = load(WORKLIST)
    registry = load(REGISTRY)

    assert work["subject"]["git_blob_sha"] == git_blob_sha(SUBJECT)
    assert work["same_subject_gate"]["git_blob_sha"] == git_blob_sha(GATE_GOV)
    assert work["scoped_registry"]["git_blob_sha"] == git_blob_sha(REGISTRY)
    assert work["current_scoped_capability_count"] == len(registry["entries"]) == 21
    assert work["root_binding_count"] == len(work["roots"]) == 12
    assert work["verified_root_subject_binding_count"] == 0

    registry_roots = {entry["root_id"] for entry in registry["entries"]}
    assert registry_roots == {row["root_id"] for row in work["roots"]}
    for row in work["roots"]:
        support = row["current_scoped_support"]
        assert support["semantic_scoped_support"] is True, row["root_id"]
        assert support["execution_scoped_support"] is True, row["root_id"]
        assert row["same_subject_binding_status"] == "OPEN__NO_INDEPENDENT_ROOT_SUBJECT_BINDING_RECEIPT"


def test_current_pointer_binds_v2_chain_and_preserves_zero_credit():
    current = load(CURRENT)

    assert current["declared_system_subject"]["git_blob_sha"] == git_blob_sha(SUBJECT)
    assert current["same_subject_composition"]["governance_git_blob_sha"] == git_blob_sha(GATE_GOV)
    assert current["same_subject_composition"]["verification_git_blob_sha"] == git_blob_sha(VERIFY)
    assert current["same_subject_root_binding_frontier"]["git_blob_sha"] == git_blob_sha(WORKLIST)
    assert current["same_subject_root_binding_frontier"]["verified_root_subject_binding_count"] == 0
    assert current["same_subject_root_binding_frontier"]["composition_admissible"] is False
    assert current["same_subject_composition"]["real_all_root_subject_bound"] is False
    assert current["same_subject_composition"]["composition_admissible"] is False
    assert current["quality_authority"] is False
    assert current["terminal_authority"] is False
    assert current["terminal_credit_delta"] == 0
    assert current["leaf_coverage_projection"]["verified_global_leaf_count"] == 0
    assert current["leaf_coverage_projection"]["open_global_leaf_count"] == 24


def test_live_v2_gate_is_current_but_requires_real_root_bindings():
    out = gate.evaluate({"root_subject_bindings": []})
    assert out["status"] == "OPEN__SAME_SUBJECT_BINDINGS_REQUIRED", out
    assert out["pass"] is False
    assert out["scoped_root_count"] == 12
    assert out["scoped_admitted_scope_count"] == 21
    assert out["composition_admissible"] is False
    assert out["professional_quality_closed"] is False
    assert out["quality_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
