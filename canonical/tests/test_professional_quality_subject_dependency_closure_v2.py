import copy
import json
from pathlib import Path

from canonical.runtime import professional_quality_subject_dependency_closure_v2 as closure

ROOT = Path(__file__).resolve().parents[2]
SUBJECT = ROOT / closure.SUBJECT_PATH


def subject():
    return json.loads(SUBJECT.read_text(encoding="utf-8"))


def omit(path):
    doc = copy.deepcopy(subject())
    doc["system_material"]["components"] = [
        row for row in doc["system_material"]["components"]
        if row["path"] != path
    ]
    return doc


def test_current_subject_passes():
    out = closure.verify_current(repo_root=ROOT)
    assert out["pass"] is True, out
    assert out["subject_component_count"] == 20
    assert out["subject_sha256"] == "dc55c7496012816b569d4ef7efe8cd836c8024b43cbbe31355bd38aebeb0627d"


def test_router_v2_required():
    out = closure.verify_subject(
        omit("canonical/runtime/professional_quality_p1_router_v2.py"),
        repo_root=ROOT,
    )
    assert out["pass"] is False
    assert "TRANSITIVE_RUNTIME_DEPENDENCY_MISSING" in out["reason"]


def test_profile_v1_required():
    out = closure.verify_subject(
        omit("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V1.json"),
        repo_root=ROOT,
    )
    assert out["pass"] is False
    assert "LOAD_BEARING_CONFIG_MISSING" in out["reason"]


def test_scoped_evidence_runtime_required():
    out = closure.verify_subject(
        omit("canonical/runtime/professional_quality_scoped_evidence_v1.py"),
        repo_root=ROOT,
    )
    assert out["pass"] is False
    assert "TRANSITIVE_RUNTIME_DEPENDENCY_MISSING" in out["reason"]


def test_assurance_graph_required():
    out = closure.verify_subject(
        omit("canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json"),
        repo_root=ROOT,
    )
    assert out["pass"] is False
    assert "LOAD_BEARING_CONFIG_MISSING" in out["reason"]


def test_leaf_evidence_registry_required():
    out = closure.verify_subject(
        omit("canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json"),
        repo_root=ROOT,
    )
    assert out["pass"] is False
    assert "LOAD_BEARING_CONFIG_MISSING" in out["reason"]


def test_goal_binding_kernel_required():
    out = closure.verify_subject(
        omit("canonical/runtime/goal_to_decision_binding_authority_v1.py"),
        repo_root=ROOT,
    )
    assert out["pass"] is False
    assert "TRANSITIVE_RUNTIME_DEPENDENCY_MISSING" in out["reason"]


def test_external_metadata_stays_outside_subject():
    out = closure.verify_current(repo_root=ROOT)
    assert out["pass"] is True, out
    targets = {row["to"] for row in out["external_metadata_edges"]}
    assert "canonical/evidence/AA_BRIEFCASE_LITE_PRESENTATION_PAIRWISE_CONTRACT_MANIFEST_20261007_V1.json" in targets
    paths = {row["path"] for row in subject()["system_material"]["components"]}
    assert "canonical/evidence/AA_BRIEFCASE_LITE_PRESENTATION_PAIRWISE_CONTRACT_MANIFEST_20261007_V1.json" not in paths
