from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import astra_runtime as astra
from canonical.runtime import load_bearing_result_propagation_gate_v1 as gate

_ORIGINAL_WRITE_STATEJ = astra.write_statej
_ORIGINAL_CONTEXT_RESULT_MAP = astra._context_result_map
_INSTALLED = False


class GuardedAstraError(ValueError):
    pass


def _certify_or_verify_record(state: Mapping[str, Any], rec: dict[str, Any]) -> None:
    if "result" not in rec:
        return
    mission_id = str(state.get("mission_id") or "")
    mission_sha256 = str(state.get("mission_sha256") or "")
    step_index = rec.get("step_index")
    step_id = str(rec.get("step_id") or "")
    verification_ok = bool(rec.get("ok"))
    certificate = rec.get("load_bearing_result_certificate")
    if certificate is None:
        certificate = gate.certify_result(
            rec["result"],
            mission_id=mission_id,
            mission_sha256=mission_sha256,
            step_index=step_index,
            step_id=step_id,
            verification_ok=verification_ok,
        )
        rec["load_bearing_result_certificate"] = certificate
    verdict = gate.verify_certificate(
        rec["result"],
        certificate,
        mission_id=mission_id,
        mission_sha256=mission_sha256,
        step_index=step_index,
        step_id=step_id,
        verification_ok=verification_ok,
    )
    if verdict.get("status") != "PASS":
        raise GuardedAstraError(
            "LOAD_BEARING_RESULT_CERTIFICATE_INVALID:"
            + str(step_index)
            + ":"
            + "|".join(verdict.get("errors") or ["UNKNOWN"])
        )


def guard_state_for_write(state: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(state, dict):
        raise GuardedAstraError("STATE_MUTABLE_MAPPING_REQUIRED")
    for rec in state.get("history", []):
        if not isinstance(rec, dict):
            raise GuardedAstraError("HISTORY_RECORD_INVALID")
        _certify_or_verify_record(state, rec)
    for batch in state.get("rehydrations", []):
        if not isinstance(batch, dict):
            raise GuardedAstraError("REHYDRATION_BATCH_INVALID")
        for rec in batch.get("steps", []):
            if not isinstance(rec, dict):
                raise GuardedAstraError("REHYDRATION_RECORD_INVALID")
            _certify_or_verify_record(state, rec)
    blocker = state.get("blocker")
    if isinstance(blocker, dict) and "result" in blocker:
        synthetic = {
            "step_index": blocker.get("step_index"),
            "step_id": blocker.get("step_id"),
            "ok": False,
            "result": blocker["result"],
        }
        existing = blocker.get("load_bearing_result_certificate")
        if existing is not None:
            synthetic["load_bearing_result_certificate"] = existing
        _certify_or_verify_record(state, synthetic)
        blocker["load_bearing_result_certificate"] = synthetic[
            "load_bearing_result_certificate"
        ]
    return state


def _guarded_write_statej(path: Any, state: Mapping[str, Any]):
    guard_state_for_write(state)
    return _ORIGINAL_WRITE_STATEJ(path, state)


def _verified_result(state: Mapping[str, Any], rec: Mapping[str, Any]) -> Any:
    if not isinstance(rec, Mapping) or "result" not in rec:
        raise GuardedAstraError("LOAD_BEARING_RESULT_RECORD_INVALID")
    certificate = rec.get("load_bearing_result_certificate")
    if not isinstance(certificate, Mapping):
        raise GuardedAstraError(
            "LOAD_BEARING_RESULT_CERTIFICATE_MISSING:" + str(rec.get("step_index"))
        )
    verdict = gate.verify_certificate(
        rec["result"],
        certificate,
        mission_id=str(state.get("mission_id") or ""),
        mission_sha256=str(state.get("mission_sha256") or ""),
        step_index=rec.get("step_index"),
        step_id=str(rec.get("step_id") or ""),
        verification_ok=bool(rec.get("ok")),
    )
    if verdict.get("status") != "PASS":
        raise GuardedAstraError(
            "LOAD_BEARING_RESULT_CERTIFICATE_INVALID:"
            + str(rec.get("step_index"))
            + ":"
            + "|".join(verdict.get("errors") or ["UNKNOWN"])
        )
    return rec["result"]


def _guarded_context_result_map(state: Mapping[str, Any]) -> dict[int, Any]:
    latest: dict[int, Any] = {}
    for rec in state.get("history", []):
        result = _verified_result(state, rec)
        if rec.get("ok"):
            latest[int(rec["step_index"])] = result
    for batch in state.get("rehydrations", []):
        for rec in batch.get("steps", []):
            result = _verified_result(state, rec)
            if rec.get("ok"):
                latest[int(rec["step_index"])] = result
    return latest


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    astra.write_statej = _guarded_write_statej
    astra._context_result_map = _guarded_context_result_map
    _INSTALLED = True


def main() -> int:
    install()
    return astra.main()


if __name__ == "__main__":
    raise SystemExit(main())
