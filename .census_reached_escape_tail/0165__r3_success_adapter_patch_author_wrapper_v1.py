"""Candidate-only patch-author wrapper for the R3 success-adapter frontier.

This module does not author, apply, verify, or promote source patches. It converts
an already-proved constructive Root1 adapter-author gap into a bounded authoring
packet and validates a returned unified diff with the existing patch firewall.

The author sees only the two mutable success-adapter source files. Independent
verification/checkpoint authority is represented only by a digest and is never
included as editable source.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import r3_root1_adapter_gap_witness_v1 as gap_witness
from canonical.runtime import r3_success_adapter_author_context_v1 as author_context
from canonical.runtime import r3_success_adapter_patch_firewall_v1 as firewall

SCHEMA = "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_PATCH_AUTHOR_WRAPPER_V1"
AUTHOR_PACKET_SCHEMA = "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_PATCH_AUTHOR_PACKET_V1"


class PatchAuthorWrapperError(ValueError):
    pass


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "candidate_only": True,
        "authoring_authority": False,
        "patch_application_authority": False,
        "source_write_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _source_snapshot(
    relative: str,
    *,
    repo_root: str | Path,
) -> dict[str, str]:
    root = Path(repo_root).resolve(strict=True)
    target = (root / relative).resolve(strict=True)
    target.relative_to(root)
    if not target.is_file() or target.is_symlink():
        raise PatchAuthorWrapperError("MUTABLE_SOURCE_FILE_INVALID:" + relative)
    raw = target.read_bytes()
    text = raw.decode("utf-8")
    return {
        "path": relative,
        "sha256": sha256(raw).hexdigest(),
        "source_text": text,
    }


def build_author_packet(
    compiled_gap: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Build an exact candidate-author request from an authenticated Root1 gap."""
    try:
        if not isinstance(compiled_gap, Mapping):
            return _fail("COMPILED_GAP_NOT_OBJECT")
        if compiled_gap.get("schema") != gap_witness.SCHEMA:
            return _fail("COMPILED_GAP_SCHEMA_INVALID")
        if compiled_gap.get("pass") is not True:
            return _fail("COMPILED_GAP_NOT_PASSING")
        if compiled_gap.get("root1_positive_gap_established") is not True:
            return _fail("ROOT1_POSITIVE_GAP_NOT_ESTABLISHED")
        if compiled_gap.get("required_primitive") != gap_witness.REQUIRED_PRIMITIVE:
            return _fail("ROOT1_REQUIRED_PRIMITIVE_MISMATCH")

        current_adapter = gap_witness._frontier_sha256(
            gap_witness.SUCCESS_ADAPTER_FRONTIER_PATHS,
            repo_root=repo_root,
        )
        current_authority = gap_witness._frontier_sha256(
            gap_witness.SUCCESS_VERIFICATION_AUTHORITY_PATHS,
            repo_root=repo_root,
        )
        if compiled_gap.get("adapter_frontier_sha256") != current_adapter:
            return _fail(
                "COMPILED_GAP_ADAPTER_FRONTIER_STALE",
                current_adapter_frontier_sha256=current_adapter,
            )
        if compiled_gap.get("verification_authority_sha256") != current_authority:
            return _fail(
                "COMPILED_GAP_VERIFICATION_AUTHORITY_STALE",
                current_verification_authority_sha256=current_authority,
            )

        mutable = [
            _source_snapshot(path, repo_root=repo_root)
            for path in firewall.MUTABLE_ADAPTER_PATHS
        ]
        base = {row["path"]: row["sha256"] for row in mutable}
        witness_id = str(compiled_gap.get("witness_id") or "").strip()
        witness = compiled_gap.get("witness")
        gap_evidence = compiled_gap.get("gap_evidence")
        redacted_context = compiled_gap.get("adapter_author_context")
        if not witness_id or not isinstance(witness, Mapping):
            return _fail("COMPILED_GAP_WITNESS_INCOMPLETE")
        if not isinstance(gap_evidence, Mapping):
            return _fail("COMPILED_GAP_EVIDENCE_MISSING")
        if (
            not isinstance(redacted_context, Mapping)
            or redacted_context.get("schema") != author_context.SCHEMA
            or redacted_context.get("pass") is not True
            or redacted_context.get("candidate_generation_authority") is not True
        ):
            return _fail("COMPILED_GAP_AUTHOR_CONTEXT_MISSING_OR_INVALID")
        context_sha = str(redacted_context.get("context_sha256") or "").strip()
        if not context_sha.startswith("sha256:") or len(context_sha) != 71:
            return _fail("COMPILED_GAP_AUTHOR_CONTEXT_DIGEST_INVALID")
        if author_context.context_sha256(redacted_context) != context_sha:
            return _fail("COMPILED_GAP_AUTHOR_CONTEXT_DIGEST_MISMATCH")
        if witness.get("adapter_author_context_sha256") != context_sha:
            return _fail("COMPILED_GAP_AUTHOR_CONTEXT_WITNESS_MISMATCH")

        packet = {
            "schema": AUTHOR_PACKET_SCHEMA,
            "status": "READY__CANDIDATE_PATCH_AUTHOR_INPUT",
            "witness_id": witness_id,
            "required_primitive": gap_witness.REQUIRED_PRIMITIVE,
            "required_behavior": str(gap_evidence.get("required_behavior") or ""),
            "adapter_author_context": deepcopy(dict(redacted_context)),
            "adapter_author_context_sha256": context_sha,
            "mutable_sources": mutable,
            "base_sha256_by_path": base,
            "mutable_paths": list(firewall.MUTABLE_ADAPTER_PATHS),
            "immutable_verification_authority_sha256": current_authority,
            "immutable_verification_paths": list(
                gap_witness.SUCCESS_VERIFICATION_AUTHORITY_PATHS
            ),
            "output_contract": {
                "type": "UNIFIED_DIFF_ONLY",
                "allowed_paths": list(firewall.MUTABLE_ADAPTER_PATHS),
                "must_bind_current_base_sha256": True,
                "candidate_only": True,
            },
            "candidate_generation_authority": True,
            "patch_application_authority": False,
            "source_write_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        return {
            "schema": SCHEMA,
            "status": "PASS__EXACT_CANDIDATE_PATCH_AUTHOR_PACKET_READY",
            "pass": True,
            "candidate_only": True,
            "author_packet": packet,
            "base_sha256_by_path": base,
            "patch_application_authority": False,
            "source_write_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def validate_author_output(
    packet_result: Mapping[str, Any],
    author_output: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Validate one externally authored candidate diff; never apply it."""
    try:
        if not isinstance(packet_result, Mapping) or packet_result.get("pass") is not True:
            return _fail("AUTHOR_PACKET_NOT_AUTHENTICATED")
        packet = packet_result.get("author_packet")
        if (
            not isinstance(packet, Mapping)
            or packet.get("schema") != AUTHOR_PACKET_SCHEMA
            or packet.get("candidate_generation_authority") is not True
        ):
            return _fail("AUTHOR_PACKET_INVALID")
        if not isinstance(author_output, Mapping):
            return _fail("AUTHOR_OUTPUT_NOT_OBJECT")
        patch_text = author_output.get("patch_text")
        if not isinstance(patch_text, str) or not patch_text.strip():
            return _fail("AUTHOR_OUTPUT_PATCH_TEXT_REQUIRED")

        base = packet.get("base_sha256_by_path")
        if not isinstance(base, Mapping):
            return _fail("AUTHOR_PACKET_BASE_BINDINGS_MISSING")
        touched, _ = firewall._parse_patch(patch_text)
        touched_base = {}
        for path in touched:
            value = base.get(path)
            if not isinstance(value, str) or len(value) != 64:
                return _fail("AUTHOR_PACKET_BASE_BINDING_MISSING:" + path)
            touched_base[path] = value
        verdict = firewall.evaluate(
            {
                "patch_text": patch_text,
                "base_sha256_by_path": touched_base,
            },
            repo_root=repo_root,
        )
        if verdict.get("pass") is not True:
            return _fail(
                "AUTHOR_CANDIDATE_REJECTED_BY_FIREWALL",
                firewall_result=deepcopy(dict(verdict)),
            )
        return {
            "schema": SCHEMA,
            "status": "PASS__CANDIDATE_PATCH_FIREWALL_VALIDATED",
            "pass": True,
            "candidate_only": True,
            "witness_id": packet.get("witness_id"),
            "patch_sha256": verdict.get("patch_sha256"),
            "touched_paths": deepcopy(verdict.get("touched_paths") or []),
            "base_sha256_by_path": deepcopy(touched_base),
            "firewall_result": deepcopy(dict(verdict)),
            "patch_text": patch_text,
            "patch_application_authority": False,
            "source_write_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def request_candidate(
    compiled_gap: Mapping[str, Any],
    *,
    repo_root: str | Path,
    author_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    author_provider_id: str,
) -> dict[str, Any]:
    """Call an untrusted candidate author and firewall its proposed diff."""
    packet = build_author_packet(compiled_gap, repo_root=repo_root)
    if packet.get("pass") is not True:
        return packet
    if not callable(author_provider):
        return _fail("AUTHOR_PROVIDER_NOT_CALLABLE")
    provider_id = str(author_provider_id or "").strip()
    if not provider_id:
        return _fail("AUTHOR_PROVIDER_ID_REQUIRED")
    raw = author_provider(deepcopy(packet["author_packet"]))
    if not isinstance(raw, Mapping):
        return _fail(
            "AUTHOR_PROVIDER_RETURNED_NO_CANDIDATE",
            author_provider_id=provider_id,
        )
    out = validate_author_output(packet, raw, repo_root=repo_root)
    out["author_provider_id"] = provider_id
    return out
