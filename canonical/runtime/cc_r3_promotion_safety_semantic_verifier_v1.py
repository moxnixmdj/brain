"""Executable CC_R3 verifier for the frozen R3 promotion-safety claim.

This is a bounded decision procedure over content-addressed current-generation
R3 source. It proves only the frozen claim identified in the certificate.
It grants no terminal authority.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CC_R3_PROMOTION_SAFETY_SEMANTIC_VERIFIER_V1"
ROOT_ID = "CC_R3_TERMINAL_CLOSURE_V1"
CERT_SCHEMA = "PROJECT_BRAIN_CC_R3_PROMOTION_SAFETY_CERTIFICATE_V1"
CLAIM_ID = "e1c519109c4b2c46a9225686fc2c5c5490564d1cc62d5c6ff3c6c436bfca4314"

PRIMARY_REQUIRED = {
    "canonical/runtime/autonomous_verified_self_improvement_v1.py",
    "canonical/runtime/r3_improvement_queue_driver_v1.py",
    "canonical/runtime/r3_independent_learning_verifier_v1.py",
    "canonical/runtime/r3_distinguishing_evidence_acquisition_v1.py",
    "canonical/runtime/r3_retained_distinguishing_evidence_provider_v1.py",
    "canonical/runtime/r3_bound_success_adapter_v1.py",
    "canonical/runtime/r3_raw_success_adapter_v1.py",
    "canonical/runtime/r3_checkpoint_reconstruction_success_adapter_v1.py",
    "canonical/runtime/r3_structural_bound_success_adapter_v1.py",
    "canonical/runtime/r3_structural_bound_rule_acquisition_v1.py",
}
DEPENDENCY_REQUIRED = {
    "canonical/runtime/executable_skill_verification_authenticator_v1.py",
    "canonical/runtime/universal_solver_episode_verification_authenticator_v1.py",
    "canonical/runtime/r3_bound_success_checkpoint_verifier_v1.py",
    "canonical/runtime/r3_raw_success_checkpoint_verifier_v1.py",
    "canonical/runtime/R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1.json",
}
AUTHORITY_FIELDS = {
    "provider_truth_authority",
    "truth_authority",
    "verification_authority",
    "promotion_authority",
    "acceptance_authority",
    "terminal_authority",
}


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _fail(reason: str, checks: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "root_id": ROOT_ID,
        "claim_id": CLAIM_ID,
        "reason": reason,
        "checks": sorted(checks or []),
        "proof_mode": "DECISION_PROCEDURE",
        "terminal_credit_delta": 0,
    }


def _load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("JSON_NOT_OBJECT:" + str(path))
    return value


def _source(root: Path, relative: str) -> tuple[str, ast.Module]:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    return text, ast.parse(text, filename=relative)


def _function(tree: ast.AST, name: str) -> ast.FunctionDef:
    matches = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]
    if len(matches) != 1:
        raise ValueError("FUNCTION_CARDINALITY:" + name + ":" + str(len(matches)))
    return matches[0]


def _unparse(node: ast.AST) -> str:
    return ast.unparse(node)


def _calls(fn: ast.AST, name: str) -> list[ast.Call]:
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Name) and target.id == name:
            out.append(node)
        elif isinstance(target, ast.Attribute) and target.attr == name:
            out.append(node)
    return out


def _string_constants(fn: ast.AST) -> set[str]:
    return {
        node.value for node in ast.walk(fn)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _parents(root: ast.AST) -> dict[int, ast.AST]:
    out: dict[int, ast.AST] = {}
    for parent in ast.walk(root):
        for child in ast.iter_child_nodes(parent):
            out[id(child)] = parent
    return out


def _assignment_lines(fn: ast.AST, needle: str) -> list[int]:
    lines = []
    for node in ast.walk(fn):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            text = _unparse(node)
            if needle in text:
                lines.append(int(getattr(node, "lineno", 0)))
    return sorted(lines)


def _ancestor_if_texts(node: ast.AST, parent_map: Mapping[int, ast.AST]) -> list[str]:
    out = []
    cursor = node
    while id(cursor) in parent_map:
        cursor = parent_map[id(cursor)]
        if isinstance(cursor, ast.If):
            out.append(_unparse(cursor.test))
    return out


def _find_assignment_nodes(fn: ast.AST, target_text: str) -> list[ast.AST]:
    out = []
    for node in ast.walk(fn):
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        else:
            continue
        if any(_unparse(target) == target_text for target in targets):
            out.append(node)
    return out


def _assert_blob_bindings(
    root: Path,
    cert: Mapping[str, Any],
    checks: list[str],
) -> None:
    primary = cert.get("primary_subject_blobs")
    deps = cert.get("proof_dependency_blobs")
    if not isinstance(primary, Mapping) or set(primary) != PRIMARY_REQUIRED:
        raise ValueError("PRIMARY_SUBJECT_SET_NOT_EXACT")
    if not isinstance(deps, Mapping) or set(deps) != DEPENDENCY_REQUIRED:
        raise ValueError("PROOF_DEPENDENCY_SET_NOT_EXACT")
    for label, rows in (("PRIMARY", primary), ("DEPENDENCY", deps)):
        for rel, claimed in rows.items():
            p = root / str(rel)
            if not p.is_file():
                raise ValueError(label + "_FILE_MISSING:" + str(rel))
            actual = _git_blob_sha(p)
            if actual != claimed:
                raise ValueError(label + "_BLOB_MISMATCH:" + str(rel))
    checks.append("EXACT_SUBJECT_AND_DEPENDENCY_BLOBS")


def _check_learning(root: Path, checks: list[str]) -> None:
    rel = "canonical/runtime/autonomous_verified_self_improvement_v1.py"
    text, tree = _source(root, rel)
    fn = _function(tree, "integrate_solver_output")
    parent_map = _parents(fn)

    episode_writes = _find_assignment_nodes(fn, "state['episodes'][episode_key]")
    if len(episode_writes) != 1:
        raise ValueError("EPISODE_WRITE_CARDINALITY")
    episode_guards = " ".join(_ancestor_if_texts(episode_writes[0], parent_map))
    if "current_episode_verified" not in episode_guards:
        raise ValueError("EPISODE_WRITE_NOT_DOMINATED_BY_VERIFIED_GUARD")
    if len(_calls(fn, "reauthenticate_episode_record")) != 1:
        raise ValueError("EPISODE_REAUTH_CARDINALITY")
    if "VERIFIED_EPISODE_REAUTHENTICATION_FAILED" not in text:
        raise ValueError("EPISODE_REAUTH_FAILURE_NOT_FAIL_CLOSED")
    checks.append("EPISODE_WRITE_VERIFIED_AND_REAUTHENTICATED")

    skill_writes = _find_assignment_nodes(fn, "state['skills'][sid]")
    if len(skill_writes) != 1:
        raise ValueError("SKILL_WRITE_CARDINALITY")
    skill_guards = " ".join(_ancestor_if_texts(skill_writes[0], parent_map))
    for token in (
        "verified_skill_reuse_authorized",
        "verified_skill",
        "reuse_authorized",
    ):
        if token not in skill_guards:
            raise ValueError("SKILL_WRITE_GUARD_MISSING:" + token)
    if len(_calls(fn, "reauthenticate_skill_record")) < 1:
        raise ValueError("SKILL_REAUTH_MISSING")
    if "VERIFIED_SKILL_REAUTHENTICATION_FAILED" not in text:
        raise ValueError("SKILL_REAUTH_FAILURE_NOT_FAIL_CLOSED")
    checks.append("SKILL_WRITE_VERIFIED_AND_REAUTHENTICATED")

    constants = _string_constants(fn)
    if "VERIFY_EPISODE" not in constants:
        raise ValueError("UNVERIFIED_EPISODE_QUEUE_MISSING")
    if "VERIFY_SKILL_CANDIDATE" not in constants:
        raise ValueError("UNVERIFIED_SKILL_QUEUE_MISSING")
    if '"permanent_reuse_authorized": False' not in text:
        raise ValueError("NO_EVIDENCE_SUCCESS_NOT_EXPLICITLY_UNPROMOTED")
    checks.append("UNVERIFIED_LEARNING_IS_QUEUED_OR_UNPROMOTED")


def _check_driver(root: Path, checks: list[str]) -> None:
    rel = "canonical/runtime/r3_improvement_queue_driver_v1.py"
    text, tree = _source(root, rel)

    ep = _function(tree, "_verify_episode_work")
    ep_verify = _calls(ep, "_post_execution_independent_verification")
    ep_integrate = _calls(ep, "integrate_solver_output")
    if len(ep_verify) != 1 or len(ep_integrate) != 1:
        raise ValueError("QUEUE_EPISODE_VERIFY_OR_INTEGRATE_CARDINALITY")
    if ep_verify[0].lineno >= ep_integrate[0].lineno:
        raise ValueError("QUEUE_EPISODE_INTEGRATES_BEFORE_VERIFY")
    ep_text = _unparse(ep)
    if "current_episode_verified" not in ep_text or "is not True" not in ep_text:
        raise ValueError("QUEUE_EPISODE_VERIFIED_GATE_MISSING")
    checks.append("QUEUE_EPISODE_INDEPENDENT_VERIFY_BEFORE_INTEGRATE")

    sk = _function(tree, "_verify_skill_work")
    sk_verify = _calls(sk, "authenticate_skill_verification")
    sk_integrate = _calls(sk, "integrate_solver_output")
    if len(sk_verify) != 1 or len(sk_integrate) != 1:
        raise ValueError("QUEUE_SKILL_VERIFY_OR_INTEGRATE_CARDINALITY")
    if sk_verify[0].lineno >= sk_integrate[0].lineno:
        raise ValueError("QUEUE_SKILL_INTEGRATES_BEFORE_AUTH")
    sk_text = _unparse(sk)
    if "verified_skill_reuse_authorized" not in sk_text:
        raise ValueError("QUEUE_SKILL_REUSE_AUTHORITY_BINDING_MISSING")
    checks.append("QUEUE_SKILL_AUTHENTICATE_BEFORE_INTEGRATE")

    acq = _function(tree, "_execute_frontier_acquisition")
    acq_text = _unparse(acq)
    for token in (
        "verification_authority_change_allowed",
        "after_authority != before_authority",
        "FRONTIER_ACQUISITION_REJECTED__VERIFICATION_AUTHORITY_REWRITTEN",
        "_reactivate_parked_successes",
    ):
        if token not in acq_text:
            raise ValueError("FRONTIER_AUTHORITY_GUARD_MISSING:" + token)
    reject_pos = acq_text.find(
        "FRONTIER_ACQUISITION_REJECTED__VERIFICATION_AUTHORITY_REWRITTEN"
    )
    reopen_pos = acq_text.find("_reactivate_parked_successes")
    if reject_pos < 0 or reopen_pos < 0 or reject_pos >= reopen_pos:
        raise ValueError("FRONTIER_AUTHORITY_REJECT_NOT_BEFORE_REOPEN")
    checks.append("VERIFICATION_AUTHORITY_REWRITE_REJECTED_BEFORE_REOPEN")

    if '"promotion_authority": False' not in text or '"terminal_authority": False' not in text:
        raise ValueError("DRIVER_ZERO_AUTHORITY_DECLARATIONS_MISSING")


def _check_evidence_acquisition(root: Path, checks: list[str]) -> None:
    rel = "canonical/runtime/r3_distinguishing_evidence_acquisition_v1.py"
    text, tree = _source(root, rel)
    fn = _function(tree, "acquire")
    fn_text = _unparse(fn)
    for field in sorted(AUTHORITY_FIELDS):
        if repr(field) not in fn_text and ('"' + field + '"') not in fn_text:
            raise ValueError("AUTHORITY_ESCALATION_FIELD_NOT_CHECKED:" + field)
    if "DISTINGUISHING_EVIDENCE_PROVIDER_AUTHORITY_ESCALATION_REJECTED" not in fn_text:
        raise ValueError("PROVIDER_AUTHORITY_ESCALATION_REJECTION_MISSING")
    if "record_success_observation" not in fn_text:
        raise ValueError("EVIDENCE_NOT_REINGESTED_AS_OBSERVATION")
    checks.append("EVIDENCE_PROVIDER_AUTHORITY_ESCALATION_REJECTED")

    for path in (
        rel,
        "canonical/runtime/r3_retained_distinguishing_evidence_provider_v1.py",
    ):
        source, subtree = _source(root, path)
        for node in ast.walk(subtree):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value in AUTHORITY_FIELDS
                    and isinstance(value, ast.Constant)
                    and value.value is True
                ):
                    raise ValueError(
                        "CANDIDATE_PROVIDER_GRANTS_AUTHORITY:"
                        + path + ":" + str(key.value)
                    )
    checks.append("CANDIDATE_EVIDENCE_OUTPUTS_HAVE_ZERO_AUTHORITY")


def _check_authenticators(root: Path, checks: list[str]) -> None:
    skill_rel = "canonical/runtime/executable_skill_verification_authenticator_v1.py"
    episode_rel = "canonical/runtime/universal_solver_episode_verification_authenticator_v1.py"
    skill_text, skill_tree = _source(root, skill_rel)
    episode_text, episode_tree = _source(root, episode_rel)

    for name in ("authenticate_and_verify", "reauthenticate_record"):
        _function(skill_tree, name)
    for token in (
        "independent_verified",
        "exact_byte_bound",
        "candidate_reexecuted_or_equivalently_checked",
        "source_episode_lineage_reverified",
        "VERIFIED_SKILL_RECORD_NOT_REUSABLE",
    ):
        if token not in skill_text:
            raise ValueError("SKILL_AUTHENTICATOR_INVARIANT_MISSING:" + token)

    for name in ("authenticate", "reauthenticate_record"):
        _function(episode_tree, name)
    for token in (
        "independent_verified",
        "behavior_verified",
        "exact_byte_bound",
        "trace_reverified",
        "state_lineage_reverified",
    ):
        if token not in episode_text:
            raise ValueError("EPISODE_AUTHENTICATOR_INVARIANT_MISSING:" + token)
    checks.append("AUTHENTICATORS_BIND_INDEPENDENT_EXACT_BYTE_EVIDENCE")


def verify_certificate(
    *,
    root: Path,
    certificate_path: Path,
    active_claim: Mapping[str, Any],
    root_id: str,
) -> dict[str, Any]:
    checks: list[str] = []
    try:
        root = Path(root).resolve()
        cert = _load_json(Path(certificate_path))
        if cert.get("schema") != CERT_SCHEMA:
            raise ValueError("CERTIFICATE_SCHEMA_INVALID")
        if root_id != ROOT_ID or cert.get("root_id") != ROOT_ID:
            raise ValueError("ROOT_ID_MISMATCH")
        if active_claim.get("claim_id") != CLAIM_ID:
            raise ValueError("ACTIVE_CLAIM_ID_MISMATCH")
        binding = cert.get("claim_binding")
        if not isinstance(binding, Mapping):
            raise ValueError("CLAIM_BINDING_MISSING")
        for field in (
            "claim_id",
            "claim_kind",
            "mission_blob_sha",
            "scope_sha256",
            "target_predicate_sha256",
            "semantics_sha256",
            "epoch",
            "authority_id",
        ):
            if binding.get(field) != active_claim.get(field):
                raise ValueError("CLAIM_BINDING_MISMATCH:" + field)
        checks.append("EXACT_ACTIVE_CLAIM_BINDING")

        _assert_blob_bindings(root, cert, checks)
        _check_learning(root, checks)
        _check_driver(root, checks)
        _check_evidence_acquisition(root, checks)
        _check_authenticators(root, checks)

        return {
            "schema": SCHEMA,
            "status": "PASS__CC_R3_PROMOTION_SAFETY_DECISION_PROCEDURE",
            "pass": True,
            "root_id": ROOT_ID,
            "claim_id": CLAIM_ID,
            "proof_mode": "DECISION_PROCEDURE",
            "checks": sorted(checks),
            "subject_blob_count": len(PRIMARY_REQUIRED) + len(DEPENDENCY_REQUIRED),
            "semantic_claim_verified": True,
            "terminal_credit_delta": 0,
            "errors": [],
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc), checks)
