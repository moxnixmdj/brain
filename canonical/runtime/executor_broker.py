#!/usr/bin/env python3
"""Provider-neutral executor admission for verification capsules.

The broker is intentionally boring: it does not create infrastructure and it
never treats one machine/provider as authority. It only selects from already
available executor attestations that satisfy the capsule's declared policy.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import pathlib
import sys
from typing import Any, Iterable

ROOT=pathlib.Path(__file__).resolve().parents[2]
_OBS_PATH=ROOT/"canonical"/"runtime"/"continuous_obs_runtime.py"
_OBS_SPEC=importlib.util.spec_from_file_location("project_brain_executor_continuous_obs",_OBS_PATH)
if _OBS_SPEC is None or _OBS_SPEC.loader is None:
    raise RuntimeError("CONTINUOUS_OBS_RUNTIME_LOAD_FAILED")
continuous_obs_runtime=importlib.util.module_from_spec(_OBS_SPEC)
sys.modules[_OBS_SPEC.name]=continuous_obs_runtime
_OBS_SPEC.loader.exec_module(continuous_obs_runtime)


class ExecutorUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ExecutorAttestation:
    executor_id: str
    provider: str
    status: str
    platforms: tuple[str, ...]
    incremental_spend_usd: float
    hard_zero_spend: bool
    gpu_allowed: bool
    heavy_compute_allowed: bool
    capabilities: tuple[str, ...] = ()


def _norm_platform(value: str) -> str:
    v=str(value or "").strip().lower()
    aliases={
        "win32":"windows","cygwin":"windows","msys":"windows",
        "linux2":"linux","darwin":"darwin",
    }
    return aliases.get(v,v)


def _from_mapping(raw: dict[str, Any]) -> ExecutorAttestation:
    return ExecutorAttestation(
        executor_id=str(raw.get("executor_id") or "").strip(),
        provider=str(raw.get("provider") or "").strip(),
        status=str(raw.get("status") or "").strip().upper(),
        platforms=tuple(_norm_platform(x) for x in (raw.get("platforms") or [])),
        incremental_spend_usd=float(raw.get("incremental_spend_usd",0.0)),
        hard_zero_spend=raw.get("hard_zero_spend") is True,
        gpu_allowed=raw.get("gpu_allowed") is True,
        heavy_compute_allowed=raw.get("heavy_compute_allowed") is True,
        capabilities=tuple(str(x) for x in (raw.get("capabilities") or [])),
    )


def select_executor(
    capsule: dict[str, Any],
    executors: Iterable[dict[str, Any] | ExecutorAttestation],
) -> ExecutorAttestation:
    obs=continuous_obs_runtime.validate_context(
        capsule.get("continuous_obs"),
        root=ROOT,
    )
    if not obs.get("pass"):
        raise ExecutorUnavailable(
            "CONTINUOUS_OBS_BLOCKED:"+repr(obs.get("errors") or ["UNKNOWN"])
        )
    policy=dict(capsule.get("executor_policy") or {})
    required=_norm_platform(policy.get("required_platform") or "")
    allow_any=required in {"","any","platform_neutral"}

    rejected=[]
    for raw in executors:
        ex=raw if isinstance(raw,ExecutorAttestation) else _from_mapping(raw)
        reason=None
        if not ex.executor_id:
            reason="EXECUTOR_ID_MISSING"
        elif ex.status!="AVAILABLE":
            reason="EXECUTOR_NOT_AVAILABLE"
        elif ex.incremental_spend_usd!=0.0:
            reason="NONZERO_INCREMENTAL_SPEND"
        elif not ex.hard_zero_spend:
            reason="HARD_ZERO_SPEND_NOT_ATTESTED"
        elif not allow_any and required not in ex.platforms:
            reason="PLATFORM_MISMATCH"
        elif policy.get("gpu_allowed") is False and ex.gpu_allowed:
            reason="GPU_POLICY_MISMATCH"
        elif policy.get("heavy_compute_allowed") is False and ex.heavy_compute_allowed:
            reason="HEAVY_COMPUTE_POLICY_MISMATCH"

        if reason is None:
            return ex
        rejected.append({"executor_id":ex.executor_id,"reason":reason})

    raise ExecutorUnavailable(
        "EXECUTOR_UNAVAILABLE:"+repr(rejected)
    )


def classify_platform_requirement(capsule: dict[str, Any]) -> str:
    required=_norm_platform(
        (capsule.get("executor_policy") or {}).get("required_platform") or ""
    )
    if required in {"","any","platform_neutral"}:
        return "PLATFORM_NEUTRAL"
    return "PLATFORM_CERTIFICATION_REQUIRED:"+required
