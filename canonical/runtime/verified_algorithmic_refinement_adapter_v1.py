"""Adapter from independently verified algorithmic theorems to refinement receipts.

This module does not invent a new theorem. It recognizes small kernel-owned proof
profiles and checks the complete content-addressed provenance chain required by
that profile. A receipt is minted only when the already-independent verification
asserts the exact concrete implementation and the required semantic claims.

Currently supported profile:
  CODING_FINITE_EXACT_ORACLE_V1

The resulting refinement is conditional on the theorem's six pre-execution
atoms. It grants no execution, benchmark, acceptance, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

CERT_SCHEMA = "PROJECT_BRAIN_VERIFIED_ALGORITHMIC_REFINEMENT_CERTIFICATE_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_VERIFIED_ALGORITHMIC_REFINEMENT_RECEIPT_V1"
PROFILE_ID = "CODING_FINITE_EXACT_ORACLE_V1"
SUBJECT_ID = "BRAIN_FINITE_CANDIDATE_EXACT_ORACLE_SOLVER_V1"
THEOREM_SCHEMA = "PROJECT_BRAIN_CODING_FINITE_EXACT_ORACLE_CONSTRUCTIVE_ADEQUACY_THEOREM_V1"
ADEQUACY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_V1"

REQUIRED_ATOMS = frozenset({
    "CODING_FINITE_SOLVER_CANDIDATE_SET_FINITE_V1",
    "CODING_FINITE_SOLVER_ORACLE_TOTAL_V1",
    "CODING_FINITE_SOLVER_ORACLE_SOUND_COMPLETE_V1",
    "CODING_FINITE_SOLVER_VALID_MEMBER_EXISTS_V1",
    "CODING_FINITE_SOLVER_CALL_BUDGET_SUFFICIENT_V1",
    "CODING_FINITE_SOLVER_ORACLE_PRETERMINAL_ADMISSIBLE_V1",
})
REQUIRED_VERIFIED = frozenset({
    "THE_EXACT_POLICY_ENUMERATES_A_FINITE_DECLARED_CANDIDATE_SEQUENCE_IN_ORDER_AND_CHECKS_EACH_AT_MOST_ONCE.",
    "WITH_A_TOTAL_CHECKER_AND_SUFFICIENT_CALL_BUDGET_THE_POLICY_TERMINATES_AFTER_AT_MOST_N_CHECKS.",
    "WITH_CHECKER_COMPLETENESS_AND_EXISTENCE_OF_A_VALID_MEMBER_THE_POLICY_REACHES_A_TRUE_CHECK.",
    "WITH_CHECKER_SOUNDNESS_THE_RETURNED_TRUE_CANDIDATE_IS_CORRECT.",
    "THE_CONSTRUCTIVE_THEOREM_IS_CONDITIONAL_ON_ALL_SIX_PREEXECUTION_ATOMS.",
    "THE_CERTIFICATE_CREATES_NO_CURSORBENCH_MEMBERSHIP_OR_WHOLE_SCOPE_COVER.",
})
_REQUIRED_FIELDS = frozenset({
    "schema",
    "profile_id",
    "subject_id",
    "concrete_implementation",
    "theorem",
    "adequacy_certificate",
    "independent_verification",
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
        "safety_refinement_verified": False,
        "liveness_refinement_verified": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _repo_path(root: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    p = Path(raw)
    if p.is_absolute() or ".." in p.parts:
        return None
    root = root.resolve()
    full = (root / p).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        return None
    return full if full.is_file() else None


def _bound_json(
    row: Any, *, root: Path, label: str
) -> tuple[dict[str, Any] | None, dict[str, str] | None, str | None]:
    if not isinstance(row, Mapping) or set(row) != {"path", "git_blob_sha"}:
        return None, None, f"{label}_BINDING_INVALID"
    p = _repo_path(root, row.get("path"))
    if p is None:
        return None, None, f"{label}_PATH_INVALID"
    actual = git_blob_sha(p)
    if row.get("git_blob_sha") != actual:
        return None, None, f"{label}_BLOB_DRIFT"
    try:
        value = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None, None, f"{label}_JSON_INVALID"
    if not isinstance(value, dict):
        return None, None, f"{label}_NOT_OBJECT"
    return value, {"path": str(row["path"]), "git_blob_sha": actual}, None


def _bound_source(
    row: Any, *, root: Path
) -> tuple[dict[str, str] | None, str | None]:
    if not isinstance(row, Mapping) or set(row) != {"path", "git_blob_sha"}:
        return None, "CONCRETE_BINDING_INVALID"
    p = _repo_path(root, row.get("path"))
    if p is None:
        return None, "CONCRETE_PATH_INVALID"
    actual = git_blob_sha(p)
    if row.get("git_blob_sha") != actual:
        return None, "CONCRETE_BLOB_DRIFT"
    return {"path": str(row["path"]), "git_blob_sha": actual}, None


def _binding_matches(raw: Any, expected: Mapping[str, str]) -> bool:
    return (
        isinstance(raw, Mapping)
        and raw.get("path") == expected.get("path")
        and raw.get("git_blob_sha") == expected.get("git_blob_sha")
    )


def _condition_atoms(condition: Any) -> set[str] | None:
    if not isinstance(condition, Mapping):
        return None
    if condition.get("op") != "AND":
        return None
    args = condition.get("args")
    if not isinstance(args, list):
        return None
    out: set[str] = set()
    for row in args:
        if (
            not isinstance(row, Mapping)
            or row.get("op") != "ATOM"
            or not isinstance(row.get("id"), str)
            or not row["id"]
        ):
            return None
        if row["id"] in out:
            return None
        out.add(row["id"])
    return out


def verify_certificate_file(
    certificate_path: str,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = (
        Path(repo_root)
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    ).resolve()
    p = _repo_path(root, certificate_path)
    if p is None:
        return _fail("CERTIFICATE_PATH_INVALID")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _fail("CERTIFICATE_JSON_INVALID")
    if not isinstance(raw, Mapping):
        return _fail("CERTIFICATE_NOT_OBJECT")
    return verify_certificate(
        raw,
        repo_root=root,
        certificate_git_blob_sha=git_blob_sha(p),
        certificate_path=certificate_path,
    )


def verify_certificate(
    raw: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    certificate_git_blob_sha: str | None = None,
    certificate_path: str | None = None,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return _fail("CERTIFICATE_NOT_OBJECT")
    if raw.get("schema") != CERT_SCHEMA:
        return _fail("CERTIFICATE_SCHEMA_INVALID")
    if set(raw) != _REQUIRED_FIELDS:
        return _fail(
            "CERTIFICATE_FIELD_SET_INVALID",
            missing_fields=sorted(_REQUIRED_FIELDS - set(raw)),
            extra_fields=sorted(set(raw) - _REQUIRED_FIELDS),
        )
    if raw.get("profile_id") != PROFILE_ID:
        return _fail("PROFILE_UNSUPPORTED")
    if raw.get("subject_id") != SUBJECT_ID:
        return _fail("SUBJECT_ID_INVALID")
    if raw.get("terminal_credit_delta") != 0:
        return _fail("NONZERO_TERMINAL_CREDIT_FORBIDDEN")
    if (
        not isinstance(certificate_git_blob_sha, str)
        or len(certificate_git_blob_sha) != 40
    ):
        return _fail("CERTIFICATE_GIT_BLOB_SHA_REQUIRED")

    root = (
        Path(repo_root)
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    ).resolve()

    concrete, reason = _bound_source(
        raw.get("concrete_implementation"), root=root
    )
    if concrete is None:
        return _fail(str(reason))

    theorem, theorem_binding, reason = _bound_json(
        raw.get("theorem"), root=root, label="THEOREM"
    )
    if theorem is None or theorem_binding is None:
        return _fail(str(reason))
    adequacy, adequacy_binding, reason = _bound_json(
        raw.get("adequacy_certificate"), root=root, label="ADEQUACY"
    )
    if adequacy is None or adequacy_binding is None:
        return _fail(str(reason))
    verification, verification_binding, reason = _bound_json(
        raw.get("independent_verification"), root=root, label="INDEPENDENT_VERIFICATION"
    )
    if verification is None or verification_binding is None:
        return _fail(str(reason))

    if theorem.get("schema") != THEOREM_SCHEMA:
        return _fail("THEOREM_SCHEMA_INVALID")
    if theorem.get("policy_id") != SUBJECT_ID:
        return _fail("THEOREM_POLICY_ID_MISMATCH")
    if not _binding_matches(theorem.get("exact_policy"), concrete):
        return _fail("THEOREM_CONCRETE_BINDING_MISMATCH")
    atoms = _condition_atoms(theorem.get("condition"))
    if atoms != REQUIRED_ATOMS:
        return _fail("THEOREM_CONDITION_PROFILE_MISMATCH")
    condition_sha = str(theorem.get("condition_sha256") or "")
    if len(condition_sha) != 64:
        return _fail("THEOREM_CONDITION_SHA_INVALID")
    proof = theorem.get("proof")
    if not isinstance(proof, Mapping):
        return _fail("THEOREM_PROOF_INVALID")
    if theorem.get("adequacy", {}).get("adequate_for_every_member") is not True:
        return _fail("THEOREM_ALL_MEMBERS_ADEQUACY_UNPROVED")
    if theorem.get("adequacy", {}).get("constructive_liveness") is not True:
        return _fail("THEOREM_CONSTRUCTIVE_LIVENESS_UNPROVED")
    if theorem.get("promotion_authority") is not False or theorem.get("terminal_authority") is not False:
        return _fail("THEOREM_AUTHORITY_BOUNDARY_INVALID")
    if theorem.get("accounting", {}).get("terminal_credit_delta") != 0:
        return _fail("THEOREM_NONZERO_TERMINAL_CREDIT")

    if adequacy.get("schema") != ADEQUACY_SCHEMA:
        return _fail("ADEQUACY_SCHEMA_INVALID")
    if adequacy.get("policy_id") != SUBJECT_ID:
        return _fail("ADEQUACY_POLICY_ID_MISMATCH")
    if adequacy.get("adequacy_proved") is not True:
        return _fail("ADEQUACY_NOT_PROVED")
    if not _binding_matches(adequacy.get("exact_policy"), concrete):
        return _fail("ADEQUACY_CONCRETE_BINDING_MISMATCH")
    if adequacy.get("policy_condition_sha256") != condition_sha:
        return _fail("ADEQUACY_CONDITION_BINDING_MISMATCH")
    if not _binding_matches(
        adequacy.get("exact_sources", {}).get("theorem"), theorem_binding
    ):
        return _fail("ADEQUACY_THEOREM_BINDING_MISMATCH")
    theorem_meta = adequacy.get("adequacy_theorem")
    if not isinstance(theorem_meta, Mapping):
        return _fail("ADEQUACY_THEOREM_METADATA_INVALID")
    if theorem_meta.get("mode") != "FORMAL_ALL_MEMBERS":
        return _fail("ADEQUACY_MODE_NOT_FORMAL_ALL_MEMBERS")
    if theorem_meta.get("constructive_liveness") is not True:
        return _fail("ADEQUACY_LIVENESS_UNPROVED")
    if adequacy.get("promotion_authority") is not False or adequacy.get("terminal_authority") is not False:
        return _fail("ADEQUACY_AUTHORITY_BOUNDARY_INVALID")
    if adequacy.get("accounting", {}).get("terminal_credit_delta") != 0:
        return _fail("ADEQUACY_NONZERO_TERMINAL_CREDIT")

    if verification.get("schema") != VERIFY_SCHEMA:
        return _fail("INDEPENDENT_VERIFICATION_SCHEMA_INVALID")
    if verification.get("policy_id") != SUBJECT_ID:
        return _fail("INDEPENDENT_VERIFICATION_POLICY_ID_MISMATCH")
    if verification.get("pass") is not True:
        return _fail("INDEPENDENT_VERIFICATION_NOT_PASSING")
    if verification.get("subject_git_blob_sha") != adequacy_binding["git_blob_sha"]:
        return _fail("INDEPENDENT_VERIFICATION_ADEQUACY_BINDING_MISMATCH")
    evidence = verification.get("evidence")
    if not isinstance(evidence, Mapping):
        return _fail("INDEPENDENT_VERIFICATION_EVIDENCE_INVALID")
    if not _binding_matches(evidence.get("exact_policy"), concrete):
        return _fail("INDEPENDENT_VERIFICATION_CONCRETE_BINDING_MISMATCH")
    if not _binding_matches(evidence.get("theorem"), theorem_binding):
        return _fail("INDEPENDENT_VERIFICATION_THEOREM_BINDING_MISMATCH")
    replay = verification.get("independent_replay")
    if not isinstance(replay, Mapping):
        return _fail("INDEPENDENT_REPLAY_INVALID")
    if replay.get("py_compile_pass") is not True:
        return _fail("INDEPENDENT_REPLAY_COMPILE_UNPROVED")
    run = replay.get("test_functions_run")
    passed = replay.get("test_functions_passed")
    if (
        isinstance(run, bool)
        or not isinstance(run, int)
        or run < 8
        or passed != run
    ):
        return _fail("INDEPENDENT_REPLAY_TESTS_INSUFFICIENT")
    patterns = replay.get("exhaustive_boolean_patterns_checked")
    if isinstance(patterns, bool) or not isinstance(patterns, int) or patterns < 510:
        return _fail("INDEPENDENT_REPLAY_PATTERN_COVERAGE_INSUFFICIENT")
    symbolic = verification.get("symbolic_core")
    if (
        not isinstance(symbolic, Mapping)
        or symbolic.get("budget_reaches_witness") is not True
        or symbolic.get("first_true_is_correct") is not True
        or symbolic.get("valid_member_is_detected") is not True
    ):
        return _fail("SYMBOLIC_CORE_UNPROVED")
    verified = verification.get("verified")
    if not isinstance(verified, list) or not REQUIRED_VERIFIED.issubset(set(verified)):
        return _fail("REQUIRED_SEMANTIC_CLAIMS_NOT_INDEPENDENTLY_VERIFIED")
    if verification.get("promotion_authority") is not False or verification.get("terminal_authority") is not False:
        return _fail("INDEPENDENT_VERIFICATION_AUTHORITY_BOUNDARY_INVALID")
    if verification.get("accounting", {}).get("terminal_credit_delta") != 0:
        return _fail("INDEPENDENT_VERIFICATION_NONZERO_TERMINAL_CREDIT")

    body = {
        "pass": True,
        "schema": RECEIPT_SCHEMA,
        "status": "PASS__CONDITIONAL_ALL_MEMBERS_ALGORITHMIC_EXECUTABLE_REFINEMENT_VERIFIED",
        "profile_id": PROFILE_ID,
        "subject_id": SUBJECT_ID,
        "certificate_path": certificate_path,
        "certificate_git_blob_sha": certificate_git_blob_sha,
        "concrete_route_git_blob_sha": concrete["git_blob_sha"],
        "concrete_implementation": concrete,
        "theorem": theorem_binding,
        "adequacy_certificate": adequacy_binding,
        "independent_verification": verification_binding,
        "condition_sha256": condition_sha,
        "required_condition_atoms": sorted(REQUIRED_ATOMS),
        "assurance_level": "CONDITIONAL_FORMAL_ALL_MEMBERS_ALGORITHMIC_REFINEMENT",
        "refinement_verified": True,
        "safety_refinement_verified": True,
        "liveness_refinement_verified": True,
        "condition_truth_created": False,
        "membership_created": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "nonclaims": [
            "NO_CONDITION_ATOM_TRUTH_CREATED",
            "NO_PRIVATE_TASK_MEMBERSHIP_CREATED",
            "NO_WHOLE_BEHAVIOR_OR_BENCHMARK_COVER",
            "NO_TERMINAL_OR_ACCEPTANCE_CREDIT",
        ],
    }
    return {
        **body,
        "receipt_sha256": sha256(_canon(body)).hexdigest(),
    }
