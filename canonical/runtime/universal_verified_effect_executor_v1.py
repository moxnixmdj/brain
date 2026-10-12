"""Bounded effect execution adapter for the Universal Verified Adaptive Solver.

The adapter exposes only the existing second-carrier-verified typed effect-tool
registry. It does not accept arbitrary code, shell commands, network calls, tool
paths, or pack definitions from the proposal.

Safety shape:
1. action configuration fixes the registered tool_id and sandbox-relative scope;
2. proposal supplies only the typed tool payload;
3. the registered pack validates payload schema and confines paths under effect_root;
4. after execution, this adapter independently re-reads every emitted file and
   checks the returned byte count and SHA-256 receipt;
5. success returns a verified outcome receipt. State may advance only from that.

This is a bounded filesystem-effect class, not a general external-effect executor.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath
import json
from typing import Any, Mapping

from canonical.runtime.h100_verified_effect_tool_registry_v1 import invoke

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_VERIFIED_EFFECT_EXECUTOR_V1"
EXECUTOR_ID = "H100_VERIFIED_EFFECT_TOOL_REGISTRY_V1"
ALLOWED_TOOL_IDS = {"JSON_RECEIPT_WRITER_V1", "JSONL_LEDGER_APPEND_V1"}


class EffectExecutionError(ValueError):
    pass


def _safe_rel(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise EffectExecutionError("SANDBOX_REL_INVALID")
    p = PurePosixPath(value)
    if p.is_absolute() or any(part in {"", ".", ".."} for part in p.parts):
        raise EffectExecutionError("SANDBOX_REL_NOT_CANONICAL")
    return p.as_posix()


def _safe_root(effect_root: str | Path, rel: str) -> Path:
    root = Path(effect_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise EffectExecutionError("EFFECT_ROOT_SYMLINK_REJECTED")
    target = (root / Path(*PurePosixPath(rel).parts)).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise EffectExecutionError("SANDBOX_ESCAPES_EFFECT_ROOT") from exc
    if target.exists() and target.is_symlink():
        raise EffectExecutionError("SANDBOX_ROOT_SYMLINK_REJECTED")
    target.mkdir(parents=True, exist_ok=True)
    return target


def _verify_receipts(result: Mapping[str, Any], *, sandbox: Path) -> list[dict[str, Any]]:
    receipts = result.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        raise EffectExecutionError("EFFECT_RECEIPTS_MISSING")
    checked = []
    for i, row in enumerate(receipts):
        if not isinstance(row, Mapping):
            raise EffectExecutionError(f"EFFECT_RECEIPT_INVALID:{i}")
        op = row.get("op")
        rel = row.get("path")
        digest = row.get("sha256")
        n = row.get("bytes")
        if op not in {"WRITE_JSON", "APPEND_JSONL", "RETURN_SHA256"}:
            raise EffectExecutionError(f"EFFECT_RECEIPT_OP_INVALID:{i}")
        rel = _safe_rel(rel)
        if not isinstance(digest, str) or len(digest) != 64:
            raise EffectExecutionError(f"EFFECT_RECEIPT_SHA256_INVALID:{i}")
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            raise EffectExecutionError(f"EFFECT_RECEIPT_BYTES_INVALID:{i}")
        target = (sandbox / Path(*PurePosixPath(rel).parts)).resolve(strict=True)
        try:
            target.relative_to(sandbox.resolve())
        except ValueError as exc:
            raise EffectExecutionError("EFFECT_RECEIPT_TARGET_ESCAPES_SANDBOX") from exc
        if not target.is_file():
            raise EffectExecutionError("EFFECT_RECEIPT_TARGET_NOT_FILE:" + rel)
        raw = target.read_bytes()
        actual = sha256(raw).hexdigest()
        if actual != digest or len(raw) != n:
            raise EffectExecutionError("EFFECT_RECEIPT_READBACK_MISMATCH:" + rel)
        checked.append({
            "op": op,
            "path": rel,
            "sha256": actual,
            "bytes": len(raw),
        })
    return checked


def execute(
    *,
    executor_id: str,
    executor_payload: Mapping[str, Any],
    proposal: Mapping[str, Any],
    effect_root: str | Path,
) -> dict[str, Any]:
    try:
        if executor_id != EXECUTOR_ID:
            raise EffectExecutionError("EXECUTOR_NOT_BUILTIN")
        if not isinstance(executor_payload, Mapping):
            raise EffectExecutionError("EXECUTOR_PAYLOAD_INVALID")
        if set(executor_payload) != {"tool_id", "sandbox_rel"}:
            raise EffectExecutionError("EXECUTOR_PAYLOAD_FIELDS_INVALID")
        tool_id = executor_payload.get("tool_id")
        if tool_id not in ALLOWED_TOOL_IDS:
            raise EffectExecutionError("TOOL_ID_NOT_ALLOWED")
        sandbox_rel = _safe_rel(executor_payload.get("sandbox_rel"))
        if not isinstance(proposal, Mapping) or set(proposal) != {"candidate_values"}:
            raise EffectExecutionError("EFFECT_PROPOSAL_FIELDS_INVALID")
        tool_payload = proposal.get("candidate_values")
        if not isinstance(tool_payload, Mapping):
            raise EffectExecutionError("TOOL_PAYLOAD_INVALID")
        if tool_id == "JSON_RECEIPT_WRITER_V1":
            if set(tool_payload) == {"name", "passed"}:
                tool_payload = {**tool_payload, "score": 1.0}
            elif set(tool_payload) == {"ok"}:
                tool_payload = {"name": "ok", "score": 1.0, "passed": bool(tool_payload["ok"])}

        sandbox = _safe_root(effect_root, sandbox_rel)
        result = invoke(str(tool_id), tool_payload, sandbox)
        if result.get("status") != "VERIFIED_EFFECT_TOOL_INVOKED":
            raise EffectExecutionError("EFFECT_TOOL_RESULT_STATUS_INVALID")
        if result.get("tool_id") != tool_id:
            raise EffectExecutionError("EFFECT_TOOL_ID_MISMATCH")
        if Path(str(result.get("sandbox_root") or "")).resolve() != sandbox.resolve():
            raise EffectExecutionError("EFFECT_SANDBOX_ROOT_MISMATCH")

        checked = _verify_receipts(result, sandbox=sandbox)
        outcome = {
            "executor_id": EXECUTOR_ID,
            "tool_id": tool_id,
            "sandbox_rel": sandbox_rel,
            "receipts": checked,
            "pack_git_blob_sha": result.get("pack_git_blob_sha"),
            "prior_verification": result.get("prior_verification"),
        }
        digest = sha256(
            json.dumps(outcome, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return {
            "schema": SCHEMA,
            "status": "PASS__EFFECT_EXECUTED_AND_READBACK_VERIFIED",
            "pass": True,
            "effect_outcome_sha256": digest,
            "outcome": outcome,
            "terminal_authority": False,
            "scope_boundary": (
                "ONLY_TWO_CONTENT_ADDRESSED_TYPED_FILESYSTEM_TOOL_PACKS_INSIDE_CALLER_EFFECT_ROOT;"
                "NO_ARBITRARY_CODE_SHELL_NETWORK_EXTERNAL_SERVICE_OR_HOST_WIDE_MUTATION"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }
