import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/"canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_MEMBERSHIP_MECHANISM_COMPLETE_RECONCILIATION_20261009_V1.json"

def git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode("ascii")+b"\0"+data)
    return h.hexdigest()

def test_five_atom_membership_mechanism_completeness_is_exact_and_zero_credit():
    doc=json.loads(DOC.read_text(encoding="utf-8"))
    assert doc["target_predicate"]=="CODING_CURSORBENCH_GE_57_8"
    assert doc["policy_id"]=="BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"
    assert doc["mechanism_accounting"]=={
        "condition_atom_count":5,
        "distinct_proof_mechanism_count":4,
        "structurally_provable_atom_count_after_exact_model_exists":1,
        "real_evidence_gated_atom_count":4,
        "real_evidence_bundle_count_for_four_atoms":3,
        "missing_implementation_mechanism_count":0,
    }
    assert set(doc["atom_mechanisms"])=={
        "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1",
        "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1",
        "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1",
        "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1",
        "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1",
    }
    for row in doc["atom_mechanisms"].values():
        for key in ("activation","verification"):
            ref=row[key]
            assert git_blob_sha(ROOT/ref["path"])==ref["git_blob_sha"], (key,ref)
    for key in ("certificate","binding"):
        ref=doc["policy"][key]
        assert git_blob_sha(ROOT/ref["path"])==ref["git_blob_sha"], key
    for key in ("conditioned_registry","p3_front_door","end_to_end_test"):
        ref=doc["composition"][key]
        assert git_blob_sha(ROOT/ref["path"])==ref["git_blob_sha"], key

    assert doc["composition"]["selected_policy_id"]==doc["policy_id"]
    assert doc["composition"]["p3_common_policy_status"]=="COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS"
    assert doc["composition"]["terminal_authority"] is False
    assert doc["exact_next_real_evidence_object"]["id"]=="CURSORBENCH_TARGET_RELEVANT_TYPED_ACCEPTANCE_EVIDENCE_BUNDLE_V1"
    assert len(doc["exact_next_real_evidence_object"]["components"])==5
    assert doc["accounting"]["acceptance_credit_delta"]==0
    assert doc["accounting"]["family_credit_delta"]==0
    assert doc["accounting"]["ownership_credit_delta"]==0
    assert doc["accounting"]["terminal_credit_delta"]==0
    assert doc["promotion_authority"] is False
    assert doc["fresh_reality_authority"] is False
