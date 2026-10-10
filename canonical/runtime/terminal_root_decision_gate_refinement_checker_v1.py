from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha1, sha256
import importlib.util
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_ROOT_DECISION_GATE_REFINEMENT_CHECKER_V1"
SPEC_SCHEMA = "PROJECT_BRAIN_TERMINAL_ROOT_DECISION_GATE_ABSTRACT_SPEC_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_TERMINAL_ROOT_DECISION_GATE_REFINEMENT_RECEIPT_V1"


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = sha1()
    h.update(f"blob {len(data)}".encode("ascii") + bytes([0]))
    h.update(data)
    return h.hexdigest()


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "pass": False,
        "refinement_verified": False,
        "reason": reason,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **detail,
    }


def _subject_path(spec: Mapping[str, Any], repo_root: Path) -> tuple[Path | None, str | None]:
    subject = spec.get("subject")
    if not isinstance(subject, Mapping):
        return None, "SUBJECT_REQUIRED"
    raw_path = subject.get("path")
    expected = subject.get("git_blob_sha")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, "SUBJECT_PATH_REQUIRED"
    if not isinstance(expected, str) or len(expected) != 40:
        return None, "SUBJECT_BLOB_REQUIRED"
    root = repo_root.resolve()
    try:
        path = (root / raw_path).resolve(strict=True)
        path.relative_to(root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None, "SUBJECT_PATH_INVALID"
    if not path.is_file():
        return None, "SUBJECT_PATH_INVALID"
    if _git_blob_sha(path) != expected:
        return None, "SUBJECT_BLOB_DRIFT"
    return path, None


def _extract_fail_reasons(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else (
            func.attr if isinstance(func, ast.Attribute) else None
        )
        if name != "_fail":
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            out.add(first.value)
    return out


def _extract_allowed_proof_kinds(tree: ast.Module) -> set[str]:
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(t, ast.Name) and t.id == "ALLOWED_PROOF_KINDS" for t in targets):
            continue
        value = node.value
        try:
            result = ast.literal_eval(value)
        except Exception as exc:
            raise ValueError("ALLOWED_PROOF_KINDS_NOT_LITERAL") from exc
        if not isinstance(result, (set, frozenset, tuple, list)):
            raise ValueError("ALLOWED_PROOF_KINDS_INVALID")
        return {str(x) for x in result}
    raise ValueError("ALLOWED_PROOF_KINDS_MISSING")


def _load_subject(path: Path):
    name = "_project_brain_root_gate_refinement_subject_" + sha256(str(path).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("SUBJECT_IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _case_payload(
    root: Path,
    *,
    kind: str,
    proof_patch: Mapping[str, Any] | None = None,
    verifier_patch: Mapping[str, Any] | None = None,
    declaration_patch: Mapping[str, Any] | None = None,
    authority_admits: bool = True,
) -> dict[str, Any]:
    proof = {
        "proof_kind": kind,
        "scope_id": "scope://opus55/observable-trace",
        "conclusion": "success",
    }
    if proof_patch:
        proof.update(deepcopy(dict(proof_patch)))
    proof_path = root / "proof.json"
    _write_json(proof_path, proof)
    proof_binding = {"path": "proof.json", "git_blob_sha": _git_blob_sha(proof_path)}

    verifier = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "proof_artifact": deepcopy(proof_binding),
    }
    if verifier_patch:
        verifier.update(deepcopy(dict(verifier_patch)))
    verifier_path = root / "verifier.json"
    _write_json(verifier_path, verifier)
    verifier_binding = {
        "path": "verifier.json",
        "git_blob_sha": _git_blob_sha(verifier_path),
    }

    authority_path = root / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
    authority = {
        "authoritative_sources": (
            {
                "fixture": {
                    **deepcopy(proof_binding),
                    "independent_verification": deepcopy(verifier_binding),
                }
            }
            if authority_admits
            else {}
        )
    }
    _write_json(authority_path, authority)
    authority_binding = {
        "path": "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
        "git_blob_sha": _git_blob_sha(authority_path),
    }

    declaration = {
        "proof_artifact": proof_binding,
        "verifier_receipt_artifact": verifier_binding,
        "authority_pointer": authority_binding,
    }
    if declaration_patch:
        declaration.update(deepcopy(dict(declaration_patch)))
    return {"closure_receipt": declaration}


def _required_true(spec: Mapping[str, Any], kind: str) -> dict[str, bool]:
    success_cases = spec.get("success_cases")
    if not isinstance(success_cases, Mapping):
        raise ValueError("SUCCESS_CASES_REQUIRED")
    row = success_cases.get(kind)
    if not isinstance(row, Mapping):
        raise ValueError("SUCCESS_CASE_MISSING:" + kind)
    fields = row.get("required_true")
    if not isinstance(fields, list) or not all(isinstance(x, str) for x in fields):
        raise ValueError("SUCCESS_REQUIRED_TRUE_INVALID:" + kind)
    return {field: True for field in fields}


def _goal_projection(out: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    return {key: out.get(key) for key in fields}


def _run_success_cases(module: Any, spec: Mapping[str, Any]) -> tuple[bool, str | None, list[dict[str, Any]]]:
    kinds = spec.get("allowed_proof_kinds")
    projection = spec.get("success_projection")
    success_cases = spec.get("success_cases")
    if not isinstance(kinds, list) or not isinstance(projection, Mapping) or not isinstance(success_cases, Mapping):
        return False, "SUCCESS_SPEC_INVALID", []
    rows: list[dict[str, Any]] = []
    for kind in kinds:
        kind = str(kind)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = _case_payload(
                root,
                kind=kind,
                proof_patch=_required_true(spec, kind),
            )
            out = module.evaluate(payload, repo_root=root)
            expected = dict(projection)
            expected["proof_kind"] = kind
            expected["scope_id"] = str(spec.get("input_contract", {}).get("scope_id") or "")
            expected["proof_rule"] = success_cases[kind]["proof_rule"]
            observed = _goal_projection(out, expected)
            if observed != expected:
                return False, "SUCCESS_PROJECTION_MISMATCH:" + kind, [
                    {"kind": kind, "expected": expected, "observed": observed}
                ]
            rows.append({"kind": kind, "pass": True})
    return True, None, rows


def _witnesses(spec: Mapping[str, Any]) -> dict[str, Any]:
    full = _required_true(spec, "FULL_SCOPE_DB_COVER")
    target = _required_true(spec, "TARGET_ESCAPE_NONOCCUPANCY")
    generator = _required_true(spec, "GENERATOR_CLOSURE_SCOPE_COMPLETE")
    selected = _required_true(spec, "SELECTED_COVER_COMPLEMENT_UNSAT")
    generator_bad = dict(generator)
    generator_bad[next(iter(generator_bad))] = False
    selected_bad = dict(selected)
    selected_bad[next(iter(selected_bad))] = False

    def make(reason: str):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            if reason == "PAYLOAD_MAPPING_REQUIRED":
                return ["not-a-mapping"], root
            if reason == "CLOSURE_RECEIPT_REQUIRED":
                return {}, root
            if reason == "CONTENT_ADDRESSED_PROOF_AND_VERIFIER_REQUIRED":
                return {
                    "closure_receipt": {
                        "proof_artifact": {"path": "missing.json", "git_blob_sha": "a" * 40},
                        "verifier_receipt_artifact": {"path": "missing2.json", "git_blob_sha": "b" * 40},
                    }
                }, root
            if reason == "CURRENT_AUTHORITY_POINTER_INVALID":
                payload = _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=full)
                payload["closure_receipt"]["authority_pointer"] = {
                    "path": "wrong.json",
                    "git_blob_sha": "c" * 40,
                }
                return payload, root
            if reason == "CURRENT_AUTHORITY_PROOF_VERIFIER_ADMISSION_REQUIRED":
                return _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=full, authority_admits=False), root
            if reason == "PROOF_KIND_INVALID":
                return _case_payload(root, kind="UNSUPPORTED_KIND"), root
            if reason == "SUCCESS_CONCLUSION_REQUIRED":
                return _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch={**full, "conclusion": "failure"}), root
            if reason == "SCOPE_ID_REQUIRED":
                return _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch={**full, "scope_id": "wrong"}), root
            if reason == "INDEPENDENT_VERIFICATION_REQUIRED":
                return _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=full, verifier_patch={"independent_verified": False}), root
            if reason == "EXACT_BYTE_BINDING_REQUIRED":
                return _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=full, verifier_patch={"exact_byte_bound": False}), root
            if reason == "VERIFIER_SUCCESS_CONCLUSION_REQUIRED":
                return _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=full, verifier_patch={"conclusion": "failure"}), root
            if reason == "VERIFIER_PROOF_BINDING_MISMATCH":
                return _case_payload(
                    root,
                    kind="FULL_SCOPE_DB_COVER",
                    proof_patch=full,
                    verifier_patch={"proof_artifact": {"path": "other.json", "git_blob_sha": "d" * 40}},
                ), root
            if reason == "DECLARATION_PROOF_MISMATCH":
                return _case_payload(
                    root,
                    kind="FULL_SCOPE_DB_COVER",
                    proof_patch=full,
                    declaration_patch={"proof_kind": "TARGET_ESCAPE_NONOCCUPANCY"},
                ), root
            if reason == "FULL_SCOPE_DB_COVER_UNPROVED":
                return _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch={"s_trace_subset_db": False}), root
            if reason == "TARGET_ESCAPE_NONOCCUPANCY_UNPROVED":
                return _case_payload(root, kind="TARGET_ESCAPE_NONOCCUPANCY", proof_patch={"u_intersection_escape_empty": False}), root
            if reason == "GENERATOR_CLOSURE_PREMISES_UNPROVED":
                return _case_payload(root, kind="GENERATOR_CLOSURE_SCOPE_COMPLETE", proof_patch=generator_bad), root
            if reason == "SELECTED_COVER_COMPLEMENT_PREMISES_UNPROVED":
                return _case_payload(root, kind="SELECTED_COVER_COMPLEMENT_UNSAT", proof_patch=selected_bad), root
            raise KeyError(reason)

    return {reason: make for reason in spec.get("fail_reasons", [])}


