"""Bounded semantic refinement proof for terminal_root_decision_gate_v1."""
from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from canonical.runtime import terminal_root_decision_gate_v1 as gate

SCHEMA = "PROJECT_BRAIN_TERMINAL_ROOT_DECISION_GATE_REFINEMENT_RECEIPT_V1"
ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = Path(
    "canonical/governance/TERMINAL_ROOT_DECISION_GATE_ABSTRACT_SPEC_20261010_V1.json"
)
RUNTIME_PATH = Path("canonical/runtime/terminal_root_decision_gate_v1.py")


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "pass": False,
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "refinement_verified": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _bound_receipt(root: Path, kind: str, **premises: Any) -> dict[str, Any]:
    proof = {
        "proof_kind": kind,
        "scope_id": gate.SCOPE_ID,
        "conclusion": "success",
        **premises,
    }
    proof_path = root / "proof.json"
    proof_path.write_text(json.dumps(proof, sort_keys=True) + "\n", encoding="utf-8")
    proof_binding = {"path": "proof.json", "git_blob_sha": gate._git_blob_sha(proof_path)}

    verifier = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "proof_artifact": proof_binding,
    }
    verifier_path = root / "verifier.json"
    verifier_path.write_text(
        json.dumps(verifier, sort_keys=True) + "\n", encoding="utf-8"
    )
    verifier_binding = {
        "path": "verifier.json",
        "git_blob_sha": gate._git_blob_sha(verifier_path),
    }
    return {
        "proof_kind": kind,
        "scope_id": gate.SCOPE_ID,
        "conclusion": "success",
        "proof_artifact": proof_binding,
        "verifier_receipt_artifact": verifier_binding,
    }


def _static_proof(source: str, legal_kinds: set[str]) -> dict[str, Any]:
    tree = ast.parse(source)
    allowed = None
    terminal_true_literals = 0
    terminal_credit_nonzero_literals = 0
    success_status_literals = 0

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "ALLOWED_PROOF_KINDS"
        ):
            try:
                allowed = set(ast.literal_eval(node.value))
            except Exception:
                allowed = None

        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "terminal":
                    if isinstance(value, ast.Constant) and value.value is True:
                        terminal_true_literals += 1
                if isinstance(key, ast.Constant) and key.value == "terminal_credit_delta":
                    if not (
                        isinstance(value, ast.Constant)
                        and value.value == 0
                        and not isinstance(value.value, bool)
                    ):
                        terminal_credit_nonzero_literals += 1

        if isinstance(node, ast.Constant) and node.value == "PASS__TERMINAL_ROOT_NOT_X_PROVED":
            success_status_literals += 1

    return {
        "pass": (
            allowed == legal_kinds
            and terminal_true_literals == 0
            and terminal_credit_nonzero_literals == 0
            and success_status_literals == 1
        ),
        "allowed_proof_kinds_exact": allowed == legal_kinds,
        "terminal_true_literal_count": terminal_true_literals,
        "nonzero_terminal_credit_literal_count": terminal_credit_nonzero_literals,
        "success_status_literal_count": success_status_literals,
    }


