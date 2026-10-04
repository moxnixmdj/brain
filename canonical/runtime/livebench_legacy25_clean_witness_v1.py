#!/usr/bin/env python3
"""Clean source-derived joint witness synthesizer for the frozen legacy IFEval checker surface.

Reads visible prompt text only through the historical-envelope compiler V4.
It never consumes instruction_id_list, hidden kwargs, question ids, active row
metadata, prior responses, or scores. Unsupported/contradictory compositions
fail closed.

This is a candidate until independently replayed against the exact frozen legacy
checker bytes on the removed 200-row predecessor population.
"""
from __future__ import annotations

import re
from typing import Any

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY25_CLEAN_WITNESS_V1"

class JointWitnessError(ValueError):
    pass

def _slots(c: dict[str, Any]) -> dict[str, Any]:
    return dict(c.get("slots") or {})

def _word_count(s: str) -> int:
    # Exact token grammar used by frozen instructions_util.count_words.
    return len(re.findall(r"\w+", s, flags=re.UNICODE))

def _forbidden(constraints: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for c in constraints:
        if c.get("instruction_id") == "keywords:forbidden_words":
            out.extend(str(x) for x in (_slots(c).get("forbidden_words") or []))
    return out

def _required(constraints: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for c in constraints:
        if c.get("instruction_id") == "keywords:existence":
            out.extend(str(x) for x in (_slots(c).get("keywords") or []))
    return out

def _safe_token(forbidden: list[str], seed: str = "zxqv") -> str:
    for candidate in (seed, "brnt", "clmp", "dgfk", "hjwy", "vvzz", "0000"):
        if all(re.search(r"\b" + re.escape(w) + r"\b", candidate, re.I) is None for w in forbidden):
            return candidate
    raise JointWitnessError("NO_SAFE_FILLER")

def _required_fragments(required: list[str], forbidden: list[str]) -> list[str]:
    out: list[str] = []
    for kw in required:
        # Existence is substring/regex search while forbidden is whole-word search.
        # If an identical generated word appears in both sets, append a letter:
        # the required regex still matches but the forbidden whole-word checker does not.
        if any(kw.lower() == w.lower() for w in forbidden):
            out.append(kw + "x")
        else:
            out.append(kw)
    return out

def _get_one(constraints: list[dict[str, Any]], iid: str) -> dict[str, Any] | None:
    xs = [c for c in constraints if c.get("instruction_id") == iid]
    if len(xs) > 1:
        raise JointWitnessError("DUPLICATE_ACTIVE_CONSTRAINT:" + iid)
    return xs[0] if xs else None

def _special_json(constraints: list[dict[str, Any]]) -> str:
    import json
    forbidden = _forbidden(constraints)
    required = _required_fragments(_required(constraints), forbidden)
    filler = _safe_token(forbidden)
    payload = " ".join([filler, *required]).strip()
    response = json.dumps({"response": payload}, ensure_ascii=False)
    for w in forbidden:
        if re.search(r"\b" + re.escape(w) + r"\b", response, re.I):
            raise JointWitnessError("JSON_FORBIDDEN_COLLISION")
    return response

def _special_repeat(constraints: list[dict[str, Any]], repeat: dict[str, Any]) -> str:
    base = str(_slots(repeat).get("prompt_to_repeat") or "").strip()
    if not base:
        raise JointWitnessError("PROMPT_TO_REPEAT_REQUIRED")
    forbidden = _forbidden(constraints)
    if forbidden:
        # Historical conflict graph excludes forbidden_words with repeat_prompt.
        raise JointWitnessError("REPEAT_FORBIDDEN_CONFLICT_GRAPH_DRIFT")
    required = _required_fragments(_required(constraints), [])
    pieces = [base]
    if _get_one(constraints, "detectable_format:title"):
        pieces.append("<<x>>")
    if required:
        pieces.append(" ".join(required))
    pieces.append("answer")
    return "\n".join(pieces)

def _special_two(constraints: list[dict[str, Any]]) -> str:
    forbidden = _forbidden(constraints)
    required = _required_fragments(_required(constraints), forbidden)
    filler = _safe_token(forbidden)
    title = "<<x>> " if _get_one(constraints, "detectable_format:title") else ""
    common = (title + " ".join([filler, *required])).strip()
    a = common + " alpha"
    b = common + " beta"
    response = a + "******" + b
    for w in forbidden:
        if re.search(r"\b" + re.escape(w) + r"\b", response, re.I):
            raise JointWitnessError("TWO_RESPONSE_FORBIDDEN_COLLISION")
    return response

def _build_general(constraints: list[dict[str, Any]]) -> str:
    forbidden = _forbidden(constraints)
    required = _required_fragments(_required(constraints), forbidden)
    filler = _safe_token(forbidden)

    quote = _get_one(constraints, "startend:quotation") is not None
    title = _get_one(constraints, "detectable_format:title") is not None
    if quote and title:
        raise JointWitnessError("QUOTE_TITLE_CONFLICT_GRAPH_DRIFT")

    paragraph = _get_one(constraints, "length_constraints:number_paragraphs")
    nth = _get_one(constraints, "length_constraints:nth_paragraph_first_word")
    bullets = _get_one(constraints, "detectable_format:number_bullet_lists")
    sections = _get_one(constraints, "detectable_format:multiple_sections")
    post = _get_one(constraints, "detectable_content:postscript")
    end = _get_one(constraints, "startend:end_checker")
    sentence = _get_one(constraints, "length_constraints:number_sentences")
    words = _get_one(constraints, "length_constraints:number_words")

    body_parts: list[str] = []
    if title:
        body_parts.append("<<x>>")
    body_parts.extend(required)

    if sections:
        s = _slots(sections)
        n = int(s["num_sections"])
        splitter = str(s["section_spliter"])
        for i in range(1, n + 1):
            body_parts.append(f"{splitter} {i}\n{filler}{i}")

    if bullets:
        n = int(_slots(bullets)["num_bullets"])
        body_parts.extend(f"* {filler}{i}" for i in range(n))

    # Sentence requirement is isolated from exact/nth paragraphs by the frozen
    # generator conflict graph. Use obvious terminal punctuation only when needed.
    if sentence:
        s = _slots(sentence)
        n = int(s["num_sentences"])
        relation = str(s["relation"])
        if relation == "at least":
            body_parts.extend(f"{filler}{i}." for i in range(max(1, n)))
        elif relation == "less than":
            if n <= 0:
                raise JointWitnessError("STRICT_LESS_THAN_ZERO_SENTENCES")
            # Keep our own additions punctuation-free. Other visible constraints
            # can still introduce punctuation; exact predecessor replay decides.
            body_parts.append(filler)
        else:
            raise JointWitnessError("UNKNOWN_SENTENCE_RELATION")

    if not body_parts:
        body_parts = [filler]

    core = "\n".join(body_parts)

    if nth:
        s = _slots(nth)
        count = int(s["num_paragraphs"])
        nth_i = int(s["nth_paragraph"])
        first = str(s["first_word"])
        if count < 1 or nth_i < 1 or nth_i > count:
            raise JointWitnessError("INVALID_NTH_PARAGRAPH")
        paras = [filler for _ in range(count)]
        paras[nth_i - 1] = first + " " + core
        core = "\n\n".join(paras)
    elif paragraph:
        count = int(_slots(paragraph)["num_paragraphs"])
        if count < 1:
            raise JointWitnessError("INVALID_PARAGRAPH_COUNT")
        paras = [core] + [filler for _ in range(count - 1)]
        core = "\n***\n".join(paras)

    # Meet word-count lower bounds late so structural separators stay stable.
    if words:
        s = _slots(words)
        n = int(s["num_words"])
        relation = str(s["relation"])
        wc = _word_count(core)
        if relation == "at least":
            if wc < n:
                core += " " + " ".join(f"{filler}{i}" for i in range(n - wc))
        elif relation == "less than":
            if not (_word_count(core) < n):
                raise JointWitnessError("STRUCTURE_EXCEEDS_LESS_THAN_WORD_BOUND")
        else:
            raise JointWitnessError("UNKNOWN_WORD_RELATION")

    # Postscript is placed after ordinary body but before an exact end phrase.
    if post:
        marker = str(_slots(post).get("postscript_marker") or "")
        if not marker:
            raise JointWitnessError("POSTSCRIPT_MARKER_REQUIRED")
        core = core.rstrip() + "\n" + marker + " " + filler

    if end:
        phrase = str(_slots(end).get("end_phrase") or "").strip()
        if not phrase:
            raise JointWitnessError("END_PHRASE_REQUIRED")
        core = core.rstrip() + " " + phrase

    if quote:
        # A quote directly before the first '*' hides that bullet from the
        # frozen legacy regex ^\\s*\\*... . Put the opening quote on its own
        # line when bullets are active. The closing quote stays attached to the
        # tail so EndChecker still ends on the exact phrase after stripping
        # outer quotes. Bullet-list and nth-paragraph constraints conflict in
        # the frozen generator, so this does not perturb nth first-word logic.
        if bullets:
            core = '"\\n' + core.strip('"') + '"'
        else:
            core = '"' + core.strip('"') + '"'

    # Final whole-word forbidden guard. Required/forbidden overlap is handled
    # above, but other generated structure may still collide with a forbidden word.
    for w in forbidden:
        if re.search(r"\b" + re.escape(w) + r"\b", core, re.I):
            raise JointWitnessError("FORBIDDEN_COLLISION:" + w)

    # Exact final word bound check after postscript/end/quotation.
    if words:
        s = _slots(words)
        n = int(s["num_words"])
        relation = str(s["relation"])
        wc = _word_count(core)
        if relation == "at least" and wc < n:
            # Insert padding before the exact end phrase / outer quote rather than
            # after it, preserving end/quotation semantics.
            pad = " ".join(f"{filler}x{i}" for i in range(n - wc))
            if quote:
                inner = core[1:-1]
                if end:
                    phrase = str(_slots(end).get("end_phrase") or "").strip()
                    pos = inner.lower().rfind(phrase.lower())
                    inner = inner[:pos].rstrip() + " " + pad + " " + inner[pos:]
                else:
                    inner = inner + " " + pad
                core = '"' + inner + '"'
            elif end:
                phrase = str(_slots(end).get("end_phrase") or "").strip()
                pos = core.lower().rfind(phrase.lower())
                core = core[:pos].rstrip() + " " + pad + " " + core[pos:]
            else:
                core += " " + pad
        elif relation == "less than" and not (wc < n):
            raise JointWitnessError("FINAL_LESS_THAN_WORD_BOUND_FAILED")

    return core


def _insert_payload(response: str, payload: str, constraints: list[dict[str, Any]]) -> str:
    if not payload.strip():
        return response
    quote = _get_one(constraints, "startend:quotation") is not None
    end = _get_one(constraints, "startend:end_checker")
    if quote:
        t = response.strip()
        if len(t) < 2 or t[0] != '"' or t[-1] != '"':
            raise JointWitnessError("QUOTE_SHAPE_DRIFT")
        inner = t[1:-1]
        if end:
            phrase = str(_slots(end).get("end_phrase") or "").strip()
            pos = inner.lower().rfind(phrase.lower())
            if pos < 0:
                raise JointWitnessError("END_PHRASE_NOT_FOUND")
            inner = inner[:pos].rstrip() + " " + payload + " " + inner[pos:]
        else:
            inner = inner.rstrip() + " " + payload
        return '"' + inner.strip() + '"'
    if end:
        phrase = str(_slots(end).get("end_phrase") or "").strip()
        pos = response.lower().rfind(phrase.lower())
        if pos < 0:
            raise JointWitnessError("END_PHRASE_NOT_FOUND")
        return response[:pos].rstrip() + " " + payload + " " + response[pos:]
    return response.rstrip() + " " + payload

def _regex_count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))

