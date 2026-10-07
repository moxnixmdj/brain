import json

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.symbolic_admission_predicate_registry_v1 import (
    ADEQUACY_SCHEMA,
    PREDICATE_SCHEMA,
    SCOPE_SCHEMA,
    SCOPE_VERIFY_SCHEMA,
    VERIFY_SCHEMA,
    _sha256,
    evaluate,
)


def write_doc(root, name, doc):
    path = root / "canonical" / "verification" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(raw)
    return {
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "git_blob_sha": git_blob_id(raw, object_format="sha1"),
    }


def write_scope(root, scope_id="scope://opus55/observable-trace", ast=None):
    ast = ast or {"op": "TRUE"}
    digest = _sha256(ast)
    subject_doc = {
        "schema": SCOPE_SCHEMA,
        "scope_id": scope_id,
        "scope_predicate_ast": ast,
        "scope_predicate_ast_sha256": digest,
    }
    subject = write_doc(root, "scope.json", subject_doc)
    verify_doc = {
        "schema": SCOPE_VERIFY_SCHEMA,
        "scope_id": scope_id,
        "subject_git_blob_sha": subject["git_blob_sha"],
        "scope_predicate_ast_sha256": digest,
        "scope_complete_for_s_trace": True,
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "verifier_id": "independent-scope-test-verifier",
    }
    verify = write_doc(root, "scope_verify.json", verify_doc)
    return subject, verify


def write_route(root, pid="A1", atom="A", scope_id="scope://opus55/observable-trace"):
    rid = "r-" + pid
    cid = "c-" + pid
    ast = {"op": "ATOM", "id": atom}
    ast_digest = _sha256(ast)
    pred_doc = {
        "schema": PREDICATE_SCHEMA,
        "scope_id": scope_id,
        "route_id": rid,
        "cell_id": cid,
        "admission_predicate_id": pid,
        "admission_predicate_ast": ast,
        "admission_predicate_ast_sha256": ast_digest,
    }
    pred = write_doc(root, pid + "_predicate.json", pred_doc)
    adequacy_doc = {
        "schema": ADEQUACY_SCHEMA,
        "scope_id": scope_id,
        "route_id": rid,
        "cell_id": cid,
        "admission_predicate_id": pid,
        "admission_predicate_git_blob_sha": pred["git_blob_sha"],
        "brain_owned": True,
        "deployed": True,
        "resource_admissible": True,
        "adequacy_proved": True,
        "conclusion": "success",
    }
    adequacy = write_doc(root, pid + "_adequacy.json", adequacy_doc)
    verify_doc = {
        "schema": VERIFY_SCHEMA,
        "scope_id": scope_id,
        "route_id": rid,
        "cell_id": cid,
        "admission_predicate_id": pid,
        "predicate_git_blob_sha": pred["git_blob_sha"],
        "adequacy_certificate_git_blob_sha": adequacy["git_blob_sha"],
        "admission_predicate_ast_sha256": ast_digest,
        "independent_verified": True,
        "exact_byte_bound": True,
        "admission_implies_route_adequacy": True,
        "conclusion": "success",
        "verifier_id": "independent-route-test-verifier",
    }
    verify = write_doc(root, pid + "_verify.json", verify_doc)
    return {
        "cell_id": cid,
        "route_id": rid,
        "admission_predicate_id": pid,
        "admission_predicate_reference": pred,
        "adequacy_certificate_reference": adequacy,
        "admission_soundness_verification_reference": verify,
    }


def payload(root):
    scope, scope_verify = write_scope(root)
    return {
        "scope_id": "scope://opus55/observable-trace",
        "scope_predicate_reference": scope,
        "scope_completeness_verification_reference": scope_verify,
        "routes": [write_route(root, "A1", "A"), write_route(root, "A2", "B")],
    }


def test_builds_content_authenticated_symbolic_residual_without_false_closure(tmp_path):
    out = evaluate(payload(tmp_path), repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["opaque_caller_soundness_claims_permitted"] is False
    assert out["residual_definition"] == "S_TRACE_AND_NOT_ANY_SOUND_ADMISSION_PREDICATE"
    assert out["selected_cover_complete"] is False
    assert out["u_empty"] is False
    assert out["terminal"] is False


def test_forged_true_predicate_with_fake_blob_fails_closed(tmp_path):
    p = payload(tmp_path)
    p["routes"][0]["admission_predicate_ast"] = {"op": "TRUE"}
    p["routes"][0]["admission_soundness_receipt"] = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "admission_implies_route_adequacy": True,
    }
    p["routes"][0]["admission_predicate_reference"]["git_blob_sha"] = "0" * 40
    out = evaluate(p, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "ROUTE_AUTHENTICATION_FAILED"


def test_scope_blob_drift_fails_closed(tmp_path):
    p = payload(tmp_path)
    p["scope_predicate_reference"]["git_blob_sha"] = "0" * 40
    out = evaluate(p, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "SCOPE_AUTHENTICATION_FAILED"


def test_verifier_subject_mismatch_fails_closed(tmp_path):
    p = payload(tmp_path)
    ref = p["routes"][0]["admission_soundness_verification_reference"]
    path = tmp_path / ref["path"]
    doc = json.loads(path.read_text())
    doc["predicate_git_blob_sha"] = "0" * 40
    p["routes"][0]["admission_soundness_verification_reference"] = write_doc(
        tmp_path, "A1_verify_mismatch.json", doc
    )
    out = evaluate(p, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "ROUTE_AUTHENTICATION_FAILED"


def test_duplicate_predicate_identity_fails_closed(tmp_path):
    p = payload(tmp_path)
    p["routes"][1]["admission_predicate_id"] = "A1"
    out = evaluate(p, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "ROUTE_AUTHENTICATION_FAILED"