def _dynamic_proof(
    legal_routes: Mapping[str, list[str]],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    success_count = 0

    for kind, premises in legal_routes.items():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            receipt = _bound_receipt(root, kind, **{name: True for name in premises})
            out = gate.evaluate({"closure_receipt": receipt}, repo_root=root)
            ok = (
                out.get("pass") is True
                and out.get("proof_kind") == kind
                and out.get("scope_id") == gate.SCOPE_ID
                and out.get("x_decided") is True
                and out.get("x") is False
                and out.get("u_empty") is True
                and out.get("abc_closed") is True
                and out.get("d_finality_required") is True
                and out.get("terminal") is False
                and out.get("terminal_credit_delta") == 0
            )
            checks["success_route:" + kind] = ok
            if ok:
                success_count += 1

            if premises:
                proof_path = root / "proof.json"
                proof = json.loads(proof_path.read_text(encoding="utf-8"))
                proof[premises[0]] = False
                proof_path.write_text(
                    json.dumps(proof, sort_keys=True) + "\n", encoding="utf-8"
                )
                receipt["proof_artifact"]["git_blob_sha"] = gate._git_blob_sha(proof_path)
                verifier_path = root / "verifier.json"
                verifier = json.loads(verifier_path.read_text(encoding="utf-8"))
                verifier["proof_artifact"] = receipt["proof_artifact"]
                verifier_path.write_text(
                    json.dumps(verifier, sort_keys=True) + "\n", encoding="utf-8"
                )
                receipt["verifier_receipt_artifact"]["git_blob_sha"] = (
                    gate._git_blob_sha(verifier_path)
                )
                failed = gate.evaluate({"closure_receipt": receipt}, repo_root=root)
                checks["missing_premise_rejected:" + kind] = failed.get("pass") is False

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        receipt = _bound_receipt(root, "FULL_SCOPE_DB_COVER", s_trace_subset_db=True)

        bad = deepcopy(receipt)
        bad["proof_kind"] = "FAKE_ROUTE"
        checks["declaration_cannot_override_bound_proof"] = (
            gate.evaluate({"closure_receipt": bad}, repo_root=root).get("reason")
            == "DECLARATION_PROOF_MISMATCH"
        )

        proof_path = root / "proof.json"
        original = proof_path.read_text(encoding="utf-8")
        proof_path.write_text("{}\n", encoding="utf-8")
        drift = gate.evaluate({"closure_receipt": receipt}, repo_root=root)
        checks["proof_byte_drift_rejected"] = (
            drift.get("pass") is False
            and drift.get("detail", {}).get("proof_error") == "GIT_BLOB_SHA_MISMATCH"
        )
        proof_path.write_text(original, encoding="utf-8")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        receipt = _bound_receipt(root, "FULL_SCOPE_DB_COVER", s_trace_subset_db=True)
        verifier_path = root / "verifier.json"
        verifier = json.loads(verifier_path.read_text(encoding="utf-8"))

        verifier["independent_verified"] = False
        verifier_path.write_text(
            json.dumps(verifier, sort_keys=True) + "\n", encoding="utf-8"
        )
        receipt["verifier_receipt_artifact"]["git_blob_sha"] = gate._git_blob_sha(
            verifier_path
        )
        out = gate.evaluate({"closure_receipt": receipt}, repo_root=root)
        checks["independent_verifier_required"] = (
            out.get("reason") == "INDEPENDENT_VERIFICATION_REQUIRED"
        )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        receipt = _bound_receipt(root, "FULL_SCOPE_DB_COVER", s_trace_subset_db=True)
        verifier_path = root / "verifier.json"
        verifier = json.loads(verifier_path.read_text(encoding="utf-8"))
        verifier["proof_artifact"] = {"path": "other.json", "git_blob_sha": "c" * 40}
        verifier_path.write_text(
            json.dumps(verifier, sort_keys=True) + "\n", encoding="utf-8"
        )
        receipt["verifier_receipt_artifact"]["git_blob_sha"] = gate._git_blob_sha(
            verifier_path
        )
        out = gate.evaluate({"closure_receipt": receipt}, repo_root=root)
        checks["verifier_exact_proof_binding_required"] = (
            out.get("reason") == "VERIFIER_PROOF_BINDING_MISMATCH"
        )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fake = {
            "proof_artifact": {"path": "missing.json", "git_blob_sha": "a" * 40},
            "verifier_receipt_artifact": {
                "path": "missing-verifier.json",
                "git_blob_sha": "b" * 40,
            },
        }
        out = gate.evaluate({"closure_receipt": fake}, repo_root=root)
        checks["fake_hex_binding_rejected"] = (
            out.get("reason") == "CONTENT_ADDRESSED_PROOF_AND_VERIFIER_REQUIRED"
        )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        receipt = _bound_receipt(root, "FULL_SCOPE_DB_COVER", s_trace_subset_db=True)
        proof_path = root / "proof.json"
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
        proof["scope_id"] = "wrong"
        proof_path.write_text(
            json.dumps(proof, sort_keys=True) + "\n", encoding="utf-8"
        )
        receipt["proof_artifact"]["git_blob_sha"] = gate._git_blob_sha(proof_path)
        verifier_path = root / "verifier.json"
        verifier = json.loads(verifier_path.read_text(encoding="utf-8"))
        verifier["proof_artifact"] = receipt["proof_artifact"]
        verifier_path.write_text(
            json.dumps(verifier, sort_keys=True) + "\n", encoding="utf-8"
        )
        receipt["verifier_receipt_artifact"]["git_blob_sha"] = gate._git_blob_sha(
            verifier_path
        )
        out = gate.evaluate({"closure_receipt": receipt}, repo_root=root)
        checks["scope_mismatch_rejected"] = out.get("reason") in {
            "SCOPE_ID_REQUIRED",
            "DECLARATION_PROOF_MISMATCH",
        }

    return {
        "pass": all(checks.values()) and success_count == len(legal_routes),
        "checks": checks,
        "check_count": len(checks),
        "failed_checks": sorted(k for k, value in checks.items() if not value),
        "successful_route_count": success_count,
    }


def prove(repo_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    spec_path = root / SPEC_PATH
    runtime_path = root / RUNTIME_PATH
    try:
        spec = _load_json(spec_path)
    except Exception as exc:
        return _fail("ABSTRACT_SPEC_LOAD_FAILED:" + type(exc).__name__ + ":" + str(exc))

    if spec.get("schema") != "PROJECT_BRAIN_TERMINAL_ROOT_DECISION_GATE_ABSTRACT_SPEC_V1":
        return _fail("ABSTRACT_SPEC_SCHEMA_INVALID")
    if spec.get("terminal_credit_delta") != 0:
        return _fail("ABSTRACT_SPEC_NONZERO_TERMINAL_CREDIT")

    binding = spec.get("bound_runtime")
    if not isinstance(binding, Mapping):
        return _fail("RUNTIME_BINDING_INVALID")
    if (
        binding.get("path") != str(RUNTIME_PATH)
        or binding.get("git_blob_sha") != _git_blob_sha(runtime_path)
    ):
        return _fail("RUNTIME_BLOB_BINDING_MISMATCH")

    routes = spec.get("legal_success_routes")
    if not isinstance(routes, Mapping) or set(routes) != gate.ALLOWED_PROOF_KINDS:
        return _fail("LEGAL_SUCCESS_ROUTE_SET_MISMATCH")
    normalized_routes = {
        str(kind): [str(x) for x in premises]
        for kind, premises in routes.items()
        if isinstance(premises, list)
    }
    if set(normalized_routes) != set(routes):
        return _fail("LEGAL_SUCCESS_ROUTE_PREMISES_INVALID")

    static = _static_proof(runtime_path.read_text(encoding="utf-8"), set(routes))
    if static.get("pass") is not True:
        return _fail("STATIC_GATE_PROOF_FAILED", static_proof=static)

    dynamic = _dynamic_proof(normalized_routes)
    if dynamic.get("pass") is not True:
        return _fail("DYNAMIC_GATE_REFINEMENT_FAILED", dynamic_proof=dynamic)

    body = {
        "pass": True,
        "schema": SCHEMA,
        "status": "PASS__BOUNDED_TERMINAL_ROOT_GATE_REFINEMENT_VERIFIED",
        "subject_id": str(spec.get("subject_id") or ""),
        "assurance_level": "FINITE_ABSTRACTION_TERMINAL_ROOT_GATE_REFINEMENT",
        "refinement_verified": True,
        "abstract_spec_git_blob_sha": _git_blob_sha(spec_path),
        "concrete_gate_git_blob_sha": _git_blob_sha(runtime_path),
        "legal_success_route_count": len(routes),
        "content_addressed_proof_required": True,
        "independent_verifier_required": True,
        "declaration_cannot_override_bound_proof": True,
        "terminal_nonamplification": True,
        "d_finality_preserved": True,
        "static_proof": static,
        "dynamic_proof": dynamic,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return {**body, "receipt_sha256": sha256(_canon(body)).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(prove(ROOT), indent=2, sort_keys=True))
