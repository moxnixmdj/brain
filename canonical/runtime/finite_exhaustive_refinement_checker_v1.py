"""Fail-closed checker for exhaustive finite-domain executable refinement.

This checker never executes the concrete implementation.  An isolated execution
carrier produces a content-addressed trace receipt.  The checker proves that the
trace covers exactly the declared finite domain and that every goal-relevant
output equals the abstract specification for the exact concrete source blob.

The theorem is deliberately bounded to the declared finite domain.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

PROOF_SCHEMA = "PROJECT_BRAIN_FINITE_EXHAUSTIVE_REFINEMENT_PROOF_V1"
ABSTRACT_SCHEMA = "PROJECT_BRAIN_FINITE_REFINEMENT_ABSTRACT_SPEC_V1"
TRACE_SCHEMA = "PROJECT_BRAIN_FINITE_REFINEMENT_TRACE_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_FINITE_EXHAUSTIVE_REFINEMENT_RECEIPT_V1"
PROOF_CLASS = "EXHAUSTIVE_FINITE_DOMAIN_TRACE_REFINEMENT"

_REQUIRED_FIELDS = frozenset({
    "schema",
    "proof_class",
    "subject_id",
    "abstract_spec",
    "concrete_implementation",
    "execution_trace",
    "terminal_credit_delta",
})


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _key(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "pass": False,
        "schema": RECEIPT_SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "refinement_verified": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _repo_file(root: Path, rel: Any) -> Path | None:
    if not isinstance(rel, str) or not rel.strip():
        return None
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        return None
    root = root.resolve()
    full = (root / p).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        return None
    if not full.is_file():
        return None
    return full


def _bound_file(
    row: Any,
    *,
    root: Path,
    label: str,
    extra_fields: set[str] | None = None,
) -> tuple[dict[str, str] | None, str | None]:
    if not isinstance(row, Mapping):
        return None, f"{label}_NOT_OBJECT"
    fields = {"path", "git_blob_sha"} | (extra_fields or set())
    if set(row) != fields:
        return None, f"{label}_FIELD_SET_INVALID"
    p = _repo_file(root, row.get("path"))
    if p is None:
        return None, f"{label}_PATH_INVALID"
    actual = git_blob_sha(p)
    if row.get("git_blob_sha") != actual:
        return None, f"{label}_BLOB_DRIFT"
    out = {"path": str(row["path"]), "git_blob_sha": actual}
    for field in sorted(extra_fields or set()):
        value = str(row.get(field) or "").strip()
        if not value:
            return None, f"{label}_{field.upper()}_REQUIRED"
        out[field] = value
    return out, None


def _load_json(path: Path, *, label: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, f"{label}_JSON_INVALID"
    if not isinstance(value, dict):
        return None, f"{label}_NOT_OBJECT"
    return value, None


def _rows_by_input(rows: Any, *, label: str) -> tuple[dict[str, dict[str, Any]] | None, str | None]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return None, f"{label}_ROWS_INVALID"
    out: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != {"input", "output"}:
            return None, f"{label}_ROW_INVALID:{index}"
        try:
            key = _key(row["input"])
            _canon(row["output"])
        except (TypeError, ValueError):
            return None, f"{label}_ROW_NONCANONICAL:{index}"
        if key in out:
            return None, f"{label}_DUPLICATE_INPUT:{index}"
        out[key] = {"input": row["input"], "output": row["output"]}
    return out, None


def verify_finite_refinement(
    raw: Mapping[str, Any], *, repo_root: str | Path | None = None
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return _fail("PROOF_NOT_OBJECT")
    if raw.get("schema") != PROOF_SCHEMA:
        return _fail("PROOF_SCHEMA_INVALID")
    if set(raw) != _REQUIRED_FIELDS:
        return _fail(
            "PROOF_FIELD_SET_INVALID",
            missing_fields=sorted(_REQUIRED_FIELDS - set(raw)),
            extra_fields=sorted(set(raw) - _REQUIRED_FIELDS),
        )
    if raw.get("proof_class") != PROOF_CLASS:
        return _fail("PROOF_CLASS_UNSUPPORTED")
    if raw.get("terminal_credit_delta") != 0:
        return _fail("NONZERO_TERMINAL_CREDIT_FORBIDDEN")

    subject_id = str(raw.get("subject_id") or "").strip()
    if not subject_id:
        return _fail("SUBJECT_ID_REQUIRED")

    root = (
        Path(repo_root)
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )

    abstract_binding, reason = _bound_file(
        raw.get("abstract_spec"), root=root, label="ABSTRACT_SPEC"
    )
    if abstract_binding is None:
        return _fail(str(reason))
    concrete_binding, reason = _bound_file(
        raw.get("concrete_implementation"),
        root=root,
        label="CONCRETE_IMPLEMENTATION",
        extra_fields={"callable"},
    )
    if concrete_binding is None:
        return _fail(str(reason))
    trace_binding, reason = _bound_file(
        raw.get("execution_trace"), root=root, label="EXECUTION_TRACE"
    )
    if trace_binding is None:
        return _fail(str(reason))

    abstract_path = root / abstract_binding["path"]
    trace_path = root / trace_binding["path"]
    abstract, reason = _load_json(abstract_path, label="ABSTRACT_SPEC")
    if abstract is None:
        return _fail(str(reason))
    trace, reason = _load_json(trace_path, label="EXECUTION_TRACE")
    if trace is None:
        return _fail(str(reason))

    if abstract.get("schema") != ABSTRACT_SCHEMA:
        return _fail("ABSTRACT_SPEC_SCHEMA_INVALID")
    if abstract.get("closed_domain") is not True:
        return _fail("ABSTRACT_DOMAIN_NOT_CLOSED")
    domain = abstract.get("domain")
    if not isinstance(domain, Sequence) or isinstance(domain, (str, bytes)) or not domain:
        return _fail("ABSTRACT_FINITE_DOMAIN_REQUIRED")

    domain_keys: dict[str, Any] = {}
    for index, item in enumerate(domain):
        try:
            key = _key(item)
        except (TypeError, ValueError):
            return _fail("ABSTRACT_DOMAIN_NONCANONICAL", index=index)
        if key in domain_keys:
            return _fail("ABSTRACT_DOMAIN_DUPLICATE", index=index)
        domain_keys[key] = item

    expected, reason = _rows_by_input(abstract.get("expected"), label="ABSTRACT")
    if expected is None:
        return _fail(str(reason))
    if set(expected) != set(domain_keys):
        return _fail(
            "ABSTRACT_EXPECTED_DOMAIN_MISMATCH",
            missing=sorted(set(domain_keys) - set(expected)),
            extra=sorted(set(expected) - set(domain_keys)),
        )

    if trace.get("schema") != TRACE_SCHEMA:
        return _fail("EXECUTION_TRACE_SCHEMA_INVALID")
    if trace.get("subject_id") != subject_id:
        return _fail("EXECUTION_TRACE_SUBJECT_MISMATCH")
    if trace.get("concrete_git_blob_sha") != concrete_binding["git_blob_sha"]:
        return _fail("EXECUTION_TRACE_CONCRETE_BLOB_MISMATCH")
    if trace.get("callable") != concrete_binding["callable"]:
        return _fail("EXECUTION_TRACE_CALLABLE_MISMATCH")
    if trace.get("independent_execution") is not True:
        return _fail("INDEPENDENT_EXECUTION_REQUIRED")
    if trace.get("execution_complete") is not True:
        return _fail("EXECUTION_TRACE_INCOMPLETE")
    if trace.get("execution_error_count") != 0:
        return _fail("EXECUTION_TRACE_ERRORS_PRESENT")
    if trace.get("side_effect_class") != "PURE_ISOLATED":
        return _fail("PURE_ISOLATED_EXECUTION_REQUIRED")

    observed, reason = _rows_by_input(trace.get("rows"), label="TRACE")
    if observed is None:
        return _fail(str(reason))
    if set(observed) != set(domain_keys):
        return _fail(
            "TRACE_DOMAIN_MISMATCH",
            missing=sorted(set(domain_keys) - set(observed)),
            extra=sorted(set(observed) - set(domain_keys)),
        )

    mismatches: list[str] = []
    for key in sorted(domain_keys):
        if _canon(observed[key]["output"]) != _canon(expected[key]["output"]):
            mismatches.append(key)
    if mismatches:
        return _fail("SEMANTIC_REFINEMENT_MISMATCH", mismatch_input_hashes=mismatches)

    proof_sha = sha256(_canon(dict(raw))).hexdigest()
    body = {
        "pass": True,
        "schema": RECEIPT_SCHEMA,
        "status": "PASS__EXHAUSTIVE_FINITE_DOMAIN_TRACE_REFINEMENT_VERIFIED",
        "assurance_level": "EXACT_DECLARED_FINITE_INPUT_DOMAIN",
        "proof_class": PROOF_CLASS,
        "subject_id": subject_id,
        "proof_sha256": proof_sha,
        "abstract_spec": abstract_binding,
        "concrete_implementation": concrete_binding,
        "execution_trace": trace_binding,
        "finite_domain_case_count": len(domain_keys),
        "refinement_verified": True,
        "safety_refinement_verified": True,
        "liveness_refinement_verified": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "nonclaims": [
            "NO_CLAIM_OUTSIDE_DECLARED_FINITE_DOMAIN",
            "NO_CLAIM_LIVENESS_OR_TERMINATION_FOR_UNEXECUTED_INPUTS",
            "NO_CLAIM_OPEN_WORLD_PROGRAM_EQUIVALENCE",
        ],
    }
    return {**body, "receipt_sha256": sha256(_canon(body)).hexdigest()}
