"""Proof-carrying one-shot reality closure V2.

V2 does not claim universal semantics or universal capability construction.
It strengthens V1 by turning every open residual into one of two explicit,
machine-checkable contracts:

* CONSTRUCTIVE_CAPABILITY_GAP: must be handed to a synthesis/acquisition
  provider that changes the verified frontier without changing verifier authority.
* PENDING_ACQUISITION_OR_EXPERIMENT: missing information/experience that may
  still be obtained by search, simulation, experiment, or replay acquisition.
* PROVEN_INFORMATION_THEORETICALLY_EXTERNAL: terminal only after V1 validates
  an independently verified indistinguishability proof and exhausts all internal
  bypass classes. Current-state absence alone is never enough.

Provider success is never accepted on assertion alone. A provider must return
a content-addressed receipt and the next V1 pass must observe a frontier digest
change. The loop therefore converts "open residual" into "repair and re-run"
without allowing fake progress.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import one_shot_verified_closure_v1 as v1
from canonical.runtime import promote_r2_direct_route_v1 as r2_direct_route_promoter

SCHEMA = "PROJECT_BRAIN_ONE_SHOT_REALITY_CLOSURE_V2"
GAP_SCHEMA = "PROJECT_BRAIN_PROOF_CARRYING_GAP_CONTRACT_V1"
CONTEXT_GATE_SCHEMA = "PROJECT_BRAIN_CONTEXT_CAPACITY_REPAIR_GATE_V1"
SEMANTIC_WORK_SCHEMA = "PROJECT_BRAIN_CONSTRUCTIVE_SEMANTIC_WORK_CONTRACT_V1"
DECISION_SUFFICIENT_SCHEMA = "PROJECT_BRAIN_DECISION_SUFFICIENT_GAP_CONTRACT_V1"
MINIMUM_INFORMATION_SCHEMA = "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_CONTRACT_V1"

REQUIRED_ATTEMPT_ORDER = (
    "REUSE_EXISTING_CAPABILITY",
    "SEARCH_CANONICAL_BRAIN",
    "SEARCH_EXTERNAL_KNOWLEDGE",
    "DERIVE_OR_COMPOSE",
    "INVENT_MINIMUM_MISSING_MECHANISM",
    "CODE_MINIMUM_TRANSFORM_IF_NECESSARY",
    "EXECUTE",
    "VERIFY_WITH_UNCHANGED_AUTHORITY",
)

_HEX = set("0123456789abcdef")


class RealityClosureError(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _s(value: Any) -> str:
    return "" if value is None else str(value)


def _valid_sha256(value: Any) -> bool:
    text = _s(value).lower()
    return len(text) == 64 and all(ch in _HEX for ch in text)


def _positive_int(name: str, value: Any, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RealityClosureError(name + "_MUST_BE_INT")
    floor = 0 if allow_zero else 1
    if value < floor:
        raise RealityClosureError(name + "_OUT_OF_RANGE")
    return value


def _pending_semantic_work(*, state_path: Any = None) -> list[dict[str, Any]]:
    """Load the exact pending R3 work that made V1 stop.

    Durable R3 state is already JSON. V2 preserves the complete pending payload
    and content-addresses each work item before exposing it to synthesis.
    """
    resolved = state_path
    if resolved is None:
        learning = getattr(v1, "learning", None)
        resolved = getattr(learning, "DEFAULT_STATE_PATH", None)
    if resolved is None:
        return []
    target = Path(resolved)
    if not target.exists():
        return []
    state = json.loads(target.read_text(encoding="utf-8"))
    queue = state.get("improvement_queue", {})
    if not isinstance(queue, Mapping):
        return []

    out: list[dict[str, Any]] = []
    for wid, raw in queue.items():
        if not isinstance(raw, Mapping):
            continue
        if raw.get("status") not in {"PENDING", "PARKED"}:
            continue
        payload = raw.get("payload")
        payload = deepcopy(dict(payload)) if isinstance(payload, Mapping) else {}
        core = {
            "work_id": _s(wid),
            "kind": _s(raw.get("kind")),
            "status": _s(raw.get("status")),
            "observations": int(raw.get("observations", 0)),
            "last_attempt_observations": raw.get("last_attempt_observations"),
            "last_attempt_status": raw.get("last_attempt_status"),
            "last_attempt_reason": raw.get("last_attempt_reason"),
            "last_attempt_provider_id": raw.get("last_attempt_provider_id"),
            "last_attempt_frontier_sha256": raw.get("last_attempt_frontier_sha256"),
            "frontier_expansion_work_id": raw.get("frontier_expansion_work_id"),
            "verification_frontier_sha256": raw.get("verification_frontier_sha256"),
            "adapter_frontier_sha256": raw.get("adapter_frontier_sha256"),
            "verification_authority_sha256": raw.get("verification_authority_sha256"),
            "payload": payload,
        }
        out.append({
            "schema": SEMANTIC_WORK_SCHEMA,
            **core,
            "work_digest": _sha(core),
        })
    return sorted(out, key=lambda row: (row["kind"], row["work_id"]))


def _constructive_capability_contracts(
    pending_work: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Compile pending durable work into verifier-preserving synthesis contracts."""
    out: list[dict[str, Any]] = []
    for raw in pending_work:
        work = deepcopy(dict(raw))
        payload = work.get("payload")
        payload = payload if isinstance(payload, Mapping) else {}
        kind = _s(work.get("kind"))
        if kind == "REPAIR_FAILURE_CLASS":
            acceptance = "ORIGINAL_FAILURE_REPLAY_MUST_PASS_UNCHANGED_VERIFIER"
            mutation = "CAPABILITY_IMPLEMENTATION_OR_POLICY_ONLY__VERIFIER_IMMUTABLE"
        elif kind == "EXPAND_SUCCESS_VERIFICATION_FRONTIER":
            acceptance = "BLOCKED_SUCCESS_MUST_ADAPT_AND_INDEPENDENTLY_VERIFY"
            mutation = "SUCCESS_ADAPTER_ONLY__VERIFIER_IMMUTABLE"
        elif kind == "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE":
            acceptance = "SUCCESS_OBSERVATION_MUST_BECOME_INDEPENDENTLY_VERIFIABLE_EPISODE"
            mutation = "ADAPTER_OR_VERIFIABLE_REPRESENTATION_ONLY__VERIFIER_IMMUTABLE"
        else:
            acceptance = "ORIGINAL_PENDING_OBLIGATION_MUST_CLOSE_UNDER_EXISTING_AUTHORITY"
            mutation = "MINIMUM_CONSTRUCTIVE_CHANGE__VERIFIER_IMMUTABLE"

        basis = {
            "work_id": _s(work.get("work_id")),
            "work_digest": _s(work.get("work_digest")),
            "kind": kind,
            "required_result": payload.get("required_result"),
            "repair_class": payload.get("repair_class"),
            "failure_fingerprint": payload.get("failure_fingerprint"),
            "failure_status": payload.get("failure_status"),
            "falsified_capability_ids": deepcopy(payload.get("falsified_capability_ids", [])),
            "counterexamples": deepcopy(payload.get("counterexamples", [])),
            "observation_id": payload.get("observation_id"),
            "retry_capsule_sha256": payload.get("retry_capsule_sha256"),
            "replay_capsule_sha256": payload.get("replay_capsule_sha256"),
            "proof_capsule_sha256": payload.get("proof_capsule_sha256"),
            "surface": payload.get("surface"),
            "boundary_root": payload.get("boundary_root"),
            "required_capability_class": payload.get("required_capability_class"),
            "verification_frontier_sha256": work.get("verification_frontier_sha256"),
            "adapter_frontier_sha256": work.get("adapter_frontier_sha256"),
            "verification_authority_sha256": work.get("verification_authority_sha256"),
            "acceptance_condition": acceptance,
            "allowed_mutation_class": mutation,
        }
        out.append({
            "schema": "PROJECT_BRAIN_CONSTRUCTIVE_CAPABILITY_CONTRACT_V1",
            "contract_id": "constructive:" + _sha(basis),
            "basis": basis,
            "required_attempt_order": list(REQUIRED_ATTEMPT_ORDER),
            "search_before_new_code_required": True,
            "minimum_missing_transform_only": True,
            "verifier_generated_or_reused_with_solution": True,
            "verification_authority_mutation_allowed": False,
            "self_verification_allowed": False,
            "promotion_authority": False,
            "terminal_authority": False,
        })
    return out


