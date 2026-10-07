from hashlib import sha1
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from canonical.runtime.terminal_root_decision_gate_v1 import evaluate

SCOPE = "scope://opus55/observable-trace"


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    digest = sha1()
    digest.update(f"blob {len(data)}".encode("ascii") + bytes([0]))
    digest.update(data)
    return digest.hexdigest()


def _bound_receipt(root: Path, kind: str, **premises):
    proof = {
        "proof_kind": kind,
        "scope_id": SCOPE,
        "conclusion": "success",
        **premises,
    }
    proof_path = root / "proof.json"
    proof_path.write_text(json.dumps(proof, sort_keys=True) + "\n", encoding="utf-8")
    proof_binding = {"path": "proof.json", "git_blob_sha": _git_blob_sha(proof_path)}

    verifier = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "proof_artifact": proof_binding,
    }
    verifier_path = root / "verifier.json"
    verifier_path.write_text(json.dumps(verifier, sort_keys=True) + "\n", encoding="utf-8")
    verifier_binding = {"path": "verifier.json", "git_blob_sha": _git_blob_sha(verifier_path)}

    return {
        "proof_kind": kind,
        "scope_id": SCOPE,
        "conclusion": "success",
        "proof_artifact": proof_binding,
        "verifier_receipt_artifact": verifier_binding,
    }


def test_full_scope_db_cover_closes_abc_only():
    with TemporaryDirectory() as td:
        root = Path(td)
        r = _bound_receipt(root, "FULL_SCOPE_DB_COVER", s_trace_subset_db=True)
        out = evaluate({"closure_receipt": r}, repo_root=root)
        assert out["pass"] is True
        assert out["x"] is False
        assert out["u_empty"] is True
        assert out["abc_closed"] is True
        assert out["d_finality_required"] is True
        assert out["terminal"] is False


def test_target_escape_nonoccupancy_closes_abc_only():
    with TemporaryDirectory() as td:
        root = Path(td)
        r = _bound_receipt(root, "TARGET_ESCAPE_NONOCCUPANCY", u_intersection_escape_empty=True)
        out = evaluate({"closure_receipt": r}, repo_root=root)
        assert out["pass"] is True
        assert out["proof_rule"] == "DIRECT_TARGET_ESCAPE_NONOCCUPANCY"


def test_generator_closure_requires_bound_load_bearing_premises():
    with TemporaryDirectory() as td:
        root = Path(td)
        r = _bound_receipt(
            root,
            "GENERATOR_CLOSURE_SCOPE_COMPLETE",
            generator_basis_complete=True,
            all_generators_covered=True,
            all_transforms_abc_preserving=True,
            all_useful_contexts_reachable=True,
        )
        assert evaluate({"closure_receipt": r}, repo_root=root)["pass"] is True

        proof_path = root / "proof.json"
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
        proof["all_transforms_abc_preserving"] = False
        proof_path.write_text(json.dumps(proof, sort_keys=True) + "\n", encoding="utf-8")
        r["proof_artifact"]["git_blob_sha"] = _git_blob_sha(proof_path)
        verifier_path = root / "verifier.json"
        verifier = json.loads(verifier_path.read_text(encoding="utf-8"))
        verifier["proof_artifact"] = r["proof_artifact"]
        verifier_path.write_text(json.dumps(verifier, sort_keys=True) + "\n", encoding="utf-8")
        r["verifier_receipt_artifact"]["git_blob_sha"] = _git_blob_sha(verifier_path)

        out = evaluate({"closure_receipt": r}, repo_root=root)
        assert out["pass"] is False
        assert out["reason"] == "GENERATOR_CLOSURE_PREMISES_UNPROVED"


def test_selected_cover_requires_bound_sound_union_and_unsat_complement():
    with TemporaryDirectory() as td:
        root = Path(td)
        r = _bound_receipt(
            root,
            "SELECTED_COVER_COMPLEMENT_UNSAT",
            every_admission_sound=True,
            residual_complement_unsat=True,
        )
        assert evaluate({"closure_receipt": r}, repo_root=root)["pass"] is True


def test_fake_hex_bindings_cannot_self_certify_root():
    declaration = {
        "proof_kind": "FULL_SCOPE_DB_COVER",
        "scope_id": SCOPE,
        "conclusion": "success",
        "independent_verified": True,
        "exact_byte_bound": True,
        "s_trace_subset_db": True,
        "proof_artifact": {"path": "missing-proof.json", "git_blob_sha": "a" * 40},
        "verifier_receipt_artifact": {"path": "missing-verifier.json", "git_blob_sha": "b" * 40},
    }
    with TemporaryDirectory() as td:
        out = evaluate({"closure_receipt": declaration}, repo_root=Path(td))
    assert out["pass"] is False
    assert out["reason"] == "CONTENT_ADDRESSED_PROOF_AND_VERIFIER_REQUIRED"


def test_proof_byte_drift_fails_closed():
    with TemporaryDirectory() as td:
        root = Path(td)
        r = _bound_receipt(root, "FULL_SCOPE_DB_COVER", s_trace_subset_db=True)
        (root / "proof.json").write_text("{}\n", encoding="utf-8")
        out = evaluate({"closure_receipt": r}, repo_root=root)
        assert out["pass"] is False
        assert out["detail"]["proof_error"] == "GIT_BLOB_SHA_MISMATCH"


def test_verifier_must_bind_exact_proof_artifact():
    with TemporaryDirectory() as td:
        root = Path(td)
        r = _bound_receipt(root, "FULL_SCOPE_DB_COVER", s_trace_subset_db=True)
        verifier_path = root / "verifier.json"
        verifier = json.loads(verifier_path.read_text(encoding="utf-8"))
        verifier["proof_artifact"] = {"path": "other.json", "git_blob_sha": "c" * 40}
        verifier_path.write_text(json.dumps(verifier, sort_keys=True) + "\n", encoding="utf-8")
        r["verifier_receipt_artifact"]["git_blob_sha"] = _git_blob_sha(verifier_path)
        out = evaluate({"closure_receipt": r}, repo_root=root)
        assert out["pass"] is False
        assert out["reason"] == "VERIFIER_PROOF_BINDING_MISMATCH"


def test_manifest_booleans_cannot_override_bound_proof():
    with TemporaryDirectory() as td:
        root = Path(td)
        r = _bound_receipt(root, "FULL_SCOPE_DB_COVER", s_trace_subset_db=False)
        r["s_trace_subset_db"] = True
        r["independent_verified"] = True
        r["exact_byte_bound"] = True
        out = evaluate({"closure_receipt": r}, repo_root=root)
        assert out["pass"] is False
        assert out["reason"] == "FULL_SCOPE_DB_COVER_UNPROVED"
