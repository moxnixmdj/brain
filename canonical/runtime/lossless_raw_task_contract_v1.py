"""Lossless raw-task contract compiler.

The routing contract and the acceptance contract are intentionally different.

Routing effects are coarse hints used to choose/search capabilities. They have no
authority to define task success.

The acceptance contract preserves every non-whitespace source segment as an exact,
content-addressed obligation. Bounded structured analyzers may attach stronger
machine-checkable requirements to a segment, but they never delete the raw segment
obligation. Therefore semantic extraction failure becomes unresolved acceptance,
not silent loss of user intent.

This module performs no model call and grants no terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.explicit_requirement_index_v2 import build_index
from canonical.runtime.instruction_constraint_compiler_v1 import (
    ConstraintError,
    compile_constraints,
)

SCHEMA = "PROJECT_BRAIN_LOSSLESS_RAW_TASK_CONTRACT_V1"


class RawTaskContractError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _segments(text: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    # Preserve punctuation and line boundaries. Whitespace-only spans are not
    # independent obligations, but all non-whitespace bytes belong to one.
    for m in re.finditer(r"[^.!?\n]+(?:[.!?]+|\n|$)", text):
        s, e = m.span()
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s < e and text[s:e].strip():
            out.append((s, e, text[s:e]))
    if not out and text.strip():
        s = next(i for i, ch in enumerate(text) if not ch.isspace())
        e = len(text.rstrip())
        out.append((s, e, text[s:e]))
    return out


def _normalize_effects(values: Any) -> list[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise RawTaskContractError("ROUTING_TARGET_EFFECTS_INVALID")
    out = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise RawTaskContractError("ROUTING_TARGET_EFFECT_INVALID")
        value = item.strip()
        if value not in out:
            out.append(value)
    if not out:
        raise RawTaskContractError("ROUTING_TARGET_EFFECTS_EMPTY")
    return sorted(out)


def _grounding_map(
    task_text: str,
    routing_effects: Sequence[str],
    semantic_goal_contract: Any,
) -> dict[str, list[int]]:
    # A semantic quorum may help routing, but this compiler treats it as an
    # optional binding aid only. It cannot weaken acceptance.
    if semantic_goal_contract is None:
        return {effect: [] for effect in routing_effects}
    if not isinstance(semantic_goal_contract, Mapping):
        raise RawTaskContractError("SEMANTIC_GOAL_CONTRACT_INVALID")
    if semantic_goal_contract.get("status") != "QUORUM_VERIFIED":
        raise RawTaskContractError("SEMANTIC_GOAL_CONTRACT_NOT_VERIFIED")
    actual_sha = sha256(task_text.encode("utf-8")).hexdigest()
    if semantic_goal_contract.get("goal_sha256") != actual_sha:
        raise RawTaskContractError("SEMANTIC_GOAL_CONTRACT_HASH_MISMATCH")
    targets = sorted(set(semantic_goal_contract.get("target_effects") or []))
    if targets != sorted(set(routing_effects)):
        raise RawTaskContractError("SEMANTIC_GOAL_TARGET_EFFECT_MISMATCH")
    grounding = semantic_goal_contract.get("grounding")
    if not isinstance(grounding, Mapping):
        raise RawTaskContractError("SEMANTIC_GOAL_GROUNDING_INVALID")
    out: dict[str, list[int]] = {}
    for effect in routing_effects:
        positions = grounding.get(effect)
        if not isinstance(positions, list) or any(
            not isinstance(x, int) or isinstance(x, bool) or x < 0 or x >= len(task_text)
            for x in positions
        ):
            raise RawTaskContractError("SEMANTIC_GOAL_GROUNDING_INVALID:" + effect)
        out[effect] = sorted(set(positions))
    return out


def compile_contract(
    task_text: str,
    *,
    source_id: str,
    routing_target_effects: Sequence[str],
    semantic_goal_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(task_text, str) or not task_text.strip():
            raise RawTaskContractError("TASK_TEXT_REQUIRED")
        if not isinstance(source_id, str) or not source_id.strip():
            raise RawTaskContractError("SOURCE_ID_REQUIRED")
        source_id = source_id.strip()
        routing = _normalize_effects(routing_target_effects)
        task_sha = sha256(task_text.encode("utf-8")).hexdigest()
        grounding = _grounding_map(task_text, routing, semantic_goal_contract)

        req_index = build_index(task_text, source_id=source_id)
        if req_index.get("status") == "FAIL_CLOSED":
            raise RawTaskContractError("EXPLICIT_REQUIREMENT_INDEX_FAIL_CLOSED")

        formal_constraints = None
        formal_constraint_error = None
        try:
            c = compile_constraints(task_text)
            formal_constraints = {
                "exact_response": c.exact_response,
                "prefix": c.prefix,
                "suffix": c.suffix,
                "min_words": c.min_words,
                "max_words": c.max_words,
                "min_unique_words": c.min_unique_words,
                "exact_numbers": c.exact_numbers,
                "lowercase_only": c.lowercase_only,
                "uppercase_only": c.uppercase_only,
                "required_literals": list(c.required_literals),
                "forbidden_literals": list(c.forbidden_literals),
            }
        except ConstraintError as exc:
            formal_constraint_error = str(exc)

        indexed_by_segment: dict[int, list[dict[str, Any]]] = {}
        for row in list(req_index.get("modal_obligations") or []) + list(
            req_index.get("imperative_directives") or []
        ):
            idx = row.get("segment_index")
            if isinstance(idx, int):
                indexed_by_segment.setdefault(idx, []).append(row)

        obligations = []
        covered_positions: set[int] = set()
        for index, (start, end, text) in enumerate(_segments(task_text)):
            for pos in range(start, end):
                if not task_text[pos].isspace():
                    covered_positions.add(pos)

            related_effects = []
            positions = set(range(start, end))
            for effect, effect_positions in grounding.items():
                if positions.intersection(effect_positions):
                    related_effects.append(effect)

            raw_payload = {
                "source_id": source_id,
                "task_sha256": task_sha,
                "segment_index": index,
                "span": [start, end],
                "segment_sha256": sha256(text.encode("utf-8")).hexdigest(),
            }
            raw_id = "RAWREQ:" + _sha(raw_payload)
            structured = indexed_by_segment.get(index, [])
            obligations.append({
                "obligation_id": raw_id,
                "kind": "RAW_SOURCE_SEGMENT_ACCEPTANCE",
                "source_id": source_id,
                "task_sha256": task_sha,
                "segment_index": index,
                "span": [start, end],
                "segment_sha256": raw_payload["segment_sha256"],
                "text": text,
                "routing_effects": sorted(related_effects),
                "structured_requirement_ids": sorted(
                    str(row.get("requirement_id") or row.get("obligation_id"))
                    for row in structured
                    if row.get("requirement_id") or row.get("obligation_id")
                ),
                "acceptance_receipt_required": True,
                "semantic_omission_may_delete_this_obligation": False,
            })

        expected_positions = {
            i for i, ch in enumerate(task_text) if not ch.isspace()
        }
        if covered_positions != expected_positions:
            missing = sorted(expected_positions - covered_positions)
            raise RawTaskContractError(
                "RAW_TASK_NONWHITESPACE_COVERAGE_INCOMPLETE:" + ",".join(map(str, missing[:32]))
            )

        contract_payload = {
            "source_id": source_id,
            "task_sha256": task_sha,
            "routing_target_effects": routing,
            "acceptance_obligations": [
                {
                    "obligation_id": row["obligation_id"],
                    "span": row["span"],
                    "segment_sha256": row["segment_sha256"],
                }
                for row in obligations
            ],
        }
        return {
            "schema": SCHEMA,
            "status": "COMPILED__LOSSLESS_RAW_TASK_ACCEPTANCE_CONTRACT",
            "pass": True,
            "source_id": source_id,
            "task_sha256": task_sha,
            "task_byte_length": len(task_text.encode("utf-8")),
            "routing_contract": {
                "target_effects": routing,
                "grounding": grounding,
                "success_authority": False,
                "purpose": "CAPABILITY_SEARCH_AND_ROUTING_ONLY",
            },
            "acceptance_contract": {
                "obligations": obligations,
                "required_obligation_ids": [row["obligation_id"] for row in obligations],
                "raw_source_is_final_semantic_reference": True,
                "routing_effects_define_success": False,
                "unverified_obligation_may_be_silently_dropped": False,
            },
            "positive_structured_requirement_index": req_index,
            "formal_instruction_constraints": formal_constraints,
            "formal_instruction_constraint_error": formal_constraint_error,
            "task_contract_sha256": _sha(contract_payload),
            "nonwhitespace_source_coverage_complete": True,
            "semantic_completeness_required_at_compile_time": False,
            "semantic_completeness_deferred_to_acceptance": True,
            "terminal_authority": False,
            "hard_rule": (
                "ROUTING_MAY_BE_COARSE__SUCCESS_REQUIRES_SEPARATE_ACCEPTANCE_OF_EVERY_EXACT_RAW_SOURCE_SEGMENT"
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