def _shared_cause_candidates(
    contracts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Find exact shared-cause keys before launching per-obligation work."""
    groups: dict[tuple[str, str], list[str]] = {}
    for raw in contracts:
        contract = dict(raw)
        basis = contract.get("basis")
        basis = basis if isinstance(basis, Mapping) else {}
        cid = _s(contract.get("contract_id"))
        for field in (
            "boundary_root",
            "required_capability_class",
            "repair_class",
            "surface",
        ):
            value = _s(basis.get(field)).strip()
            if value:
                groups.setdefault((field, value), []).append(cid)
    out = []
    for (field, value), ids in groups.items():
        unique_ids = sorted(set(ids))
        if len(unique_ids) < 2:
            continue
        basis = {
            "shared_field": field,
            "shared_value": value,
            "obligation_ids": unique_ids,
            "terminal_obligations_reached": len(unique_ids),
        }
        out.append({
            "candidate_id": "shared-cause:" + _sha(basis),
            **basis,
        })
    return sorted(
        out,
        key=lambda row: (
            -row["terminal_obligations_reached"],
            row["shared_field"],
            row["shared_value"],
        ),
    )


def certify_context_capacity_repair(
    *,
    observed_request_tokens: int,
    configured_context_tokens: int,
    candidate_context_tokens: int,
    headroom_tokens: int = 0,
    live_probe_receipt: Mapping[str, Any] | None = None,
    expected_model_sha256: str | None = None,
    expected_runtime_commit: str | None = None,
) -> dict[str, Any]:
    """Certify the arithmetic and, when supplied, the live zero-exposure gate.

    Arithmetic sufficiency proves only that the configured candidate is large
    enough for the observed request class plus requested headroom. Live route
    sufficiency additionally requires an exact-identity, zero-benchmark-exposure
    receipt whose observed probe reaches that request class.
    """
    observed = _positive_int("OBSERVED_REQUEST_TOKENS", observed_request_tokens)
    configured = _positive_int("CONFIGURED_CONTEXT_TOKENS", configured_context_tokens)
    candidate = _positive_int("CANDIDATE_CONTEXT_TOKENS", candidate_context_tokens)
    headroom = _positive_int("HEADROOM_TOKENS", headroom_tokens, allow_zero=True)

    required = observed + headroom + 1
    arithmetic_pass = candidate >= required
    payload: dict[str, Any] = {
        "schema": CONTEXT_GATE_SCHEMA,
        "observed_request_tokens": observed,
        "configured_context_tokens": configured,
        "candidate_context_tokens": candidate,
        "headroom_tokens": headroom,
        "strict_required_context_tokens": required,
        "original_route_insufficient": configured <= observed,
        "arithmetic_capacity_pass": arithmetic_pass,
        "live_zero_exposure_pass": False,
        "pass": False,
        "authority_added": "NONE",
    }

    if live_probe_receipt is None:
        payload["status"] = (
            "ARITHMETIC_CAPACITY_PASS__LIVE_ZERO_EXPOSURE_RECEIPT_REQUIRED"
            if arithmetic_pass
            else "FAIL__CANDIDATE_CONTEXT_CAPACITY_INSUFFICIENT"
        )
        payload["digest"] = _sha(payload)
        return payload

    receipt = dict(live_probe_receipt)
    exposure = receipt.get("benchmark_exposure_count")
    probe_tokens = receipt.get("observed_probe_tokens")
    receipt_candidate = receipt.get("candidate_context_tokens")
    identity_ok = True

    if expected_model_sha256 is not None:
        identity_ok = identity_ok and (
            _s(receipt.get("model_sha256")) == _s(expected_model_sha256)
        )
    if expected_runtime_commit is not None:
        identity_ok = identity_ok and (
            _s(receipt.get("runtime_commit")) == _s(expected_runtime_commit)
        )

    receipt_shape_ok = (
        isinstance(exposure, int)
        and not isinstance(exposure, bool)
        and exposure == 0
        and isinstance(probe_tokens, int)
        and not isinstance(probe_tokens, bool)
        and probe_tokens >= observed
        and isinstance(receipt_candidate, int)
        and not isinstance(receipt_candidate, bool)
        and receipt_candidate == candidate
        and receipt.get("live_probe_pass") is True
        and _valid_sha256(receipt.get("receipt_sha256"))
    )

    live_pass = arithmetic_pass and identity_ok and receipt_shape_ok
    payload.update(
        {
            "live_zero_exposure_pass": live_pass,
            "identity_match": identity_ok,
            "receipt_shape_valid": receipt_shape_ok,
            "receipt_sha256": receipt.get("receipt_sha256"),
            "pass": live_pass,
            "status": (
                "PASS__STRICT_CONTEXT_CAPACITY_AND_ZERO_EXPOSURE_LIVE_GATE"
                if live_pass
                else "FAIL__LIVE_CONTEXT_CAPACITY_GATE_NOT_PROVED"
            ),
            "authority_added": (
                "CONTEXT_CAPACITY_REPAIR_GATE_ONLY" if live_pass else "NONE"
            ),
        }
    )
    payload["digest"] = _sha(payload)
    return payload


def compile_gap_contract(
    closure_result: Mapping[str, Any],
    *,
    pending_work: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Convert one V1 residual into an exact repair/acquisition contract."""
    row = deepcopy(dict(closure_result))
    residual = row.get("residual")
    if not isinstance(residual, Mapping):
        residual = {}

    internal = sorted({_s(x) for x in residual.get("internal_blockers", []) if _s(x)})
    evidence = sorted({_s(x) for x in residual.get("evidence_blockers", []) if _s(x)})
    external_proved = (
        row.get("irreducible_external_information_proved") is True
        or residual.get("irreducible_external_information_proved") is True
    )

    pending_acquisition = (
        residual.get("pending_acquisition_or_experiment_required") is True
    )
    externality_guard = (
        "EXTERNALITY_NOT_PROVED__CONTINUE_INTERNAL_SEARCH_SYNTHESIS_OR_BYPASS"
    )
    constructive_internal = [
        item for item in internal if item != externality_guard
    ]
    r2_acquisition_requests = [
        deepcopy(dict(x))
        for x in (residual.get("r2_acquisition_requests") or [])
        if isinstance(x, Mapping)
    ]

    if row.get("pass") is True and not internal:
        if external_proved:
            gap_class = "PROVEN_INFORMATION_THEORETICALLY_EXTERNAL"
        else:
            gap_class = "NONE"
        required_action = "NONE"
    elif pending_acquisition and evidence and not constructive_internal:
        gap_class = "PENDING_ACQUISITION_OR_EXPERIMENT"
        required_action = "SEARCH_SIMULATE_EXPERIMENT_OR_ACQUIRE_MINIMUM_NEEDED_EVIDENCE"
    elif internal:
        gap_class = "CONSTRUCTIVE_CAPABILITY_GAP"
        required_action = "SYNTHESIZE_OR_ACQUIRE_VERIFIABLE_CAPABILITY"
    elif evidence:
        gap_class = "PENDING_ACQUISITION_OR_EXPERIMENT"
        required_action = "SEARCH_SIMULATE_EXPERIMENT_OR_ACQUIRE_MINIMUM_NEEDED_EVIDENCE"
    else:
        gap_class = "UNCLASSIFIED_OPEN_GAP"
        required_action = "FAIL_CLOSED_AND_REFINE_GAP_CONTRACT"

    basis = {
        "source_schema": _s(row.get("schema")),
        "source_status": _s(row.get("status")),
        "source_initial_frontier_digest": _s(row.get("initial_frontier_digest")),
        "source_final_frontier_digest": _s(row.get("final_frontier_digest")),
        "source_final_state_sha256": _s(row.get("final_state_sha256")),
        "closure_class": _s(row.get("closure_class")),
        "internal_blockers": internal,
        "evidence_blockers": evidence,
        "irreducible_external_information_proved": external_proved,
        "information_theoretic_externality_proved": (
            residual.get("information_theoretic_externality_proved") is True
        ),
        "internal_unsolved": residual.get("internal_unsolved") is True,
        "pending_acquisition_or_experiment_required": pending_acquisition,
        "constructive_internal_blockers": constructive_internal,
        "r2_acquisition_requests": r2_acquisition_requests,
        "r2_acquisition_request_count": len(r2_acquisition_requests),
    }
    semantic_work = [deepcopy(dict(x)) for x in pending_work]
    constructive_contracts = _constructive_capability_contracts(semantic_work)
    shared_causes = _shared_cause_candidates(constructive_contracts)
    return {
        "schema": GAP_SCHEMA,
        "gap_class": gap_class,
        "required_action": required_action,
        "basis": basis,
        "basis_digest": _sha(basis),
        "pending_semantic_work": semantic_work,
        "pending_semantic_work_digest": _sha(semantic_work),
        "constructive_capability_contracts": constructive_contracts,
        "constructive_capability_contract_count": len(constructive_contracts),
        "shared_cause_candidates": shared_causes,
        "shared_cause_candidate_count": len(shared_causes),
        "required_attempt_order": list(REQUIRED_ATTEMPT_ORDER),
        "search_before_new_code_required": True,
        "minimum_missing_transform_only": True,
        "verifier_generated_or_reused_with_solution": True,
        "verification_authority_mutation_allowed": False,
        "terminal_credit": False,
    }


def compile_decision_sufficient_contract(
    gap_contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile a gap into a lossless decision-sufficient representation.

    The built-in baseline drops nothing. This is intentionally stronger than an
    unverified semantic summary: every source bit remains committed by digest.
    Future compressors may replace the identity representation only with an
    independently verified omission certificate proving that omitted evidence
    cannot change the required action under the frozen acceptance contract.
    """
    source = deepcopy(dict(gap_contract))
    basis = source.get("basis")
    basis = deepcopy(dict(basis)) if isinstance(basis, Mapping) else {}
    constructive = source.get("constructive_capability_contracts")
    constructive = (
        [deepcopy(dict(x)) for x in constructive if isinstance(x, Mapping)]
        if isinstance(constructive, Sequence) and not isinstance(constructive, (str, bytes))
        else []
    )
    policy_requirements: list[dict[str, Any]] = []
    for item in basis.get("constructive_internal_blockers", []) or []:
        if _s(item):
            policy_requirements.append({"kind": "INTERNAL_BLOCKER", "value": _s(item)})
    for item in basis.get("evidence_blockers", []) or []:
        if _s(item):
            policy_requirements.append({"kind": "EVIDENCE_BLOCKER", "value": _s(item)})
    for request in basis.get("r2_acquisition_requests", []) or []:
        if not isinstance(request, Mapping):
            continue
        policy_requirements.append({
            "kind": "R2_STRUCTURED_ACQUISITION_REQUEST",
            "cell_id": request.get("cell_id"),
            "request_sha256": request.get("request_sha256"),
            "required_action": request.get("required_action"),
            "remaining_boundary": request.get("remaining_boundary"),
            "wake_conditions": deepcopy(list(request.get("wake_conditions") or [])),
        })
    for contract in constructive:
        cbasis = contract.get("basis")
        cbasis = cbasis if isinstance(cbasis, Mapping) else {}
        policy_requirements.append({
            "kind": "CONSTRUCTIVE_CONTRACT",
            "contract_id": contract.get("contract_id"),
            "required_result": cbasis.get("required_result"),
            "repair_class": cbasis.get("repair_class"),
            "acceptance_condition": cbasis.get("acceptance_condition"),
            "verification_authority_sha256": cbasis.get("verification_authority_sha256"),
        })

    source_digest = _sha(source)
    representation = {
        "gap_class": source.get("gap_class"),
        "required_action": source.get("required_action"),
        "basis_digest": source.get("basis_digest"),
        "pending_semantic_work_digest": source.get("pending_semantic_work_digest"),
        "policy_changing_requirements": policy_requirements,
        "source_contract_sha256": source_digest,
    }
    return {
        "schema": DECISION_SUFFICIENT_SCHEMA,
        "scope": "EXACT_CURRENT_GAP_CONTRACT_ONLY",
        "status": "PASS__LOSSLESS_IDENTITY_DECISION_SUFFICIENT_BASELINE",
        "pass": True,
        "representation": representation,
        "representation_sha256": _sha(representation),
        "source_contract_sha256": source_digest,
        "reduction_mode": "LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION",
        "omitted_evidence": [],
        "omission_certificate_required_for_future_compression": True,
        "verification_authority_mutation_allowed": False,
        "terminal_credit": False,
    }


def compile_minimum_information_contract(
    gap_contract: Mapping[str, Any],
    decision_contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile evidence acquisition to the smallest currently justified requests.

    One request is emitted per unique evidence blocker. The compiler does not
    claim that a blocker requires a full benchmark or broad crawl. Providers must
    first attempt proof/reuse and then acquire only an observation whose value can
    change the current decision.
    """
    gap = deepcopy(dict(gap_contract))
    decision = deepcopy(dict(decision_contract))
    basis = gap.get("basis")
    basis = basis if isinstance(basis, Mapping) else {}
    blockers = sorted({_s(x) for x in basis.get("evidence_blockers", []) or [] if _s(x)})
    structured = [
        deepcopy(dict(x))
        for x in (basis.get("r2_acquisition_requests") or [])
        if isinstance(x, Mapping)
    ]
    requests = []
    structured_blockers: set[str] = set()
    for request in sorted(
        structured,
        key=lambda row: (
            _s(row.get("cell_id")),
            _s(row.get("request_sha256")),
        ),
    ):
        cell_id = _s(request.get("cell_id"))
        blocker = "R2_PENDING_ACQUISITION:" + cell_id if cell_id else ""
        if blocker:
            structured_blockers.add(blocker)
        row = {
            "kind": "R2_STRUCTURED_POLICY_CHANGING_ACQUISITION",
            "blocker": blocker or None,
            "r2_cell_id": cell_id or None,
            "source_request_sha256": request.get("request_sha256"),
            "source_r2_authority_sha256": request.get("source_r2_authority_sha256"),
            "required_action": request.get("required_action"),
            "remaining_boundary": request.get("remaining_boundary"),
            "wake_conditions": deepcopy(list(request.get("wake_conditions") or [])),
            "required_property": "OBSERVATION_OR_CERTIFICATE_MUST_SATISFY_AT_LEAST_ONE_BOUND_WAKE_CONDITION_AND_CHANGE_OR_CLOSE_THE_EXACT_R2_CELL",
            "proof_or_existing_receipt_precedes_new_reality": True,
            "broad_acquisition_forbidden_without_minimality_proof": True,
            "full_benchmark_default": False,
        }
        requests.append({
            **row,
            "request_id": "minimum-info:r2:" + _sha(row),
        })
    for blocker in blockers:
        if blocker in structured_blockers:
            continue
        row = {
            "kind": "GENERIC_EVIDENCE_BLOCKER",
            "blocker": blocker,
            "required_property": "OBSERVATION_MUST_BE_CAPABLE_OF_CHANGING_CURRENT_POLICY_OR_CLOSING_EXACT_OBLIGATION",
            "proof_or_existing_receipt_precedes_new_reality": True,
            "broad_acquisition_forbidden_without_minimality_proof": True,
        }
        requests.append({
            **row,
            "request_id": "minimum-info:" + _sha(row),
        })
    payload = {
        "schema": MINIMUM_INFORMATION_SCHEMA,
        "source_gap_contract_sha256": _sha(gap),
        "decision_contract_sha256": _sha(decision),
        "requests": requests,
        "request_count": len(requests),
        "structured_r2_request_count": sum(
            row.get("kind") == "R2_STRUCTURED_POLICY_CHANGING_ACQUISITION"
            for row in requests
        ),
        "acquisition_objective": "MINIMIZE_NEW_INFORMATION_SUBJECT_TO_CLOSING_OR_CHANGING_THE_EXACT_CURRENT_DECISION",
        "proof_precedence": [
            "FORMAL_IMPLICATION",
            "EXISTING_CONTENT_ADDRESSED_RECEIPT",
            "DETERMINISTIC_SCOPE_OR_DOMINANCE_CERTIFICATE",
            "MINIMUM_POLICY_CHANGING_OBSERVATION",
            "FULL_EMPIRICAL_EVALUATION_LAST",
        ],
        "verification_authority_mutation_allowed": False,
        "terminal_credit": False,
    }
    payload["digest"] = _sha(payload)
    return payload


def conservative_leverage_score(candidate: Mapping[str, Any]) -> float:
    """Rank actions using lower-bound success probability, never invented midpoint."""
    p = candidate.get("success_probability_interval")
    if (
        not isinstance(p, Sequence)
        or isinstance(p, (str, bytes))
        or len(p) != 2
    ):
        raise RealityClosureError("SUCCESS_PROBABILITY_INTERVAL_REQUIRED")
    lo, hi = p
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in (lo, hi)):
        raise RealityClosureError("SUCCESS_PROBABILITY_INTERVAL_INVALID")
    lo = float(lo)
    hi = float(hi)
    if not (0.0 <= lo <= hi <= 1.0):
        raise RealityClosureError("SUCCESS_PROBABILITY_INTERVAL_OUT_OF_RANGE")
    reach = float(candidate.get("truth_reach_lower_bound", 0.0))
    future = float(candidate.get("future_reuse_multiplier_lower_bound", 1.0))
    seconds = float(candidate.get("critical_path_seconds", 0.0))
    if reach < 0 or future < 0 or seconds <= 0:
        raise RealityClosureError("LEVERAGE_INPUT_OUT_OF_RANGE")
    return lo * reach * future / seconds


def rank_candidates(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for raw in candidates:
        row = deepcopy(dict(raw))
        row["conservative_leverage_score"] = conservative_leverage_score(row)
        rows.append(row)
    return sorted(
        rows,
        key=lambda x: (-x["conservative_leverage_score"], _s(x.get("id"))),
    )


def _validate_provider_receipt(
    result: Mapping[str, Any] | None,
    *,
    provider_kind: str,
) -> dict[str, Any]:
    if not isinstance(result, Mapping):
        raise RealityClosureError(provider_kind + "_PROVIDER_RETURNED_NO_RECEIPT")
    receipt = deepcopy(dict(result))
    if receipt.get("pass") is not True:
        raise RealityClosureError(provider_kind + "_PROVIDER_DID_NOT_PASS")
    if not _valid_sha256(receipt.get("receipt_sha256")):
        raise RealityClosureError(provider_kind + "_RECEIPT_SHA256_INVALID")
    if receipt.get("frontier_changed") is not True:
        raise RealityClosureError(provider_kind + "_CLAIMED_SUCCESS_WITHOUT_FRONTIER_CHANGE")
    if receipt.get("verification_authority_mutated") is not False:
        raise RealityClosureError(provider_kind + "_VERIFICATION_AUTHORITY_MUTATION_FORBIDDEN")
    if provider_kind == "CAPABILITY_SYNTHESIS":
        if receipt.get("reuse_or_search_trace_complete") is not True:
            raise RealityClosureError("CAPABILITY_SYNTHESIS_SEARCH_BEFORE_CODE_NOT_PROVED")
        if receipt.get("new_code_written") is True:
            if receipt.get("pre_code_search_exhausted") is not True:
                raise RealityClosureError("CAPABILITY_SYNTHESIS_PRE_CODE_SEARCH_NOT_EXHAUSTED")
            if receipt.get("minimal_missing_transform_only") is not True:
                raise RealityClosureError("CAPABILITY_SYNTHESIS_NOT_MINIMUM_MISSING_TRANSFORM")
        if receipt.get("verifier_generated_or_reused") is not True:
            raise RealityClosureError("CAPABILITY_SYNTHESIS_VERIFIER_REQUIRED")
        if receipt.get("verifier_passed") is not True:
            raise RealityClosureError("CAPABILITY_SYNTHESIS_VERIFIER_DID_NOT_PASS")
    if provider_kind == "EVIDENCE_ACQUISITION":
        if receipt.get("acquisition_or_experiment_attempted") is not True:
            raise RealityClosureError("EVIDENCE_ACQUISITION_ATTEMPT_NOT_PROVED")
        if not _valid_sha256(receipt.get("evidence_trace_sha256")):
            raise RealityClosureError("EVIDENCE_ACQUISITION_TRACE_SHA256_INVALID")
    return receipt


def _r2_direct_route_deployment_contract(
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Describe the exact current proof obligations for an optional new live route."""
    root = Path(repo_root).resolve()
    admission = r2_direct_route_promoter.admission
    current = admission.load_current_admissions(repo_root=root)

    wrapper_rel = admission.LIVE_WRAPPER_PATH
    wrapper = (root / wrapper_rel).resolve()
    if wrapper == root or root not in wrapper.parents or not wrapper.is_file():
        raise RealityClosureError("R2_DIRECT_ROUTE_LIVE_WRAPPER_MISSING")
    wrapper_sha = admission.git_blob_sha(wrapper)

    route_ids = sorted(
        str(row["route_id"]) for row in current["admissions"]
    )
    return {
        "schema": "PROJECT_BRAIN_R2_DIRECT_ROUTE_DEPLOYMENT_PROVIDER_CONTRACT_V2",
        "optional_direct_route_proposal": True,
        "provider_deployment_authority": False,
        "provider_receipt_proposal_fields": [
            "r2_direct_route_candidate_path",
            "r2_direct_route_independent_receipt_path",
        ],
        "new_route_noninterference_required": True,
        "existing_exact_binding_repromotion_exempt": True,
        "noninterference": {
            "proof_schema": admission.NONINTERFERENCE_SCHEMA,
            "proof_status": "INDEPENDENT_PASS__R2_DIRECT_ROUTE_NONINTERFERENCE",
            "proof_class": admission.NONINTERFERENCE_PROOF_CLASS,
            "deployment_receipt_required_fields": [
                "noninterference_verification_path",
                "noninterference_verification_git_blob_sha",
            ],
            "required_propositions": [
                "legacy_overlap_absent_verified",
                "dynamic_overlap_absent_verified",
                "scope_complete_for_candidate_match_domain",
                "independent_verified",
            ],
            "baseline_dynamic_manifest_git_blob_sha": current[
                "target_git_blob_sha"
            ],
            "baseline_dynamic_route_ids": route_ids,
            "baseline_live_wrapper_path": wrapper_rel,
            "baseline_live_wrapper_git_blob_sha": wrapper_sha,
            "staleness_rule": (
                "PROMOTER_REJECTS_IF_CURRENT_MANIFEST_OR_ROUTE_SET_DIFFERS_"
                "FROM_PROOF_BASELINE"
            ),
        },
        "verification_authority_mutation_allowed": False,
        "terminal_authority": False,
        "terminal_credit": False,
    }


def _maybe_promote_verified_r2_direct_route(
    receipt: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Promote an optional independently verified direct-route deployment.

    The synthesis provider receives no deployment authority. It may only point to
    a candidate and an independent deployment receipt. The Brain-owned promoter
    revalidates both content-addressed files and updates the live admission pointer.
    """
    candidate_path = _s(receipt.get("r2_direct_route_candidate_path")).strip()
    independent_receipt_path = _s(
        receipt.get("r2_direct_route_independent_receipt_path")
    ).strip()
    if not candidate_path and not independent_receipt_path:
        return {
            "attempted": False,
            "frontier_changed": False,
            "already_live": False,
            "verification_authority_mutated": False,
        }
    if not candidate_path or not independent_receipt_path:
        raise RealityClosureError("R2_DIRECT_ROUTE_PROMOTION_BINDING_INCOMPLETE")

    promoted = r2_direct_route_promoter.promote(
        candidate_path=candidate_path,
        receipt_path=independent_receipt_path,
        repo_root=repo_root,
    )
    if not isinstance(promoted, Mapping) or promoted.get("pass") is not True:
        reason = (
            _s(promoted.get("reason") or promoted.get("status"))
            if isinstance(promoted, Mapping)
            else "PROMOTER_RETURNED_NO_RESULT"
        )
        raise RealityClosureError("R2_DIRECT_ROUTE_PROMOTION_FAILED:" + reason)
    if promoted.get("verification_authority_mutated") is not False:
        raise RealityClosureError("R2_DIRECT_ROUTE_PROMOTION_MUTATED_VERIFICATION_AUTHORITY")
    changed = promoted.get("frontier_changed") is True
    already_live = promoted.get("status") == "ALREADY_LIVE_EXACT_BINDING"
    if not changed and not already_live:
        raise RealityClosureError("R2_DIRECT_ROUTE_PROMOTION_NO_LIVE_FRONTIER_RESULT")
    return {
        "attempted": True,
        "pass": True,
        "status": promoted.get("status"),
        "route_id": promoted.get("route_id"),
        "frontier_changed": changed,
        "already_live": already_live,
        "current_manifest_git_blob_sha": promoted.get("new_manifest_git_blob_sha")
        or promoted.get("current_manifest_git_blob_sha"),
        "receipt_sha256": promoted.get("receipt_sha256"),
        "verification_authority_mutated": False,
        "terminal_authority": False,
    }


def _infrastructure_failure_result(
    *,
    stage: str,
    repair_round: int,
    exc: BaseException,
    transcript: Sequence[Mapping[str, Any]],
    gap_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    failure = {
        "stage": stage,
        "exception_type": type(exc).__name__,
        "reason": str(exc),
        "classification": "INTERNAL_INFRASTRUCTURE_OR_PROVIDER_BUG",
        "externality_proved": False,
    }
    out = {
        "schema": SCHEMA,
        "status": "OPEN__INTERNAL_UNSOLVED__INFRASTRUCTURE_OR_PROVIDER_FAILURE",
        "pass": False,
        "fixed_point": False,
        "repair_round": repair_round,
        "internal_unsolved": True,
        "failure": failure,
        "transcript": [deepcopy(dict(x)) for x in transcript],
        "terminal_authority": False,
    }
    if gap_contract is not None:
        out["gap_contract"] = deepcopy(dict(gap_contract))
    return out


def _attempt_infrastructure_repair(
    provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
    *,
    stage: str,
    repair_round: int,
    exc: BaseException,
    transcript: list[dict[str, Any]],
    gap_contract: Mapping[str, Any] | None = None,
) -> bool:
    if provider is None:
        return False
    request = {
        "schema": "PROJECT_BRAIN_INFRASTRUCTURE_REPAIR_REQUEST_V1",
        "stage": stage,
        "repair_round": repair_round,
        "exception_type": type(exc).__name__,
        "reason": str(exc),
        "classification": "INTERNAL_INFRASTRUCTURE_OR_PROVIDER_BUG",
        "gap_contract": deepcopy(dict(gap_contract)) if gap_contract is not None else None,
        "verification_authority_mutation_allowed": False,
        "terminal_credit": False,
    }
    try:
        raw = provider(deepcopy(request))
    except Exception:
        return False
    if not isinstance(raw, Mapping):
        return False
    receipt = deepcopy(dict(raw))
    if receipt.get("pass") is not True:
        return False
    if receipt.get("infrastructure_repaired") is not True:
        return False
    if receipt.get("verification_authority_mutated") is not False:
        return False
    if not _valid_sha256(receipt.get("receipt_sha256")):
        return False
    transcript.append({
        "repair_round": repair_round,
        "stage": stage,
        "status": "INFRASTRUCTURE_REPAIR_RECEIPT_ACCEPTED__RETRY_CLOSURE_LOOP",
        "receipt_sha256": receipt["receipt_sha256"],
        "terminal_credit": False,
    })
    return True


def run(
    *,
    repo_root,
    state_path=None,
    verification_frontier_acquisition_provider=None,
    verification_frontier_acquisition_provider_id="ONE_SHOT_ROOT1_ACQUISITION_PROVIDER",
    failure_repair_provider=None,
    externality_certificate_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    capability_synthesis_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    evidence_acquisition_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    reality_acquisition_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    infrastructure_repair_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    max_repair_rounds: int = 8,
    v1_max_rounds: int = 64,
    v1_max_actions_per_round: int = 32,
) -> dict[str, Any]:
    """Drive V1 to closure, repairing constructive gaps and strictly external gaps.

    The providers perform mutations/effects; V2 only supplies proof-carrying
    contracts and then verifies that the next V1 invocation observes a new
    frontier. This keeps synthesis separate from verification authority.
    """
    rounds = _positive_int("MAX_REPAIR_ROUNDS", max_repair_rounds)
    previous_frontier_after_provider: str | None = None
    transcript: list[dict[str, Any]] = []

    for repair_round in range(rounds):
        kwargs = {
            "repo_root": repo_root,
            "verification_frontier_acquisition_provider": (
                verification_frontier_acquisition_provider
            ),
            "verification_frontier_acquisition_provider_id": (
                verification_frontier_acquisition_provider_id
            ),
            "failure_repair_provider": failure_repair_provider,
            "externality_certificate_provider": (
                externality_certificate_provider
            ),
            "max_rounds": v1_max_rounds,
            "max_actions_per_round": v1_max_actions_per_round,
        }
        if state_path is not None:
            kwargs["state_path"] = state_path
        try:
            closure = v1.run(**kwargs)
        except Exception as exc:
            if _attempt_infrastructure_repair(
                infrastructure_repair_provider,
                stage="V1_CLOSURE_ENGINE",
                repair_round=repair_round,
                exc=exc,
                transcript=transcript,
            ):
                continue
            return _infrastructure_failure_result(
                stage="V1_CLOSURE_ENGINE",
                repair_round=repair_round,
                exc=exc,
                transcript=transcript,
            )

        current_initial = _s(closure.get("initial_frontier_digest"))
        if (
            previous_frontier_after_provider is not None
            and current_initial
            and current_initial == previous_frontier_after_provider
        ):
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__PROVIDER_RECEIPT_WITHOUT_OBSERVED_FRONTIER_CHANGE",
                "pass": False,
                "repair_round": repair_round,
                "transcript": transcript,
                "last_closure": deepcopy(dict(closure)),
                "terminal_authority": False,
            }

        pending_work = _pending_semantic_work(state_path=state_path)
        contract = compile_gap_contract(closure, pending_work=pending_work)
        decision_contract = compile_decision_sufficient_contract(contract)
        minimum_information_contract = compile_minimum_information_contract(
            contract, decision_contract
        )
        transcript.append(
            {
                "repair_round": repair_round,
                "closure_status": closure.get("status"),
                "closure_pass": closure.get("pass") is True,
                "gap_class": contract["gap_class"],
                "basis_digest": contract["basis_digest"],
                "pending_semantic_work_digest": contract["pending_semantic_work_digest"],
                "constructive_capability_contract_count": contract["constructive_capability_contract_count"],
                "decision_sufficient_contract_sha256": decision_contract["representation_sha256"],
                "minimum_information_contract_sha256": minimum_information_contract["digest"],
            }
        )

        if closure.get("pass") is True:
            return {
                "schema": SCHEMA,
                "status": "PASS__PROOF_CARRYING_REALITY_CLOSURE_FIXED_POINT",
                "pass": True,
                "fixed_point": closure.get("fixed_point") is True,
                "repair_rounds_executed": repair_round,
                "transcript": transcript,
                "final_closure": deepcopy(dict(closure)),
                "terminal_authority": False,
            }

        gap_class = contract["gap_class"]
        if gap_class == "CONSTRUCTIVE_CAPABILITY_GAP":
            if capability_synthesis_provider is None:
                return {
                    "schema": SCHEMA,
                    "status": "OPEN__CAPABILITY_SYNTHESIS_PROVIDER_REQUIRED",
                    "pass": False,
                    "gap_contract": contract,
                    "transcript": transcript,
                    "terminal_authority": False,
                }
            try:
                deployment_contract = _r2_direct_route_deployment_contract(
                    repo_root=repo_root
                )
                receipt = _validate_provider_receipt(
                    capability_synthesis_provider({
                        **deepcopy(contract),
                        "decision_sufficient_contract": deepcopy(decision_contract),
                        "r2_direct_route_deployment_contract": deepcopy(
                            deployment_contract
                        ),
                    }),
                    provider_kind="CAPABILITY_SYNTHESIS",
                )
                direct_route_promotion = _maybe_promote_verified_r2_direct_route(
                    receipt,
                    repo_root=repo_root,
                )
            except Exception as exc:
                if _attempt_infrastructure_repair(
                    infrastructure_repair_provider,
                    stage="CAPABILITY_SYNTHESIS_PROVIDER",
                    repair_round=repair_round,
                    exc=exc,
                    transcript=transcript,
                    gap_contract=contract,
                ):
                    continue
                return _infrastructure_failure_result(
                    stage="CAPABILITY_SYNTHESIS_PROVIDER",
                    repair_round=repair_round,
                    exc=exc,
                    transcript=transcript,
                    gap_contract=contract,
                )
        elif gap_class == "PENDING_ACQUISITION_OR_EXPERIMENT":
            if evidence_acquisition_provider is None:
                return {
                    "schema": SCHEMA,
                    "status": "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT_PROVIDER_REQUIRED",
                    "pass": False,
                    "gap_contract": contract,
                    "transcript": transcript,
                    "terminal_authority": False,
                }
            try:
                receipt = _validate_provider_receipt(
                    evidence_acquisition_provider({
                        **deepcopy(contract),
                        "decision_sufficient_contract": deepcopy(decision_contract),
                        "minimum_information_contract": deepcopy(minimum_information_contract),
                    }),
                    provider_kind="EVIDENCE_ACQUISITION",
                )
            except Exception as exc:
                if _attempt_infrastructure_repair(
                    infrastructure_repair_provider,
                    stage="EVIDENCE_ACQUISITION_PROVIDER",
                    repair_round=repair_round,
                    exc=exc,
                    transcript=transcript,
                    gap_contract=contract,
                ):
                    continue
                return _infrastructure_failure_result(
                    stage="EVIDENCE_ACQUISITION_PROVIDER",
                    repair_round=repair_round,
                    exc=exc,
                    transcript=transcript,
                    gap_contract=contract,
                )
        elif gap_class == "PROVEN_INFORMATION_THEORETICALLY_EXTERNAL":
            return {
                "schema": SCHEMA,
                "status": "PASS__PROVEN_INFORMATION_THEORETICALLY_EXTERNAL",
                "pass": True,
                "fixed_point": True,
                "gap_contract": contract,
                "transcript": transcript,
                "terminal_authority": False,
            }
        else:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__UNCLASSIFIED_GAP_CONTRACT",
                "pass": False,
                "gap_contract": contract,
                "transcript": transcript,
                "terminal_authority": False,
            }

        previous_frontier_after_provider = _s(closure.get("final_frontier_digest"))
        transcript[-1]["provider_receipt_sha256"] = receipt["receipt_sha256"]
        transcript[-1]["provider_kind"] = gap_class
        if gap_class == "CONSTRUCTIVE_CAPABILITY_GAP":
            transcript[-1]["r2_direct_route_promotion"] = deepcopy(
                direct_route_promotion
            )

    return {
        "schema": SCHEMA,
        "status": "OPEN__REPAIR_ROUND_LIMIT_REACHED",
        "pass": False,
        "repair_rounds_executed": rounds,
        "transcript": transcript,
        "terminal_authority": False,
    }
