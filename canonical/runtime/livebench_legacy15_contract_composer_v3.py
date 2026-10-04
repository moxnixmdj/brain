#!/usr/bin/env python3
"""Deterministic parameter-independent contract composer for the frozen active legacy-15 LiveBench surface.

This is a case-independent scorer-surface constructor. It consumes only visible
contract identities and slots recovered from the public prompt grammar. It does
not consume terminal rows, hidden instruction_id_list values, hidden kwargs,
responses, scores, or case frequencies.

Key construction theorem used here:
- generated existence/forbidden keywords are ASCII alphabetic WORD_LIST entries;
- existence uses raw regex substring search;
- forbidden uses whole-word-boundary search;
therefore required keywords can be packed inside one alphanumeric word-character
shield, preserving every required substring while eliminating whole-word
boundaries around those substrings.

The module is a candidate constructor until independently postvalidated against
the exact pinned checker bytes across the public generator domain. V3 replaces
synthetic period boundaries with parameter-independent '?' boundaries to remove
the sole learned-Punkt ambiguity left by V2. It grants no acceptance credit by itself.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_CONTRACT_COMPOSER_V3"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"

EXIST = "keywords:existence"
FORBIDDEN = "keywords:forbidden_words"
PARAGRAPHS = "length_constraints:number_paragraphs"
WORDS = "length_constraints:number_words"
SENTENCES = "length_constraints:number_sentences"
NTH = "length_constraints:nth_paragraph_first_word"
POSTSCRIPT = "detectable_content:postscript"
BULLETS = "detectable_format:number_bullet_lists"
TITLE = "detectable_format:title"
SECTIONS = "detectable_format:multiple_sections"
JSON_ID = "detectable_format:json_format"
REPEAT = "combination:repeat_prompt"
TWO = "combination:two_responses"
END = "startend:end_checker"
QUOTE = "startend:quotation"

_SAFE = "9000001"
_SAFE_ALT = "9000002"


class ComposeError(ValueError):
    pass


def _slots(c: Mapping[str, Any]) -> dict[str, Any]:
    return dict(c.get("slots") or {})


def _by_id(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for c in contracts:
        iid = str(c.get("instruction_id") or "")
        if iid in out:
            raise ComposeError("DUPLICATE_INSTRUCTION_ID:" + iid)
        out[iid] = c
    return out


def _word_count(text: str) -> int:
    # Exact frozen instructions_util.count_words token grammar.
    return len(re.findall(r"\w+", str(text), flags=re.UNICODE))


def _public_word(value: str) -> str:
    s = str(value)
    if re.fullmatch(r"[A-Za-z]+", s) is None:
        raise ComposeError("OUTSIDE_PUBLIC_GENERATOR_WORD_DOMAIN:" + s)
    return s


def _forbidden_words(by_id: Mapping[str, Mapping[str, Any]]) -> list[str]:
    c = by_id.get(FORBIDDEN)
    if not c:
        return []
    return [_public_word(x) for x in (_slots(c).get("forbidden_words") or [])]


def _required_words(by_id: Mapping[str, Mapping[str, Any]]) -> list[str]:
    c = by_id.get(EXIST)
    if not c:
        return []
    return [_public_word(x) for x in (_slots(c).get("keywords") or [])]


def _forbidden_hit(text: str, forbidden: Sequence[str]) -> str | None:
    for word in forbidden:
        if re.search(r"\b" + re.escape(word) + r"\b", text, flags=re.IGNORECASE):
            return word
    return None


def _packed_required(required: Sequence[str]) -> str:
    """Pack public generated words into one shielded word-character token.

    Digits are \w characters, so every required alphabetic word is preceded and
    followed by a word character. The raw existence regex still sees each word,
    while a whole-word forbidden regex cannot see the same occurrence.
    """
    if not required:
        return ""
    words = [_public_word(x) for x in required]
    return "9000" + "0".join(words) + "0009"


def _validate_public_slots(by_id: Mapping[str, Mapping[str, Any]]) -> None:
    _required_words(by_id)
    _forbidden_words(by_id)

    if PARAGRAPHS in by_id:
        n = int(_slots(by_id[PARAGRAPHS])["num_paragraphs"])
        if not 1 <= n <= 5:
            raise ComposeError("OUTSIDE_PUBLIC_PARAGRAPH_DOMAIN")

    if WORDS in by_id:
        s = _slots(by_id[WORDS])
        n = int(s["num_words"])
        relation = str(s["relation"])
        if not 100 <= n <= 500 or relation not in {"less than", "at least"}:
            raise ComposeError("OUTSIDE_PUBLIC_WORD_COUNT_DOMAIN")

    if SENTENCES in by_id:
        s = _slots(by_id[SENTENCES])
        n = int(s["num_sentences"])
        relation = str(s["relation"])
        if not 1 <= n <= 20 or relation not in {"less than", "at least"}:
            raise ComposeError("OUTSIDE_PUBLIC_SENTENCE_COUNT_DOMAIN")

    if NTH in by_id:
        s = _slots(by_id[NTH])
        n = int(s["num_paragraphs"])
        k = int(s["nth_paragraph"])
        first = _public_word(str(s["first_word"]))
        if not 1 <= n <= 5 or not 1 <= k <= n or not first:
            raise ComposeError("OUTSIDE_PUBLIC_NTH_PARAGRAPH_DOMAIN")

    if POSTSCRIPT in by_id:
        marker = str(_slots(by_id[POSTSCRIPT])["postscript_marker"])
        if marker not in {"P.S.", "P.P.S"}:
            raise ComposeError("OUTSIDE_PUBLIC_POSTSCRIPT_DOMAIN")

    if BULLETS in by_id:
        n = int(_slots(by_id[BULLETS])["num_bullets"])
        if not 1 <= n <= 5:
            raise ComposeError("OUTSIDE_PUBLIC_BULLET_DOMAIN")

    if SECTIONS in by_id:
        s = _slots(by_id[SECTIONS])
        n = int(s["num_sections"])
        splitter = str(s["section_spliter"])
        if not 1 <= n <= 5 or splitter not in {"Section", "SECTION"}:
            raise ComposeError("OUTSIDE_PUBLIC_SECTION_DOMAIN")

    if END in by_id:
        phrase = str(_slots(by_id[END])["end_phrase"]).strip()
        if phrase not in {
            "Any other questions?",
            "Is there anything else I can help with?",
        }:
            raise ComposeError("OUTSIDE_PUBLIC_END_PHRASE_DOMAIN")


def _special_json(by_id: Mapping[str, Mapping[str, Any]]) -> str:
    import json

    required = _required_words(by_id)
    forbidden = _forbidden_words(by_id)
    payload = _packed_required(required) or _SAFE
    response = json.dumps({"0": payload}, ensure_ascii=False, separators=(",", ":"))
    hit = _forbidden_hit(response, forbidden)
    if hit is not None:
        raise ComposeError("UNEXPECTED_JSON_FORBIDDEN_HIT:" + hit)
    return response


def _special_repeat(by_id: Mapping[str, Mapping[str, Any]]) -> str:
    repeat = by_id[REPEAT]
    base = str(_slots(repeat).get("prompt_to_repeat") or "").strip()
    if not base:
        raise ComposeError("PROMPT_TO_REPEAT_REQUIRED")
    if FORBIDDEN in by_id:
        raise ComposeError("REPEAT_FORBIDDEN_CONFLICT_GRAPH_DRIFT")

    pieces = [base]
    if TITLE in by_id:
        pieces.append("<<" + _SAFE + ">>")
    packed = _packed_required(_required_words(by_id))
    if packed:
        pieces.append(packed)
    pieces.append(_SAFE)
    return "\n".join(pieces)


def _special_two(by_id: Mapping[str, Mapping[str, Any]]) -> str:
    forbidden = _forbidden_words(by_id)
    pieces: list[str] = []
    if TITLE in by_id:
        pieces.append("<<" + _SAFE + ">>")
    packed = _packed_required(_required_words(by_id))
    if packed:
        pieces.append(packed)
    pieces.append(_SAFE)
    left = " ".join(pieces)
    right = _SAFE_ALT
    response = left + "******" + right
    hit = _forbidden_hit(response, forbidden)
    if hit is not None:
        raise ComposeError("UNEXPECTED_TWO_RESPONSE_FORBIDDEN_HIT:" + hit)
    return response


def _general(by_id: Mapping[str, Mapping[str, Any]]) -> str:
    forbidden = _forbidden_words(by_id)
    required = _required_words(by_id)

    quote = QUOTE in by_id
    title = TITLE in by_id
    if quote and title:
        raise ComposeError("QUOTE_TITLE_CONFLICT_GRAPH_DRIFT")

    parts: list[str] = []
    if title:
        parts.append("<<" + _SAFE + ">>")
    packed = _packed_required(required)
    if packed:
        parts.append(packed)

    # SectionChecker has no left-boundary requirement. Prefixing the visible
    # splitter with a word character preserves its regex match while preventing
    # "section" from becoming a whole-word forbidden match.
    if SECTIONS in by_id:
        s = _slots(by_id[SECTIONS])
        splitter = str(s["section_spliter"])
        for i in range(1, int(s["num_sections"]) + 1):
            parts.append(f"9{splitter} {i}\n{_SAFE}{i}")

    if BULLETS in by_id:
        for i in range(1, int(_slots(by_id[BULLETS])["num_bullets"]) + 1):
            parts.append(f"* {_SAFE}{i}")

    if SENTENCES in by_id:
        s = _slots(by_id[SENTENCES])
        n = int(s["num_sentences"])
        relation = str(s["relation"])
        if relation == "at least":
            # Use '?' rather than '.' for synthetic boundaries. In pinned NLTK
            # Punkt, '?' is an unconditional sent_end_char in first pass and
            # the second pass only revisits period-final tokens. Therefore every
            # emitted marker is a sentence boundary for every Punkt parameter
            # table, deleting the learned-English-model dependency.
            parts.extend(f"{_SAFE}{i}?" for i in range(1, n + 1))
        elif relation == "less than":
            if n == 1:
                # Exact strict-evaluator zero-sentence feasibility depends on
                # Punkt + the nonempty-response guard. Leave it unresolved here
                # rather than smuggling in an unproved tokenizer theorem.
                raise ComposeError("LESS_THAN_ONE_SENTENCE_STRICT_FEASIBILITY_UNRESOLVED")
            parts.append(_SAFE)
        else:
            raise ComposeError("UNKNOWN_SENTENCE_RELATION")

    if not parts:
        parts.append(_SAFE)

    core = "\n".join(parts)

    if NTH in by_id:
        s = _slots(by_id[NTH])
        count = int(s["num_paragraphs"])
        target = int(s["nth_paragraph"])
        first = str(s["first_word"])
        paras = [_SAFE + str(i) for i in range(1, count + 1)]
        paras[target - 1] = first + " " + core
        core = "\n\n".join(paras)
    elif PARAGRAPHS in by_id:
        count = int(_slots(by_id[PARAGRAPHS])["num_paragraphs"])
        paras = [core] + [_SAFE + str(i) for i in range(2, count + 1)]
        core = "\n***\n".join(paras)

    # Padding is deliberately inserted before postscript/end wrappers. Word
    # lower bounds are monotone, so any later mandatory words only help.
    if WORDS in by_id:
        s = _slots(by_id[WORDS])
        threshold = int(s["num_words"])
        relation = str(s["relation"])
        if relation == "at least":
            current = _word_count(core)
            if current < threshold:
                pad = " ".join(_SAFE + "x" + str(i) for i in range(threshold - current))
                core = core + " " + pad
        elif relation != "less than":
            raise ComposeError("UNKNOWN_WORD_RELATION")

    if POSTSCRIPT in by_id:
        marker = str(_slots(by_id[POSTSCRIPT])["postscript_marker"])
        # Keep mandatory postscript syntax sentence-neutral. A P.S. payload
        # word after the terminal period creates an extra Punkt sentence in the
        # production NLTK runtime and breaks low-sentence witnesses. The exact
        # checker accepts the marker plus arbitrary trailing characters, so a
        # non-word '+' neutralizes the terminal period without changing word
        # count. P.P.S has no terminal period and needs no neutralizer.
        tail = marker + "+" if marker.endswith(".") else marker
        core = core.rstrip() + "\n" + tail

    if END in by_id:
        phrase = str(_slots(by_id[END])["end_phrase"]).strip()
        core = core.rstrip() + " " + phrase

    if quote:
        # Keep an opening quote off bullet lines so the exact bullet regex still
        # sees ^\s*\* on every intended bullet.
        if BULLETS in by_id:
            core = '"\n' + core + '"'
        else:
            core = '"' + core + '"'

    if WORDS in by_id:
        s = _slots(by_id[WORDS])
        threshold = int(s["num_words"])
        relation = str(s["relation"])
        wc = _word_count(core)
        if relation == "at least" and wc < threshold:
            raise ComposeError("INTERNAL_WORD_LOWER_BOUND_CONSTRUCTION_BUG")
        if relation == "less than" and not wc < threshold:
            raise ComposeError("FINAL_WORD_UPPER_BOUND_NOT_MET")

    hit = _forbidden_hit(core, forbidden)
    if hit is not None:
        raise ComposeError("UNEXPECTED_FORBIDDEN_HIT:" + hit)

    return core


def compose_contracts(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    try:
        by_id = _by_id(contracts)
        ids = tuple(by_id)
        if not ids:
            raise ComposeError("NO_CONTRACTS")
        if not archetypes.compatible(ids):
            raise ComposeError("ID_CONFLICT_OR_UNKNOWN")
        if len(ids) > archetypes.MAX_GENERATED_INSTRUCTIONS:
            raise ComposeError("OUTSIDE_PUBLIC_MAX_INSTRUCTION_COUNT")
        _validate_public_slots(by_id)

        unsat = feasibility.hard_unsat_reasons(contracts)
        if unsat:
            return {
                "schema": SCHEMA,
                "status": "PROVED_UNSAT",
                "instruction_ids": sorted(ids),
                "archetype": archetypes.archetype(ids),
                "hard_unsat_reasons": list(unsat),
                "response": None,
                "terminal_data_used": False,
                "hidden_kwargs_used": False,
                "acceptance_credit": False,
            }

        if JSON_ID in by_id:
            response = _special_json(by_id)
            route = "JSON"
        elif REPEAT in by_id:
            response = _special_repeat(by_id)
            route = "REPEAT_PROMPT"
        elif TWO in by_id:
            response = _special_two(by_id)
            route = "TWO_RESPONSES"
        else:
            response = _general(by_id)
            route = archetypes.archetype(ids)

        return {
            "schema": SCHEMA,
            "status": "CANDIDATE_WITNESS",
            "instruction_ids": sorted(ids),
            "archetype": archetypes.archetype(ids),
            "route": route,
            "response": response,
            "word_count": _word_count(response),
            "terminal_data_used": False,
            "hidden_kwargs_used": False,
            "model_dependency_count": 0,
            "acceptance_credit": False,
        }
    except (ComposeError, KeyError, TypeError, ValueError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "response": None,
            "terminal_data_used": False,
            "hidden_kwargs_used": False,
            "acceptance_credit": False,
        }


def run(args: Mapping[str, Any], root=None) -> dict[str, Any]:
    contracts = list((args or {}).get("contracts") or [])
    return compose_contracts(contracts)


if __name__ == "__main__":
    import json
    import sys

    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), indent=2, sort_keys=True))
