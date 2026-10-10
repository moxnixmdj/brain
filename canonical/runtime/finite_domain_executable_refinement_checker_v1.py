"""Exhaustive semantic refinement checker for explicitly finite domains."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import ast
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINITE_DOMAIN_EXECUTABLE_REFINEMENT_PROOF_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_FINITE_DOMAIN_EXECUTABLE_REFINEMENT_RECEIPT_V1"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "refinement_verified": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _bound(root: Path, row: Any) -> Path | None:
    if not isinstance(row, Mapping) or set(row) != {"path", "git_blob_sha"}:
        return None
    rel = Path(str(row.get("path") or ""))
    if rel.is_absolute() or ".." in rel.parts:
        return None
    path = (root / rel).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    if not path.is_file() or _blob(path) != row.get("git_blob_sha"):
        return None
    return path


def _static_domain_guard(
    path: Path,
    callable_name: str,
    expected_inputs: list[Any],
) -> str | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return "IMPLEMENTATION_AST_INVALID"

    domain_values = None
    target = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "DOMAIN" for t in node.targets):
                try:
                    value = ast.literal_eval(node.value)
                except Exception:
                    return "DOMAIN_LITERAL_REQUIRED"
                if not isinstance(value, tuple):
                    return "DOMAIN_TUPLE_REQUIRED"
                domain_values = list(value)
        if isinstance(node, ast.FunctionDef) and node.name == callable_name:
            target = node

    if domain_values is None:
        return "DOMAIN_LITERAL_REQUIRED"
    if _canon(domain_values) != _canon(expected_inputs):
        return "DOMAIN_SPEC_MISMATCH"
    if target is None or len(target.args.args) != 1 or not target.body:
        return "CALLABLE_AST_SHAPE_INVALID"

    arg = target.args.args[0].arg
    first = target.body[0]
    if not isinstance(first, ast.If):
        return "DOMAIN_GUARD_REQUIRED"
    test = first.test
    if not (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == arg
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.NotIn)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Name)
        and test.comparators[0].id == "DOMAIN"
    ):
        return "DOMAIN_GUARD_SHAPE_INVALID"
    if not first.body or not isinstance(first.body[0], ast.Raise):
        return "DOMAIN_GUARD_MUST_RAISE"
    return None


def verify(
    raw: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or raw.get("schema") != SCHEMA:
        return _fail("PROOF_SCHEMA_INVALID")

    required = {
        "schema",
        "subject_id",
        "abstract_spec",
        "concrete_implementation",
        "callable",
        "terminal_credit_delta",
    }
    if set(raw) != required:
        return _fail("PROOF_FIELD_SET_INVALID")
    if raw.get("terminal_credit_delta") != 0:
        return _fail("NONZERO_TERMINAL_CREDIT_FORBIDDEN")

    subject = str(raw.get("subject_id") or "").strip()
    callable_name = str(raw.get("callable") or "").strip()
    if not subject or not callable_name:
        return _fail("SUBJECT_OR_CALLABLE_REQUIRED")

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    spec_path = _bound(root, raw.get("abstract_spec"))
    impl_path = _bound(root, raw.get("concrete_implementation"))
    if spec_path is None:
        return _fail("ABSTRACT_SPEC_BINDING_INVALID")
    if impl_path is None:
        return _fail("CONCRETE_IMPLEMENTATION_BINDING_INVALID")

    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except Exception:
        return _fail("ABSTRACT_SPEC_JSON_INVALID")
    if not isinstance(spec, Mapping) or spec.get("subject_id") != subject:
        return _fail("ABSTRACT_SUBJECT_MISMATCH")

    cases = spec.get("finite_domain_cases")
    if not isinstance(cases, list) or not cases:
        return _fail("FINITE_DOMAIN_CASES_REQUIRED")

    seen: set[str] = set()
    expected: list[Mapping[str, Any]] = []
    expected_inputs: list[Any] = []
    for index, row in enumerate(cases):
        if not isinstance(row, Mapping) or set(row) != {"input", "expected_output"}:
            return _fail("FINITE_CASE_INVALID", index=index)
        key = sha256(_canon(row["input"])).hexdigest()
        if key in seen:
            return _fail("FINITE_DOMAIN_DUPLICATE", index=index)
        seen.add(key)
        expected.append(row)
        expected_inputs.append(row["input"])

    guard_reason = _static_domain_guard(impl_path, callable_name, expected_inputs)
    if guard_reason is not None:
        return _fail(guard_reason)

    module_name = "_brain_refinement_" + sha256(str(impl_path).encode()).hexdigest()
    module_spec = importlib.util.spec_from_file_location(module_name, impl_path)
    if module_spec is None or module_spec.loader is None:
        return _fail("IMPLEMENTATION_LOAD_FAILED")
    module = importlib.util.module_from_spec(module_spec)
    try:
        module_spec.loader.exec_module(module)
    except Exception as exc:
        return _fail("IMPLEMENTATION_IMPORT_FAILED", error=type(exc).__name__)

    fn = getattr(module, callable_name, None)
    if not callable(fn):
        return _fail("CALLABLE_NOT_FOUND")

    results = []
    for index, row in enumerate(expected):
        try:
            actual = fn(deepcopy(row["input"]))
        except Exception as exc:
            return _fail(
                "CONCRETE_EXECUTION_FAILED",
                index=index,
                error=type(exc).__name__,
            )
        if _canon(actual) != _canon(row["expected_output"]):
            return _fail(
                "SEMANTIC_MISMATCH",
                index=index,
                actual=actual,
                expected=row["expected_output"],
            )
        results.append(
            {
                "index": index,
                "input_sha256": sha256(_canon(row["input"])).hexdigest(),
                "output_sha256": sha256(_canon(actual)).hexdigest(),
            }
        )

    body = {
        "schema": RECEIPT_SCHEMA,
        "pass": True,
        "status": "PASS__EXHAUSTIVE_FINITE_DOMAIN_REFINEMENT",
        "subject_id": subject,
        "refinement_verified": True,
        "assurance_level": "EXHAUSTIVE_FINITE_DOMAIN",
        "abstract_spec": {
            "path": raw["abstract_spec"]["path"],
            "git_blob_sha": raw["abstract_spec"]["git_blob_sha"],
        },
        "concrete_implementation": {
            "path": raw["concrete_implementation"]["path"],
            "git_blob_sha": raw["concrete_implementation"]["git_blob_sha"],
        },
        "domain_case_count": len(expected),
        "case_results": results,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return {
        **body,
        "receipt_sha256": sha256(_canon(body)).hexdigest(),
    }
