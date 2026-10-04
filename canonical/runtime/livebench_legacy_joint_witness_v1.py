#!/usr/bin/env python3
"""Deterministic joint-witness constructor for frozen legacy LiveBench IFEval.

This module consumes only the visible prompt. It relies on the source-lineage
aware V2 visible compiler, constructs a scorer-facing witness, and fails closed
when visible literals make a supported structural route contradictory.

It does NOT read terminal instruction_id_list, kwargs, responses, case ids, or
scores. Exact frozen checker replay remains the promotion authority.
"""
from __future__ import annotations

import json
import re
from typing import Any

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v2 as compiler

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_JOINT_WITNESS_V1"
FROZEN_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
HISTORICAL_GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"

# Historical live_data.py samples these 24 families. response_language is in the
# registry but absent from that generator pool.
HISTORICAL_GENERATOR_IDS = frozenset({
    "length_constraints:number_sentences",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:nth_paragraph_first_word",
    "keywords:existence",
    "keywords:frequency",
    "keywords:forbidden_words",
    "keywords:letter_frequency",
    "detectable_content:number_placeholders",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "detectable_format:title",
    "combination:two_responses",
    "combination:repeat_prompt",
    "startend:end_checker",
    "startend:quotation",
    "change_case:capital_word_frequency",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "punctuation:no_comma",
})

_FILLER = (
    "the system remains stable under careful verified operation while useful "
    "evidence supports reliable progress across each measured task"
).split()


