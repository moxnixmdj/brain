"""Proof-carrying one-shot reality closure V2.

V2 does not claim universal semantics or universal capability construction.
It strengthens V1 by turning every open residual into one of two explicit,
machine-checkable contracts:

* CONSTRUCTIVE_CAPABILITY_GAP: must be handed to a synthesis/acquisition
  provider that changes the verified frontier without changing verifier authority.
* STRICT_EXTERNAL_INFORMATION_GAP: may be handed to a reality acquisition
  provider only after V1 proves the exact residual irreducibly requires external
  information.

Provider success is never accepted on assertion alone. A provider must return
a content-addressed receipt and the next V1 pass must observe a frontier digest
change. The loop therefore converts "open residual" into "repair and re-run"
without allowing fake progress.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import one_shot_verified_closure_v1 as v1

SCHEMA = "PROJECT_BRAIN_ONE_SHOT_REALITY_CLOSURE_V2"
GAP_SCHEMA = "PROJECT_BRAIN_PROOF_CARRYING_GAP_CONTRACT_V1"
CONTEXT_GATE_SCHEMA = "PROJECT_BRAIN_CONTEXT_CAPACITY_REPAIR_GATE_V1"

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


def compile_gap_contract(closure_result: Mapping[str, Any]) -> dict[str, Any]:
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

    if row.get("pass") is True and not internal:
        gap_class = "NONE"
        required_action = "NONE"
    elif internal:
        gap_class = "CONSTRUCTIVE_CAPABILITY_GAP"
        required_action = "SYNTHESIZE_OR_ACQUIRE_VERIFIABLE_CAPABILITY"
    elif evidence and external_proved:
        gap_class = "STRICT_EXTERNAL_INFORMATION_GAP"
        required_action = "ACQUIRE_MINIMUM_POLICY_CHANGING_INFORMATION"
    elif evidence:
        gap_class = "EXTERNALITY_NOT_PROVED"
        required_action = "PROVE_EXTERNALITY_OR_RECLASSIFY_AS_CONSTRUCTIVE"
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
    }
    return {
        "schema": GAP_SCHEMA,
        "gap_class": gap_class,
        "required_action": required_action,
        "basis": basis,
        "basis_digest": _sha(basis),
        "verification_authority_mutation_allowed": False,
        "terminal_credit": False,
    }


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
    return receipt


def run(
    *,
    repo_root,
    state_path=None,
    verification_frontier_acquisition_provider=None,
    verification_frontier_acquisition_provider_id="ONE_SHOT_ROOT1_ACQUISITION_PROVIDER",
    failure_repair_provider=None,
    capability_synthesis_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    reality_acquisition_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
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
            "max_rounds": v1_max_rounds,
            "max_actions_per_round": v1_max_actions_per_round,
        }
        if state_path is not None:
            kwargs["state_path"] = state_path
        closure = v1.run(**kwargs)

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

        contract = compile_gap_contract(closure)
        transcript.append(
            {
                "repair_round": repair_round,
                "closure_status": closure.get("status"),
                "closure_pass": closure.get("pass") is True,
                "gap_class": contract["gap_class"],
                "basis_digest": contract["basis_digest"],
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
            receipt = _validate_provider_receipt(
                capability_synthesis_provider(deepcopy(contract)),
                provider_kind="CAPABILITY_SYNTHESIS",
            )
        elif gap_class == "STRICT_EXTERNAL_INFORMATION_GAP":
            if reality_acquisition_provider is None:
                return {
                    "schema": SCHEMA,
                    "status": "OPEN__STRICT_EXTERNAL_REALITY_PROVIDER_REQUIRED",
                    "pass": False,
                    "gap_contract": contract,
                    "transcript": transcript,
                    "terminal_authority": False,
                }
            receipt = _validate_provider_receipt(
                reality_acquisition_provider(deepcopy(contract)),
                provider_kind="REALITY_ACQUISITION",
            )
        elif gap_class == "EXTERNALITY_NOT_PROVED":
            return {
                "schema": SCHEMA,
                "status": "OPEN__EXTERNALITY_NOT_PROVED__NO_REALITY_ACQUISITION_AUTHORIZED",
                "pass": False,
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

    return {
        "schema": SCHEMA,
        "status": "OPEN__REPAIR_ROUND_LIMIT_REACHED",
        "pass": False,
        "repair_rounds_executed": rounds,
        "transcript": transcript,
        "terminal_authority": False,
    }