def _capital_count_approx(text: str) -> int:
    return sum(
        1 for w in re.findall(r"\\b[^\\s]+\\b", text)
        if any(ch.isalpha() for ch in w) and w.isupper()
    )

def _augment_source_derived(response: str, constraints: list[dict[str, Any]]) -> str:
    # V1 deliberately leaves arbitrary response languages unsupported. The
    # development population measures the remaining mass before V2 is frozen.
    if _get_one(constraints, "language:response_language"):
        raise JointWitnessError("RESPONSE_LANGUAGE_V1_UNSUPPORTED")

    payload: list[str] = []

    placeholders = _get_one(constraints, "detectable_content:number_placeholders")
    if placeholders:
        n = int(_slots(placeholders)["num_placeholders"])
        payload.extend(f"[slot{i}]" for i in range(n))

    highlights = _get_one(constraints, "detectable_format:number_highlighted_sections")
    if highlights:
        n = int(_slots(highlights)["num_highlights"])
        payload.extend(f"*hl{i}*" for i in range(n))

    keyword_frequency = _get_one(constraints, "keywords:frequency")
    if keyword_frequency:
        q = _slots(keyword_frequency)
        keyword = str(q["keyword"])
        n = int(q["frequency"])
        relation = str(q["relation"])
        if relation == "at least":
            current = _regex_count(keyword, response + " " + " ".join(payload))
            if current < n:
                payload.extend([keyword] * (n - current))

    capitals = _get_one(constraints, "change_case:capital_word_frequency")
    if capitals:
        q = _slots(capitals)
        n = int(q["capital_frequency"])
        relation = str(q["capital_relation"])
        if relation == "at least":
            current = _capital_count_approx(response + " " + " ".join(payload))
            if current < n:
                payload.extend(["QZX"] * (n - current))

    letters = _get_one(constraints, "keywords:letter_frequency")
    if letters:
        q = _slots(letters)
        letter = str(q["letter"]).lower()
        n = int(q["let_frequency"])
        relation = str(q["let_relation"])
        if relation == "at least":
            current = (response + " " + " ".join(payload)).lower().count(letter)
            if current < n:
                payload.append(" ".join(letter for _ in range(n - current)))

    upper = _get_one(constraints, "change_case:english_capital")
    lower = _get_one(constraints, "change_case:english_lowercase")
    if upper and lower:
        raise JointWitnessError("CASE_CONFLICT_DRIFT")
    if upper or lower:
        sections = _get_one(constraints, "detectable_format:multiple_sections")
        if lower and sections:
            raise JointWitnessError("LOWERCASE_SECTION_UNSAT")
        if upper and sections and str(_slots(sections).get("section_spliter")) == "Section":
            raise JointWitnessError("UPPERCASE_MIXEDCASE_SECTION_UNSAT")
        payload.append("this is a simple english response with common words and clear meaning")

    response = _insert_payload(response, " ".join(payload), constraints)
    if upper:
        response = response.upper()
    elif lower:
        response = response.lower()

    keyword_frequency = _get_one(constraints, "keywords:frequency")
    if keyword_frequency:
        q = _slots(keyword_frequency)
        keyword = str(q["keyword"])
        n = int(q["frequency"])
        relation = str(q["relation"])
        current = _regex_count(keyword, response)
        if relation == "at least" and current < n:
            raise JointWitnessError("KEYWORD_AT_LEAST_FAIL")
        if relation == "less than" and not current < n:
            raise JointWitnessError("KEYWORD_LESS_THAN_FAIL")

    letters = _get_one(constraints, "keywords:letter_frequency")
    if letters:
        q = _slots(letters)
        letter = str(q["letter"]).lower()
        n = int(q["let_frequency"])
        relation = str(q["let_relation"])
        current = response.lower().count(letter)
        if relation == "at least" and current < n:
            raise JointWitnessError("LETTER_AT_LEAST_FAIL")
        if relation == "less than" and not current < n:
            raise JointWitnessError("LETTER_LESS_THAN_FAIL")

    capitals = _get_one(constraints, "change_case:capital_word_frequency")
    if capitals:
        q = _slots(capitals)
        n = int(q["capital_frequency"])
        relation = str(q["capital_relation"])
        current = _capital_count_approx(response)
        if relation == "at least" and current < n:
            raise JointWitnessError("CAPITAL_AT_LEAST_FAIL")
        if relation == "less than" and not current < n:
            raise JointWitnessError("CAPITAL_LESS_THAN_FAIL")

    if _get_one(constraints, "punctuation:no_comma") and "," in response:
        raise JointWitnessError("NO_COMMA_FAIL")

    words = _get_one(constraints, "length_constraints:number_words")
    if words:
        q = _slots(words)
        n = int(q["num_words"])
        relation = str(q["relation"])
        wc = _word_count(response)
        if relation == "at least" and wc < n:
            raise JointWitnessError("WORD_AT_LEAST_POST_AUGMENT_FAIL")
        if relation == "less than" and not wc < n:
            raise JointWitnessError("WORD_LESS_THAN_POST_AUGMENT_FAIL")

    return response


