#!/usr/bin/env python3
"""Legacy IFEval visible-contract core V2.

Two structural repairs for the Root1 LiveBench path:

1. Preserve multiple predicates from the same instruction family. A bounded
   range such as 20..25 sentences is two distinct checker predicates, not an
   error.
2. Quotient only *exactly identical semantic predicates* when reasoning about
   full-score witness sufficiency. If one response satisfies the unique
   predicates, duplicated identical checker instances are automatically true
   as well, so multiplicity cannot prevent full score.

The module also recovers combination:repeat_prompt.prompt_to_repeat from
visible edge structure. In the pinned public classic IFEval population every
repeat target is a contiguous prompt prefix or suffix.

No terminal LiveBench cases, ids, kwargs, responses, or scores are consumed.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_CONTRACT_CORE_V2"


class VisibleContractError(ValueError):
    pass


@dataclass(frozen=True)
class Predicate:
    instruction_id: str
    kwargs: Mapping[str, Any]

    def key(self) -> str:
        return semantic_predicate_key(self.instruction_id, self.kwargs)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _jsonable(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_jsonable(x) for x in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise VisibleContractError("NON_JSONABLE_PREDICATE_ARGUMENT")


def semantic_predicate_key(instruction_id: str, kwargs: Mapping[str, Any] | None) -> str:
    """Canonical identity for an exact checker predicate.

    List order is intentionally preserved. We quotient only exact semantic
    identity, never merely a shared family name.
    """
    iid = str(instruction_id or "").strip()
    if not iid:
        raise VisibleContractError("INSTRUCTION_ID_REQUIRED")
    normalized = _jsonable(dict(kwargs or {}))
    return iid + "|" + json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def quotient_exact_predicates(
    instances: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Collapse only exact duplicate (instruction_id, kwargs) predicates."""
    groups: dict[str, dict[str, Any]] = {}
    family_counts: dict[str, int] = {}

    for position, raw in enumerate(instances):
        iid = str(raw.get("instruction_id") or "").strip()
        kwargs = raw.get("kwargs") or {}
        if not isinstance(kwargs, Mapping):
            raise VisibleContractError("KWARGS_MAPPING_REQUIRED")
        key = semantic_predicate_key(iid, kwargs)
        family_counts[iid] = family_counts.get(iid, 0) + 1
        if key not in groups:
            groups[key] = {
                "instruction_id": iid,
                "kwargs": _jsonable(dict(kwargs)),
                "multiplicity": 0,
                "source_positions": [],
            }
        groups[key]["multiplicity"] += 1
        groups[key]["source_positions"].append(position)

    predicates = list(groups.values())
    duplicate_families = sorted(k for k, n in family_counts.items() if n > 1)
    exact_duplicate_groups = [x for x in predicates if x["multiplicity"] > 1]

    return {
        "schema": SCHEMA,
        "instance_count": sum(family_counts.values()),
        "unique_predicate_count": len(predicates),
        "predicates": predicates,
        "duplicate_family_ids": duplicate_families,
        "exact_duplicate_group_count": len(exact_duplicate_groups),
        "exact_duplicate_extra_instances": sum(
            x["multiplicity"] - 1 for x in exact_duplicate_groups
        ),
        "full_score_quotient_safe": True,
        "hard_nonclaim": (
            "QUOTIENTING_EXACT_DUPLICATES_PRESERVES_FULL_SCORE_SUFFICIENCY;"
            "IT_DOES_NOT_PRESERVE_ARBITRARY_PARTIAL_SCORE_ARITHMETIC"
        ),
    }


_REPEAT_TOKEN = re.compile(r"\brep(?:eat|leat)\b", re.IGNORECASE)
_REPEAT_OBJECT = re.compile(
    r"\b(request|question|prompt|sentence|line|text)\b", re.IGNORECASE
)
_REPEAT_EXACTNESS = re.compile(
    r"\b(word\s+(?:for|by)\s+word|exact(?:ly)?|without\s+(?:any\s+)?change|"
    r"without\s+changing|do\s+not\s+change|don['’]?t\s+change|"
    r"no\s+change|as\s+it\s+is|above|below|first)\b",
    re.IGNORECASE,
)


def _looks_like_repeat_directive(text: str) -> bool:
    return bool(
        _REPEAT_TOKEN.search(text)
        and _REPEAT_OBJECT.search(text)
        and _REPEAT_EXACTNESS.search(text)
    )


def _clean_target(text: str) -> str:
    return text.strip("\r\n ")


