"""Fail-closed executable-refinement certificate verifier V1.

This module verifies only bounded, content-addressed refinement claims. It does
not infer refinement from tests, artifact identity alone, or attestation.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_EXECUTABLE_REFINEMENT_CERTIFICATE_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_EXECUTABLE_REFINEMENT_RECEIPT_V1"
ALLOWED_TRANSITION_KINDS = frozenset({"PASS", "FAIL_CLOSED", "TYPE_ERROR", "STUTTER"})
ALLOWED_COVERAGE_MODES = frozenset({"DECLARED_FINITE_PARTITION", "EXHAUSTIVE_ENUMERATION"})
ALLOWED_INPUT_BINDING_MODES = frozenset({"CANONICAL_JSON", "DIRECT_TYPED_MAPPING", "EXACT_BYTES"})
ALLOWED_STATE_MAPPING_MODES = frozenset({"IDENTITY", "DECLARED_RELATION", "STATELESS"})
ALLOWED_OBSERVATION_MODES = frozenset({"EXACT_GOAL_PROJECTION", "SAFE_REFINEMENT"})
ALLOWED_NONDETERMINISM_MODES = frozenset({"DETERMINISTIC", "ABSTRACT_SUPERSET", "DECLARED_RELATION"})

_REQUIRED_FIELDS = frozenset(
    {
        "schema",
        "subject_id",
        "abstract_spec",
        "concrete_implementation",
        "state_mapping",
        "input_binding",
        "transition_refinement",
        "observation_refinement",
        "nondeterminism_contract",
        "safety_refinement",
        "liveness_refinement",
        "proof_dependencies",
        "terminal_credit_delta",
    }
)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "pass": False,
        "schema": RECEIPT_SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _repo_path(repo_root: Path, raw: Any) -> Path | None:
    value = str(raw or "").strip()
    p = Path(value)
    if not value or p.is_absolute() or ".." in p.parts:
        return None
    full = (repo_root / p).resolve()
    root = repo_root.resolve()
    try:
        full.relative_to(root)
    except ValueError:
        return None
    if not full.is_file():
        return None
    return full


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def verify_certificate(
    raw: Mapping[str, Any], *, repo_root: Path | None = None
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return _fail("CERTIFICATE_NOT_OBJECT")
    if raw.get("schema") != SCHEMA:
        return _fail("CERTIFICATE_SCHEMA_INVALID")
    if set(raw) != _REQUIRED_FIELDS:
        return _fail(
            "CERTIFICATE_FIELD_SET_INVALID",
            missing_fields=sorted(_REQUIRED_FIELDS - set(raw)),
            extra_fields=sorted(set(raw) - _REQUIRED_FIELDS),
        )
    subject_id = str(raw.get("subject_id") or "").strip()
    if not subject_id:
        return _fail("SUBJECT_ID_REQUIRED")
    if raw.get("terminal_credit_delta") != 0:
        return _fail("NONZERO_TERMINAL_CREDIT_FORBIDDEN")

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]

    abstract = _mapping(raw.get("abstract_spec"))
    if abstract is None or set(abstract) != {"path", "git_blob_sha", "semantic_version"}:
        return _fail("ABSTRACT_SPEC_BINDING_INVALID")
    abstract_path = _repo_path(root, abstract.get("path"))
    if abstract_path is None:
        return _fail("ABSTRACT_SPEC_PATH_INVALID")
    if abstract.get("git_blob_sha") != git_blob_sha(abstract_path):
        return _fail("ABSTRACT_SPEC_BLOB_DRIFT")
    if not str(abstract.get("semantic_version") or "").strip():
        return _fail("ABSTRACT_SPEC_SEMANTIC_VERSION_REQUIRED")

    concrete = raw.get("concrete_implementation")
    if not isinstance(concrete, Sequence) or isinstance(concrete, (str, bytes)) or not concrete:
        return _fail("CONCRETE_IMPLEMENTATION_BINDING_INVALID")
    concrete_receipts: list[dict[str, str]] = []
    for index, row in enumerate(concrete):
        if not isinstance(row, Mapping) or set(row) != {"path", "git_blob_sha"}:
            return _fail("CONCRETE_IMPLEMENTATION_ROW_INVALID", index=index)
        path = _repo_path(root, row.get("path"))
        if path is None:
            return _fail("CONCRETE_IMPLEMENTATION_PATH_INVALID", index=index)
        actual = git_blob_sha(path)
        if row.get("git_blob_sha") != actual:
            return _fail("CONCRETE_IMPLEMENTATION_BLOB_DRIFT", index=index)
        concrete_receipts.append({"path": str(row.get("path")), "git_blob_sha": actual})

    state_mapping = _mapping(raw.get("state_mapping"))
    if state_mapping is None or state_mapping.get("proved") is not True:
        return _fail("STATE_MAPPING_UNPROVED")
    if state_mapping.get("mode") not in ALLOWED_STATE_MAPPING_MODES:
        return _fail("STATE_MAPPING_MODE_UNSUPPORTED")

    input_binding = _mapping(raw.get("input_binding"))
    if input_binding is None or input_binding.get("proved") is not True:
        return _fail("INPUT_BINDING_UNPROVED")
    if input_binding.get("mode") not in ALLOWED_INPUT_BINDING_MODES:
        return _fail("INPUT_BINDING_MODE_UNSUPPORTED")

    transition = _mapping(raw.get("transition_refinement"))
    if transition is None:
        return _fail("TRANSITION_REFINEMENT_INVALID")
    if transition.get("coverage_mode") not in ALLOWED_COVERAGE_MODES:
        return _fail("TRANSITION_COVERAGE_MODE_UNSUPPORTED")
    if transition.get("unsupported_behavior") != "FAIL_CLOSED":
        return _fail("UNSUPPORTED_BEHAVIOR_MUST_FAIL_CLOSED")
    classes = transition.get("classes")
    if not isinstance(classes, Sequence) or isinstance(classes, (str, bytes)) or not classes:
        return _fail("TRANSITION_CLASSES_REQUIRED")
    seen: set[str] = set()
    for index, row in enumerate(classes):
        if not isinstance(row, Mapping) or set(row) != {"case_id", "kind"}:
            return _fail("TRANSITION_CLASS_INVALID", index=index)
        case_id = str(row.get("case_id") or "").strip()
        if not case_id or case_id in seen:
            return _fail("TRANSITION_CLASS_ID_INVALID", index=index)
        seen.add(case_id)
        if row.get("kind") not in ALLOWED_TRANSITION_KINDS:
            return _fail("TRANSITION_CLASS_KIND_UNSUPPORTED", index=index)

    observation = _mapping(raw.get("observation_refinement"))
    if observation is None or observation.get("proved") is not True:
        return _fail("OBSERVATION_REFINEMENT_UNPROVED")
    if observation.get("mode") not in ALLOWED_OBSERVATION_MODES:
        return _fail("OBSERVATION_REFINEMENT_MODE_UNSUPPORTED")

    nondeterminism = _mapping(raw.get("nondeterminism_contract"))
    if nondeterminism is None or nondeterminism.get("proved") is not True:
        return _fail("NONDETERMINISM_CONTRACT_UNPROVED")
    if nondeterminism.get("mode") not in ALLOWED_NONDETERMINISM_MODES:
        return _fail("NONDETERMINISM_MODE_UNSUPPORTED")

    safety = _mapping(raw.get("safety_refinement"))
    if safety is None or safety.get("proved") is not True:
        return _fail("SAFETY_REFINEMENT_UNPROVED")

    liveness = _mapping(raw.get("liveness_refinement"))
    if liveness is None or type(liveness.get("required")) is not bool or type(liveness.get("proved")) is not bool:
        return _fail("LIVENESS_REFINEMENT_INVALID")
    if liveness.get("required") is True and liveness.get("proved") is not True:
        return _fail("LIVENESS_REFINEMENT_REQUIRED_BUT_UNPROVED")

    dependencies = raw.get("proof_dependencies")
    if not isinstance(dependencies, Sequence) or isinstance(dependencies, (str, bytes)):
        return _fail("PROOF_DEPENDENCIES_INVALID")
    checked_deps: list[dict[str, str]] = []
    for index, row in enumerate(dependencies):
        if not isinstance(row, Mapping) or set(row) != {"path", "git_blob_sha"}:
            return _fail("PROOF_DEPENDENCY_ROW_INVALID", index=index)
        path = _repo_path(root, row.get("path"))
        if path is None:
            return _fail("PROOF_DEPENDENCY_PATH_INVALID", index=index)
        actual = git_blob_sha(path)
        if row.get("git_blob_sha") != actual:
            return _fail("PROOF_DEPENDENCY_BLOB_DRIFT", index=index)
        checked_deps.append({"path": str(row.get("path")), "git_blob_sha": actual})

    certificate_sha = sha256(_canon(dict(raw))).hexdigest()
    receipt_body = {
        "pass": True,
        "schema": RECEIPT_SCHEMA,
        "status": "PASS__BOUNDED_EXECUTABLE_REFINEMENT_VERIFIED",
        "subject_id": subject_id,
        "certificate_sha256": certificate_sha,
        "abstract_spec": {
            "path": str(abstract.get("path")),
            "git_blob_sha": str(abstract.get("git_blob_sha")),
            "semantic_version": str(abstract.get("semantic_version")),
        },
        "concrete_implementation": concrete_receipts,
        "proof_dependencies": checked_deps,
        "transition_case_ids": sorted(seen),
        "safety_refinement_verified": True,
        "liveness_refinement_required": bool(liveness.get("required")),
        "liveness_refinement_verified": bool(liveness.get("proved")),
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    receipt_sha = sha256(_canon(receipt_body)).hexdigest()
    return {**receipt_body, "receipt_sha256": receipt_sha}