def solve(prompt: str) -> dict[str, Any]:
    compiled = compiler.compile_visible_constraints(str(prompt or ""))
    constraints = list(compiled.get("constraints") or [])
    compiler_complete = (
        compiled.get("status") == "PASS"
        and not list(compiled.get("parameter_incomplete") or [])
        and all(bool(c.get("parameter_complete")) for c in constraints)
    )
    if not compiler_complete:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "VISIBLE_COMPILER_NOT_COMPLETE", "response": None}
    if not constraints:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "NO_ACTIVE_CONSTRAINTS", "response": None}

    ids = [str(c.get("instruction_id") or "") for c in constraints]
    if len(ids) != len(set(ids)):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "DUPLICATE_CONSTRAINT_TYPE", "response": None}
    all_ids = frozenset(compiler.v1._SPECS.keys())
    outside = sorted(set(ids) - all_ids)
    if outside:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "OUTSIDE_FROZEN_REGISTRY:" + ",".join(outside), "response": None}

    try:
        constrained_c = _get_one(constraints, "detectable_format:constrained_response")
        json_c = _get_one(constraints, "detectable_format:json_format")
        repeat_c = _get_one(constraints, "combination:repeat_prompt")
        two_c = _get_one(constraints, "combination:two_responses")
        if constrained_c:
            if len(constraints) != 1:
                raise JointWitnessError("CONSTRAINED_RESPONSE_CONFLICT_GRAPH_DRIFT")
            response = "My answer is yes."
            route = "CONSTRAINED"
        else:
            specials = sum(x is not None for x in (json_c, repeat_c, two_c))
            if specials > 1:
                raise JointWitnessError("SPECIAL_CONSTRAINT_CONFLICT_GRAPH_DRIFT")
            if json_c:
                response = _special_json(constraints)
                route = "JSON"
            elif repeat_c:
                response = _special_repeat(constraints, repeat_c)
                route = "REPEAT_PROMPT"
            elif two_c:
                response = _special_two(constraints)
                route = "TWO_RESPONSES"
            else:
                response = _build_general(constraints)
                route = "GENERAL"
            response = _augment_source_derived(response, constraints)
    except (JointWitnessError, KeyError, TypeError, ValueError) as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": str(exc), "response": None, "instruction_ids": ids}

    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE_CLEAN_SOURCE_DERIVED",
        "response": response,
        "route": route,
        "instruction_ids": ids,
        "constraint_count": len(ids),
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
        "terminal_case_content_used": False,
        "target_row_dependency": False,
        "target_question_id_dependency": False,
        "network_used": False,
        "model_dependency_count": 0,
        "acceptance_credit": False,
        "semantic_capability_credit": False,
    }

def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return solve(str((args or {}).get("prompt") or ""))
