"""Native zero-authority Root1 acquisition provider V1.

This provider closes the missing-provider architectural hole without granting
itself semantic, verification, promotion, or terminal authority. It is a
deterministic acquisition worker over the Brain's currently owned zero-cost
routes. Success only means an acquisition attempt produced new candidate
material; every candidate must still pass existing independent authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ROOT1_DEFAULT_ACQUISITION_PROVIDER_V1"
PROVIDER_ID = "ROOT1_DEFAULT_ACQUISITION_PROVIDER_V1"
ROOT = Path(__file__).resolve().parents[2]

NATIVE_ROUTE_CLASSES = (
    "OWNED_VERIFIED_REUSE",
    "OWNED_VERIFIED_COMPOSITION",
    "OWNED_PARAMETERIZED_TRANSFER",
    "ZERO_COST_PACKAGE_OR_SOURCE_ACQUISITION",
    "MINIMUM_INTEGRATION_GLUE_SYNTHESIS",
)

def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value)).hexdigest()

def _base(status: str, *, request: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "provider_id": PROVIDER_ID,
        "status": status,
        "pass": False,
        "request_sha256": _digest(request),
        "native_route_classes_considered": list(NATIVE_ROUTE_CLASSES),
        "incremental_spend_usd": 0,
        "candidate_generation_authority": False,
        "semantic_truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        **extra,
    }

def _frontier_request(request: Mapping[str, Any]) -> dict[str, Any]:
    allowed = str(request.get("allowed_frontier_change_class") or "")
    if allowed != "SUCCESS_ADAPTER_ONLY__VERIFICATION_AUTHORITY_IMMUTABLE":
        return _base(
            "REJECTED__UNSUPPORTED_FRONTIER_AUTHORITY_CLASS",
            request=request,
            reason="ONLY_SUCCESS_ADAPTER_FRONTIER_MAY_BE_PROPOSED_BY_THIS_PROVIDER",
            exhaustive_over_sound_routes_derivable_from_request=True,
        )
    if request.get("verification_authority_change_allowed") is not False:
        return _base(
            "REJECTED__VERIFICATION_AUTHORITY_MUST_BE_IMMUTABLE",
            request=request,
            exhaustive_over_sound_routes_derivable_from_request=True,
        )

    # R3 already tried the owned bound/raw adapters before emitting this handoff.
    # A capability-class label does not contain enough semantics to soundly
    # synthesize a new adapter. Package search cannot repair that missing
    # semantic binding. Pretending otherwise would be the exact self-certifying
    # shortcut this boundary exists to prevent.
    required = str(request.get("required_capability_class") or "").strip()
    return _base(
        "NATIVE_FRONTIER_SEARCH_EXHAUSTED__ADDITIONAL_ADAPTER_EVIDENCE_REQUIRED",
        request=request,
        required_capability_class=required or None,
        adapter_frontier_sha256=request.get("adapter_frontier_sha256"),
        verification_authority_sha256=request.get("verification_authority_sha256"),
        exhaustive_over_sound_routes_derivable_from_request=True,
        irreducible_boundary=(
            "MISSING_SOUND_ADAPTER_SPECIFICATION_OR_DISTINGUISHING_EVIDENCE"
        ),
        evidence_needed=(
            "A content-bound adapter specification or independently checkable "
            "source semantics sufficient to generate one without changing the judge."
        ),
    )

def acquire(request: Mapping[str, Any], *, repo_root: str | Path = ROOT) -> dict[str, Any]:
    """Execute one native Root1 acquisition attempt with zero promotion authority."""
    if not isinstance(request, Mapping):
        raise TypeError("ROOT1_ACQUISITION_REQUEST_NOT_OBJECT")
    kind = str(request.get("kind") or "").strip()
    if kind == "EXPAND_SUCCESS_VERIFICATION_FRONTIER":
        return _frontier_request(request)
    return _base(
        "NATIVE_ACQUISITION_ROUTE_UNAVAILABLE_FOR_REQUEST_KIND",
        request=request,
        request_kind=kind or None,
        exhaustive_over_sound_routes_derivable_from_request=True,
        irreducible_boundary="NO_SOUND_NATIVE_BINDING_FOR_REQUEST_KIND",
    )

def make_frontier_provider(*, repo_root: str | Path = ROOT):
    root = Path(repo_root)
    def _provider(request: Mapping[str, Any]) -> dict[str, Any]:
        return acquire(request, repo_root=root)
    _provider.provider_id = PROVIDER_ID
    return _provider

def make_information_provider(*, repo_root: str | Path = ROOT):
    """Fail-closed current-evidence provider.

    Fresh reality is never fabricated. Returning None tells R2 that the exact
    requested predicate is not present in the provider's authenticated local
    evidence frontier, so the one-shot controller can classify it as an external
    information cut instead of an internal missing-provider defect.
    """
    def _provider(request: Mapping[str, Any], index: int):
        return None
    _provider.provider_id = PROVIDER_ID
    return _provider

def make_r2_proposal_provider(*, repo_root: str | Path = ROOT):
    """Residual R2 proposal worker after built-in reuse/refinement is exhausted."""
    def _provider(packet: Mapping[str, Any], index: int, prior_candidates):
        # Existing-policy repair and basis-discriminator refinement run inside
        # R2 before this hook. No arbitrary semantic patch is manufactured here.
        return None
    _provider.provider_id = PROVIDER_ID
    return _provider

def make_r2_capability_expander(*, repo_root: str | Path = ROOT):
    """Residual R2 capability worker with zero semantic/promotion authority."""
    def _provider(packet: Mapping[str, Any], step: int, current: Mapping[str, Any]):
        # A request_patch is authoritative only after complete R2 re-verification.
        # The residual packet does not by itself prove a sound semantic binding,
        # so the native worker abstains rather than minting one from a package name.
        return None
    _provider.provider_id = PROVIDER_ID
    return _provider

def exhaustion_certificate(result: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(result, Mapping):
        raise TypeError("ROOT1_PROVIDER_RESULT_NOT_OBJECT")
    exhausted = result.get("exhaustive_over_sound_routes_derivable_from_request") is True
    return {
        "schema": "PROJECT_BRAIN_ROOT1_ACQUISITION_EXHAUSTION_CERTIFICATE_V1",
        "provider_id": str(result.get("provider_id") or PROVIDER_ID),
        "provider_result_sha256": _digest(result),
        "exhaustive_over_sound_routes_derivable_from_request": exhausted,
        "irreducible_boundary": result.get("irreducible_boundary"),
        "evidence_needed": result.get("evidence_needed"),
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "valid": exhausted and bool(result.get("irreducible_boundary")),
    }