def _run_fail_cases(module: Any, spec: Mapping[str, Any]) -> tuple[bool, str | None, list[dict[str, Any]]]:
    reasons = spec.get("fail_reasons")
    projection = spec.get("fail_projection")
    if not isinstance(reasons, list) or not isinstance(projection, Mapping):
        return False, "FAIL_SPEC_INVALID", []
    factories = _witnesses(spec)
    rows: list[dict[str, Any]] = []
    if set(factories) != {str(x) for x in reasons}:
        return False, "FAIL_WITNESS_SET_MISMATCH", []
    for reason in reasons:
        reason = str(reason)
        factory = factories[reason]
        # Each factory must keep its TemporaryDirectory alive through evaluation.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Rebuild the requested case directly in this live directory.
            if reason == "PAYLOAD_MAPPING_REQUIRED":
                payload = ["not-a-mapping"]
            elif reason == "CLOSURE_RECEIPT_REQUIRED":
                payload = {}
            elif reason == "CONTENT_ADDRESSED_PROOF_AND_VERIFIER_REQUIRED":
                payload = {"closure_receipt": {
                    "proof_artifact": {"path": "missing.json", "git_blob_sha": "a" * 40},
                    "verifier_receipt_artifact": {"path": "missing2.json", "git_blob_sha": "b" * 40},
                }}
            elif reason == "CURRENT_AUTHORITY_POINTER_INVALID":
                payload = _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=_required_true(spec, "FULL_SCOPE_DB_COVER"))
                payload["closure_receipt"]["authority_pointer"] = {"path": "wrong.json", "git_blob_sha": "c" * 40}
            elif reason == "CURRENT_AUTHORITY_PROOF_VERIFIER_ADMISSION_REQUIRED":
                payload = _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=_required_true(spec, "FULL_SCOPE_DB_COVER"), authority_admits=False)
            elif reason == "PROOF_KIND_INVALID":
                payload = _case_payload(root, kind="UNSUPPORTED_KIND")
            elif reason == "SUCCESS_CONCLUSION_REQUIRED":
                payload = _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch={**_required_true(spec, "FULL_SCOPE_DB_COVER"), "conclusion": "failure"})
            elif reason == "SCOPE_ID_REQUIRED":
                payload = _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch={**_required_true(spec, "FULL_SCOPE_DB_COVER"), "scope_id": "wrong"})
            elif reason == "INDEPENDENT_VERIFICATION_REQUIRED":
                payload = _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=_required_true(spec, "FULL_SCOPE_DB_COVER"), verifier_patch={"independent_verified": False})
            elif reason == "EXACT_BYTE_BINDING_REQUIRED":
                payload = _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=_required_true(spec, "FULL_SCOPE_DB_COVER"), verifier_patch={"exact_byte_bound": False})
            elif reason == "VERIFIER_SUCCESS_CONCLUSION_REQUIRED":
                payload = _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=_required_true(spec, "FULL_SCOPE_DB_COVER"), verifier_patch={"conclusion": "failure"})
            elif reason == "VERIFIER_PROOF_BINDING_MISMATCH":
                payload = _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=_required_true(spec, "FULL_SCOPE_DB_COVER"), verifier_patch={"proof_artifact": {"path": "other.json", "git_blob_sha": "d" * 40}})
            elif reason == "DECLARATION_PROOF_MISMATCH":
                payload = _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch=_required_true(spec, "FULL_SCOPE_DB_COVER"), declaration_patch={"proof_kind": "TARGET_ESCAPE_NONOCCUPANCY"})
            elif reason == "FULL_SCOPE_DB_COVER_UNPROVED":
                payload = _case_payload(root, kind="FULL_SCOPE_DB_COVER", proof_patch={"s_trace_subset_db": False})
            elif reason == "TARGET_ESCAPE_NONOCCUPANCY_UNPROVED":
                payload = _case_payload(root, kind="TARGET_ESCAPE_NONOCCUPANCY", proof_patch={"u_intersection_escape_empty": False})
            elif reason == "GENERATOR_CLOSURE_PREMISES_UNPROVED":
                p = _required_true(spec, "GENERATOR_CLOSURE_SCOPE_COMPLETE"); p[next(iter(p))] = False
                payload = _case_payload(root, kind="GENERATOR_CLOSURE_SCOPE_COMPLETE", proof_patch=p)
            elif reason == "SELECTED_COVER_COMPLEMENT_PREMISES_UNPROVED":
                p = _required_true(spec, "SELECTED_COVER_COMPLEMENT_UNSAT"); p[next(iter(p))] = False
                payload = _case_payload(root, kind="SELECTED_COVER_COMPLEMENT_UNSAT", proof_patch=p)
            else:
                return False, "FAIL_WITNESS_MISSING:" + reason, rows
            out = module.evaluate(payload, repo_root=root)
            expected = dict(projection)
            expected["reason"] = reason
            observed = _goal_projection(out, expected)
            if observed != expected:
                return False, "FAIL_PROJECTION_MISMATCH:" + reason, [
                    {"reason": reason, "expected": expected, "observed": observed}
                ]
            rows.append({"reason": reason, "pass": True})
    return True, None, rows


