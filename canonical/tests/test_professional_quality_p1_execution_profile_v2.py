import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P1=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V2.json"
BIND=ROOT/"canonical/governance/PROFESSIONAL_ARTIFACT_HARD_DEFECT_PREFLIGHT_BINDING_20261010_V1.json"
RUNTIME=ROOT/"canonical/runtime/professional_artifact_hard_defect_preflight_v1.py"

def blob(path: Path) -> str:
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode("ascii")+b"\0"+data)
    return h.hexdigest()

def test_p1_v2_binds_exact_verified_preflight_before_holistic_judgment():
    p=json.loads(P1.read_text(encoding="utf-8"))
    b=json.loads(BIND.read_text(encoding="utf-8"))
    pre=p["bound_hard_defect_preflight"]
    assert blob(BIND)==pre["binding_git_blob_sha"]
    assert blob(RUNTIME)==pre["runtime_git_blob_sha"]
    assert b["capability"]["runtime"]["git_blob_sha"]==blob(RUNTIME)
    steps=p["steps"]
    i=steps.index("RUN_FROZEN_SOURCE_OR_POLICY_BOUND_HARD_DEFECT_PREFLIGHT_WHEN_SUPPORTED")
    j=steps.index("RUN_CRITERION_SPECIFIC_PLUS_HOLISTIC_COMPARATIVE_EVALUATION")
    assert i < j
    assert p["preflight_semantics"]["quality_equivalence"] is False
    assert p["preflight_semantics"]["professional_excellence_authority"] is False
    assert p["accounting"]["acceptance_credit_delta"]==0
    assert p["accounting"]["terminal_credit_delta"]==0
    assert "NO_COMPLETE_PRESENTATION_ORDER" in p["hard_nonclaims"]
