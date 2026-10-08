"""Independent evidence-recomputation worker for R3 learning promotion.

This module is deliberately separate from the learner and queue scheduler. It may
produce the content-addressed receipt pairs consumed by the existing episode and
skill authenticators, but only after independently recomputing evidence already
recorded by the solver.

Current admitted scope:
- non-effectful Universal Solver episodes whose accepted proposals can be
  deterministically rechecked by the Brain-owned built-in verifiers;
- exact-scope executable-skill candidates recomputed from already authenticated
  source episodes.

Effectful episodes are intentionally not replayed. Without an independently
re-readable effect root in the verification request, they remain fail-closed.
Likewise this worker never manufactures PROVEN_SUPERSET scope claims.

No terminal, capability, ownership, or execution authority is granted here.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime import universal_verified_adaptive_solver_v4 as v4
from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime.resolved_capability_semantics_authenticator_v1 import (
    authenticate as authenticate_resolved_semantics,
)
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
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


def _reverify_non_effectful_trace(
    *,
    problem: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    fact_capsule_head_hash: str,
    value_capsule_head_hash: str,
    repo_root: str | Path,
) -> dict[str, Any]:
    caps = _caps(problem)
    fact_capsule = initialize_fact_capsule(problem)
    value_capsule = initialize_value_capsule(problem)
    expected_steps: list[dict[str, Any]] = []
    current_facts = sorted(str(x) for x in problem.get("initial_facts", []))

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

        # Recompute the unexcluded planner frontier. If the recorded successful
        # step is not the first deterministic plan choice, some hidden failed or
        # deferred branch was omitted from the proof material.
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

        # Never replay or self-attest an effect. A future worker may admit an
        # effectful episode only when it can independently read back the effect.
        if row.get("effect_outcome_sha256"):
            raise R3IndependentVerificationError(
                "EFFECTFUL_EPISODE_REQUIRES_INDEPENDENT_READBACK_VERIFIER"
            )

        action = _active_action(cap, row)
        if v1._digest(action) != row.get("action_contract_sha256"):
            raise R3IndependentVerificationError("ACTION_CONTRACT_DIGEST_MISMATCH:" + cid)
        action_type = str(action.get("type") or "")
        if action_type == "verified_effect_tool":
            raise R3IndependentVerificationError(
                "EFFECTFUL_ACTION_REQUIRES_INDEPENDENT_READBACK_VERIFIER"
            )

        # Reauthenticate the semantic implication from verifier success to the
        # declared provided effects. Replaying the builtin verifier alone is not
        # enough: its output has no authority to mint arbitrary caller labels.
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

        verifier_id = str(action.get("verifier_id") or "").strip()
        if verifier_id != str(row.get("verifier_id") or "").strip():
            raise R3IndependentVerificationError("VERIFIER_ID_MISMATCH:" + cid)
        verifier = v1.BUILTIN_VERIFIERS.get(verifier_id)
        if verifier is None:
            raise R3IndependentVerificationError("VERIFIER_NOT_BRAIN_OWNED:" + verifier_id)
        payload = action.get("verifier_payload")
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

        recomputed = _reverify_non_effectful_trace(
            problem=problem,
            trace=trace,
            fact_capsule_head_hash=fact_head,
            value_capsule_head_hash=value_head,
            repo_root=repo_root,
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
        # The verifier independently recomputes the deterministic unexcluded
        # planner choice at every successful trace step. That proves this admitted
        # class is straight-through; therefore any claimed route invalidator is
        # outside the proof and must fail closed.
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
            "verification_basis": "DETERMINISTIC_ACCEPTED_PROPOSAL_REEXECUTION_AND_CAPSULE_REBUILD",
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
            "effect_outcomes_reverified": False,
            "independent_verifier_id": INDEPENDENT_VERIFIER_ID,
            "verification_basis": "SEPARATE_R3_EVIDENCE_RECOMPUTATION_WORKER",
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


def verify_skill_request(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path,
    state_path: str | Path,
    receipt_dir: str = DEFAULT_RECEIPT_DIR,
) -> Mapping[str, Any] | None:
    """Verify only exact observed-scope candidates from authenticated episodes."""
    try:
        if not isinstance(request, Mapping) or request.get("kind") != "SKILL_VERIFICATION":
            return None
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

        bindings = {
            "candidate_sha256": candidate.get("candidate_sha256"),
            "source_episode_ids": source_ids,
            "scope_relation": "EXACT",
        }
        receipt = {
            "schema": SKILL_RECEIPT_SCHEMA,
            **bindings,
            "scope_predicate": None,
            "pass": True,
            "conclusion": "success",
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
            "verification_basis": "EXACT_REINDUCTION_FROM_REAUTHENTICATED_SOURCE_EPISODES",
        }
        verification = {
            "schema": SKILL_VERIFY_SCHEMA,
            **bindings,
            "scope_predicate": None,
            "pass": True,
            "independent_verified": True,
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
            "candidate_reexecuted_or_equivalently_checked": True,
            "source_episode_lineage_reverified": True,
            "independent_verifier_id": INDEPENDENT_VERIFIER_ID,
            "verification_basis": "SEPARATE_R3_EXACT_SKILL_REINDUCTION_WORKER",
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
