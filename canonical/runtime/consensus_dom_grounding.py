"""Fail-closed multi-channel DOM/accessibility/OCR consensus grounding.

This component extends exact structured grounding only for explicitly supplied target
constraints. It normalizes superficial Unicode/case/whitespace differences and
requires multiple independent matching channels before selecting an element.

It does not infer a target from a goal, perform fuzzy semantic matching, or own
screenshot-only perception. Conflicts, ambiguity, weak evidence, hidden/disabled
state, and unsupported actions all escalate.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ObservedElement:
    element_id: str
    role: str | None
    name: str | None
    text: str | None
    ocr_text: str | None
    attrs: Mapping[str, str]
    actions: frozenset[str]
    visible: bool = True
    enabled: bool = True


@dataclass(frozen=True)
class ConsensusRequest:
    action: str
    role: str | None = None
    name: str | None = None
    text: str | None = None
    ocr_text: str | None = None
    attrs: Mapping[str, str] | None = None
    min_independent_cues: int = 2


def _norm(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def _valid_map(values: Mapping[str, str] | None) -> bool:
    if values is None:
        return True
    if not isinstance(values, Mapping):
        return False
    return all(
        isinstance(k, str) and bool(k.strip()) and isinstance(v, str)
        for k, v in values.items()
    )


def ground_consensus_action(req: ConsensusRequest, elements: Sequence[ObservedElement]) -> dict:
    if not isinstance(req.action, str) or not req.action.strip():
        return {"status": "ESCALATE", "reason": "ACTION_INVALID", "terminal_authority": False}
    if (
        not isinstance(req.min_independent_cues, int)
        or isinstance(req.min_independent_cues, bool)
        or not 1 <= req.min_independent_cues <= 5
    ):
        return {"status": "ESCALATE", "reason": "CUE_THRESHOLD_INVALID", "terminal_authority": False}
    if not _valid_map(req.attrs):
        return {"status": "ESCALATE", "reason": "REQUEST_ATTRIBUTES_INVALID", "terminal_authority": False}
    if not isinstance(elements, Sequence):
        return {"status": "ESCALATE", "reason": "ELEMENTS_NOT_SEQUENCE", "terminal_authority": False}

    ids = [e.element_id for e in elements]
    if any(not isinstance(x, str) or not x.strip() for x in ids) or len(ids) != len(set(ids)):
        return {"status": "ESCALATE", "reason": "ELEMENT_IDENTITIES_INVALID_OR_DUPLICATE", "terminal_authority": False}

    requested = {
        "role": _norm(req.role),
        "name": _norm(req.name),
        "text": _norm(req.text),
        "ocr_text": _norm(req.ocr_text),
    }
    wanted_attrs = {_norm(k): _norm(v) for k, v in dict(req.attrs or {}).items()}
    explicit_cue_groups = sum(v is not None for v in requested.values()) + (1 if wanted_attrs else 0)
    if explicit_cue_groups < req.min_independent_cues:
        return {
            "status": "ESCALATE",
            "reason": "REQUEST_HAS_INSUFFICIENT_INDEPENDENT_CUES",
            "available_cue_groups": explicit_cue_groups,
            "required_cue_groups": req.min_independent_cues,
            "terminal_authority": False,
        }

    candidates: list[tuple[ObservedElement, list[str]]] = []
    for e in elements:
        if not e.visible or not e.enabled or req.action not in e.actions:
            continue
        if not _valid_map(e.attrs):
            continue

        observed = {
            "role": _norm(e.role),
            "name": _norm(e.name),
            "text": _norm(e.text),
            "ocr_text": _norm(e.ocr_text),
        }
        matched: list[str] = []
        conflict = False
        for cue, wanted in requested.items():
            if wanted is None:
                continue
            if observed[cue] != wanted:
                conflict = True
                break
            matched.append(cue)
        if conflict:
            continue

        if wanted_attrs:
            normalized_attrs = {_norm(k): _norm(v) for k, v in e.attrs.items()}
            if any(normalized_attrs.get(k) != v for k, v in wanted_attrs.items()):
                continue
            matched.append("attrs")

        if len(matched) < req.min_independent_cues:
            continue
        candidates.append((e, matched))

    if len(candidates) == 1:
        element, matched = candidates[0]
        return {
            "status": "SELECT",
            "element_id": element.element_id,
            "action": req.action,
            "matched_cues": sorted(matched),
            "reason": "UNIQUE_MULTI_CHANNEL_NORMALIZED_CONSENSUS",
            "scope": "EXPLICIT_TARGET_CONSTRAINTS_ONLY__NO_GOAL_TO_TARGET_INFERENCE",
            "semantic_authority": False,
            "terminal_authority": False,
        }

    return {
        "status": "ESCALATE",
        "reason": "NO_CONSENSUS_MATCH" if not candidates else "AMBIGUOUS_CONSENSUS_MATCH",
        "candidate_ids": sorted(e.element_id for e, _ in candidates),
        "semantic_authority": False,
        "terminal_authority": False,
    }
