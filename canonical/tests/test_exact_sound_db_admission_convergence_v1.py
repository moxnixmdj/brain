from hashlib import sha1
import json

from canonical.runtime.exact_sound_db_admission_convergence_v1 import (
    SCHEMA,
    SCOPE_ID,
    compile_region_set,
)


def _blob(path):
    data = path.read_bytes()
    h = sha1()
    h.update(f"blob {len(data)}".encode("ascii") + b"\0")
    h.update(data)
    return h.hexdigest()


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (dict, list)):
        path.write_text(json.dumps(content, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_text(content, encoding="utf-8")
    return _blob(path)


def _flattened():
    return {
        "schema": "PROJECT_BRAIN_EXACT_SOUND_DB_REGION_SET_ROOT_INPUT_V1",
        "regions": [
            {"id": "A", "source_path": "canonical/governance/a.json"},
            {"id": "B", "source_path": "canonical/governance/b.json"},
        ],
        "flattening_checks": {"region_count": 2},
    }


def _binding(tmp_path, region_id, source_path):
    source_file = tmp_path / source_path
    source_sha = _write(source_file, {"region": region_id})

    route_path = f"canonical/runtime/{region_id.lower()}_route.py"
    route_file = tmp_path / route_path
    route_sha = _write(route_file, f"def run_{region_id.lower()}():\n    return True\n")

    pred_path = f"canonical/runtime/{region_id.lower()}_predicate.py"
    pred_file = tmp_path / pred_path
    pred_sha = _write(pred_file, f"def admit_{region_id.lower()}(x):\n    return True\n")

    adequacy_path = f"canonical/verification/{region_id}_adequacy.json"
    adequacy_file = tmp_path / adequacy_path
    adequacy_sha = _write(adequacy_file, {"adequate": True})

    route_id = f"route-{region_id}"
    predicate_id = f"predicate-{region_id}"
    receipt_path = f"canonical/verification/{region_id}_soundness.json"
    receipt_file = tmp_path / receipt_path
    receipt = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "admission_implies_route_adequacy": True,
        "brain_owned_route": True,
        "scope_id": SCOPE_ID,
        "region_id": region_id,
        "route_id": route_id,
        "admission_predicate_id": predicate_id,
        "route_blob_sha": route_sha,
        "admission_predicate_blob_sha": pred_sha,
        "adequacy_certificate_blob_sha": adequacy_sha,
    }
    receipt_sha = _write(receipt_file, receipt)

    return {
        "region_id": region_id,
        "scope_id": SCOPE_ID,
        "source_path": source_path,
        "source_artifact_blob_sha": source_sha,
        "route_id": route_id,
        "route_path": route_path,
        "route_blob_sha": route_sha,
        "admission_predicate_id": predicate_id,
        "admission_predicate_path": pred_path,
        "admission_predicate_blob_sha": pred_sha,
        "adequacy_certificate_path": adequacy_path,
        "adequacy_certificate_blob_sha": adequacy_sha,
        "admission_soundness_receipt_path": receipt_path,
        "admission_soundness_receipt_blob_sha": receipt_sha,
    }


def test_missing_bindings_are_the_only_output_frontier():
    out = compile_region_set(_flattened(), [])
    assert out["schema"] == SCHEMA
    assert out["pass"] is True
    assert out["status"] == "INCOMPLETE__EXACT_BINDINGS_REQUIRED"
    assert out["missing_region_count"] == 2
    assert out["complement_ready"] is False
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False


def test_fake_hex_and_nonexistent_paths_cannot_self_certify(tmp_path):
    fake = {
        "region_id": "A",
        "scope_id": SCOPE_ID,
        "source_path": "canonical/governance/a.json",
        "source_artifact_blob_sha": "1" * 40,
        "route_id": "route-A",
        "route_path": "canonical/runtime/a_route.py",
        "route_blob_sha": "2" * 40,
        "admission_predicate_id": "predicate-A",
        "admission_predicate_path": "canonical/runtime/a_predicate.py",
        "admission_predicate_blob_sha": "3" * 40,
        "adequacy_certificate_path": "canonical/verification/A_adequacy.json",
        "adequacy_certificate_blob_sha": "4" * 40,
        "admission_soundness_receipt_path": "canonical/verification/A_soundness.json",
        "admission_soundness_receipt_blob_sha": "5" * 40,
    }
    out = compile_region_set(_flattened(), [fake], repo_root=tmp_path)
    assert out["complement_ready"] is False
    assert out["missing_region_count"] == 2
    a = next(x for x in out["missing_bindings"] if x["region_id"] == "A")
    assert any("BOUND_FILE_MISSING" in x for x in a["missing"])


def test_complete_content_bound_set_compiles_exact_digest_but_no_terminal_credit(tmp_path):
    a = _binding(tmp_path, "A", "canonical/governance/a.json")
    b = _binding(tmp_path, "B", "canonical/governance/b.json")
    out = compile_region_set(_flattened(), [a, b], repo_root=tmp_path)
    assert out["pass"] is True
    assert out["complement_ready"] is True
    assert out["missing_region_count"] == 0
    assert out["predicate_set_sha256"].startswith("sha256:")
    assert out["u_empty_authorized"] is False
    assert out["abc_closed_authorized"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0


def test_receipt_byte_drift_fails_closed(tmp_path):
    a = _binding(tmp_path, "A", "canonical/governance/a.json")
    b = _binding(tmp_path, "B", "canonical/governance/b.json")
    receipt = tmp_path / a["admission_soundness_receipt_path"]
    receipt.write_text("{}\n", encoding="utf-8")
    out = compile_region_set(_flattened(), [a, b], repo_root=tmp_path)
    assert out["complement_ready"] is False
    a_missing = next(x for x in out["missing_bindings"] if x["region_id"] == "A")
    assert "UNBOUND:admission_soundness_receipt:GIT_BLOB_SHA_MISMATCH" in a_missing["missing"]


def test_receipt_binding_disagreement_fails_closed(tmp_path):
    a = _binding(tmp_path, "A", "canonical/governance/a.json")
    b = _binding(tmp_path, "B", "canonical/governance/b.json")
    receipt_path = tmp_path / a["admission_soundness_receipt_path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["route_blob_sha"] = "f" * 40
    a["admission_soundness_receipt_blob_sha"] = _write(receipt_path, receipt)
    out = compile_region_set(_flattened(), [a, b], repo_root=tmp_path)
    assert out["complement_ready"] is False
    a_missing = next(x for x in out["missing_bindings"] if x["region_id"] == "A")
    assert "RECEIPT_ROUTE_BLOB_MISMATCH" in a_missing["missing"]


def test_path_escape_fails_closed(tmp_path):
    a = _binding(tmp_path, "A", "canonical/governance/a.json")
    b = _binding(tmp_path, "B", "canonical/governance/b.json")
    a["route_path"] = "../escape.py"
    out = compile_region_set(_flattened(), [a, b], repo_root=tmp_path)
    assert out["complement_ready"] is False
    a_missing = next(x for x in out["missing_bindings"] if x["region_id"] == "A")
    assert "UNBOUND:route:PATH_ESCAPES_REPOSITORY" in a_missing["missing"]


def test_unknown_region_binding_fails_closed(tmp_path):
    x = _binding(tmp_path, "X", "canonical/governance/x.json")
    out = compile_region_set(_flattened(), [x], repo_root=tmp_path)
    assert out["pass"] is False
    assert out["reason"] == "UNKNOWN_REGION_BINDING"
