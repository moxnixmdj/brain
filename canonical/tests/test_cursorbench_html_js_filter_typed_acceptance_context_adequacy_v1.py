import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
A=ROOT/"canonical/governance/CURSORBENCH_HTML_JS_FILTER_TYPED_ACCEPTANCE_CONTEXT_POLICY_ADEQUACY_ACTIVATION_20261009_V1.json"

def git_blob_sha(path):
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode()+b"\0"+data)
    return h.hexdigest()

def test_exact_context_applies_existing_five_atom_adequacy_theorem_without_widening():
    a=json.loads(A.read_text())
    for ref in [
        a["policy"]["adequacy_certificate"],
        a["policy"]["exact_policy"],
        a["exact_model"],
        a["condition_truth"]["source"],
        a["postfreeze_validation"],
        a["preverifier_freeze"],
    ]:
        assert git_blob_sha(ROOT/ref["path"])==ref["git_blob_sha"]
    cert=json.loads((ROOT/a["policy"]["adequacy_certificate"]["path"]).read_text())
    replay=json.loads((ROOT/a["condition_truth"]["source"]["path"]).read_text())
    audit=json.loads((ROOT/a["postfreeze_validation"]["path"]).read_text())
    expected={x["id"] for x in cert["policy_condition"]["args"]}
    assert expected==set(a["condition_truth"]["proved_atoms"])
    assert set(replay["summary"]["proved_atoms"])==expected
    assert all(replay["summary"][k] is True for k in [
        "supported_transform_pass","source_coverage_pass","dependency_provenance_pass","information_boundary_pass"
    ])
    assert audit["pass"] is True
    assert a["theorem_application"]["policy_condition_satisfied_for_exact_context"] is True
    assert a["theorem_application"]["policy_adequate_for_behavior_on_exact_context"] is True
    assert a["theorem_application"]["whole_behavior_adequacy"] is False
    assert a["theorem_application"]["whole_cursorbench_adequacy"] is False
    assert a["target_relevance"]["actual_cursorbench_task_membership_proved"] is False
    assert a["accounting"]["terminal_credit_delta"]==0
