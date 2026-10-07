from hashlib import sha1
import json

from canonical.runtime.predicate_selected_cover_complement_gate_v1 import (
    evaluate,
    predicate_set_digest,
)

SCOPE = "scope://opus55/observable-trace"


def _blob(path):
    data = path.read_bytes()
    h = sha1()
    h.update(f"blob {len(data)}".encode("ascii") + b"\0")
    h.update(data)
    return h.hexdigest()


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return _blob(path)


def _route(tmp_path, cell, route, pid, ch):
    route_file = tmp_path / f"canonical/runtime/{route}.py"
    route_file.parent.mkdir(parents=True, exist_ok=True)
    route_file.write_text("def run():\n    return True\n", encoding="utf-8")
    route_sha = _blob(route_file)

    pred_file = tmp_path / f"canonical/runtime/{pid}.py"
    pred_file.write_text("def admit(x):\n    return True\n", encoding="utf-8")
    pred_sha = _blob(pred_file)

    adequacy_file = tmp_path / f"canonical/verification/{cell}_adequacy.json"
    adequacy_sha = _write(adequacy_file, {"adequate": True, "seed": ch})

    receipt_path = f"canonical/verification/{cell}_soundness.json"
    receipt_file = tmp_path / receipt_path
    receipt = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "admission_implies_route_adequacy": True,
        "brain_owned_route": True,
        "scope_id": SCOPE,
        "cell_id": cell,
        "route_id": route,
        "admission_predicate_id": pid,
        "route_blob_sha": route_sha,
        "admission_predicate_blob_sha": pred_sha,
        "adequacy_certificate_blob_sha": adequacy_sha,
    }
    receipt_sha = _write(receipt_file, receipt)

    return {
        "cell_id": cell,
        "route_id": route,
        "route_blob_sha": route_sha,
        "admission_predicate_id": pid,
        "admission_predicate_blob_sha": pred_sha,
        "adequacy_certificate_blob_sha": adequacy_sha,
        "admission_soundness_receipt_path": receipt_path,
        "admission_soundness_receipt_blob_sha": receipt_sha,
    }


def _payload(tmp_path):
    routes = [
        _route(tmp_path, "c1", "r1", "A1", "1"),
        _route(tmp_path, "c2", "r2", "A2", "4"),
    ]
    receipt = {
        "receipt_id": "cover",
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "proof_kind": "FORMAL_UNSAT",
        "residual_complement_unsat": True,
        "scope_id": SCOPE,
        "predicate_set_sha256": predicate_set_digest(SCOPE, routes),
        "residual_definition": "S_TRACE_AND_NOT_ANY_SOUND_ADMISSION_PREDICATE",
    }
    receipt_path = tmp_path / "canonical/verification/complement.json"
    receipt_sha = _write(receipt_path, receipt)
    return {
        "scope_id": SCOPE,
        "routes": routes,
        "complement_coverage_receipt_artifact": {
            "path": "canonical/verification/complement.json",
            "git_blob_sha": receipt_sha,
        },
    }


def test_sound_predicates_plus_unsat_complement_close_abc_not_terminal(tmp_path):
    out = evaluate(_payload(tmp_path), repo_root=tmp_path)
    assert out["pass"] is True
    assert out["selected_cover_complete_authorized"] is True
    assert out["u_empty_authorized"] is True
    assert out["abc_closed_authorized"] is True
    assert out["d_finality_required"] is True
    assert out["terminal_authority"] is False


def test_inline_self_certified_complement_receipt_is_rejected(tmp_path):
    p = _payload(tmp_path)
    p.pop("complement_coverage_receipt_artifact")
    p["complement_coverage_receipt"] = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "residual_complement_unsat": True,
    }
    out = evaluate(p, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "COMPLEMENT_COVERAGE_RECEIPT_ARTIFACT_REQUIRED"


def test_stale_predicate_set_digest_blocks_cover(tmp_path):
    p = _payload(tmp_path)
    receipt_path = tmp_path / p["complement_coverage_receipt_artifact"]["path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["predicate_set_sha256"] = "sha256:" + "0" * 64
    p["complement_coverage_receipt_artifact"]["git_blob_sha"] = _write(
        receipt_path, receipt
    )
    out = evaluate(p, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "COMPLEMENT_PREDICATE_SET_DIGEST_MISMATCH"


def test_soundness_receipt_byte_drift_blocks_cover(tmp_path):
    p = _payload(tmp_path)
    receipt_path = tmp_path / p["routes"][0]["admission_soundness_receipt_path"]
    receipt_path.write_text("{}\n", encoding="utf-8")
    out = evaluate(p, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "ADMISSION_SOUNDNESS_RECEIPT_UNBOUND"
    assert out["detail"]["binding_error"] == "GIT_BLOB_SHA_MISMATCH"


def test_complement_receipt_byte_drift_blocks_cover(tmp_path):
    p = _payload(tmp_path)
    receipt_path = tmp_path / p["complement_coverage_receipt_artifact"]["path"]
    receipt_path.write_text("{}\n", encoding="utf-8")
    out = evaluate(p, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "COMPLEMENT_COVERAGE_RECEIPT_UNBOUND"
    assert out["detail"]["binding_error"] == "GIT_BLOB_SHA_MISMATCH"


def test_scope_mismatch_blocks_cover(tmp_path):
    p = _payload(tmp_path)
    path = tmp_path / p["routes"][1]["admission_soundness_receipt_path"]
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["scope_id"] = "other"
    p["routes"][1]["admission_soundness_receipt_blob_sha"] = _write(path, receipt)
    out = evaluate(p, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "ADMISSION_SOUNDNESS_SCOPE_MISMATCH"


def test_duplicate_predicate_id_fails_closed(tmp_path):
    p = _payload(tmp_path)
    p["routes"][1]["admission_predicate_id"] = "A1"
    out = evaluate(p, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "ADMISSION_PREDICATE_ID_DUPLICATE"
