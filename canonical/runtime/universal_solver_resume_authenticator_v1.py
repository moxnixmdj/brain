"""Authenticated resume verifier for Universal Verified Adaptive Solver V4.

This verifier authenticates a persisted V4 continuation state for the currently
supported external-effect class.

It does NOT trust a historical checkpoint merely because it has a hash. It
recomputes the load-bearing facts:

1. exact full problem/capability contract identity;
2. every historical built-in verifier verdict from the persisted accepted proposal;
3. every V3/V4 effect-semantics receipt and independent-verification binding;
4. every historical verified effect tool identity and pinned pack blob;
5. current external filesystem bytes for every load-bearing effect receipt;
6. every state-capsule transition and final capsule head;
7. the exact set of currently verified facts.

The currently supported effect class is the universal_verified_effect_executor_v1
bounded filesystem registry. A path written by more than one historical effect is
rejected in V1 rather than guessing which old logical facts remain externally true.

Passing this verifier authenticates continuation state. It grants no terminal,
capability, or ownership credit.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime import universal_verified_adaptive_solver_v4 as v4
from canonical.runtime.universal_solver_state_capsule_v1 import (
    initialize as initialize_state_capsule,
    append_verified_transition as append_state_transition,
    verify_targets as verify_state_targets,
)
from canonical.runtime.universal_verified_effect_executor_v1 import EXECUTOR_ID
from canonical.runtime.h100_verified_effect_tool_registry_v1 import registry_snapshot

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_RESUME_AUTHENTICATOR_V1"
RESUME_SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_RESUME_STATE_V1"


class ResumeAuthenticationError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=lambda x: {
            "__brain_type__": "bytes",
            "base64": __import__("base64").b64encode(x).decode("ascii"),
        } if isinstance(x, bytes) else (_ for _ in ()).throw(TypeError(type(x).__name__)),
    )


def _digest(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _effect_outcome_digest(value: Mapping[str, Any]) -> str:
    # Must exactly match universal_verified_effect_executor_v1.execute.
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def make_resume_state(
    problem: Mapping[str, Any],
    solver_result: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(problem, Mapping) or not isinstance(solver_result, Mapping):
        raise ResumeAuthenticationError("PROBLEM_AND_SOLVER_RESULT_REQUIRED")
    trace = solver_result.get("trace")
    capsule = solver_result.get("state_capsule")
    verified = solver_result.get("verified_facts")
    if not isinstance(trace, list) or not isinstance(capsule, Mapping) or not isinstance(verified, list):
        raise ResumeAuthenticationError("SOLVER_RESULT_HAS_NO_RESUMABLE_STATE")
    head = capsule.get("head_hash")
    if not isinstance(head, str) or not head:
        raise ResumeAuthenticationError("SOLVER_RESULT_CAPSULE_HEAD_MISSING")
    return {
        "schema": RESUME_SCHEMA,
        "problem_sha256": v1._digest(problem),
        "task_contract_sha256": v4.task_contract_sha256(problem),
        "verified_facts": list(verified),
        "trace": deepcopy(trace),
        "state_capsule": deepcopy(dict(capsule)),
        "state_capsule_head_hash": head,
        "source_solver_status": solver_result.get("status"),
    }


def _tokens(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ResumeAuthenticationError(label + "_INVALID")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ResumeAuthenticationError(label + "_ITEM_INVALID")
        token = item.strip()
        if token in out:
            raise ResumeAuthenticationError(label + "_DUPLICATE:" + token)
        out.append(token)
    return out


def _safe_rel(value: Any, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ResumeAuthenticationError(label + "_INVALID")
    p = PurePosixPath(value)
    if p.is_absolute() or any(part in {"", ".", ".."} for part in p.parts):
        raise ResumeAuthenticationError(label + "_NONCANONICAL")
    return p


def _registry() -> dict[str, Mapping[str, Any]]:
    snap = registry_snapshot()
    entries = snap.get("entries")
    if not isinstance(entries, list):
        raise ResumeAuthenticationError("EFFECT_TOOL_REGISTRY_INVALID")
    out: dict[str, Mapping[str, Any]] = {}
    for row in entries:
        if not isinstance(row, Mapping):
            raise ResumeAuthenticationError("EFFECT_TOOL_REGISTRY_ROW_INVALID")
        tid = row.get("tool_id")
        if not isinstance(tid, str) or not tid or tid in out:
            raise ResumeAuthenticationError("EFFECT_TOOL_REGISTRY_ID_INVALID")
        out[tid] = row
    return out


def _revalidate_effect(
    *,
    cap: Mapping[str, Any],
    trace_row: Mapping[str, Any],
    effect_root: str | Path,
    seen_targets: set[str],
) -> dict[str, Any]:
    action = cap.get("action")
    if not isinstance(action, Mapping) or action.get("type") != "verified_effect_tool":
        raise ResumeAuthenticationError("TRACE_EFFECT_ON_NON_EFFECT_CAPABILITY")
    outcome = trace_row.get("effect_outcome")
    digest = trace_row.get("effect_outcome_sha256")
    if not isinstance(outcome, Mapping) or not isinstance(digest, str) or len(digest) != 64:
        raise ResumeAuthenticationError("EFFECT_OUTCOME_MISSING_OR_INVALID")
    if _effect_outcome_digest(outcome) != digest:
        raise ResumeAuthenticationError("EFFECT_OUTCOME_DIGEST_MISMATCH")

    executor_payload = action.get("executor_payload")
    if not isinstance(executor_payload, Mapping):
        raise ResumeAuthenticationError("EFFECT_EXECUTOR_PAYLOAD_INVALID")
    tool_id = executor_payload.get("tool_id")
    sandbox_rel = executor_payload.get("sandbox_rel")
    if outcome.get("executor_id") != EXECUTOR_ID:
        raise ResumeAuthenticationError("EFFECT_EXECUTOR_ID_MISMATCH")
    if outcome.get("tool_id") != tool_id or outcome.get("sandbox_rel") != sandbox_rel:
        raise ResumeAuthenticationError("EFFECT_OUTCOME_ACTION_BINDING_MISMATCH")

    reg = _registry().get(str(tool_id))
    if reg is None:
        raise ResumeAuthenticationError("EFFECT_TOOL_NO_LONGER_REGISTERED:" + str(tool_id))
    if outcome.get("pack_git_blob_sha") != reg.get("pack_git_blob_sha"):
        raise ResumeAuthenticationError("EFFECT_TOOL_PACK_BLOB_MISMATCH:" + str(tool_id))
    if outcome.get("prior_verification") != reg.get("prior_verification"):
        raise ResumeAuthenticationError("EFFECT_TOOL_PRIOR_VERIFICATION_MISMATCH:" + str(tool_id))

    root = Path(effect_root).resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise ResumeAuthenticationError("EFFECT_ROOT_INVALID")
    sandbox = (root / Path(*_safe_rel(sandbox_rel, "SANDBOX_REL").parts)).resolve(strict=True)
    try:
        sandbox.relative_to(root)
    except ValueError as exc:
        raise ResumeAuthenticationError("EFFECT_SANDBOX_ESCAPES_ROOT") from exc
    if not sandbox.is_dir() or sandbox.is_symlink():
        raise ResumeAuthenticationError("EFFECT_SANDBOX_INVALID")

    receipts = outcome.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        raise ResumeAuthenticationError("EFFECT_RECEIPTS_MISSING")
    checked: list[dict[str, Any]] = []
    for i, rec in enumerate(receipts):
        if not isinstance(rec, Mapping):
            raise ResumeAuthenticationError(f"EFFECT_RECEIPT_INVALID:{i}")
        rel = _safe_rel(rec.get("path"), f"EFFECT_RECEIPT_PATH:{i}")
        key = _safe_rel(str(sandbox_rel), "SANDBOX_REL").as_posix() + "/" + rel.as_posix()
        if key in seen_targets:
            raise ResumeAuthenticationError("EFFECT_TARGET_MUTATED_MULTIPLE_TIMES:" + key)
        target = (sandbox / Path(*rel.parts)).resolve(strict=True)
        try:
            target.relative_to(sandbox)
        except ValueError as exc:
            raise ResumeAuthenticationError("EFFECT_RECEIPT_TARGET_ESCAPES_SANDBOX:" + key) from exc
        if not target.is_file() or target.is_symlink():
            raise ResumeAuthenticationError("EFFECT_RECEIPT_TARGET_INVALID:" + key)
        raw = target.read_bytes()
        actual = sha256(raw).hexdigest()
        if actual != rec.get("sha256") or len(raw) != rec.get("bytes"):
            raise ResumeAuthenticationError("CURRENT_EFFECT_WORLD_STATE_MISMATCH:" + key)
        checked.append({
            "path": key,
            "sha256": actual,
            "bytes": len(raw),
        })
    seen_targets.update(r["path"] for r in checked)
    return {
        "capability_id": cap.get("id"),
        "tool_id": tool_id,
        "effect_outcome_sha256": digest,
        "current_world_receipts": checked,
    }


def authenticate(
    problem: Mapping[str, Any],
    resume_state: Mapping[str, Any],
    *,
    repo_root: str | Path,
    effect_root: str | Path | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(problem, Mapping):
            raise ResumeAuthenticationError("PROBLEM_NOT_OBJECT")
        if not isinstance(resume_state, Mapping) or resume_state.get("schema") != RESUME_SCHEMA:
            raise ResumeAuthenticationError("RESUME_STATE_SCHEMA_INVALID")

        problem_sha = v1._digest(problem)
        if resume_state.get("problem_sha256") != problem_sha:
            raise ResumeAuthenticationError("RESUME_PROBLEM_SHA256_MISMATCH")
        if resume_state.get("task_contract_sha256") != v4.task_contract_sha256(problem):
            raise ResumeAuthenticationError("RESUME_TASK_CONTRACT_SHA256_MISMATCH")

        caps = v4._caps(problem)
        initial = v4._tokens(problem.get("initial_facts", []), "INITIAL_FACTS")
        targets = v4._tokens(problem.get("target_effects", []), "TARGET_EFFECTS", allow_empty=False)

        trace = resume_state.get("trace")
        if not isinstance(trace, list):
            raise ResumeAuthenticationError("RESUME_TRACE_INVALID")
        supplied_capsule = resume_state.get("state_capsule")
        if not isinstance(supplied_capsule, Mapping):
            raise ResumeAuthenticationError("RESUME_CAPSULE_INVALID")
        supplied_facts = sorted(_tokens(resume_state.get("verified_facts", []), "VERIFIED_FACTS"))

        capsule = initialize_state_capsule(problem)
        current = sorted(set(initial))
        reverified_effects: list[dict[str, Any]] = []
        seen_effect_targets: set[str] = set()

        for index, row in enumerate(trace):
            if not isinstance(row, Mapping) or row.get("cycle") != index:
                raise ResumeAuthenticationError("TRACE_CYCLE_INVALID:" + str(index))
            cid = row.get("capability_id")
            if not isinstance(cid, str) or cid not in caps:
                raise ResumeAuthenticationError("TRACE_CAPABILITY_UNKNOWN:" + str(cid))
            cap = caps[cid]
            requires = set(v4._tokens(cap.get("requires", []), cid + "_REQUIRES"))
            if not requires.issubset(current):
                raise ResumeAuthenticationError("TRACE_PRECONDITION_NOT_IN_CURRENT_STATE:" + cid)

            semantics = v4._authenticate_effect_semantics(problem, cap, repo_root=repo_root)
            expected_effects = list(semantics["effects"])
            if row.get("new_verified_facts") != expected_effects:
                raise ResumeAuthenticationError("TRACE_EFFECT_SET_MISMATCH:" + cid)
            if row.get("verifier_success_condition") != semantics["verifier_success_condition"]:
                raise ResumeAuthenticationError("TRACE_VERIFIER_SUCCESS_CONDITION_MISMATCH:" + cid)
            if row.get("effect_semantics_receipt") != semantics["receipt"]:
                raise ResumeAuthenticationError("TRACE_EFFECT_SEMANTICS_RECEIPT_MISMATCH:" + cid)
            if row.get("effect_semantics_verification") != semantics["verification"]:
                raise ResumeAuthenticationError("TRACE_EFFECT_SEMANTICS_VERIFICATION_MISMATCH:" + cid)

            action = cap.get("action")
            if not isinstance(action, Mapping):
                raise ResumeAuthenticationError("TRACE_ACTION_INVALID:" + cid)
            if row.get("action_contract_sha256") != v1._digest(action):
                raise ResumeAuthenticationError("TRACE_ACTION_CONTRACT_DIGEST_MISMATCH:" + cid)
            proposal = row.get("accepted_proposal")
            if not isinstance(proposal, Mapping):
                raise ResumeAuthenticationError("TRACE_ACCEPTED_PROPOSAL_MISSING:" + cid)

            verifier_id, payload, effectful = v4._active_verifier(cap)
            if row.get("verifier_id") != verifier_id:
                raise ResumeAuthenticationError("TRACE_VERIFIER_ID_MISMATCH:" + cid)
            verifier = v1.BUILTIN_VERIFIERS[verifier_id]
            verdict = verifier(payload, proposal)
            if verdict.get("pass") is not True:
                raise ResumeAuthenticationError("TRACE_PROPOSAL_NO_LONGER_VERIFIES:" + cid)
            if row.get("proof_digest") != verdict.get("proof_digest"):
                raise ResumeAuthenticationError("TRACE_PROOF_DIGEST_MISMATCH:" + cid)
            if row.get("proposal_sha256") != v1._digest(proposal):
                raise ResumeAuthenticationError("TRACE_PROPOSAL_DIGEST_MISMATCH:" + cid)

            if effectful:
                if effect_root is None:
                    raise ResumeAuthenticationError("EFFECT_ROOT_REQUIRED_FOR_RESUME")
                reverified_effects.append(
                    _revalidate_effect(
                        cap=cap,
                        trace_row=row,
                        effect_root=effect_root,
                        seen_targets=seen_effect_targets,
                    )
                )
            elif row.get("effect_outcome_sha256") is not None or row.get("effect_outcome") is not None:
                raise ResumeAuthenticationError("NON_EFFECT_CAPABILITY_CARRIES_EFFECT_OUTCOME:" + cid)

            capsule = append_state_transition(capsule, capability=cap, trace_row=row)
            current = sorted(set(current) | set(expected_effects))

        if current != supplied_facts:
            raise ResumeAuthenticationError("RESUME_VERIFIED_FACT_SET_MISMATCH")
        if _canon(capsule) != _canon(supplied_capsule):
            raise ResumeAuthenticationError("RESUME_CAPSULE_REBUILD_MISMATCH")
        if resume_state.get("state_capsule_head_hash") != capsule.get("head_hash"):
            raise ResumeAuthenticationError("RESUME_CAPSULE_HEAD_MISMATCH")

        target_verdict = verify_state_targets(capsule, targets)
        state_digest = _digest({
            "problem_sha256": problem_sha,
            "task_contract_sha256": v4.task_contract_sha256(problem),
            "verified_facts": current,
            "state_capsule_head_hash": capsule.get("head_hash"),
            "trace_sha256": _digest(trace),
            "reverified_effects": reverified_effects,
        })
        return {
            "schema": SCHEMA,
            "status": "PASS__RESUME_STATE_AND_CURRENT_EFFECT_WORLD_REVERIFIED",
            "pass": True,
            "problem_sha256": problem_sha,
            "task_contract_sha256": v4.task_contract_sha256(problem),
            "verified_facts": current,
            "trace": deepcopy(trace),
            "state_capsule": deepcopy(capsule),
            "state_capsule_head_hash": capsule.get("head_hash"),
            "target_verdict": target_verdict,
            "reverified_effects": reverified_effects,
            "resume_state_sha256": state_digest,
            "external_effect_target_count": len(seen_effect_targets),
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "scope_boundary": (
                "AUTHENTICATES_RESUME_ONLY_FOR_V4_DECLARED_CAPABILITIES_AND_CURRENT_"
                "BOUNDED_FILESYSTEM_EFFECT_REGISTRY__REPEATED_MUTATION_OF_ONE_EFFECT_"
                "PATH_IS_NOT_YET_SUPPORTED"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