def recover_repeat_prompt_target(prompt: str) -> dict[str, Any]:
    """Recover visible repeat target from an edge-separated prompt.

    The routine does not know instruction ids or kwargs. It searches structural
    boundaries and accepts only a unique prefix/suffix decomposition in which
    the other side is recognizably a repeat directive.
    """
    p = str(prompt or "")
    if not p.strip():
        return {
            "schema": SCHEMA,
            "status": "ABSTAIN_EMPTY_PROMPT",
            "prompt_to_repeat": None,
            "orientation": None,
        }

    candidates: list[tuple[str, str, int]] = []

    # Prefix target + trailing directive. Test line boundaries because the
    # public corpus uses both one and two newlines before the directive.
    for m in re.finditer(r"\n+", p):
        left = _clean_target(p[: m.start()])
        right = _clean_target(p[m.end() :])
        if left and right and _looks_like_repeat_directive(right):
            candidates.append(("PREFIX_TARGET", left, m.start()))

    # Leading directive + suffix target. Public forms separate them with a
    # blank line; permit one-or-more newline boundaries but require the entire
    # leading block to look like the directive.
    for m in re.finditer(r"\n+", p):
        left = _clean_target(p[: m.start()])
        right = _clean_target(p[m.end() :])
        if left and right and _looks_like_repeat_directive(left):
            candidates.append(("SUFFIX_TARGET", right, m.end()))

    # Exact quoted target inside a repeat directive is another fully visible
    # route. Keep it only when it agrees with an edge candidate or is unique.
    if _looks_like_repeat_directive(p):
        for m in re.finditer(
            r"rep(?:eat|leat)[^\n]{0,100}?[\"“](.+?)[\"”]"
            r"[^\n]{0,100}?(?:word\s+for\s+word|without\s+change|exact)",
            p,
            flags=re.IGNORECASE,
        ):
            value = _clean_target(m.group(1))
            if value and value in p:
                candidates.append(("QUOTED_VISIBLE_TARGET", value, m.start(1)))

    # Deduplicate by recovered value. Multiple structural boundaries can point
    # to the same target; that is not ambiguity.
    by_value: dict[str, set[str]] = {}
    for orientation, value, _ in candidates:
        by_value.setdefault(value, set()).add(orientation)

    if not by_value:
        return {
            "schema": SCHEMA,
            "status": "ABSTAIN_REPEAT_TARGET_NOT_UNIQUELY_VISIBLE",
            "prompt_to_repeat": None,
            "orientation": None,
        }
    if len(by_value) != 1:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_AMBIGUOUS_REPEAT_TARGET",
            "prompt_to_repeat": None,
            "orientation": None,
            "candidate_count": len(by_value),
        }

    value, orientations = next(iter(by_value.items()))
    orientation = (
        next(iter(orientations)) if len(orientations) == 1 else "MULTIPLE_VISIBLE_CUES"
    )
    return {
        "schema": SCHEMA,
        "status": "RECOVERED",
        "prompt_to_repeat": value,
        "orientation": orientation,
        "candidate_count": 1,
        "hidden_kwargs_used": False,
        "model_dependency_count": 0,
    }


def full_score_quotient_theorem(
    unique_predicate_truths: Iterable[bool],
    multiplicities: Iterable[int],
) -> dict[str, Any]:
    """Executable statement of the exact-duplicate full-score theorem.

    If every unique predicate is true and every multiplicity is positive, every
    checker instance in the expanded multiset is true. Therefore:
      ALL_CHECKERS_TRUE = 1
      TRUE_CHECKER_COUNT / TOTAL_CHECKER_COUNT = 1
      0.5*1 + 0.5*1 = 1
    """
    truths = tuple(bool(x) for x in unique_predicate_truths)
    mult = tuple(int(x) for x in multiplicities)
    if len(truths) != len(mult):
        raise VisibleContractError("TRUTH_MULTIPLICITY_LENGTH_MISMATCH")
    if any(x < 1 for x in mult):
        raise VisibleContractError("MULTIPLICITY_MUST_BE_POSITIVE")
    if not truths:
        raise VisibleContractError("PREDICATES_REQUIRED")

    expanded_total = sum(mult)
    expanded_true = sum(m for truth, m in zip(truths, mult) if truth)
    all_true = all(truths)
    score = (
        0.5 * (1.0 if all_true else 0.0)
        + 0.5 * (expanded_true / expanded_total)
    )
    return {
        "schema": SCHEMA,
        "unique_predicate_count": len(truths),
        "expanded_instance_count": expanded_total,
        "all_unique_predicates_true": all_true,
        "expanded_true_count": expanded_true,
        "score": score,
        "full_score": score == 1.0,
    }


def run(args: Mapping[str, Any], root=None) -> dict[str, Any]:
    args = dict(args or {})
    op = args.get("op")
    if op == "repeat_target":
        return recover_repeat_prompt_target(str(args.get("prompt") or ""))
    if op == "quotient":
        return quotient_exact_predicates(args.get("instances") or [])
    if op == "full_score_theorem":
        return full_score_quotient_theorem(
            args.get("truths") or [],
            args.get("multiplicities") or [],
        )
    raise VisibleContractError("UNKNOWN_OP")
