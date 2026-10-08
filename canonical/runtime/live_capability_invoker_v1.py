"""Universal live capability invocation adapter V1.

This is the execution half of R1. The ownership ontology says what the live
Brain owns; this module gives every admitted ownership identity one deterministic
front-door invocation contract.

It deliberately does not solve semantic selection. Choosing the right capability
from arbitrary intent is R2. Once a capability identity is selected, this adapter
must either dispatch that exact identity or fail closed.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import autonomous_verified_self_improvement_v1 as self_improvement
from canonical.runtime import certificate_gated_selected_route_runtime_entrypoint_v2 as certified_route
from canonical.runtime import h100_verified_capability_registry_v8 as h100
from canonical.runtime.verified_bound_capability_execution_adapter_v1 import execute as execute_bound

SCHEMA = "PROJECT_BRAIN_LIVE_CAPABILITY_INVOKER_V1"
ROOT = Path(__file__).resolve().parents[2]

KINDS = (
    "ENGINE",
    "BOUND_CAPABILITY",
    "H100_VERIFIED_CAPABILITY",
    "ACTIVE_VERIFIED_LEARNED_SKILL",
    "CERTIFIED_ROUTE",
)


class LiveCapabilityInvocationError(ValueError):
    pass


def classify(capability_id: str) -> dict[str, str]:
    cid = str(capability_id or "").strip()
    if not cid:
        raise LiveCapabilityInvocationError("CAPABILITY_ID_REQUIRED")
    if cid.startswith("engine:") and cid[7:]:
        return {"kind": "ENGINE", "local_id": cid[7:]}
    if cid.startswith("bound:") and cid[6:]:
        return {"kind": "BOUND_CAPABILITY", "local_id": cid[6:]}
    if cid.startswith("h100:") and cid[5:]:
        raw = cid[5:]
        base, sep, route = raw.partition("@")
        if not base:
            raise LiveCapabilityInvocationError("H100_CAPABILITY_ID_INVALID")
        return {
            "kind": "H100_VERIFIED_CAPABILITY",
            "local_id": base,
            "route": route if sep else "",
        }
    if cid.startswith("skill:") and cid[6:]:
        return {"kind": "ACTIVE_VERIFIED_LEARNED_SKILL", "local_id": cid}
    if cid.startswith("certified_route:") and cid[16:]:
        return {"kind": "CERTIFIED_ROUTE", "local_id": cid[16:]}
    raise LiveCapabilityInvocationError("OWNED_CAPABILITY_ID_KIND_UNKNOWN:" + cid)


def coverage(capability_ids: Sequence[str]) -> dict[str, Any]:
    if not isinstance(capability_ids, Sequence) or isinstance(capability_ids, (str, bytes)):
        raise LiveCapabilityInvocationError("CAPABILITY_IDS_NOT_SEQUENCE")
    supported: list[str] = []
    missing: list[dict[str, str]] = []
    kinds: dict[str, int] = {kind: 0 for kind in KINDS}
    for raw in capability_ids:
        cid = str(raw)
        try:
            row = classify(cid)
        except LiveCapabilityInvocationError as exc:
            missing.append({"capability_id": cid, "reason": str(exc)})
            continue
        supported.append(cid)
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
    passed = len(missing) == 0 and len(supported) == len(capability_ids)
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__EVERY_LIVE_OWNED_CAPABILITY_HAS_UNIVERSAL_INVOCATION_CONTRACT"
            if passed
            else "FAIL_CLOSED__LIVE_CAPABILITY_INVOCATION_COVERAGE_GAP"
        ),
        "pass": passed,
        "capability_count": len(capability_ids),
        "supported_capability_count": len(supported),
        "missing_capability_count": len(missing),
        "missing": missing,
        "kind_counts": kinds,
        "single_invocation_api": "unified_cognitive_fabric_v1.run(mode=LIVE_CAPABILITY)",
        "semantic_selection_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def _match_h100_resolution(
    capability_id: str,
    expected_route: str,
    resolution: Mapping[str, Any],
) -> None:
    match = resolution.get("match")
    if not isinstance(match, Mapping):
        raise LiveCapabilityInvocationError("H100_RESOLUTION_MATCH_MISSING")
    if str(match.get("capability_id") or "") != capability_id:
        raise LiveCapabilityInvocationError(
            "H100_RESOLUTION_CAPABILITY_MISMATCH:"
            + str(match.get("capability_id") or "")
        )
    if expected_route and str(match.get("route") or "") != expected_route:
        raise LiveCapabilityInvocationError(
            "H100_RESOLUTION_ROUTE_MISMATCH:" + str(match.get("route") or "")
        )


def _invoke_h100(local_id: str, expected_route: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    operation = str(payload.get("operation") or "INVOKE").strip().upper()
    if operation == "INVOKE":
        if expected_route:
            raise LiveCapabilityInvocationError(
                "ROUTE_QUALIFIED_H100_REQUIRES_RESOLUTION_BOUND_INVOCATION"
            )
        raw = payload.get("inputs")
        if raw is None:
            raw = {k: deepcopy(v) for k, v in payload.items() if k != "operation"}
        if not isinstance(raw, Mapping):
            raise LiveCapabilityInvocationError("H100_INVOKE_INPUTS_NOT_OBJECT")
        out = h100.invoke(local_id, raw)
        return {"pass": True, "status": "PASS__EXACT_H100_CAPABILITY_INVOKED", "result": out}

    if operation in {"RESOLVE", "RESOLVE_AND_PREDICT"}:
        rows = payload.get("rows")
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
            raise LiveCapabilityInvocationError("H100_ROWS_NOT_SEQUENCE")
        resolution = h100.resolve_verified_capability(
            rows,
            target=str(payload.get("target") or ""),
            input_name=payload.get("input_name"),
            exact_nrmse=float(payload.get("exact_nrmse", 1e-8)),
        )
        _match_h100_resolution(local_id, expected_route, resolution)
        result: dict[str, Any] = {
            "resolution": deepcopy(dict(resolution)),
            "capability_id": local_id,
            "route": expected_route or str(resolution["match"].get("route") or ""),
        }
        if operation == "RESOLVE_AND_PREDICT":
            point = payload.get("point")
            if not isinstance(point, Mapping):
                raise LiveCapabilityInvocationError("H100_POINT_NOT_OBJECT")
            result["prediction"] = h100.predict(resolution, point)
        return {
            "pass": True,
            "status": "PASS__EXACT_H100_CAPABILITY_RESOLVED"
            if operation == "RESOLVE"
            else "PASS__EXACT_H100_CAPABILITY_RESOLVED_AND_PREDICTED",
            "result": result,
        }

    if operation == "PREDICT":
        resolution = payload.get("resolution")
        point = payload.get("point")
        if not isinstance(resolution, Mapping):
            raise LiveCapabilityInvocationError("H100_RESOLUTION_NOT_OBJECT")
        if not isinstance(point, Mapping):
            raise LiveCapabilityInvocationError("H100_POINT_NOT_OBJECT")
        _match_h100_resolution(local_id, expected_route, resolution)
        return {
            "pass": True,
            "status": "PASS__EXACT_H100_CAPABILITY_PREDICTED",
            "result": {
                "prediction": h100.predict(resolution, point),
                "capability_id": local_id,
                "route": expected_route or str(resolution["match"].get("route") or ""),
            },
        }

    raise LiveCapabilityInvocationError("H100_OPERATION_INVALID:" + operation)


def _invoke_skill(
    skill_id: str,
    problem: Mapping[str, Any],
    *,
    options: Mapping[str, Any],
) -> dict[str, Any]:
    state_path = options.get("state_path", self_improvement.DEFAULT_STATE_PATH)
    scope_id = str(options.get("scope_id") or "scope")
    known_absent = options.get("known_absent_invalidators", ())
    state = self_improvement.load_state(state_path)
    selected = self_improvement._select_active_skill(
        problem,
        state,
        scope_id=scope_id,
        known_absent_invalidators=known_absent,
    )
    if not isinstance(selected, Mapping):
        raise LiveCapabilityInvocationError("REQUESTED_ACTIVE_SKILL_NOT_APPLICABLE")
    if str(selected.get("skill_id") or "") != skill_id:
        raise LiveCapabilityInvocationError(
            "REQUESTED_ACTIVE_SKILL_NOT_SELECTED:" + str(selected.get("skill_id") or "")
        )
    out = self_improvement.run_learning_episode(
        problem,
        repo_root=ROOT,
        state_path=state_path,
        proposal_packets=options.get("proposal_packets"),
        resolved_semantics_bindings=options.get("resolved_semantics_bindings"),
        effect_root=options.get("effect_root"),
        episode_id=str(options.get("episode_id") or "episode"),
        scope_id=scope_id,
        episode_verification_binding=options.get("episode_verification_binding"),
        skill_verification_binding=options.get("skill_verification_binding"),
        resume_binding=options.get("resume_binding"),
        retry_context=options.get("retry_context"),
        known_absent_invalidators=known_absent,
        proposal_provider=options.get("proposal_provider"),
        capability_expander=options.get("capability_expander"),
        proposal_provider_id=str(options.get("proposal_provider_id") or "HOST_GENERAL_COGNITION_SUBSTRATE"),
        proposal_provider_max_candidates=int(options.get("proposal_provider_max_candidates", 4)),
        capability_expander_id=str(options.get("capability_expander_id") or "HOST_CAPABILITY_EXPANDER"),
        max_capability_expansions=int(options.get("max_capability_expansions", 4)),
    )
    if out.get("reused_skill_id") != skill_id:
        raise LiveCapabilityInvocationError("LEARNED_SKILL_IDENTITY_DRIFT")
    return deepcopy(dict(out))


def _invoke_certified_route(route_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    context = payload.get("context")
    route_payload = payload.get("route_payload")
    if not isinstance(context, Mapping):
        raise LiveCapabilityInvocationError("CERTIFIED_ROUTE_CONTEXT_NOT_OBJECT")
    if not isinstance(route_payload, Mapping):
        raise LiveCapabilityInvocationError("CERTIFIED_ROUTE_PAYLOAD_NOT_OBJECT")
    registry = certified_route.load_registry()
    receipts, _ = certified_route._verified_rows(registry)
    selected = certified_route.select_certified_route(
        actual_context_digest=certified_route.context_digest(context),
        receipts=receipts,
    )
    if selected.route_id != route_id:
        raise LiveCapabilityInvocationError(
            "CERTIFIED_ROUTE_IDENTITY_MISMATCH:" + selected.route_id
        )
    out = certified_route.dispatch(context, route_payload)
    return {"pass": True, **dict(out)}


def invoke(
    capability_id: str,
    payload: Mapping[str, Any],
    *,
    engine_runner: Callable[[str, Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
    options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise LiveCapabilityInvocationError("CAPABILITY_PAYLOAD_NOT_OBJECT")
    opts = dict(options or {})
    row = classify(capability_id)
    kind = row["kind"]
    local_id = row["local_id"]

    if kind == "ENGINE":
        nested = engine_runner(local_id, payload, opts)
        if not isinstance(nested, Mapping):
            raise LiveCapabilityInvocationError("ENGINE_RESULT_NOT_OBJECT")
        passed = (
            nested.get("inner_pass") is True
            if nested.get("status") == "FABRIC_DISPATCH_COMPLETE"
            else nested.get("pass") is True
        )
        return {
            "schema": SCHEMA,
            "status": (
                "PASS__EXACT_ENGINE_CAPABILITY_DISPATCHED"
                if passed else "FAIL__EXACT_ENGINE_CAPABILITY_DISPATCHED"
            ),
            "pass": passed,
            "capability_id": capability_id,
            "result": deepcopy(dict(nested)),
        }

    if kind == "BOUND_CAPABILITY":
        out = execute_bound(local_id, inputs=dict(payload))
        return {
            "schema": SCHEMA,
            "status": "PASS__EXACT_BOUND_CAPABILITY_DISPATCHED"
            if out.get("pass") is True else "FAIL__EXACT_BOUND_CAPABILITY_DISPATCHED",
            "pass": out.get("pass") is True,
            "capability_id": capability_id,
            "result": deepcopy(dict(out)),
        }

    if kind == "H100_VERIFIED_CAPABILITY":
        out = _invoke_h100(local_id, row.get("route", ""), payload)
        return {
            "schema": SCHEMA,
            "capability_id": capability_id,
            **out,
        }

    if kind == "ACTIVE_VERIFIED_LEARNED_SKILL":
        out = _invoke_skill(local_id, payload, options=opts)
        return {
            "schema": SCHEMA,
            "status": out.get("status"),
            "pass": out.get("pass") is True,
            "capability_id": capability_id,
            "result": out,
        }

    if kind == "CERTIFIED_ROUTE":
        out = _invoke_certified_route(local_id, payload)
        return {
            "schema": SCHEMA,
            "status": out.get("status"),
            "pass": out.get("pass", True) is True,
            "capability_id": capability_id,
            "result": out,
        }

    raise LiveCapabilityInvocationError("CAPABILITY_KIND_UNIMPLEMENTED:" + kind)
