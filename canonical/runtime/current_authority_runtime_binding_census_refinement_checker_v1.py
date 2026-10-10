from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha1, sha256
import importlib.util
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CURRENT_AUTHORITY_RUNTIME_BINDING_CENSUS_REFINEMENT_CHECKER_V1"
SPEC_SCHEMA = "PROJECT_BRAIN_CURRENT_AUTHORITY_RUNTIME_BINDING_CENSUS_ABSTRACT_SPEC_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_CURRENT_AUTHORITY_RUNTIME_BINDING_CENSUS_REFINEMENT_RECEIPT_V1"


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


def _extract_error_kinds(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if (
                isinstance(key, ast.Constant)
                and key.value == "kind"
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                out.add(value.value)
    return out


def _extract_exception_reasons(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise):
            continue
        exc = node.exc
        if not isinstance(exc, ast.Call) or not exc.args:
            continue
        if not isinstance(exc.func, ast.Name) or exc.func.id != "ValueError":
            continue
        arg = exc.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            out.add(arg.value)
    return out


def _load_subject(path: Path):
    name = "_project_brain_runtime_binding_census_subject_" + sha256(str(path).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("SUBJECT_IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _authority(root: Path, payload: Any) -> Path:
    return _write(
        root,
        "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
        json.dumps(payload, indent=2) + "\n",
    )


def _runtime(root: Path, rel: str = "canonical/runtime/a.py") -> Path:
    return _write(root, rel, "x = 1\n")


def _different_sha(good: str) -> str:
    candidate = "f" * 40
    return candidate if candidate != good else "0" * 40


def _case_payload(case_id: str, root: Path) -> None:
    if case_id == "NO_RUNTIME_BINDINGS_PASS":
        _authority(root, {"governance": {"path": "canonical/governance/X.json", "git_blob_sha": "0" * 40}})
        return
    if case_id == "NON_RUNTIME_PATH_IGNORED":
        _authority(root, {"artifact": {"path": "canonical/tests/x.py", "git_blob_sha": "0" * 40}})
        return
    if case_id == "MISSING_RUNTIME_FILE":
        _authority(root, {"current": {"runtime": {"path": "canonical/runtime/missing.py", "git_blob_sha": "a" * 40}}})
        return

    runtime = _runtime(root)
    good = _git_blob_sha(runtime)
    bad = _different_sha(good)

    if case_id == "EXACT_CURRENT_PASS":
        payload = {"current": {"runtime": {"path": "canonical/runtime/a.py", "git_blob_sha": good}}}
    elif case_id == "SUPERSEDED_STALE_IGNORED":
        payload = {
            "current": {"runtime": {"path": "canonical/runtime/a.py", "git_blob_sha": good}},
            "historical": {
                "status": "SUPERSEDED_RUNTIME_BINDING__EVIDENCE_RETAINED",
                "runtime": {"path": "canonical/runtime/a.py", "git_blob_sha": bad},
            },
        }
    elif case_id == "STALE_CURRENT_DRIFT":
        payload = {"current": {"runtime": {"path": "canonical/runtime/a.py", "git_blob_sha": bad}}}
    elif case_id == "MISSING_BLOB_BINDING":
        payload = {"current": {"runtime": {"path": "canonical/runtime/a.py"}}}
    elif case_id == "CONFLICTING_CURRENT_BINDINGS":
        payload = {
            "one": {"runtime": {"path": "canonical/runtime/a.py", "git_blob_sha": good}},
            "two": {"runtime": {"path": "canonical/runtime/a.py", "git_blob_sha": bad}},
        }
    elif case_id == "DUPLICATE_IDENTICAL_BINDINGS_PASS":
        payload = {
            "one": {"runtime": {"path": "canonical/runtime/a.py", "git_blob_sha": good}},
            "two": {"runtime": {"path": "canonical/runtime/a.py", "git_blob_sha": good}},
        }
    elif case_id == "INHERITED_STATUS_SUPERSEDED":
        payload = {
            "historical": {
                "status": "SUPERSEDED_RUNTIME_BINDING__EVIDENCE_RETAINED",
                "nested": {"runtime": {"path": "canonical/runtime/a.py", "git_blob_sha": bad}},
            }
        }
    elif case_id == "INHERITED_SUPERSEDED_BY":
        payload = {
            "historical": {
                "superseded_by": "replacement-node",
                "nested": {"runtime": {"path": "canonical/runtime/a.py", "git_blob_sha": bad}},
            }
        }
    else:
        raise KeyError(case_id)
    _authority(root, payload)


def _projection(out: Mapping[str, Any], fields: list[str]) -> dict[str, Any]:
    return {key: out.get(key) for key in fields}


def _run_branch_cases(module: Any, spec: Mapping[str, Any]) -> tuple[bool, str | None, list[dict[str, Any]]]:
    rows = spec.get("branch_cases")
    fields = spec.get("projection_fields")
    if not isinstance(rows, list) or not isinstance(fields, list):
        return False, "BRANCH_SPEC_INVALID", []
    declared_ids = [str(row.get("id") or "") for row in rows if isinstance(row, Mapping)]
    expected_ids = {
        "NO_RUNTIME_BINDINGS_PASS",
        "EXACT_CURRENT_PASS",
        "SUPERSEDED_STALE_IGNORED",
        "STALE_CURRENT_DRIFT",
        "MISSING_BLOB_BINDING",
        "MISSING_RUNTIME_FILE",
        "CONFLICTING_CURRENT_BINDINGS",
        "DUPLICATE_IDENTICAL_BINDINGS_PASS",
        "INHERITED_STATUS_SUPERSEDED",
        "INHERITED_SUPERSEDED_BY",
        "NON_RUNTIME_PATH_IGNORED",
    }
    if set(declared_ids) != expected_ids or len(declared_ids) != len(expected_ids):
        return False, "BRANCH_CASE_SET_MISMATCH", []

    results: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            return False, "BRANCH_CASE_INVALID", results
        case_id = str(raw.get("id") or "")
        expected = raw.get("expected")
        error_kinds = raw.get("error_kinds")
        if not isinstance(expected, Mapping) or not isinstance(error_kinds, list):
            return False, "BRANCH_EXPECTATION_INVALID:" + case_id, results
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _case_payload(case_id, root)
            out = module.run(root)
            observed = _projection(out, [str(x) for x in fields])
            if observed != dict(expected):
                return False, "BRANCH_PROJECTION_MISMATCH:" + case_id, [
                    {"case_id": case_id, "expected": dict(expected), "observed": observed}
                ]
            observed_kinds = sorted(
                str(row.get("kind"))
                for row in out.get("errors", [])
                if isinstance(row, Mapping) and isinstance(row.get("kind"), str)
            )
            if observed_kinds != sorted(str(x) for x in error_kinds):
                return False, "ERROR_KIND_PROJECTION_MISMATCH:" + case_id, [
                    {"case_id": case_id, "expected": sorted(error_kinds), "observed": observed_kinds}
                ]
            results.append({"case_id": case_id, "pass": True})
    return True, None, results


def _run_exception_cases(module: Any, spec: Mapping[str, Any]) -> tuple[bool, str | None, list[dict[str, Any]]]:
    rows = spec.get("exception_cases")
    if not isinstance(rows, list):
        return False, "EXCEPTION_SPEC_INVALID", []
    expected_ids = {"AUTHORITY_POINTER_MISSING", "AUTHORITY_POINTER_NOT_OBJECT"}
    ids = {str(row.get("id") or "") for row in rows if isinstance(row, Mapping)}
    if ids != expected_ids or len(rows) != len(expected_ids):
        return False, "EXCEPTION_CASE_SET_MISMATCH", []
    results: list[dict[str, Any]] = []
    for row in rows:
        case_id = str(row["id"])
        expected = str(row.get("exception") or "")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            if case_id == "AUTHORITY_POINTER_NOT_OBJECT":
                _write(
                    root,
                    "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
                    "[]\n",
                )
            try:
                module.run(root)
            except ValueError as exc:
                if str(exc) != expected:
                    return False, "EXCEPTION_MISMATCH:" + case_id, [
                        {"case_id": case_id, "expected": expected, "observed": str(exc)}
                    ]
            else:
                return False, "EXPECTED_EXCEPTION_NOT_RAISED:" + case_id, []
            results.append({"case_id": case_id, "pass": True})
    return True, None, results


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
        source_error_kinds = _extract_error_kinds(tree)
        declared_error_kinds = {str(x) for x in spec.get("expected_error_kinds", [])}
        if source_error_kinds != declared_error_kinds:
            return _fail(
                "ERROR_KIND_CENSUS_MISMATCH",
                source_only=sorted(source_error_kinds - declared_error_kinds),
                spec_only=sorted(declared_error_kinds - source_error_kinds),
            )
        source_exceptions = _extract_exception_reasons(tree)
        declared_exceptions = {str(x) for x in spec.get("expected_exceptions", [])}
        if source_exceptions != declared_exceptions:
            return _fail(
                "EXCEPTION_CENSUS_MISMATCH",
                source_only=sorted(source_exceptions - declared_exceptions),
                spec_only=sorted(declared_exceptions - source_exceptions),
            )

        module = _load_subject(subject)
        ok, reason, branch_rows = _run_branch_cases(module, spec)
        if not ok:
            return _fail(reason or "BRANCH_CASES_FAILED", witness_detail=branch_rows)
        ok, reason, exception_rows = _run_exception_cases(module, spec)
        if not ok:
            return _fail(reason or "EXCEPTION_CASES_FAILED", witness_detail=exception_rows)

        material = {
            "subject_path": spec["subject"]["path"],
            "subject_git_blob_sha": spec["subject"]["git_blob_sha"],
            "error_kinds": sorted(declared_error_kinds),
            "exceptions": sorted(declared_exceptions),
            "branch_rows": branch_rows,
            "exception_rows": exception_rows,
            "root_assumptions": list(spec.get("root_assumptions") or []),
        }
        return {
            "schema": RECEIPT_SCHEMA,
            "pass": True,
            "refinement_verified": True,
            "assurance_level": "STATIC_ERROR_EXCEPTION_CENSUS_PLUS_WITNESS_PARTITION_EXECUTION",
            "subject": deepcopy(dict(spec["subject"])),
            "error_kind_count": len(declared_error_kinds),
            "exception_case_count": len(exception_rows),
            "branch_case_count": len(branch_rows),
            "witness_count": len(branch_rows) + len(exception_rows),
            "root_assumptions": list(spec.get("root_assumptions") or []),
            "receipt_sha256": sha256(_canon(material)).hexdigest(),
            "repository_wide_refinement": False,
            "transitive_dependency_refinement": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail("CHECKER_EXCEPTION:" + type(exc).__name__ + ":" + str(exc))
