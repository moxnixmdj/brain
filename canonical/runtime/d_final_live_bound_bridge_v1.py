"""Live binding bridge for D-final stdlib bound capabilities V1.

This module is the only D-final-specific logic needed by the universal live
capability invoker for the initial stdlib class.

It requires:
- an active D execution epoch;
- the requested live ownership identity admitted by that epoch;
- every provider/verifier/registry byte present in the epoch material closure;
- the registry-entry hash equal to the epoch capability-contract hash;
- the exact member adapter blob present in the epoch material closure.

Only then does it call the independently verified minimal stdlib provider.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import d_finality_execution_epoch_v1 as d_epoch
from canonical.runtime import d_final_bound_stdlib_provider_v1 as provider

SCHEMA="PROJECT_BRAIN_D_FINAL_LIVE_BOUND_BRIDGE_V1"

PROVIDER_CLOSURE=(
    "canonical/runtime/d_final_bound_stdlib_provider_v1.py",
    "canonical/runtime/bound_capability_execution_verifier_v1.py",
    "canonical/runtime/capability_planner.py",
    "canonical/runtime/capability_execution_trace_capsule_v1.py",
    "canonical/runtime/composition_state_capsule_v1.py",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
)


class DFinalLiveBoundBridgeError(ValueError):
    pass


def active_epoch_or_none():
    try:
        return d_epoch.current_epoch()
    except d_epoch.DFinalityError as exc:
        if str(exc)=="NO_ACTIVE_D_FINALITY_EPOCH":
            return None
        raise


def invoke(
    ownership_capability_id: str,
    local_capability_id: str,
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    root=Path(repo_root).resolve()
    epoch=d_epoch.require_capability(ownership_capability_id)

    for rel in PROVIDER_CLOSURE:
        d_epoch.require_material(rel,repo_root=root)

    registry_path=root/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    inspected=provider.inspect(local_capability_id,registry_path=registry_path)
    if inspected["registry_entry_sha256"]!=epoch.capability_contract_sha256:
        raise DFinalLiveBoundBridgeError(
            "D_EPOCH_CAPABILITY_CONTRACT_MISMATCH:"+ownership_capability_id
        )

    entry=inspected["entry"]
    source=entry.get("source") or {}
    adapter_rel=str(source.get("adapter_path") or "").strip()
    if not adapter_rel:
        module_name=str(entry.get("adapter_module") or "").strip()
        if not module_name:
            raise DFinalLiveBoundBridgeError("D_EPOCH_ADAPTER_IDENTITY_MISSING")
        adapter_rel="canonical/runtime/bound_capabilities/"+module_name+".py"

    d_epoch.require_material(adapter_rel,repo_root=root)
    expected_blob=dict(epoch.material_bindings).get(adapter_rel)
    if expected_blob is None:
        raise DFinalLiveBoundBridgeError("D_EPOCH_ADAPTER_NOT_BOUND:"+adapter_rel)

    out=provider.execute(
        local_capability_id,
        inputs=dict(payload),
        repo_root=root,
        registry_path=registry_path,
        adapter_path=root/adapter_rel,
        expected_adapter_git_blob_sha=expected_blob,
        expected_registry_entry_sha256=epoch.capability_contract_sha256,
    )
    if out.get("pass") is not True:
        raise DFinalLiveBoundBridgeError(
            "D_FINAL_BOUND_PROVIDER_FAILED:"+";".join(out.get("errors") or [])
        )
    return {
        "schema":SCHEMA,
        "status":"PASS__D_FINAL_LIVE_BOUND_BRIDGE",
        "pass":True,
        "capability_id":ownership_capability_id,
        "result":out,
    }
