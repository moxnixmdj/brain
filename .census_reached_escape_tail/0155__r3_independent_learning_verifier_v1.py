"""Independent evidence-recomputation worker for R3 learning promotion.

This module is deliberately separate from the learner and queue scheduler. It may
produce the content-addressed receipt pairs consumed by the existing episode and
skill authenticators, but only after independently recomputing evidence already
recorded by the solver.

Current admitted scope:
- Universal Solver episodes whose accepted proposals can be deterministically
  rechecked by the Brain-owned built-in verifiers; bounded filesystem effects are
  admitted only when their exact effect root is retained and every recorded file
  receipt is independently re-read byte-for-byte;
- exact-scope executable-skill candidates recomputed from already authenticated
  source episodes;
- PROVEN_SUPERSET planning-scope claims only for STRUCTURAL_MATCH_V1 when every
  source episode was independently proved non-effectful, the candidate is exact
  re-induction, and its program is structurally closed. Reuse still passes the
  runtime structural guard and fresh V12 execution verification.

Effectful episodes are never replayed. The currently owned filesystem-effect
class is verified by independent post-execution readback from the retained effect
root. V12 BOUND_CAPABILITY_EXECUTION_V1 carrier rows are admitted only when the
stored accepted inner execution can be independently recomputed by the Brain-owned
bound verifier without invoking the capability again. Any other effect without
an independent readback/recomputation path remains fail-closed.

No terminal, capability, ownership, or execution authority is granted here.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime import r3_bound_success_checkpoint_verifier_v1 as bound_success_verifier
from canonical.runtime import r3_raw_success_checkpoint_verifier_v1 as raw_success_verifier
from canonical.runtime import universal_verified_adaptive_solver_v4 as v4
from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime.resolved_capability_semantics_authenticator_v1 import (
    authenticate as authenticate_resolved_semantics,
)
from canonical.runtime.universal_verified_effect_executor_v1 import (
    ALLOWED_TOOL_IDS as VERIFIED_EFFECT_TOOL_IDS,
    EXECUTOR_ID as VERIFIED_EFFECT_EXECUTOR_ID,
)
from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    git_blob_id,
    resolve_receipt_bytes,
)
from canonical.runtime.executable_skill_program_v7 import (
    candidate_digest,
    induce_candidate,
    normalize_steps,
    program_digest,
)
from canonical.runtime.executable_skill_verification_authenticator_v1 import (
    RECEIPT_SCHEMA as SKILL_RECEIPT_SCHEMA,
    VERIFY_SCHEMA as SKILL_VERIFY_SCHEMA,
)
from canonical.runtime.universal_solver_episode_verification_authenticator_v1 import (
    RECEIPT_SCHEMA as EPISODE_RECEIPT_SCHEMA,
    VERIFY_SCHEMA as EPISODE_VERIFY_SCHEMA,
    reauthenticate_record as reauthenticate_episode_record,
)
from canonical.runtime.universal_solver_state_capsule_v1 import (
    append_verified_transition as append_fact_transition,
    initialize as initialize_fact_capsule,
    verify_targets as verify_fact_targets,
)
from canonical.runtime.universal_solver_value_state_v1 import (
    append_verified_transition as append_value_transition,
    initialize as initialize_value_capsule,
)

SCHEMA = "PROJECT_BRAIN_R3_INDEPENDENT_LEARNING_VERIFIER_V1"
INDEPENDENT_VERIFIER_ID = "R3_INDEPENDENT_EVIDENCE_RECOMPUTATION_V1"
DEFAULT_RECEIPT_DIR = "canonical/runtime/r3_learning_verification_receipts"
STRUCTURAL_MATCH_SCOPE_PREDICATE = "STRUCTURAL_MATCH_V1"
NON_EFFECTFUL_VERIFICATION_BASIS = "SEPARATE_R3_EVIDENCE_RECOMPUTATION_WORKER"
EFFECTFUL_READBACK_VERIFICATION_BASIS = (
    "SEPARATE_R3_EVIDENCE_RECOMPUTATION_PLUS_EFFECT_READBACK_V1"
)
BOUND_CARRIER_VERIFICATION_BASIS = (
    "SEPARATE_R3_BOUND_CARRIER_ACCEPTED_EXECUTION_RECOMPUTATION_V1"
)


class R3IndependentVerificationError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _write_json(
    document: Mapping[str, Any],
    *,
    repo_root: str | Path,
    relative_path: str,
) -> dict[str, str]:
    root = Path(repo_root).resolve(strict=True)
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise R3IndependentVerificationError("RECEIPT_PATH_ESCAPES_REPOSITORY") from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = _canon(dict(document)).encode("utf-8")
    if target.exists():
        existing = target.read_bytes()
        if existing != raw:
            raise R3IndependentVerificationError(
                "DETERMINISTIC_RECEIPT_PATH_CONTENT_MISMATCH:" + relative_path
            )
    else:
        target.write_bytes(raw)
    return {
        "path": relative_path,
        "git_blob_sha": git_blob_id(raw, object_format="sha1"),
    }


def _emit_pair(
    *,
    stem: str,
    receipt: Mapping[str, Any],
    verification_core: Mapping[str, Any],
    repo_root: str | Path,
    receipt_dir: str = DEFAULT_RECEIPT_DIR,
) -> dict[str, Any]:
    token = _sha({"receipt": receipt, "verification_core": verification_core})
    base = receipt_dir.strip("/").replace("\\", "/")
    receipt_path = f"{base}/{stem}_{token}.receipt.json"
    receipt_ref = _write_json(receipt, repo_root=repo_root, relative_path=receipt_path)
    verification = {
        **dict(verification_core),
        "subject_git_blob_sha": receipt_ref["git_blob_sha"],
    }
    verification_path = f"{base}/{stem}_{token}.verification.json"
    verification_ref = _write_json(
        verification,
        repo_root=repo_root,
        relative_path=verification_path,
    )
    return {
        "receipt": receipt_ref,
        "verification": verification_ref,
        "independent_verifier_id": INDEPENDENT_VERIFIER_ID,
        "terminal_authority": False,
    }


def _caps(problem: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = problem.get("capabilities")
    if not isinstance(raw, list) or not raw:
        raise R3IndependentVerificationError("CAPABILITIES_REQUIRED")
    out: dict[str, Mapping[str, Any]] = {}
    for row in raw:
        if not isinstance(row, Mapping):
            raise R3IndependentVerificationError("CAPABILITY_NOT_OBJECT")
        cid = str(row.get("id") or "").strip()
        if not cid or cid in out:
            raise R3IndependentVerificationError("CAPABILITY_ID_INVALID_OR_DUPLICATE")
        out[cid] = row
    return out


def _active_action(
    cap: Mapping[str, Any],
    row: Mapping[str, Any],
) -> Mapping[str, Any]:
    resolved = row.get("resolved_action")
    action = resolved if isinstance(resolved, Mapping) else cap.get("action")
    if not isinstance(action, Mapping):
        raise R3IndependentVerificationError("ACTION_INVALID")
    return action


def _contains_effect_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        if "$effect_result" in value:
            return True
        return any(_contains_effect_ref(x) for x in value.values())
    if isinstance(value, list):
        return any(_contains_effect_ref(x) for x in value)
    return False


def _needs_resolved_semantics(cap: Mapping[str, Any]) -> bool:
    fields = cap.get("result_fields")
    return (
        isinstance(fields, list)
        and bool(fields)
    ) or _contains_effect_ref(cap.get("action"))


def _safe_effect_rel(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise R3IndependentVerificationError(label + "_INVALID")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise R3IndependentVerificationError(label + "_NOT_CANONICAL")
    return path.as_posix()


def _reverify_effect_outcome(
    *,
    cap: Mapping[str, Any],
    row: Mapping[str, Any],
    action: Mapping[str, Any],
    effect_root: str | Path | None,
) -> None:
    if effect_root is None or not str(effect_root).strip():
        raise R3IndependentVerificationError(
            "EFFECTFUL_EPISODE_REQUIRES_INDEPENDENT_READBACK_ROOT"
        )
    if action.get("type") != "verified_effect_tool":
        raise R3IndependentVerificationError("EFFECT_OUTCOME_ON_NON_EFFECT_ACTION")

    outcome = row.get("effect_outcome")
    digest = row.get("effect_outcome_sha256")
    if not isinstance(outcome, Mapping) or not isinstance(digest, str):
        raise R3IndependentVerificationError("EFFECT_OUTCOME_BINDING_MISSING")
    if set(outcome) != {
        "executor_id",
        "tool_id",
        "sandbox_rel",
        "receipts",
        "pack_git_blob_sha",
        "prior_verification",
    }:
        raise R3IndependentVerificationError("EFFECT_OUTCOME_FIELDS_INVALID")
    if _sha(dict(outcome)) != digest:
        raise R3IndependentVerificationError("EFFECT_OUTCOME_DIGEST_MISMATCH")

    executor_payload = action.get("executor_payload")
    if not isinstance(executor_payload, Mapping):
        raise R3IndependentVerificationError("EFFECT_EXECUTOR_PAYLOAD_INVALID")
    if set(executor_payload) != {"tool_id", "sandbox_rel"}:
        raise R3IndependentVerificationError("EFFECT_EXECUTOR_PAYLOAD_FIELDS_INVALID")
    if action.get("executor_id") != VERIFIED_EFFECT_EXECUTOR_ID:
        raise R3IndependentVerificationError("EFFECT_EXECUTOR_ID_NOT_ADMITTED")
    if outcome.get("executor_id") != VERIFIED_EFFECT_EXECUTOR_ID:
        raise R3IndependentVerificationError("EFFECT_OUTCOME_EXECUTOR_ID_MISMATCH")

    tool_id = str(executor_payload.get("tool_id") or "")
    if tool_id not in VERIFIED_EFFECT_TOOL_IDS or outcome.get("tool_id") != tool_id:
        raise R3IndependentVerificationError("EFFECT_TOOL_ID_MISMATCH")
    sandbox_rel = _safe_effect_rel(
        executor_payload.get("sandbox_rel"),
        "EFFECT_SANDBOX_REL",
    )
    if outcome.get("sandbox_rel") != sandbox_rel:
        raise R3IndependentVerificationError("EFFECT_SANDBOX_REL_MISMATCH")

    root_raw = Path(effect_root)
    if not root_raw.exists() or root_raw.is_symlink():
        raise R3IndependentVerificationError("EFFECT_ROOT_NOT_STABLE_DIRECTORY")
    root = root_raw.resolve(strict=True)
    if not root.is_dir():
        raise R3IndependentVerificationError("EFFECT_ROOT_NOT_DIRECTORY")
    if row.get("effect_root_sha256") != v1._digest(str(root)):
        raise R3IndependentVerificationError("EFFECT_ROOT_BINDING_MISMATCH")
    sandbox = (root / Path(*PurePosixPath(sandbox_rel).parts)).resolve(strict=True)
    try:
        sandbox.relative_to(root)
    except ValueError as exc:
        raise R3IndependentVerificationError("EFFECT_SANDBOX_ESCAPES_ROOT") from exc
    if not sandbox.is_dir():
        raise R3IndependentVerificationError("EFFECT_SANDBOX_NOT_DIRECTORY")

    receipts = outcome.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        raise R3IndependentVerificationError("EFFECT_RECEIPTS_MISSING")
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, Mapping) or set(receipt) != {
            "op",
            "path",
            "sha256",
            "bytes",
        }:
            raise R3IndependentVerificationError(
                "EFFECT_RECEIPT_FIELDS_INVALID:" + str(index)
            )
        if receipt.get("op") not in {"WRITE_JSON", "APPEND_JSONL", "RETURN_SHA256"}:
            raise R3IndependentVerificationError(
                "EFFECT_RECEIPT_OP_INVALID:" + str(index)
            )
        rel = _safe_effect_rel(receipt.get("path"), "EFFECT_RECEIPT_PATH")
        expected_sha = receipt.get("sha256")
        expected_bytes = receipt.get("bytes")
        if (
            not isinstance(expected_sha, str)
            or len(expected_sha) != 64
            or not all(ch in "0123456789abcdef" for ch in expected_sha)
        ):
            raise R3IndependentVerificationError(
                "EFFECT_RECEIPT_SHA256_INVALID:" + str(index)
            )
        if (
            isinstance(expected_bytes, bool)
            or not isinstance(expected_bytes, int)
            or expected_bytes < 0
        ):
            raise R3IndependentVerificationError(
                "EFFECT_RECEIPT_BYTES_INVALID:" + str(index)
            )
        target = (sandbox / Path(*PurePosixPath(rel).parts)).resolve(strict=True)
        try:
            target.relative_to(sandbox)
        except ValueError as exc:
            raise R3IndependentVerificationError(
                "EFFECT_RECEIPT_TARGET_ESCAPES_SANDBOX"
            ) from exc
        if not target.is_file():
            raise R3IndependentVerificationError(
                "EFFECT_RECEIPT_TARGET_NOT_FILE:" + rel
            )
        raw = target.read_bytes()
        if len(raw) != expected_bytes or sha256(raw).hexdigest() != expected_sha:
            raise R3IndependentVerificationError(
                "EFFECT_RECEIPT_READBACK_MISMATCH:" + rel
            )


def _reverify_non_effectful_trace(
    *,
    problem: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    fact_capsule_head_hash: str,
    value_capsule_head_hash: str,
    repo_root: str | Path,
    effect_root: str | Path | None = None,
) -> dict[str, Any]:
    caps = _caps(problem)
    fact_capsule = initialize_fact_capsule(problem)
    value_capsule = initialize_value_capsule(problem)
    expected_steps: list[dict[str, Any]] = []
    current_facts = sorted(str(x) for x in problem.get("initial_facts", []))
    effectful_trace = False
    bound_carrier_effectful_trace = False

    for expected_cycle, raw_row in enumerate(trace):
        if not isinstance(raw_row, Mapping):
            raise R3IndependentVerificationError("TRACE_ROW_NOT_OBJECT")
        row = dict(raw_row)
        if row.get("cycle") != expected_cycle:
            raise R3IndependentVerificationError("TRACE_CYCLE_NONCANONICAL")
        cid = str(row.get("capability_id") or "").strip()
        cap = caps.get(cid)
        if cap is None:
            raise R3IndependentVerificationError("TRACE_CAPABILITY_UNKNOWN:" + cid)

        replanning_problem = deepcopy(dict(problem))
        replanning_problem["initial_facts"] = list(current_facts)
        try:
            planned = plan_capabilities(replanning_problem)
        except PlanningFailure as exc:
            raise R3IndependentVerificationError(
                "PLANNER_RECOMPUTATION_FAILED:" + str(exc)
            ) from exc
        plan = planned.get("plan")
        if not isinstance(plan, list) or not plan or str(plan[0]) != cid:
            raise R3IndependentVerificationError(
                "TRACE_NOT_STRAIGHT_THROUGH_DETERMINISTIC_PLAN:" + cid
            )

        action = _active_action(cap, row)
        if v1._digest(action) != row.get("action_contract_sha256"):
            raise R3IndependentVerificationError("ACTION_CONTRACT_DIGEST_MISMATCH:" + cid)
        action_type = str(action.get("type") or "")
        has_effect_outcome = bool(row.get("effect_outcome_sha256"))
        bound_carrier_effect = False
        if action_type == "verified_effect_tool":
            if not has_effect_outcome:
                raise R3IndependentVerificationError(
                    "EFFECTFUL_ACTION_MISSING_VERIFIED_OUTCOME"
                )
            _reverify_effect_outcome(
                cap=cap,
                row=row,
                action=action,
                effect_root=effect_root,
            )
            effectful_trace = True
        elif has_effect_outcome:
            bound_carrier_effect = (
                row.get("bound_capability_carrier_authenticated") is True
                and str(action.get("verifier_id") or "").strip()
                    == "BOUND_CAPABILITY_EXECUTION_V1"
            )
            if not bound_carrier_effect:
                raise R3IndependentVerificationError(
                    "EFFECT_OUTCOME_ON_NON_EFFECT_ACTION"
                )
        elif row.get("bound_capability_carrier_authenticated") is True:
            raise R3IndependentVerificationError(
                "BOUND_CARRIER_AUTHENTICATION_WITHOUT_EFFECT_OUTCOME"
            )

        pair = {
            "receipt": row.get("effect_semantics_receipt"),
            "verification": row.get("effect_semantics_verification"),
        }
        if _needs_resolved_semantics(cap):
            if row.get("value_capsule_head_before") != value_capsule.get("head_hash"):
                raise R3IndependentVerificationError(
                    "VALUE_CAPSULE_HEAD_BEFORE_MISMATCH:" + cid
                )
            semantics = authenticate_resolved_semantics(
                problem,
                cap,
                action,
                value_capsule,
                pair,
                repo_root=repo_root,
            )
            if semantics.get("pass") is not True:
                raise R3IndependentVerificationError(
                    "RESOLVED_EFFECT_SEMANTICS_REAUTHENTICATION_FAILED:" + cid
                )
        else:
            semantics = v4._authenticate_effect_semantics(
                problem,
                cap,
                repo_root=repo_root,
            )
        if semantics.get("receipt") != pair["receipt"]:
            raise R3IndependentVerificationError(
                "EFFECT_SEMANTICS_RECEIPT_REF_MISMATCH:" + cid
            )
        if semantics.get("verification") != pair["verification"]:
            raise R3IndependentVerificationError(
                "EFFECT_SEMANTICS_VERIFICATION_REF_MISMATCH:" + cid
            )
        if row.get("effect_semantics_authenticated") is not True:
            raise R3IndependentVerificationError(
                "EFFECT_SEMANTICS_AUTHENTICATED_FLAG_MISSING:" + cid
            )
        if (
            str(row.get("independent_effect_semantics_verifier_id") or "")
            != str(semantics.get("independent_verifier_id") or "")
        ):
            raise R3IndependentVerificationError(
                "EFFECT_SEMANTICS_VERIFIER_ID_MISMATCH:" + cid
            )
        if (
            row.get("verifier_success_condition")
            != semantics.get("verifier_success_condition")
        ):
            raise R3IndependentVerificationError(
                "VERIFIER_SUCCESS_CONDITION_REAUTHENTICATION_MISMATCH:" + cid
            )

        verifier_id = str(
            action.get("pre_verifier_id")
            if action_type == "verified_effect_tool"
            else action.get("verifier_id")
            or ""
        ).strip()
        if verifier_id != str(row.get("verifier_id") or "").strip():
            raise R3IndependentVerificationError("VERIFIER_ID_MISMATCH:" + cid)
        verifier = v1.BUILTIN_VERIFIERS.get(verifier_id)
        if verifier is None:
            raise R3IndependentVerificationError("VERIFIER_NOT_BRAIN_OWNED:" + verifier_id)
        payload = (
            action.get("pre_verifier_payload")
            if action_type == "verified_effect_tool"
            else action.get("verifier_payload")
        )
        proposal = row.get("accepted_proposal")
        if not isinstance(payload, Mapping):
            raise R3IndependentVerificationError("VERIFIER_PAYLOAD_INVALID:" + cid)
        if not isinstance(proposal, Mapping):
            raise R3IndependentVerificationError("ACCEPTED_PROPOSAL_MISSING:" + cid)
        if v1._digest(proposal) != row.get("proposal_sha256"):
            raise R3IndependentVerificationError("PROPOSAL_DIGEST_MISMATCH:" + cid)

        verdict = verifier(deepcopy(dict(payload)), deepcopy(dict(proposal)))
        if not isinstance(verdict, Mapping) or verdict.get("pass") is not True:
            raise R3IndependentVerificationError("VERIFIER_REEXECUTION_FAILED:" + cid)
        if verdict.get("proof_digest") != row.get("proof_digest"):
            raise R3IndependentVerificationError("VERIFIER_PROOF_DIGEST_MISMATCH:" + cid)
        if _canon(verdict.get("verified_output")) != _canon(row.get("verified_output")):
            raise R3IndependentVerificationError("VERIFIED_OUTPUT_MISMATCH:" + cid)

        if bound_carrier_effect:
            effect_outcome = row.get("effect_outcome")
            execution = proposal.get("execution")
            if not isinstance(effect_outcome, Mapping):
                raise R3IndependentVerificationError(
                    "BOUND_CARRIER_EFFECT_OUTCOME_INVALID:" + cid
                )
            if not isinstance(execution, Mapping):
                raise R3IndependentVerificationError(
                    "BOUND_CARRIER_ACCEPTED_EXECUTION_MISSING:" + cid
                )
            inner_trace = execution.get("trace")
            if (
                not isinstance(inner_trace, Sequence)
                or isinstance(inner_trace, (str, bytes))
                or not inner_trace
            ):
                raise R3IndependentVerificationError(
                    "BOUND_CARRIER_INNER_TRACE_INVALID:" + cid
                )
            expected_outcome = {
                "carrier_schema": "PROJECT_BRAIN_UNIVERSAL_BOUND_CAPABILITY_CARRIER_V1",
                "execution_verification": deepcopy(dict(verdict)),
                "inner_execution_sha256": v1._digest(execution),
                "executed_nonfinish_action_count": max(len(inner_trace) - 1, 0),
            }
            if _canon(effect_outcome) != _canon(expected_outcome):
                raise R3IndependentVerificationError(
                    "BOUND_CARRIER_EFFECT_OUTCOME_RECOMPUTATION_MISMATCH:" + cid
                )
            if row.get("effect_outcome_sha256") != v1._digest(expected_outcome):
                raise R3IndependentVerificationError(
                    "BOUND_CARRIER_EFFECT_OUTCOME_DIGEST_MISMATCH:" + cid
                )
            effectful_trace = True
            bound_carrier_effectful_trace = True

        provides = sorted(str(x) for x in cap.get("provides", []))
        semantic_effects = sorted(
            str(x)
            for x in (
                semantics.get("provided_effects")
                or semantics.get("effects")
                or []
            )
        )
        observed = sorted(str(x) for x in row.get("new_verified_facts", []))
        if not provides or observed != provides or semantic_effects != provides:
            raise R3IndependentVerificationError("VERIFIED_EFFECT_SET_MISMATCH:" + cid)

        fact_capsule = append_fact_transition(
            fact_capsule,
            capability=cap,
            trace_row=row,
        )
        value_capsule = append_value_transition(
            value_capsule,
            capability=cap,
            trace_row=row,
        )
        if (
            row.get("value_capsule_head_after") is not None
            and row.get("value_capsule_head_after") != value_capsule.get("head_hash")
        ):
            raise R3IndependentVerificationError(
                "VALUE_CAPSULE_HEAD_AFTER_MISMATCH:" + cid
            )
        current_facts = sorted(set(current_facts) | set(provides))
        expected_steps.append({
            "op": cid,
            "inputs": sorted(str(x) for x in cap.get("requires", [])),
            "outputs": provides,
        })

    if fact_capsule.get("head_hash") != fact_capsule_head_hash:
        raise R3IndependentVerificationError("FACT_CAPSULE_HEAD_MISMATCH")
    if value_capsule.get("head_hash") != value_capsule_head_hash:
        raise R3IndependentVerificationError("VALUE_CAPSULE_HEAD_MISMATCH")
    target_verdict = verify_fact_targets(
        fact_capsule,
        problem.get("target_effects", []),
    )
    if target_verdict.get("pass") is not True:
        raise R3IndependentVerificationError("TARGET_FACT_LINEAGE_REVERIFICATION_FAILED")
    return {
        "steps": expected_steps,
        "fact_capsule_head_hash": fact_capsule.get("head_hash"),
        "value_capsule_head_hash": value_capsule.get("head_hash"),
        "target_verdict": target_verdict,
        "effectful_trace": effectful_trace,
        "effect_outcomes_reverified": effectful_trace,
        "bound_carrier_effectful_trace": bound_carrier_effectful_trace,
    }


def verify_episode_request(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path,
    receipt_dir: str = DEFAULT_RECEIPT_DIR,
) -> Mapping[str, Any] | None:
    """Return an authenticator-compatible binding only after independent recomputation."""
    try:
        if not isinstance(request, Mapping) or request.get("kind") != "EPISODE_VERIFICATION":
            return None
        problem = request.get("problem")
        episode = request.get("episode")
        trace = request.get("trace")
        if not isinstance(problem, Mapping) or not isinstance(episode, Mapping):
            raise R3IndependentVerificationError("EPISODE_REQUEST_MATERIAL_INVALID")
        if not isinstance(trace, Sequence) or isinstance(trace, (str, bytes)):
            raise R3IndependentVerificationError("EPISODE_TRACE_INVALID")
        fact_head = str(request.get("fact_capsule_head_hash") or "")
        value_head = str(request.get("value_capsule_head_hash") or "")
        if len(fact_head) != 64 or len(value_head) != 64:
            raise R3IndependentVerificationError("EPISODE_CAPSULE_HEAD_INVALID")

        if problem.get("verification_kind") == raw_success_verifier.VERIFICATION_KIND:
            verdict = raw_success_verifier.verify_material(
                problem=problem,
                episode=episode,
                trace=trace,
                fact_capsule_head_hash=fact_head,
                value_capsule_head_hash=value_head,
                repo_root=repo_root,
            )
            if verdict.get("pass") is not True:
                raise R3IndependentVerificationError(
                    "RAW_ACCEPTED_SUCCESS_READBACK_VERIFICATION_FAILED:"
                    + str(verdict.get("reason") or verdict.get("status") or "")
                )
            bindings = {
                "problem_sha256": v1._digest(problem),
                "episode_id": episode.get("episode_id"),
                "scope_id": episode.get("scope_id"),
                "program_sha256": episode.get("program_sha256"),
                "trace_sha256": _sha(list(trace)),
                "fact_capsule_head_hash": fact_head,
                "value_capsule_head_hash": value_head,
            }
            if any(not isinstance(v, str) or not v for v in bindings.values()):
                raise R3IndependentVerificationError("EPISODE_BINDING_FIELD_INVALID")
            receipt = {
                "schema": EPISODE_RECEIPT_SCHEMA,
                **bindings,
                "pass": True,
                "conclusion": "success",
                "behavior_verified": True,
                "exact_byte_bound": True,
                "verification_basis": verdict.get("verification_basis"),
            }
            verification = {
                "schema": EPISODE_VERIFY_SCHEMA,
                **bindings,
                "pass": True,
                "independent_verified": True,
                "behavior_verified": True,
                "exact_byte_bound": True,
                "trace_reverified": True,
                "state_lineage_reverified": True,
                "effect_outcomes_reverified": True,
                "non_effectful_trace": False,
                "independent_verifier_id": INDEPENDENT_VERIFIER_ID,
                "verification_basis": verdict.get("verification_basis"),
            }
            return _emit_pair(
                stem="episode-raw-accepted-success",
                receipt=receipt,
                verification_core=verification,
                repo_root=repo_root,
                receipt_dir=receipt_dir,
            )

        if problem.get("verification_kind") == bound_success_verifier.VERIFICATION_KIND:
            verdict = bound_success_verifier.verify_material(
                problem=problem,
                episode=episode,
                trace=trace,
                fact_capsule_head_hash=fact_head,
                value_capsule_head_hash=value_head,
                repo_root=repo_root,
            )
            if verdict.get("pass") is not True:
                raise R3IndependentVerificationError(
                    "BOUND_SUCCESS_READBACK_VERIFICATION_FAILED:"
                    + str(verdict.get("reason") or verdict.get("status") or "")
                )
            bindings = {
                "problem_sha256": v1._digest(problem),
                "episode_id": episode.get("episode_id"),
                "scope_id": episode.get("scope_id"),
                "program_sha256": episode.get("program_sha256"),
                "trace_sha256": _sha(list(trace)),
                "fact_capsule_head_hash": fact_head,
                "value_capsule_head_hash": value_head,
            }
            if any(not isinstance(v, str) or not v for v in bindings.values()):
                raise R3IndependentVerificationError("EPISODE_BINDING_FIELD_INVALID")
            receipt = {
                "schema": EPISODE_RECEIPT_SCHEMA,
                **bindings,
                "pass": True,
                "conclusion": "success",
                "behavior_verified": True,
                "exact_byte_bound": True,
                "verification_basis": verdict.get("verification_basis"),
            }
            verification = {
                "schema": EPISODE_VERIFY_SCHEMA,
                **bindings,
                "pass": True,
                "independent_verified": True,
                "behavior_verified": True,
                "exact_byte_bound": True,
                "trace_reverified": True,
                "state_lineage_reverified": True,
                "effect_outcomes_reverified": True,
                "non_effectful_trace": False,
                "independent_verifier_id": INDEPENDENT_VERIFIER_ID,
                "verification_basis": verdict.get("verification_basis"),
            }
            return _emit_pair(
                stem="episode-bound-success",
                receipt=receipt,
                verification_core=verification,
                repo_root=repo_root,
                receipt_dir=receipt_dir,
            )

        recomputed = _reverify_non_effectful_trace(
            problem=problem,
            trace=trace,
            fact_capsule_head_hash=fact_head,
            value_capsule_head_hash=value_head,
            repo_root=repo_root,
            effect_root=request.get("effect_root"),
        )
        expected_pre = sorted(str(x) for x in problem.get("initial_facts", []))
        expected_post = sorted(str(x) for x in problem.get("target_effects", []))
        if normalize_steps(episode.get("steps")) != normalize_steps(recomputed["steps"]):
            raise R3IndependentVerificationError("EPISODE_STEPS_MISMATCH")
        if sorted(str(x) for x in episode.get("preconditions", [])) != expected_pre:
            raise R3IndependentVerificationError("EPISODE_PRECONDITIONS_MISMATCH")
        if sorted(str(x) for x in episode.get("postconditions", [])) != expected_post:
            raise R3IndependentVerificationError("EPISODE_POSTCONDITIONS_MISMATCH")
        invalidators = sorted(str(x) for x in episode.get("invalidators", []))
        if invalidators:
            raise R3IndependentVerificationError(
                "NONEMPTY_INVALIDATORS_REQUIRE_INDEPENDENT_ROUTE_FAILURE_REPLAY"
            )
        expected_program = program_digest(
            steps=recomputed["steps"],
            preconditions=expected_pre,
            postconditions=expected_post,
            invalidators=invalidators,
        )
        if episode.get("program_sha256") != expected_program:
            raise R3IndependentVerificationError("EPISODE_PROGRAM_DIGEST_MISMATCH")

        bindings = {
            "problem_sha256": v1._digest(problem),
            "episode_id": episode.get("episode_id"),
            "scope_id": episode.get("scope_id"),
            "program_sha256": episode.get("program_sha256"),
            "trace_sha256": _sha(list(trace)),
            "fact_capsule_head_hash": fact_head,
            "value_capsule_head_hash": value_head,
        }
        if any(not isinstance(v, str) or not v for v in bindings.values()):
            raise R3IndependentVerificationError("EPISODE_BINDING_FIELD_INVALID")
        receipt = {
            "schema": EPISODE_RECEIPT_SCHEMA,
            **bindings,
            "pass": True,
            "conclusion": "success",
            "behavior_verified": True,
            "exact_byte_bound": True,
            "verification_basis": (
                BOUND_CARRIER_VERIFICATION_BASIS
                if recomputed.get("bound_carrier_effectful_trace")
                else EFFECTFUL_READBACK_VERIFICATION_BASIS
                if recomputed["effectful_trace"]
                else "DETERMINISTIC_ACCEPTED_PROPOSAL_REEXECUTION_AND_CAPSULE_REBUILD"
            ),
        }
        verification = {
            "schema": EPISODE_VERIFY_SCHEMA,
            **bindings,
            "pass": True,
            "independent_verified": True,
            "behavior_verified": True,
            "exact_byte_bound": True,
            "trace_reverified": True,
            "state_lineage_reverified": True,
            "effect_outcomes_reverified": bool(
                recomputed["effect_outcomes_reverified"]
            ),
            "non_effectful_trace": not bool(recomputed["effectful_trace"]),
            "independent_verifier_id": INDEPENDENT_VERIFIER_ID,
            "bound_carrier_effectful_trace": bool(
                recomputed.get("bound_carrier_effectful_trace")
            ),
            "verification_basis": (
                BOUND_CARRIER_VERIFICATION_BASIS
                if recomputed.get("bound_carrier_effectful_trace")
                else EFFECTFUL_READBACK_VERIFICATION_BASIS
                if recomputed["effectful_trace"]
                else NON_EFFECTFUL_VERIFICATION_BASIS
            ),
        }
        return _emit_pair(
            stem="episode",
            receipt=receipt,
            verification_core=verification,
            repo_root=repo_root,
            receipt_dir=receipt_dir,
        )
    except Exception:
        return None


def _load_state(path: str | Path) -> Mapping[str, Any]:
    p = Path(path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise R3IndependentVerificationError("SELF_IMPROVEMENT_STATE_INVALID")
    return doc


def _candidate_core(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_episode_ids": sorted(str(x) for x in candidate.get("source_episode_ids", [])),
        "source_episode_receipts": sorted(
            str(x) for x in candidate.get("source_episode_receipts", [])
        ),
        "source_scopes": sorted(str(x) for x in candidate.get("source_scopes", [])),
        "steps": normalize_steps(candidate.get("steps")),
        "preconditions": sorted(str(x) for x in candidate.get("preconditions", [])),
        "postconditions": sorted(str(x) for x in candidate.get("postconditions", [])),
        "invalidators": sorted(str(x) for x in candidate.get("invalidators", [])),
        "candidate_sha256": candidate.get("candidate_sha256"),
    }


def _assert_structurally_closed_candidate(candidate: Mapping[str, Any]) -> None:
    steps = normalize_steps(candidate.get("steps"))
    available = set(str(x) for x in candidate.get("preconditions", []))
    seen: set[str] = set()
    for step in steps:
        op = str(step.get("op") or "").strip()
        if not op or op in seen:
            raise R3IndependentVerificationError("STRUCTURAL_MATCH_OPERATION_INVALID_OR_REPEATED")
        required = set(str(x) for x in step.get("inputs", []))
        provided = set(str(x) for x in step.get("outputs", []))
        if not required.issubset(available):
            raise R3IndependentVerificationError("STRUCTURAL_MATCH_INPUT_NOT_DERIVABLE:" + op)
        if not provided:
            raise R3IndependentVerificationError("STRUCTURAL_MATCH_OUTPUT_REQUIRED:" + op)
        available.update(provided)
        seen.add(op)
    targets = set(str(x) for x in candidate.get("postconditions", []))
    if not targets or not targets.issubset(available):
        raise R3IndependentVerificationError("STRUCTURAL_MATCH_POSTCONDITION_NOT_DERIVABLE")


def _assert_non_effectful_source_proof(
    record: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> None:
    binding = record.get("verification_binding")
    if not isinstance(binding, Mapping):
        raise R3IndependentVerificationError("GENERALIZATION_SOURCE_BINDING_MISSING")
    resolved = resolve_receipt_bytes(binding.get("verification"), repo_root=repo_root)
    document = resolved.get("document")
    if not isinstance(document, Mapping):
        raise R3IndependentVerificationError("GENERALIZATION_SOURCE_VERIFICATION_INVALID")
    if document.get("independent_verifier_id") != INDEPENDENT_VERIFIER_ID:
        raise R3IndependentVerificationError("GENERALIZATION_SOURCE_VERIFIER_NOT_ADMITTED")
    if document.get("verification_basis") != NON_EFFECTFUL_VERIFICATION_BASIS:
        raise R3IndependentVerificationError("GENERALIZATION_SOURCE_BASIS_NOT_ADMITTED")
    if document.get("non_effectful_trace") is not True:
        raise R3IndependentVerificationError("GENERALIZATION_SOURCE_NOT_PROVED_NON_EFFECTFUL")


def verify_skill_request(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path,
    state_path: str | Path,
    receipt_dir: str = DEFAULT_RECEIPT_DIR,
) -> Mapping[str, Any] | None:
    """Verify exact candidates and narrowly proved non-effectful structural supersets."""
    try:
        if not isinstance(request, Mapping):
            return None
        kind = request.get("kind")
        if kind not in {
            "SKILL_VERIFICATION",
            "SKILL_SCOPE_GENERALIZATION_VERIFICATION",
        }:
            return None
        generalization = kind == "SKILL_SCOPE_GENERALIZATION_VERIFICATION"
        candidate = request.get("candidate")
        if not isinstance(candidate, Mapping) or candidate.get("candidate_only") is not True:
            raise R3IndependentVerificationError("SKILL_CANDIDATE_INVALID")
        source_ids = sorted(str(x) for x in candidate.get("source_episode_ids", []) if str(x))
        if len(source_ids) < 2 or len(source_ids) != len(set(source_ids)):
            raise R3IndependentVerificationError("SKILL_SOURCE_EPISODES_INVALID")

        state = _load_state(state_path)
        rows = state.get("episodes", {})
        if not isinstance(rows, Mapping):
            raise R3IndependentVerificationError("EPISODE_STORE_INVALID")
        by_id: dict[str, Mapping[str, Any]] = {}
        for raw in rows.values():
            if not isinstance(raw, Mapping):
                continue
            eid = str(raw.get("episode_id") or "")
            if eid in source_ids:
                if eid in by_id:
                    raise R3IndependentVerificationError("SOURCE_EPISODE_ID_AMBIGUOUS:" + eid)
                by_id[eid] = raw
        if sorted(by_id) != source_ids:
            raise R3IndependentVerificationError("SOURCE_EPISODE_RECORD_MISSING")

        authenticated: list[Mapping[str, Any]] = []
        for eid in source_ids:
            verdict = reauthenticate_episode_record(by_id[eid], repo_root=repo_root)
            if verdict.get("pass") is not True:
                raise R3IndependentVerificationError(
                    "SOURCE_EPISODE_REAUTHENTICATION_FAILED:" + eid
                )
            authenticated.append(verdict["authenticated_episode"])

        expected = induce_candidate(authenticated)
        if _canon(_candidate_core(candidate)) != _canon(_candidate_core(expected)):
            raise R3IndependentVerificationError("SKILL_CANDIDATE_NOT_EXACT_REINDUCTION")
        expected_digest = candidate_digest(
            source_episode_ids=source_ids,
            steps=candidate.get("steps"),
            preconditions=candidate.get("preconditions", []),
            postconditions=candidate.get("postconditions", []),
            invalidators=candidate.get("invalidators", []),
        )
        if candidate.get("candidate_sha256") != expected_digest:
            raise R3IndependentVerificationError("SKILL_CANDIDATE_DIGEST_MISMATCH")

        relation = "EXACT"
        scope_predicate = None
        verification_basis = "EXACT_REINDUCTION_FROM_REAUTHENTICATED_SOURCE_EPISODES"
        if generalization:
            requested_relation = str(request.get("requested_scope_relation") or "")
            requested_predicate = str(request.get("requested_scope_predicate") or "")
            supported = {
                str(x)
                for x in request.get("supported_scope_predicates", [])
                if isinstance(x, str)
            }
            if requested_relation != "PROVEN_SUPERSET":
                raise R3IndependentVerificationError("GENERALIZATION_RELATION_NOT_ADMITTED")
            if (
                requested_predicate != STRUCTURAL_MATCH_SCOPE_PREDICATE
                or requested_predicate not in supported
            ):
                raise R3IndependentVerificationError("GENERALIZATION_PREDICATE_NOT_ADMITTED")
            for eid in source_ids:
                _assert_non_effectful_source_proof(by_id[eid], repo_root=repo_root)
            _assert_structurally_closed_candidate(candidate)
            relation = "PROVEN_SUPERSET"
            scope_predicate = STRUCTURAL_MATCH_SCOPE_PREDICATE
            verification_basis = (
                "EXACT_REINDUCTION_PLUS_NON_EFFECTFUL_SOURCE_PROOF_PLUS_"
                "STRUCTURAL_MATCH_RUNTIME_GUARD"
            )

        bindings = {
            "candidate_sha256": candidate.get("candidate_sha256"),
            "source_episode_ids": source_ids,
            "scope_relation": relation,
        }
        receipt = {
            "schema": SKILL_RECEIPT_SCHEMA,
            **bindings,
            "scope_predicate": scope_predicate,
            "pass": True,
            "conclusion": "success",
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
            "verification_basis": verification_basis,
            "scope_claim": (
                "STRUCTURAL_ROUTE_ONLY__EXECUTION_STILL_REVERIFIED"
                if generalization
                else "EXACT_OBSERVED_SOURCE_SCOPE"
            ),
        }
        verification = {
            "schema": SKILL_VERIFY_SCHEMA,
            **bindings,
            "scope_predicate": scope_predicate,
            "pass": True,
            "independent_verified": True,
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
            "candidate_reexecuted_or_equivalently_checked": True,
            "source_episode_lineage_reverified": True,
            "independent_verifier_id": INDEPENDENT_VERIFIER_ID,
            "verification_basis": verification_basis,
            "structural_match_runtime_guard_verified": bool(generalization),
            "non_effectful_source_proof_required": bool(generalization),
        }
        return _emit_pair(
            stem="skill",
            receipt=receipt,
            verification_core=verification,
            repo_root=repo_root,
            receipt_dir=receipt_dir,
        )
    except Exception:
        return None
