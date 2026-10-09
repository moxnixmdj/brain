"""Reuse-first one-shot evidence-acquisition provider V1.

This is the minimum adapter between the proof-carrying one-shot minimum-
information contract and the Brain's existing residual-witness retrieval plane.

It deliberately separates four authorities:
1. the one-shot controller states the exact policy-changing information need;
2. retrieval backends discover candidates only;
3. an injected independent verifier decides whether evidence satisfies a bound
   wake condition / exact obligation;
4. an injected frontier committer durably incorporates only verified evidence.

The provider never turns a search hit into truth, never treats an empty search as
nonexistence, and never claims success unless durable frontier change is reported.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import minimum_information_origin_policy_v1 as origin
from canonical.runtime import residual_witness_backend_router_v1 as router
from canonical.runtime import residual_witness_retrieval_compiler_v1 as retrieval

SCHEMA = "PROJECT_BRAIN_ONE_SHOT_EVIDENCE_ACQUISITION_PROVIDER_V1"
_HEX = set("0123456789abcdef")


class EvidenceAcquisitionProviderError(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _valid_sha256(value: Any) -> bool:
    text = _text(value).lower()
    return len(text) == 64 and all(ch in _HEX for ch in text)


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return [value]


def _existing_rows(value: Any) -> list[dict[str, Any]]:
    rows = []
    for raw in _list(value):
        if isinstance(raw, Mapping):
            rows.append(deepcopy(dict(raw)))
    return rows


def _request_to_residual(request: Mapping[str, Any]) -> dict[str, Any]:
    request_id = _text(request.get("request_id"))
    if not request_id:
        raise EvidenceAcquisitionProviderError("MINIMUM_INFORMATION_REQUEST_ID_REQUIRED")
    wake = sorted({_text(x) for x in _list(request.get("wake_conditions")) if _text(x)})
    effect_parts = [
        _text(request.get("required_action")),
        _text(request.get("required_property")),
        _text(request.get("remaining_boundary")),
    ]
    effect = " | ".join(x.replace("_", " ") for x in effect_parts if x)
    required = [x.replace("_", " ") for x in wake]
    if not effect and not required:
        blocker = _text(request.get("blocker"))
        effect = blocker.replace("_", " ") if blocker else "policy changing evidence"

    return {
        "residual_id": request_id,
        "effect": effect,
        "required_capabilities": required,
        "aliases": wake,
        "observables": {},
    }


def _verify_evidence(
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    *,
    request: Mapping[str, Any],
    evidence: Mapping[str, Any],
    source_kind: str,
    source_surface: str,
) -> dict[str, Any] | None:
    raw = verifier({
        "schema": "PROJECT_BRAIN_ONE_SHOT_EVIDENCE_VERIFICATION_QUERY_V1",
        "request": deepcopy(dict(request)),
        "evidence": deepcopy(dict(evidence)),
        "source_kind": source_kind,
        "source_surface": source_surface,
    })
    if not isinstance(raw, Mapping) or raw.get("pass") is not True:
        return None

    out = deepcopy(dict(raw))
    if out.get("independently_verified") is not True:
        raise EvidenceAcquisitionProviderError("INDEPENDENT_VERIFICATION_FLAG_REQUIRED")
    if out.get("verification_authority_mutated") is not False:
        raise EvidenceAcquisitionProviderError("VERIFICATION_AUTHORITY_MUTATION_FORBIDDEN")
    if not _text(out.get("witness_id")):
        raise EvidenceAcquisitionProviderError("VERIFIED_WITNESS_ID_REQUIRED")
    if not _valid_sha256(out.get("independent_receipt_sha256")):
        raise EvidenceAcquisitionProviderError("INDEPENDENT_RECEIPT_SHA256_REQUIRED")
    if not _valid_sha256(out.get("evidence_sha256")):
        raise EvidenceAcquisitionProviderError("VERIFIED_EVIDENCE_SHA256_REQUIRED")

    wake = sorted({_text(x) for x in _list(request.get("wake_conditions")) if _text(x)})
    if wake:
        satisfied = _text(out.get("satisfied_wake_condition"))
        if satisfied not in wake:
            raise EvidenceAcquisitionProviderError(
                "VERIFIED_EVIDENCE_DOES_NOT_SATISFY_BOUND_WAKE_CONDITION"
            )
    elif out.get("closes_exact_obligation") is not True:
        raise EvidenceAcquisitionProviderError(
            "GENERIC_VERIFIED_EVIDENCE_MUST_CLOSE_EXACT_OBLIGATION"
        )
    return out


def _commit_verified_evidence(
    committer: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    *,
    request: Mapping[str, Any],
    verified: Mapping[str, Any],
) -> dict[str, Any]:
    raw = committer({
        "schema": "PROJECT_BRAIN_VERIFIED_EVIDENCE_FRONTIER_COMMIT_V1",
        "request": deepcopy(dict(request)),
        "verified_evidence": deepcopy(dict(verified)),
    })
    if not isinstance(raw, Mapping):
        raise EvidenceAcquisitionProviderError("FRONTIER_COMMIT_RECEIPT_REQUIRED")
    out = deepcopy(dict(raw))
    if out.get("pass") is not True:
        raise EvidenceAcquisitionProviderError("FRONTIER_COMMIT_DID_NOT_PASS")
    if out.get("frontier_changed") is not True:
        raise EvidenceAcquisitionProviderError("VERIFIED_EVIDENCE_DID_NOT_CHANGE_FRONTIER")
    if out.get("verification_authority_mutated") is not False:
        raise EvidenceAcquisitionProviderError(
            "FRONTIER_COMMIT_MUTATED_VERIFICATION_AUTHORITY"
        )
    if not _valid_sha256(out.get("new_frontier_digest")):
        raise EvidenceAcquisitionProviderError("NEW_FRONTIER_DIGEST_REQUIRED")
    if not _valid_sha256(out.get("commit_receipt_sha256")):
        raise EvidenceAcquisitionProviderError("FRONTIER_COMMIT_RECEIPT_SHA256_REQUIRED")
    return out


def _success_receipt(
    *,
    request: Mapping[str, Any],
    verified: Mapping[str, Any],
    commit: Mapping[str, Any],
    trace: list[dict[str, Any]],
    existing_reuse: bool,
    acquisition_attempted: bool,
) -> dict[str, Any]:
    trace_sha = _sha(trace)
    basis = {
        "request_id": request.get("request_id"),
        "witness_id": verified.get("witness_id"),
        "independent_receipt_sha256": verified.get("independent_receipt_sha256"),
        "evidence_sha256": verified.get("evidence_sha256"),
        "satisfied_wake_condition": verified.get("satisfied_wake_condition"),
        "commit_receipt_sha256": commit.get("commit_receipt_sha256"),
        "new_frontier_digest": commit.get("new_frontier_digest"),
        "evidence_trace_sha256": trace_sha,
        "existing_verified_receipt_reused": existing_reuse,
        "acquisition_or_experiment_attempted": acquisition_attempted,
    }
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__EXISTING_VERIFIED_RECEIPT_REUSED_AND_FRONTIER_CHANGED"
            if existing_reuse
            else "PASS__MINIMUM_POLICY_CHANGING_EVIDENCE_VERIFIED_AND_FRONTIER_CHANGED"
        ),
        "pass": True,
        "frontier_changed": True,
        "verification_authority_mutated": False,
        "reuse_or_acquisition_attempted": True,
        "existing_verified_receipt_reused": existing_reuse,
        "acquisition_or_experiment_attempted": acquisition_attempted,
        "new_reality_consumed": bool(acquisition_attempted),
        "evidence_trace_sha256": trace_sha,
        "receipt_sha256": _sha(basis),
        "new_frontier_digest": commit.get("new_frontier_digest"),
        "commit_receipt_sha256": commit.get("commit_receipt_sha256"),
        "verified_witness_id": verified.get("witness_id"),
        "satisfied_wake_condition": verified.get("satisfied_wake_condition"),
        "trace": trace,
        "terminal_authority": False,
    }


def _open_receipt(
    *,
    status: str,
    trace: list[dict[str, Any]],
    lookup_attempted: bool,
    acquisition_attempted: bool,
) -> dict[str, Any]:
    trace_sha = _sha(trace)
    basis = {
        "status": status,
        "evidence_trace_sha256": trace_sha,
        "lookup_attempted": lookup_attempted,
        "acquisition_attempted": acquisition_attempted,
    }
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": False,
        "frontier_changed": False,
        "verification_authority_mutated": False,
        "reuse_or_acquisition_attempted": bool(lookup_attempted or acquisition_attempted),
        "existing_receipt_lookup_attempted": lookup_attempted,
        "existing_verified_receipt_reused": False,
        "acquisition_or_experiment_attempted": acquisition_attempted,
        "new_reality_consumed": acquisition_attempted,
        "evidence_trace_sha256": trace_sha,
        "receipt_sha256": _sha(basis),
        "trace": trace,
        "terminal_authority": False,
    }


def make_provider(
    *,
    independent_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    frontier_committer: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    existing_receipt_lookup: Callable[[Mapping[str, Any]], Any] | None = None,
    backend_providers: Mapping[
        str, Callable[[Mapping[str, Any]], Mapping[str, Any]]
    ] | None = None,
    discovery_delegated: bool = False,
    source_scope: Mapping[str, Any] | None = None,
    max_backend_actions: int = 12,
) -> Callable[[Mapping[str, Any]], dict[str, Any]]:
    """Build a V2 evidence-acquisition provider.

    The returned provider is safe to hand directly to
    one_shot_reality_closure_v2.run(..., evidence_acquisition_provider=...).

    It does not invent verification or commit authority. Those remain injected.
    """
    if not callable(independent_verifier):
        raise ValueError("INDEPENDENT_VERIFIER_CALLABLE_REQUIRED")
    if not callable(frontier_committer):
        raise ValueError("FRONTIER_COMMITTER_CALLABLE_REQUIRED")
    if existing_receipt_lookup is not None and not callable(existing_receipt_lookup):
        raise ValueError("EXISTING_RECEIPT_LOOKUP_MUST_BE_CALLABLE")
    if not isinstance(discovery_delegated, bool):
        raise ValueError("DISCOVERY_DELEGATED_BOOLEAN_REQUIRED")
    if isinstance(max_backend_actions, bool) or not isinstance(max_backend_actions, int):
        raise ValueError("MAX_BACKEND_ACTIONS_INT_REQUIRED")
    if max_backend_actions < 1 or max_backend_actions > 128:
        raise ValueError("MAX_BACKEND_ACTIONS_OUT_OF_RANGE")

    providers = dict(backend_providers or {})
    configured_scope = deepcopy(dict(source_scope)) if isinstance(source_scope, Mapping) else {
        "kind": origin.UNBOUND_SOURCE,
    }

    def provider(contract: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(contract, Mapping):
            raise EvidenceAcquisitionProviderError("GAP_CONTRACT_MAPPING_REQUIRED")
        minimum = contract.get("minimum_information_contract")
        if not isinstance(minimum, Mapping):
            raise EvidenceAcquisitionProviderError("MINIMUM_INFORMATION_CONTRACT_REQUIRED")
        requests = [
            deepcopy(dict(x))
            for x in (minimum.get("requests") or [])
            if isinstance(x, Mapping)
        ]
        if int(minimum.get("request_count", -1)) != len(requests):
            raise EvidenceAcquisitionProviderError("MINIMUM_INFORMATION_REQUEST_COUNT_MISMATCH")
        if not requests:
            raise EvidenceAcquisitionProviderError("MINIMUM_INFORMATION_REQUESTS_EMPTY")

        trace: list[dict[str, Any]] = []
        lookup_attempted = False
        acquisition_attempted = False

        for request in requests:
            request_id = _text(request.get("request_id"))
            if not request_id:
                raise EvidenceAcquisitionProviderError("REQUEST_ID_REQUIRED")

            if existing_receipt_lookup is not None:
                lookup_attempted = True
                existing = _existing_rows(existing_receipt_lookup(deepcopy(request)))
                trace.append({
                    "request_id": request_id,
                    "stage": "EXISTING_CONTENT_ADDRESSED_RECEIPT_LOOKUP",
                    "candidate_count": len(existing),
                })
                for row in existing:
                    verified = _verify_evidence(
                        independent_verifier,
                        request=request,
                        evidence=row,
                        source_kind="EXISTING_CONTENT_ADDRESSED_RECEIPT",
                        source_surface=_text(row.get("source_surface")) or "EXISTING_RECEIPT",
                    )
                    if verified is None:
                        continue
                    commit = _commit_verified_evidence(
                        frontier_committer,
                        request=request,
                        verified=verified,
                    )
                    trace.append({
                        "request_id": request_id,
                        "stage": "EXISTING_RECEIPT_VERIFIED_AND_COMMITTED",
                        "witness_id": verified.get("witness_id"),
                        "commit_receipt_sha256": commit.get("commit_receipt_sha256"),
                    })
                    return _success_receipt(
                        request=request,
                        verified=verified,
                        commit=commit,
                        trace=trace,
                        existing_reuse=True,
                        acquisition_attempted=False,
                    )

            origin_result = origin.route({
                "decision_relevant": True,
                "context_value_bound": False,
                "information_owner": origin.EXTERNAL_WORLD,
                "source_scope": deepcopy(configured_scope),
                "discovery_delegated": discovery_delegated,
            })
            trace.append({
                "request_id": request_id,
                "stage": "MINIMUM_INFORMATION_ORIGIN_ROUTING",
                "action": origin_result.get("action"),
                "external_research_authorized": (
                    origin_result.get("external_research_authorized") is True
                ),
                "bound_source_only": origin_result.get("bound_source_only") is True,
            })
            if origin_result.get("pass") is not True:
                continue
            if origin_result.get("action") not in {
                "RESEARCH_MINIMUM_AUTHENTICATED_FACT",
                "OBSERVE_BOUND_SOURCE_ONLY",
            }:
                continue

            residual = _request_to_residual(request)
            program = retrieval.compile_residual(residual)
            state = retrieval.initial_state(program)

            for step in range(max_backend_actions):
                outcome = router.execute_next(
                    program,
                    state,
                    providers=providers,
                )
                acquisition_attempted = True
                result = outcome.get("result")
                normalized = dict(result) if isinstance(result, Mapping) else {}
                candidates = [
                    deepcopy(dict(x))
                    for x in (normalized.get("candidates") or [])
                    if isinstance(x, Mapping)
                ]
                action = outcome.get("action")
                action = dict(action) if isinstance(action, Mapping) else {}
                trace.append({
                    "request_id": request_id,
                    "stage": "RETRIEVAL_BACKEND",
                    "step": step,
                    "status": outcome.get("status"),
                    "surface": action.get("surface") or normalized.get("surface"),
                    "query_id": action.get("query_id") or normalized.get("query_id"),
                    "candidate_count": len(candidates),
                })

                for candidate in candidates:
                    verified = _verify_evidence(
                        independent_verifier,
                        request=request,
                        evidence=candidate,
                        source_kind="RETRIEVED_CANDIDATE",
                        source_surface=_text(candidate.get("retrieval_surface"))
                        or _text(normalized.get("surface")),
                    )
                    if verified is None:
                        continue
                    commit = _commit_verified_evidence(
                        frontier_committer,
                        request=request,
                        verified=verified,
                    )
                    trace.append({
                        "request_id": request_id,
                        "stage": "RETRIEVED_EVIDENCE_VERIFIED_AND_COMMITTED",
                        "witness_id": verified.get("witness_id"),
                        "commit_receipt_sha256": commit.get("commit_receipt_sha256"),
                    })
                    return _success_receipt(
                        request=request,
                        verified=verified,
                        commit=commit,
                        trace=trace,
                        existing_reuse=False,
                        acquisition_attempted=True,
                    )

                next_state = outcome.get("state")
                if isinstance(next_state, Mapping):
                    state = deepcopy(dict(next_state))
                next_action = outcome.get("next_action")
                if isinstance(next_action, Mapping) and next_action.get("action") == "STOP":
                    break

        status = (
            "OPEN__NO_VERIFIED_POLICY_CHANGING_WITNESS_YET"
            if acquisition_attempted
            else "OPEN__REUSE_OR_DISCOVERY_DID_NOT_AUTHORIZE_OR_YIELD_VERIFIED_EVIDENCE"
        )
        return _open_receipt(
            status=status,
            trace=trace,
            lookup_attempted=lookup_attempted,
            acquisition_attempted=acquisition_attempted,
        )

    return provider
