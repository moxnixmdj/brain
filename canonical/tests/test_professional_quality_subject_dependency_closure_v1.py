import copy
import json
from pathlib import Path

from canonical.runtime.professional_quality_subject_dependency_closure_v1 import (
    ROOTS,
    DependencyClosureError,
    classify_registry,
    verify_current,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"


def load_registry():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_current_registry_dependency_classification_passes_and_requires_one_refresh():
    out = verify_current(repo_root=ROOT)
    assert out["pass"] is True, out
    assert out["dependency_classification_complete"] is True
    assert out["classified_root_count"] == 12
    assert out["dynamic_external_input_root_count"] == 12
    assert out["subject_refresh_required"] is True
    assert out["missing_required_subject_components"]


def test_all_twelve_roots_have_both_static_subject_and_external_roles():
    out = classify_registry(load_registry())
    assert out["classified_root_count"] == len(ROOTS)
    for row in out["roots"]:
        assert row["subject_components"]
        assert row["external_evidence_references"]
        assert row["dynamic_external_inputs"]


def test_unknown_content_reference_field_fails_closed():
    reg = load_registry()
    reg["entries"][0]["mystery_reference"] = {
        "path": reg["entries"][0]["source_receipt"]["path"],
        "git_blob_sha": reg["entries"][0]["source_receipt"]["git_blob_sha"],
    }
    try:
        classify_registry(reg)
    except DependencyClosureError as exc:
        assert "UNCLASSIFIED_CONTENT_REFERENCE_FIELD:mystery_reference" in str(exc)
    else:
        raise AssertionError("unknown content-addressed role was accepted")


def test_missing_root_fails_closed():
    reg = load_registry()
    reg["entries"] = [
        e for e in reg["entries"] if e["root_id"] != "R9_TEMPORAL_DEPLOYMENT"
    ]
    try:
        classify_registry(reg)
    except DependencyClosureError as exc:
        assert "ROOT_COVERAGE_INCOMPLETE:R9_TEMPORAL_DEPLOYMENT" in str(exc)
    else:
        raise AssertionError("missing root was accepted")


def test_subject_external_role_collision_fails_closed():
    reg = load_registry()
    probe = copy.deepcopy(reg["entries"][0]["source_receipt"])
    reg["entries"][0]["reusable_compiler"] = probe
    try:
        classify_registry(reg)
    except DependencyClosureError as exc:
        assert "SUBJECT_EXTERNAL_ROLE_COLLISION" in str(exc)
    else:
        raise AssertionError("same dependency in subject and evidence roles was accepted")


def test_dynamic_dependency_inventory_is_total():
    out = classify_registry(load_registry())
    assert set(out["dynamic_external_inputs_by_root"]) == set(ROOTS)
    assert all(out["dynamic_external_inputs_by_root"][root] for root in ROOTS)