def verify(spec: Mapping[str, Any], *, repo_root: str | Path) -> dict[str, Any]:
    try:
        if not isinstance(spec, Mapping) or spec.get("schema") != SPEC_SCHEMA:
            return _fail("SPEC_SCHEMA_INVALID")
        root = Path(repo_root).resolve()
        subject, error = _subject_path(spec, root)
        if error is not None or subject is None:
            return _fail(error or "SUBJECT_INVALID")

        source = subject.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(subject))
        source_fail_reasons = _extract_fail_reasons(tree)
        declared_fail_reasons = {str(x) for x in spec.get("fail_reasons", [])}
        if source_fail_reasons != declared_fail_reasons:
            return _fail(
                "FAIL_REASON_CENSUS_MISMATCH",
                source_only=sorted(source_fail_reasons - declared_fail_reasons),
                spec_only=sorted(declared_fail_reasons - source_fail_reasons),
            )

        source_kinds = _extract_allowed_proof_kinds(tree)
        declared_kinds = {str(x) for x in spec.get("allowed_proof_kinds", [])}
        if source_kinds != declared_kinds:
            return _fail(
                "PROOF_KIND_CENSUS_MISMATCH",
                source_only=sorted(source_kinds - declared_kinds),
                spec_only=sorted(declared_kinds - source_kinds),
            )

        module = _load_subject(subject)
        ok, reason, success_rows = _run_success_cases(module, spec)
        if not ok:
            return _fail(reason or "SUCCESS_CASES_FAILED", witness_detail=success_rows)
        ok, reason, fail_rows = _run_fail_cases(module, spec)
        if not ok:
            return _fail(reason or "FAIL_CASES_FAILED", witness_detail=fail_rows)

        material = {
            "subject_path": spec["subject"]["path"],
            "subject_git_blob_sha": spec["subject"]["git_blob_sha"],
            "fail_reasons": sorted(declared_fail_reasons),
            "proof_kinds": sorted(declared_kinds),
            "success_rows": success_rows,
            "fail_rows": fail_rows,
            "root_assumptions": list(spec.get("root_assumptions") or []),
        }
        return {
            "schema": RECEIPT_SCHEMA,
            "pass": True,
            "refinement_verified": True,
            "assurance_level": "STATIC_AST_BRANCH_CENSUS_PLUS_WITNESS_COMPLETE_EXECUTION",
            "subject": deepcopy(dict(spec["subject"])),
            "fail_reason_count": len(fail_rows),
            "success_case_count": len(success_rows),
            "witness_count": len(fail_rows) + len(success_rows),
            "root_assumptions": list(spec.get("root_assumptions") or []),
            "receipt_sha256": sha256(_canon(material)).hexdigest(),
            "repository_wide_refinement": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail("CHECKER_EXCEPTION:" + type(exc).__name__ + ":" + str(exc))
