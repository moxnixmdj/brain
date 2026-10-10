"""Deterministic candidate patch author for one narrow R3 adapter subclass.

This author handles only one mechanical source repair:
widen the compiled-bound adapter's replay-mode admission guard to one exact,
redacted, deterministic replay mode while leaving proof reconstruction and all
independent verification/checkpoint authority untouched.

It is candidate-only. The returned diff must still pass the existing patch
firewall and all downstream independent verification/replay before any source
change can be considered.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence

from canonical.runtime import r3_success_adapter_patch_author_wrapper_v1 as wrapper
from canonical.runtime import r3_success_adapter_patch_firewall_v1 as firewall

SCHEMA = "PROJECT_BRAIN_R3_DETERMINISTIC_MODE_GUARD_PATCH_AUTHOR_V1"
TARGET_PATH = "canonical/runtime/r3_bound_success_adapter_v1.py"
SUPPORTED_NEW_MODES = frozenset({"generic", "specialized", "decision"})
OLD_GUARD = '    if str(replay.get("mode") or "").strip() != "compiled_bound":'
OLD_RETURN = "        return None"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "NO_CANDIDATE",
        "pass": False,
        "reason": reason,
        "candidate_only": True,
        "authoring_authority": False,
        "source_write_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        **extra,
    }


def _source(packet: Mapping[str, Any], path: str) -> str | None:
    rows = packet.get("mutable_sources")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return None
    for row in rows:
        if (
            isinstance(row, Mapping)
            and row.get("path") == path
            and isinstance(row.get("source_text"), str)
        ):
            return row["source_text"]
    return None


def _mode(context: Mapping[str, Any]) -> str | None:
    replay = context.get("replay")
    if not isinstance(replay, Mapping):
        return None
    mode = replay.get("mode")
    return mode if isinstance(mode, str) else None


def _proof_eligible(context: Mapping[str, Any]) -> tuple[bool, str]:
    proof = context.get("proof")
    if not isinstance(proof, Mapping):
        return False, "PROOF_CONTEXT_MISSING"
    if proof.get("controller_checkpoint_present") is not True:
        return False, "DURABLE_CONTROLLER_CHECKPOINT_REQUIRED"
    selected = proof.get("selected_plan_count")
    execution = proof.get("execution_count")
    verified_effects = proof.get("verified_target_effect_count")
    if not isinstance(selected, int) or selected <= 0:
        return False, "SELECTED_PLAN_REQUIRED"
    if not isinstance(execution, int) or execution != selected:
        return False, "EXECUTION_COUNT_MUST_MATCH_SELECTED_PLAN"
    if not isinstance(verified_effects, int) or verified_effects <= 0:
        return False, "VERIFIED_TARGET_EFFECT_REQUIRED"
    rows = proof.get("execution_rows")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes, bytearray))
        or len(rows) != selected
    ):
        return False, "EXECUTION_ROWS_INCOMPLETE"
    for row in rows:
        if not isinstance(row, Mapping):
            return False, "EXECUTION_ROW_INVALID"
        if row.get("pass") is not True:
            return False, "NONPASSING_EXECUTION_ROW"
        if row.get("composition_digest_present") is not True:
            return False, "EXECUTION_COMPOSITION_DIGEST_REQUIRED"
    if proof.get("cognition_dependency_class") != "DETERMINISTIC_ONLY":
        return False, "DETERMINISTIC_ONLY_REQUIRED"
    if proof.get("model_dependency_count") not in (0, None):
        return False, "MODEL_DEPENDENCY_NOT_ADMITTED"
    return True, "PASS"


def _patch(source: str, mode: str) -> str:
    lines = source.splitlines()
    matches = [i for i, line in enumerate(lines) if line == OLD_GUARD]
    if len(matches) != 1:
        raise ValueError("BOUND_MODE_GUARD_NOT_UNIQUE")
    index = matches[0]
    if index + 1 >= len(lines) or lines[index + 1] != OLD_RETURN:
        raise ValueError("BOUND_MODE_GUARD_RETURN_SHAPE_INVALID")
    new_guard = (
        '    if str(replay.get("mode") or "").strip() '
        f'not in {{"compiled_bound", "{mode}"}}:'
    )
    line_no = index + 1
    return (
        f"diff --git a/{TARGET_PATH} b/{TARGET_PATH}\n"
        "index 0000000..0000000 100644\n"
        f"--- a/{TARGET_PATH}\n"
        f"+++ b/{TARGET_PATH}\n"
        f"@@ -{line_no},2 +{line_no},2 @@\n"
        f"-{OLD_GUARD}\n"
        f"+{new_guard}\n"
        f" {OLD_RETURN}\n"
    )


def author(packet: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return one firewallable candidate diff or None when the subclass does not apply."""
    if not isinstance(packet, Mapping):
        return None
    if packet.get("schema") != wrapper.AUTHOR_PACKET_SCHEMA:
        return None
    if packet.get("candidate_generation_authority") is not True:
        return None
    if packet.get("source_write_authority") is not False:
        return None
    if packet.get("verification_authority") is not False:
        return None

    context = packet.get("adapter_author_context")
    if not isinstance(context, Mapping):
        return None
    mode = _mode(context)
    if mode not in SUPPORTED_NEW_MODES:
        return None
    eligible, _ = _proof_eligible(context)
    if not eligible:
        return None

    source = _source(packet, TARGET_PATH)
    if not isinstance(source, str):
        return None
    try:
        patch_text = _patch(source, mode)
    except Exception:
        return None

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE__DETERMINISTIC_MODE_GUARD_WIDENING",
        "pass": True,
        "candidate_only": True,
        "patch_text": patch_text,
        "target_path": TARGET_PATH,
        "target_mode": mode,
        "source_sha256": sha256(source.encode("utf-8")).hexdigest(),
        "authorship_class": "EXACT_DETERMINISTIC_REPLAY_MODE_GUARD_WIDENING",
        "source_write_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }
