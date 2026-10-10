import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
POINTER=ROOT/"canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
WORKLIST=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_P1_V4_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V4.json"
SUBJECT=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_P1_V4_DECLARED_SYSTEM_SUBJECT_20261010_V4.json"
DEP=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_SUBJECT_DEPENDENCY_CLOSURE_20261010_V1.json"
R1_BINDING=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_R1_ROOT_SUBJECT_BINDING_20261010_V2.json"
R1_VERIFY=ROOT/"canonical/verification/PROFESSIONAL_QUALITY_R1_ROOT_SUBJECT_BINDING_VERIFY_20261010_V2.json"


def blob(path):
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_pointer_binds_exact_v4_frontier_bytes():
    p=load(POINTER)
    assert p["declared_system_subject"]["git_blob_sha"] == blob(SUBJECT)
    assert p["subject_dependency_closure"]["git_blob_sha"] == blob(DEP)
    assert p["same_subject_root_binding_frontier"]["git_blob_sha"] == blob(WORKLIST)
    assert p["r1_root_subject_binding"]["binding_git_blob_sha"] == blob(R1_BINDING)
    assert p["r1_root_subject_binding"]["verification_git_blob_sha"] == blob(R1_VERIFY)


def test_v4_frontier_truth_is_noninflating_and_r2_next():
    p=load(POINTER)
    w=load(WORKLIST)
    v=load(R1_VERIFY)
    assert p["subject_dependency_closure"]["dependency_classification_complete"] is True
    assert p["same_subject_root_binding_frontier"]["verified_root_subject_binding_count"] == 1
    assert p["same_subject_root_binding_frontier"]["composition_admissible"] is False
    assert p["same_subject_root_binding_frontier"]["next_root"] == "R2_CANDIDATE_SEARCH"
    assert w["subject_dependency_closure_complete"] is True
    assert w["verified_root_subject_binding_count"] == 1
    assert w["next"].startswith("R2_CANDIDATE_SEARCH")
    assert v["pass"] is True and v["root_subject_binding_authority"] is True
    assert p["quality_authority"] is False
    assert p["terminal_authority"] is False
    assert p["terminal_credit_delta"] == 0
    assert "NO_ROOT_SUBJECT_BINDING_VERIFIED_YET" not in p["hard_nonclaims"]
