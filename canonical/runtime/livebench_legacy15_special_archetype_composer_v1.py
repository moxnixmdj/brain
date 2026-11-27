#!/usr/bin/env python3
"""Contamination-safe constructive composer for the three special legacy15 archetypes.

Scope is intentionally narrow and strong:
- JSON, REPEAT_PROMPT, and TWO_RESPONSES only;
- visible recovered contracts only;
- no terminal rows, hidden kwargs, case IDs, prior responses, or scores;
- generator-admitted keyword / forbidden-word slots from the pinned historical
  LiveBench generator.

The module returns a witness candidate for every structurally compatible special
archetype contract tuple. Acceptance credit remains zero until independent replay
against the exact pinned checker bytes.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_SPECIAL_ARCHETYPE_COMPOSER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"

EXIST = "keywords:existence"
FORBID = "keywords:forbidden_words"
TITLE = "detectable_format:title"
JSON_ID = "detectable_format:json_format"
REPEAT = "combination:repeat_prompt"
TWO = "combination:two_responses"

SPECIAL_ARCHETYPES = ("JSON", "REPEAT_PROMPT", "TWO_RESPONSES")
_SPECIAL_ALLOWED = {
    "JSON": frozenset({JSON_ID, EXIST, FORBID}),
    "REPEAT_PROMPT": frozenset({REPEAT, EXIST, TITLE}),
    "TWO_RESPONSES": frozenset({TWO, EXIST, FORBID, TITLE}),
}


class SpecialComposerError(ValueError):
    pass


def _by_id(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for raw in contracts:
        iid = str(raw.get("instruction_id") or "")
        if not iid:
            raise SpecialComposerError("INSTRUCTION_ID_REQUIRED")
        if iid in out:
            raise SpecialComposerError("DUPLICATE_INSTRUCTION_ID:" + iid)
        if raw.get("parameter_complete", True) is not True:
            raise SpecialComposerError("PARAMETER_INCOMPLETE:" + iid)
        out[iid] = raw
    return out


def _slots(contract: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(contract.get("slots") or {}) if contract else {}


def _forbidden_patterns(by_id: Mapping[str, Mapping[str, Any]]) -> list[str]:
    return [str(x) for x in (_slots(by_id.get(FORBID)).get("forbidden_words") or [])]


def _required_patterns(by_id: Mapping[str, Mapping[str, Any]]) -> list[str]:
    return [str(x) for x in (_slots(by_id.get(EXIST)).get("keywords") or [])]


def _forbidden_ok(text: str, forbidden: Sequence[str]) -> bool:
    for word in forbidden:
        try:
            if re.search(r"\b" + word + r"\b", text, flags=re.IGNORECASE):
                return False
        except re.error as exc:
            raise SpecialComposerError("INVALID_GENERATOR_FORBIDDEN_REGEX:" + word) from exc
    return True


def _required_ok(text: str, required: Sequence[str]) -> bool:
    for keyword in required:
        try:
            if re.search(keyword, text, flags=re.IGNORECASE) is None:
                return False
        except re.error as exc:
            raise SpecialComposerError("INVALID_GENERATOR_REQUIRED_REGEX:" + keyword) from exc
    return True


def _protected_required_fragment(keyword: str, forbidden: Sequence[str]) -> str:
    """Embed a required regex while avoiding every whole-word forbidden regex.

    The pinned historical generator draws plain lexical items for these slots.
    Appending a word character therefore preserves the required substring match
    while destroying a whole-word match when the same lexical item is forbidden.
    Iterate because another forbidden item may equal an earlier extension.
    """
    for n in range(1, 257):
        candidate = keyword + ("x" * n)
        if _required_ok(candidate, [keyword]) and _forbidden_ok(candidate, forbidden):
            return candidate
    raise SpecialComposerError("NO_PROTECTED_REQUIRED_FRAGMENT:" + keyword)


def _payload(required: Sequence[str], forbidden: Sequence[str]) -> str:
    parts = [_protected_required_fragment(k, forbidden) for k in required]
    # Private-use characters are not ASCII word characters, so they cannot equal
    # any pinned generator WORD_LIST entry and add no accidental lexical token.
    parts.append("\ue000")
    text = " ".join(parts)
    if not _required_ok(text, required):
        raise SpecialComposerError("REQUIRED_CONSTRUCTION_INVARIANT_FAILED")
    if not _forbidden_ok(text, forbidden):
        raise SpecialComposerError("FORBIDDEN_CONSTRUCTION_INVARIANT_FAILED")
    return text


def _compose_json(by_id: Mapping[str, Mapping[str, Any]]) -> str:
    required = _required_patterns(by_id)
    forbidden = _forbidden_patterns(by_id)
    # Empty JSON key prevents an ordinary alphabetic key from colliding with a
    # generated forbidden word.
    response = json.dumps({"": _payload(required, forbidden)}, ensure_ascii=False, separators=(",", ":"))
    if not _required_ok(response, required) or not _forbidden_ok(response, forbidden):
        raise SpecialComposerError("JSON_LEXICAL_INVARIANT_FAILED")
    json.loads(response)
    return response


def _compose_repeat(by_id: Mapping[str, Mapping[str, Any]]) -> str:
    base = str(_slots(by_id.get(REPEAT)).get("prompt_to_repeat") or "").strip()
    if not base:
        raise SpecialComposerError("PROMPT_TO_REPEAT_REQUIRED")
    required = _required_patterns(by_id)
    pieces = [base]
    if TITLE in by_id:
        pieces.append("<<\ue001>>")
    if required:
        # Repeat archetype is structurally incompatible with forbidden_words, so
        # exact visible required strings can be appended directly.
        pieces.extend(required)
    pieces.append("\ue002")
    response = "\n".join(pieces)
    if not response.strip().lower().startswith(base.lower()):
        raise SpecialComposerError("REPEAT_PREFIX_INVARIANT_FAILED")
    if not _required_ok(response, required):
        raise SpecialComposerError("REPEAT_REQUIRED_INVARIANT_FAILED")
    if TITLE in by_id and re.search(r"<<[^\n]+>>", response) is None:
        raise SpecialComposerError("REPEAT_TITLE_INVARIANT_FAILED")
    return response


def _compose_two(by_id: Mapping[str, Mapping[str, Any]]) -> str:
    required = _required_patterns(by_id)
    forbidden = _forbidden_patterns(by_id)
    common = _payload(required, forbidden)
    if TITLE in by_id:
        # Private-use title content avoids all generator lexical forbidden words.
        common = "<<\ue003>> " + common
    left = common + "\ue004"
    right = common + "\ue005"
    response = left + "******" + right
    parts = response.split("******")
    if len(parts) != 2 or not all(p.strip() for p in parts) or parts[0].strip() == parts[1].strip():
        raise SpecialComposerError("TWO_RESPONSE_INVARIANT_FAILED")
    if not _required_ok(response, required) or not _forbidden_ok(response, forbidden):
        raise SpecialComposerError("TWO_LEXICAL_INVARIANT_FAILED")
    if TITLE in by_id and re.search(r"<<[^\n]+>>", response) is None:
        raise SpecialComposerError("TWO_TITLE_INVARIANT_FAILED")
    return response


def compose(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    try:
        by_id = _by_id(contracts)
        ids = tuple(by_id)
        if not ids or not archetypes.compatible(ids):
            raise SpecialComposerError("INCOMPATIBLE_OR_UNKNOWN_ID_SET")
        arch = archetypes.archetype(ids)
        if arch not in SPECIAL_ARCHETYPES:
            raise SpecialComposerError("OUTSIDE_SPECIAL_ARCHETYPE_SCOPE:" + arch)
        if set(ids) - set(_SPECIAL_ALLOWED[arch]):
            raise SpecialComposerError("SPECIAL_ARCHETYPE_ALLOWED_SET_DRIFT:" + arch)

        feasible = feasibility.classify_visible_contracts(contracts)
        if feasible.get("status") == "PROVED_UNSAT":
            return {
                "schema": SCHEMA,
                "status": "PROVED_UNSAT",
                "archetype": arch,
                "instruction_ids": sorted(ids),
                "hard_unsat_reasons": list(feasible.get("hard_unsat_reasons") or []),
                "response": None,
                "terminal_data_used": False,
                "hidden_kwargs_used": False,
                "acceptance_credit": False,
            }

        if arch == "JSON":
            response = _compose_json(by_id)
        elif arch == "REPEAT_PROMPT":
            response = _compose_repeat(by_id)
        else:
            response = _compose_two(by_id)

        return {
            "schema": SCHEMA,
            "status": "PASS_CANDIDATE_WITNESS",
            "archetype": arch,
            "instruction_ids": sorted(ids),
            "response": response,
            "requires_exact_pinned_checker_postvalidation": True,
            "terminal_data_used": False,
            "terminal_case_content_used": False,
            "terminal_case_metadata_used": False,
            "hidden_instruction_ids_used": False,
            "hidden_kwargs_used": False,
            "model_dependency_count": 0,
            "network_used": False,
            "acceptance_credit": False,
        }
    except SpecialComposerError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "response": None,
            "terminal_data_used": False,
            "hidden_kwargs_used": False,
            "acceptance_credit": False,
        }


def verify_structural_cover() -> dict[str, Any]:
    special_sets = [
        ids for ids in archetypes.enumerate_compatible_sets()
        if archetypes.archetype(ids) in SPECIAL_ARCHETYPES
    ]
    counts = {arch: 0 for arch in SPECIAL_ARCHETYPES}
    for ids in special_sets:
        arch = archetypes.archetype(ids)
        counts[arch] += 1
        if set(ids) - set(_SPECIAL_ALLOWED[arch]):
            raise RuntimeError("SPECIAL_ALLOWED_SET_PROOF_FAILED:" + arch)
    expected = {"JSON": 4, "REPEAT_PROMPT": 4, "TWO_RESPONSES": 8}
    if counts != expected or len(special_sets) != 16:
        raise RuntimeError("SPECIAL_ARCHETYPE_COVER_DRIFT")
    return {
        "schema": SCHEMA,
        "status": "PASS__16_OF_928_STRUCTURAL_SETS_ARE_SPECIAL_ARCHETYPES",
        "counts_by_archetype": counts,
        "covered_structural_set_count": len(special_sets),
        "total_structural_set_count": len(archetypes.enumerate_compatible_sets()),
        "remaining_structural_set_count": len(archetypes.enumerate_compatible_sets()) - len(special_sets),
        "independent_exact_checker_verification_required": True,
        "terminal_data_used": False,
        "acceptance_credit": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    if (args or {}).get("mode") == "structural_cover":
        return verify_structural_cover()
    return compose((args or {}).get("contracts") or [])


if __name__ == "__main__":
    print(json.dumps(verify_structural_cover(), indent=2, sort_keys=True))