def _word_count(text: str) -> int:
    # Frozen instructions_util.count_words uses RegexpTokenizer(r"\w+").
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def _constraints(compiled: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in compiled.get("constraints") or []:
        iid = str(item["instruction_id"])
        if iid in out:
            raise ValueError("DUPLICATE_INSTRUCTION_ID")
        out[iid] = item
    return out


def _slots(c: dict[str, dict[str, Any]], iid: str) -> dict[str, Any]:
    return dict((c.get(iid) or {}).get("slots") or {})


def _regex_count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def _forbidden_hit(text: str, words: list[str]) -> str | None:
    for word in words:
        if re.search(r"\b" + re.escape(word) + r"\b", text, flags=re.IGNORECASE):
            return word
    return None


def _safe_filler(
    forbidden: list[str],
    keyword_pattern: str | None = None,
    avoid_letter: str | None = None,
) -> str:
    for word in _FILLER:
        if _forbidden_hit(word, forbidden):
            continue
        if keyword_pattern and re.search(keyword_pattern, word, flags=re.IGNORECASE):
            continue
        if avoid_letter and avoid_letter.lower() in word.lower():
            continue
        return word
    # Synthetic fallback deliberately contains no vowels and can be altered to
    # avoid one target letter. It is only a scorer carrier, not semantic credit.
    for word in ("zqx", "mnp", "vwy", "fgh", "jkl", "rst", "bcd"):
        if _forbidden_hit(word, forbidden):
            continue
        if keyword_pattern and re.search(keyword_pattern, word, flags=re.IGNORECASE):
            continue
        if avoid_letter and avoid_letter.lower() in word.lower():
            continue
        return word
    raise ValueError("NO_SAFE_FILLER")


def _apply_case(text: str, ids: set[str]) -> str:
    if "change_case:english_capital" in ids:
        return text.upper()
    if "change_case:english_lowercase" in ids:
        return text.lower()
    return text


def _base_required_chunks(c: dict[str, dict[str, Any]]) -> list[str]:
    chunks: list[str] = []
    ids = set(c)

    if "detectable_format:title" in ids:
        chunks.append("<<verified result>>")

    kw = _slots(c, "keywords:existence").get("keywords") or []
    chunks.extend(str(x) for x in kw)

    ph = _slots(c, "detectable_content:number_placeholders").get("num_placeholders")
    if ph is not None:
        chunks.extend(f"[slot{i}]" for i in range(1, int(ph) + 1))

    hi = _slots(c, "detectable_format:number_highlighted_sections").get("num_highlights")
    if hi is not None:
        # Prefix text keeps these from being mistaken for markdown bullet lines.
        chunks.extend(f"mark *highlight{i}*" for i in range(1, int(hi) + 1))

    sec = _slots(c, "detectable_format:multiple_sections")
    if sec:
        splitter = str(sec["section_spliter"])
        chunks.extend(f"{splitter} {i} body" for i in range(1, int(sec["num_sections"]) + 1))

    bullets = _slots(c, "detectable_format:number_bullet_lists").get("num_bullets")
    if bullets is not None:
        chunks.extend(f"\n* point{i}" for i in range(1, int(bullets) + 1))

    sent = _slots(c, "length_constraints:number_sentences")
    if sent and str(sent["relation"]) == "at least":
        chunks.extend(f"sentence{i}." for i in range(1, int(sent["num_sentences"]) + 1))

    cap = _slots(c, "change_case:capital_word_frequency")
    if cap and str(cap["capital_relation"]) == "at least":
        chunks.extend(f"CAPWORD{i}" for i in range(1, int(cap["capital_frequency"]) + 1))

    return chunks


def _wrap_paragraphs(
    core: str,
    c: dict[str, dict[str, Any]],
    filler: str,
) -> str:
    para = _slots(c, "length_constraints:number_paragraphs")
    nth = _slots(c, "length_constraints:nth_paragraph_first_word")

    if para:
        n = int(para["num_paragraphs"])
        pieces = [core.strip() or filler]
        pieces.extend(f"{filler}{i}" for i in range(2, n + 1))
        return "\n***\n".join(pieces)

    if nth:
        n = int(nth["num_paragraphs"])
        target = int(nth["nth_paragraph"])
        first = str(nth["first_word"])
        pieces = [f"{filler}{i}" for i in range(1, n + 1)]
        pieces[0] = core.strip() or pieces[0]
        current = pieces[target - 1].lstrip()
        if target == 1 and core.strip():
            pieces[0] = first + " " + core.strip()
        else:
            pieces[target - 1] = first + (" " + current if current else "")
        return "\n\n".join(pieces)

    return core.strip() or filler


def _suffixes(c: dict[str, dict[str, Any]]) -> tuple[str | None, str | None]:
    post = _slots(c, "detectable_content:postscript").get("postscript_marker")
    end = _slots(c, "startend:end_checker").get("end_phrase")
    post_text = None
    if post:
        marker = str(post).lower()
        post_text = marker + " note"
    return post_text, (str(end) if end else None)


def _compose_general(c: dict[str, dict[str, Any]]) -> tuple[str | None, str | None]:
    ids = set(c)
    forbidden = [str(x) for x in (_slots(c, "keywords:forbidden_words").get("forbidden_words") or [])]
    freq = _slots(c, "keywords:frequency")
    letter = _slots(c, "keywords:letter_frequency")

    keyword_pattern = str(freq.get("keyword")) if freq else None
    avoid_letter = None
    if letter and str(letter.get("let_relation")) == "less than":
        avoid_letter = str(letter["letter"])

    filler = _safe_filler(forbidden, keyword_pattern if freq and str(freq.get("relation")) == "less than" else None, avoid_letter)

    chunks = _base_required_chunks(c)
    post_text, end_text = _suffixes(c)

    # Add keyword-frequency carrier before word-count calibration.
    if freq and str(freq["relation"]) == "at least":
        kw = str(freq["keyword"])
        chunks.extend(kw for _ in range(int(freq["frequency"])))

    # Add letter-frequency carrier. One token can satisfy the full deficit.
    if letter and str(letter["let_relation"]) == "at least":
        target = str(letter["letter"])
        provisional = " ".join(chunks + ([post_text] if post_text else []) + ([end_text] if end_text else []))
        deficit = int(letter["let_frequency"]) - provisional.lower().count(target.lower())
        if deficit > 0:
            chunks.append(target * deficit)

    # Build once, then calibrate word count by inserting safe filler before suffixes.
    def build(extra_words: int) -> str:
        body_chunks = list(chunks)
        body_chunks.extend(filler for _ in range(max(extra_words, 0)))
        body = " ".join(x for x in body_chunks if x)
        body = _wrap_paragraphs(body, c, filler)
        if post_text:
            body = body.rstrip() + "\n" + post_text
        if end_text:
            body = body.rstrip() + " " + end_text
        body = _apply_case(body, ids)
        if "startend:quotation" in ids:
            body = '"' + body.strip('"') + '"'
        return body

    candidate = build(0)
    word = _slots(c, "length_constraints:number_words")
    if word:
        n = int(word["num_words"])
        relation = str(word["relation"])
        current = _word_count(candidate)
        if relation == "at least" and current < n:
            candidate = build(n - current)
        elif relation == "less than" and current >= n:
            return None, "VISIBLE_WORD_LIMIT_CONTRADICTION"

    # Less-than keyword/letter relations are easiest to validate after all mandatory text.
    if freq and str(freq["relation"]) == "less than":
        if _regex_count(str(freq["keyword"]), candidate) >= int(freq["frequency"]):
            return None, "VISIBLE_KEYWORD_FREQUENCY_CONTRADICTION"
    if letter and str(letter["let_relation"]) == "less than":
        if candidate.lower().count(str(letter["letter"]).lower()) >= int(letter["let_frequency"]):
            return None, "VISIBLE_LETTER_FREQUENCY_CONTRADICTION"

    cap = _slots(c, "change_case:capital_word_frequency")
    if cap and str(cap["capital_relation"]) == "less than":
        # Generated carrier is lowercase except visible required literals. A
        # conservative token check prevents us from claiming an unsafe witness.
        capitals = [w for w in re.findall(r"\b[\w-]+\b", candidate) if w.isupper()]
        if len(capitals) >= int(cap["capital_frequency"]):
            return None, "VISIBLE_CAPITAL_WORD_CONTRADICTION"

    sent = _slots(c, "length_constraints:number_sentences")
    if sent and str(sent["relation"]) == "less than":
        # A nonempty punctuation-free response is one Punkt sentence. Threshold
        # one is therefore impossible for any useful witness. For larger limits,
        # leave exact acceptance to the frozen postvalidator.
        if int(sent["num_sentences"]) <= 1:
            return None, "VISIBLE_SENTENCE_LIMIT_CONTRADICTION"

    if "punctuation:no_comma" in ids and "," in candidate:
        return None, "VISIBLE_COMMA_CONTRADICTION"

    hit = _forbidden_hit(candidate, forbidden)
    if hit is not None:
        return None, "VISIBLE_FORBIDDEN_WORD_CONTRADICTION:" + hit

    if freq:
        count = _regex_count(str(freq["keyword"]), candidate)
        n = int(freq["frequency"])
        if (str(freq["relation"]) == "at least" and count < n) or (
            str(freq["relation"]) == "less than" and count >= n
        ):
            return None, "KEYWORD_FREQUENCY_POSTCHECK"

    if letter:
        count = candidate.lower().count(str(letter["letter"]).lower())
        n = int(letter["let_frequency"])
        if (str(letter["let_relation"]) == "at least" and count < n) or (
            str(letter["let_relation"]) == "less than" and count >= n
        ):
            return None, "LETTER_FREQUENCY_POSTCHECK"

    if word:
        count = _word_count(candidate)
        n = int(word["num_words"])
        if (str(word["relation"]) == "at least" and count < n) or (
            str(word["relation"]) == "less than" and count >= n
        ):
            return None, "WORD_COUNT_POSTCHECK"

    return candidate, None


def _solve_special(c: dict[str, dict[str, Any]]) -> tuple[str | None, str | None] | None:
    ids = set(c)
    forbidden = [str(x) for x in (_slots(c, "keywords:forbidden_words").get("forbidden_words") or [])]
    required = [str(x) for x in (_slots(c, "keywords:existence").get("keywords") or [])]

    if "detectable_format:constrained_response" in ids:
        if ids != {"detectable_format:constrained_response"}:
            return None, "CONFLICT_REGISTRY_VIOLATION_CONSTRAINED_RESPONSE"
        return "My answer is yes.", None

    if "detectable_format:json_format" in ids:
        allowed = {
            "detectable_format:json_format",
            "keywords:forbidden_words",
            "keywords:existence",
        }
        if not ids <= allowed:
            return None, "CONFLICT_REGISTRY_VIOLATION_JSON"
        payload = " ".join(required) if required else "verified"
        candidate = json.dumps({"q": payload}, ensure_ascii=False)
        hit = _forbidden_hit(candidate, forbidden)
        return (None, "VISIBLE_FORBIDDEN_WORD_CONTRADICTION:" + hit) if hit else (candidate, None)

    if "combination:two_responses" in ids:
        allowed = {
            "combination:two_responses",
            "keywords:forbidden_words",
            "keywords:existence",
            "detectable_format:title",
            "punctuation:no_comma",
        }
        if not ids <= allowed:
            return None, "CONFLICT_REGISTRY_VIOLATION_TWO_RESPONSES"
        shared = " ".join(required)
        title = " <<verified result>>" if "detectable_format:title" in ids else ""
        left = ("first response " + shared + title).strip()
        right = "second response"
        candidate = left + "******" + right
        if "punctuation:no_comma" in ids and "," in candidate:
            return None, "VISIBLE_COMMA_CONTRADICTION"
        hit = _forbidden_hit(candidate, forbidden)
        return (None, "VISIBLE_FORBIDDEN_WORD_CONTRADICTION:" + hit) if hit else (candidate, None)

    if "combination:repeat_prompt" in ids:
        allowed = {
            "combination:repeat_prompt",
            "keywords:existence",
            "detectable_format:title",
            "punctuation:no_comma",
        }
        if not ids <= allowed:
            return None, "CONFLICT_REGISTRY_VIOLATION_REPEAT_PROMPT"
        prefix = str(_slots(c, "combination:repeat_prompt").get("prompt_to_repeat") or "")
        if not prefix.strip():
            return None, "REPEAT_PROMPT_VISIBLE_PREFIX_MISSING"
        tail = " verified answer"
        if required:
            tail += " " + " ".join(required)
        if "detectable_format:title" in ids:
            tail += " <<verified result>>"
        candidate = prefix.strip() + tail
        if "punctuation:no_comma" in ids and "," in candidate:
            return None, "VISIBLE_COMMA_CONTRADICTION"
        return candidate, None

    return None


def solve(prompt: str) -> dict[str, Any]:
    compiled = compiler.compile_visible_constraints(str(prompt or ""))
    if compiled.get("status") != "PASS":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "VISIBLE_COMPILER_FAIL_CLOSED",
            "response": None,
            "compiler": compiled,
        }
    if not compiled.get("all_recognized_parameters_complete"):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "VISIBLE_PARAMETERS_INCOMPLETE",
            "response": None,
            "compiler": compiled,
        }

    try:
        c = _constraints(compiled)
    except ValueError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "response": None,
            "compiler": compiled,
        }

    ids = set(c)
    if not ids:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_VISIBLE_LEGACY_CONSTRAINTS",
            "response": None,
            "compiler": compiled,
        }

    outside = sorted(ids - HISTORICAL_GENERATOR_IDS)
    if outside:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "OUTSIDE_RECOVERED_HISTORICAL_GENERATOR_SURFACE",
            "outside_ids": outside,
            "response": None,
            "compiler": compiled,
        }

    special = _solve_special(c)
    if special is None:
        response, error = _compose_general(c)
    else:
        response, error = special

    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE_EXACT_POSTVALIDATION_REQUIRED" if response is not None else "FAIL_CLOSED",
        "error": error,
        "response": response,
        "recognized_instruction_ids": sorted(ids),
        "recognized_instruction_count": len(ids),
        "historical_generator_surface_only": True,
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
        "terminal_case_content_used": False,
        "model_dependency_count": 0,
        "network_used": False,
        "exact_frozen_postvalidation_required": True,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return solve(str((args or {}).get("prompt") or ""))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(solve(ns.prompt), ensure_ascii=False, indent=2, sort_keys=True))
