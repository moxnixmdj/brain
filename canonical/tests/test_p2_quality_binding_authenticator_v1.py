import hashlib
import json

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.p2_explicit_contract_membership_v1 import P2, compile_membership
from canonical.runtime.p2_quality_binding_authenticator_v1 import (
    authenticate, RECEIPT_SCHEMA, VERIFY_SCHEMA,
)
from canonical.runtime.p2_strong_quality_visible_certifier_v5 import certify


def raw_task():
    return json.dumps({
        "contract": P2,
        "task": {
            "audience": "executive",
            "required_topics": ["T1"],
            "evidence": [{"fact_id": "F1"}],
            "edit_candidates": [{
                "id": "E1", "analysis_kind": "quantify", "topic": "T1",
                "claims": ["F1"], "intended_audience": "executive", "cost": 1,
            }],
            "edit_budget": 1,
        },
    }, separators=(",", ":"))


def write_pair(root, kind, context, claim):
    base = root / "canonical" / "verification"
    base.mkdir(parents=True, exist_ok=True)
    rp = base / (kind.lower() + "_receipt.json")
    vp = base / (kind.lower() + "_verify.json")
    rd = {
        "schema": RECEIPT_SCHEMA,
        "kind": kind,
        "context_sha256": context,
        "pass": True,
        "claim": claim,
    }
    raw = json.dumps(rd, sort_keys=True, separators=(",", ":")).encode()
    rp.write_bytes(raw)
    rblob = git_blob_id(raw, object_format="sha1")
    vd = {
        "schema": VERIFY_SCHEMA,
        "kind": kind,
        "context_sha256": context,
        "subject_git_blob_sha": rblob,
        "pass": True,
        "verifier_id": "independent-test-verifier",
    }
    vraw = json.dumps(vd, sort_keys=True, separators=(",", ":")).encode()
    vp.write_bytes(vraw)
    vblob = git_blob_id(vraw, object_format="sha1")
    return {
        "receipt": {"path": str(rp.relative_to(root)).replace("\\", "/"), "git_blob_sha": rblob},
        "verification": {"path": str(vp.relative_to(root)).replace("\\", "/"), "git_blob_sha": vblob},
    }


def valid_bindings(tmp_path, context):
    return {
        "BASELINE_LAYOUT_NONOBSCURING": write_pair(
            tmp_path, "BASELINE_LAYOUT_NONOBSCURING", context,
            {"baseline_layout_nonobscuring": True},
        ),
        "EMPTY_BASELINE_EQUIVALENCE": write_pair(
            tmp_path, "EMPTY_BASELINE_EQUIVALENCE", context,
            {"mechanics_only_baseline_equals_empty_p2_plan": True},
        ),
        "ABLATION_RESCUE_SEMANTICS": write_pair(
            tmp_path, "ABLATION_RESCUE_SEMANTICS", context,
            {
                "ablation_rescue_semantics_bound_to_certifier_policy": True,
                "policy": "REMOVE_MAXIMUM_MARGINAL_VALUE_SELECTED_EDIT__LEXICAL_TIE_BREAK",
            },
        ),
        "RUBRIC_EQUIVALENCE": write_pair(
            tmp_path, "RUBRIC_EQUIVALENCE", context,
            {"explicit_rubric_equivalent_to_p2_objective": True},
        ),
        "NATIVE_GATE_REQUIREMENT": write_pair(
            tmp_path, "NATIVE_GATE_REQUIREMENT", context,
            {"native_mechanical_gate_required": False},
        ),
    }


def test_authenticated_quality_bindings_reconstruct_certifier_input(tmp_path):
    member = compile_membership(raw_task(), source_id="task")
    refs = valid_bindings(tmp_path, member["normalized_public_sha256"])
    out = authenticate(refs, context_sha256=member["normalized_public_sha256"], repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["quality_binding"]["explicit_rubric_equivalent_to_p2_objective"] is True


def test_v5_certifier_uses_only_authenticated_bindings(tmp_path):
    member = compile_membership(raw_task(), source_id="task")
    refs = valid_bindings(tmp_path, member["normalized_public_sha256"])
    out = certify({
        "raw_p2_source": raw_task(),
        "raw_p2_source_id": "task",
        "quality_binding_references": refs,
    }, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["opaque_caller_receipts_permitted"] is False


def test_receipt_blob_drift_fails_closed(tmp_path):
    member = compile_membership(raw_task(), source_id="task")
    refs = valid_bindings(tmp_path, member["normalized_public_sha256"])
    refs["RUBRIC_EQUIVALENCE"]["receipt"]["git_blob_sha"] = "0" * 40
    out = authenticate(refs, context_sha256=member["normalized_public_sha256"], repo_root=tmp_path)
    assert out["pass"] is False


def test_context_mismatch_fails_closed(tmp_path):
    member = compile_membership(raw_task(), source_id="task")
    refs = valid_bindings(tmp_path, "0" * 64)
    out = authenticate(refs, context_sha256=member["normalized_public_sha256"], repo_root=tmp_path)
    assert out["pass"] is False


def test_native_gate_requirement_true_requires_separate_pass_receipt(tmp_path):
    member = compile_membership(raw_task(), source_id="task")
    context = member["normalized_public_sha256"]
    refs = valid_bindings(tmp_path, context)
    refs["NATIVE_GATE_REQUIREMENT"] = write_pair(
        tmp_path, "NATIVE_GATE_REQUIREMENT", context,
        {"native_mechanical_gate_required": True},
    )
    out = authenticate(refs, context_sha256=context, repo_root=tmp_path)
    assert out["pass"] is False
    assert "NATIVE_MECHANICAL_GATE_PASS_BINDING_REQUIRED" in out["errors"]
