"""Subject-bound verified improvement loop V2.

This gate makes UNDERSTAND -> PLAN -> COMPOSE -> ACT -> VERIFY -> LEARN ->
GENERALIZE -> COMPRESS -> REUSE a content-bound promotion precondition.

V1 proved ordering but allowed opaque receipt hashes to be spliced across
episodes. V2 binds every phase to the same episode and subject, self-digests
each receipt, chains phase outputs into the next phase input, binds the learned
route to the exact learn/generalize/compress outputs, and binds independent
neighbor replays to the exact route manifest.

Passing this gate creates a promotion candidate only. It grants no promotion,
execution, fresh-reality, acceptance, capability, ownership, or terminal
authority.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_VERIFIED_IMPROVEMENT_LOOP_V2"
PHASES = (
    "understand",
    "plan",
    "compose",
    "act",
    "verify",
    "learn",
    "generalize",
    "compress",
    "reuse",
)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _valid_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "promotion_candidate": False,
        "promotion_authority": False,
        "execution_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def phase_receipt_digest(receipt: Mapping[str, Any]) -> str:
    core = {
        "episode_id": receipt.get("episode_id"),
        "phase": receipt.get("phase"),
        "subject_sha256": receipt.get("subject_sha256"),
        "input_sha256": receipt.get("input_sha256"),
        "output_sha256": receipt.get("output_sha256"),
        "evidence_sha256": receipt.get("evidence_sha256"),
        "pass": receipt.get("pass"),
        "previous_phase_receipt_sha256": receipt.get(
            "previous_phase_receipt_sha256"
        ),
    }
    if receipt.get("phase") == "verify":
        core.update(
            {
                "independently_verified": receipt.get(
                    "independently_verified"
                ),
                "verifier_id": receipt.get("verifier_id"),
                "verification_subject_sha256": receipt.get(
                    "verification_subject_sha256"
                ),
                "verifier_receipt_sha256": receipt.get(
                    "verifier_receipt_sha256"
                ),
            }
        )
    return _sha(core)


def compression_receipt_digest(compression: Mapping[str, Any]) -> str:
    return _sha(
        {
            "quality_preserved": compression.get("quality_preserved"),
            "resource_metric_id": compression.get("resource_metric_id"),
            "resource_before": compression.get("resource_before"),
            "resource_after": compression.get("resource_after"),
            "behavior_sha256": compression.get("behavior_sha256"),
            "scope_relation_sha256": compression.get(
                "scope_relation_sha256"
            ),
            "compressed_artifact_sha256": compression.get(
                "compressed_artifact_sha256"
            ),
        }
    )


def route_manifest_digest(route: Mapping[str, Any]) -> str:
    return _sha(
        {
            "route_id": route.get("route_id"),
            "episode_id": route.get("episode_id"),
            "subject_sha256": route.get("subject_sha256"),
            "behavior_sha256": route.get("behavior_sha256"),
            "scope_relation_sha256": route.get("scope_relation_sha256"),
            "behavior_preservation_verified": route.get(
                "behavior_preservation_verified"
            ),
            "learn_phase_output_sha256": route.get(
                "learn_phase_output_sha256"
            ),
            "generalize_phase_output_sha256": route.get(
                "generalize_phase_output_sha256"
            ),
            "compress_phase_output_sha256": route.get(
                "compress_phase_output_sha256"
            ),
            "compression_receipt_sha256": route.get(
                "compression_receipt_sha256"
            ),
        }
    )


def neighbor_receipt_digest(row: Mapping[str, Any]) -> str:
    return _sha(
        {
            "route_id": row.get("route_id"),
            "route_manifest_sha256": row.get("route_manifest_sha256"),
            "neighbor_subject_sha256": row.get(
                "neighbor_subject_sha256"
            ),
            "behavior_sha256": row.get("behavior_sha256"),
            "scope_relation_sha256": row.get(
                "scope_relation_sha256"
            ),
            "pass": row.get("pass"),
            "independently_verified": row.get(
                "independently_verified"
            ),
            "verifier_id": row.get("verifier_id"),
            "result_sha256": row.get("result_sha256"),
        }
    )


def verify_loop(episode: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(episode, Mapping):
            return _fail("EPISODE_NOT_MAPPING")
        episode_id = episode.get("episode_id")
        subject_sha = episode.get("subject_sha256")
        if not _nonempty(episode_id):
            return _fail("EPISODE_ID_INVALID")
        if not _valid_sha(subject_sha):
            return _fail("SUBJECT_SHA256_INVALID")

        receipts = episode.get("phase_receipts")
        if not isinstance(receipts, Mapping):
            return _fail("PHASE_RECEIPTS_MISSING")
        if set(receipts) != set(PHASES):
            return _fail("PHASE_RECEIPT_SET_NOT_EXACT")

        previous_output = subject_sha
        previous_receipt = None
        bound_receipts: dict[str, str] = {}
        bound_outputs: dict[str, str] = {}
        for phase in PHASES:
            row = receipts.get(phase)
            if not isinstance(row, Mapping):
                return _fail("PHASE_RECEIPT_INVALID", phase=phase)
            if row.get("episode_id") != episode_id:
                return _fail("PHASE_EPISODE_BINDING_MISMATCH", phase=phase)
            if row.get("phase") != phase:
                return _fail("PHASE_ID_BINDING_MISMATCH", phase=phase)
            if row.get("subject_sha256") != subject_sha:
                return _fail("PHASE_SUBJECT_BINDING_MISMATCH", phase=phase)
            if row.get("pass") is not True:
                return _fail("PHASE_NOT_PASS", phase=phase)
            for key in ("input_sha256", "output_sha256", "evidence_sha256"):
                if not _valid_sha(row.get(key)):
                    return _fail("PHASE_SHA256_INVALID", phase=phase, field=key)
            if row.get("input_sha256") != previous_output:
                return _fail("PHASE_INPUT_OUTPUT_CHAIN_BROKEN", phase=phase)
            if phase == "understand":
                if row.get("previous_phase_receipt_sha256") is not None:
                    return _fail("UNDERSTAND_PREDECESSOR_MUST_BE_NULL")
            elif row.get("previous_phase_receipt_sha256") != previous_receipt:
                return _fail("PHASE_RECEIPT_CHAIN_BROKEN", phase=phase)

            if phase == "verify":
                if row.get("independently_verified") is not True:
                    return _fail("VERIFY_NOT_INDEPENDENT")
                if not _nonempty(row.get("verifier_id")):
                    return _fail("VERIFY_VERIFIER_ID_MISSING")
                if row.get("verification_subject_sha256") != row.get(
                    "input_sha256"
                ):
                    return _fail("VERIFY_SUBJECT_BINDING_MISMATCH")
                if not _valid_sha(row.get("verifier_receipt_sha256")):
                    return _fail("VERIFY_RECEIPT_SHA256_INVALID")

            expected_receipt = phase_receipt_digest(row)
            if row.get("receipt_sha256") != expected_receipt:
                return _fail("PHASE_RECEIPT_SELF_DIGEST_MISMATCH", phase=phase)

            previous_output = row["output_sha256"]
            previous_receipt = row["receipt_sha256"]
            bound_receipts[phase] = previous_receipt
            bound_outputs[phase] = previous_output

        compression = episode.get("compression")
        if not isinstance(compression, Mapping):
            return _fail("COMPRESSION_PROOF_MISSING")
        if compression.get("quality_preserved") is not True:
            return _fail("COMPRESSION_QUALITY_NOT_PRESERVED")
        if not _nonempty(compression.get("resource_metric_id")):
            return _fail("COMPRESSION_RESOURCE_METRIC_MISSING")
        before = compression.get("resource_before")
        after = compression.get("resource_after")
        if (
            isinstance(before, bool)
            or isinstance(after, bool)
            or not isinstance(before, (int, float))
            or not isinstance(after, (int, float))
            or not math.isfinite(float(before))
            or not math.isfinite(float(after))
            or before < 0
            or after < 0
            or after > before
        ):
            return _fail("COMPRESSION_RESOURCE_RELATION_INVALID")
        for key in (
            "behavior_sha256",
            "scope_relation_sha256",
            "compressed_artifact_sha256",
        ):
            if not _valid_sha(compression.get(key)):
                return _fail("COMPRESSION_BINDING_INVALID", field=key)
        if (
            compression.get("compressed_artifact_sha256")
            != bound_outputs["compress"]
        ):
            return _fail("COMPRESSION_PHASE_OUTPUT_MISMATCH")
        expected_compression = compression_receipt_digest(compression)
        if compression.get("receipt_sha256") != expected_compression:
            return _fail("COMPRESSION_RECEIPT_SELF_DIGEST_MISMATCH")

        route = episode.get("learned_route")
        if not isinstance(route, Mapping):
            return _fail("LEARNED_ROUTE_MISSING")
        if not _nonempty(route.get("route_id")):
            return _fail("ROUTE_ID_INVALID")
        if route.get("episode_id") != episode_id:
            return _fail("ROUTE_EPISODE_BINDING_MISMATCH")
        if route.get("subject_sha256") != subject_sha:
            return _fail("ROUTE_SUBJECT_BINDING_MISMATCH")
        if route.get("behavior_preservation_verified") is not True:
            return _fail("BEHAVIOR_PRESERVATION_UNPROVED")
        for key in ("behavior_sha256", "scope_relation_sha256"):
            if not _valid_sha(route.get(key)):
                return _fail("ROUTE_BINDING_INVALID", field=key)
        if route.get("behavior_sha256") != compression.get("behavior_sha256"):
            return _fail("ROUTE_COMPRESSION_BEHAVIOR_MISMATCH")
        if route.get("scope_relation_sha256") != compression.get(
            "scope_relation_sha256"
        ):
            return _fail("ROUTE_COMPRESSION_SCOPE_MISMATCH")
        phase_bindings = (
            ("learn_phase_output_sha256", "learn"),
            ("generalize_phase_output_sha256", "generalize"),
            ("compress_phase_output_sha256", "compress"),
        )
        for key, phase in phase_bindings:
            if route.get(key) != bound_outputs[phase]:
                return _fail("ROUTE_PHASE_OUTPUT_BINDING_MISMATCH", phase=phase)
        if route.get("compression_receipt_sha256") != compression.get(
            "receipt_sha256"
        ):
            return _fail("ROUTE_COMPRESSION_RECEIPT_MISMATCH")

        manifest_sha = route_manifest_digest(route)
        if route.get("route_manifest_sha256") != manifest_sha:
            return _fail("ROUTE_MANIFEST_SELF_DIGEST_MISMATCH")
        if bound_outputs["reuse"] != manifest_sha:
            return _fail("REUSE_PHASE_ROUTE_MANIFEST_MISMATCH")

        neighbors = episode.get("neighbor_replays")
        if not isinstance(neighbors, list) or len(neighbors) < 2:
            return _fail("NEIGHBOR_REPLAY_INSUFFICIENT")
        seen_subjects: set[str] = set()
        neighbor_receipts: list[str] = []
        for row in neighbors:
            if not isinstance(row, Mapping):
                return _fail("NEIGHBOR_REPLAY_INVALID")
            if row.get("route_id") != route["route_id"]:
                return _fail("NEIGHBOR_ROUTE_ID_MISMATCH")
            if row.get("route_manifest_sha256") != manifest_sha:
                return _fail("NEIGHBOR_ROUTE_MANIFEST_MISMATCH")
            if row.get("behavior_sha256") != route["behavior_sha256"]:
                return _fail("NEIGHBOR_BEHAVIOR_BINDING_MISMATCH")
            if row.get("scope_relation_sha256") != route[
                "scope_relation_sha256"
            ]:
                return _fail("NEIGHBOR_SCOPE_BINDING_MISMATCH")
            neighbor_subject = row.get("neighbor_subject_sha256")
            if not _valid_sha(neighbor_subject) or neighbor_subject == subject_sha:
                return _fail("NEIGHBOR_SUBJECT_INVALID")
            if neighbor_subject in seen_subjects:
                return _fail("NEIGHBOR_SUBJECT_DUPLICATE")
            seen_subjects.add(neighbor_subject)
            if row.get("pass") is not True:
                return _fail("NEIGHBOR_REPLAY_NOT_PASS")
            if row.get("independently_verified") is not True:
                return _fail("NEIGHBOR_REPLAY_NOT_INDEPENDENT")
            if not _nonempty(row.get("verifier_id")):
                return _fail("NEIGHBOR_VERIFIER_ID_MISSING")
            if not _valid_sha(row.get("result_sha256")):
                return _fail("NEIGHBOR_RESULT_SHA256_INVALID")
            expected_neighbor = neighbor_receipt_digest(row)
            if row.get("receipt_sha256") != expected_neighbor:
                return _fail("NEIGHBOR_RECEIPT_SELF_DIGEST_MISMATCH")
            neighbor_receipts.append(expected_neighbor)

        core = {
            "episode_id": episode_id,
            "subject_sha256": subject_sha,
            "route_id": route["route_id"],
            "route_manifest_sha256": manifest_sha,
            "phase_receipt_sha256": bound_receipts,
            "phase_output_sha256": bound_outputs,
            "neighbor_receipt_sha256": sorted(neighbor_receipts),
            "compression_receipt_sha256": compression["receipt_sha256"],
        }
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": (
                "PASS__SUBJECT_BOUND_VERIFIED_IMPROVEMENT_LOOP__"
                "ROUTE_ELIGIBLE_FOR_SEPARATE_LIVE_PROMOTION"
            ),
            "reason": None,
            **core,
            "improvement_receipt_sha256": _sha(core),
            "promotion_candidate": True,
            "promotion_authority": False,
            "execution_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
