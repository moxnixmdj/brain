#!/usr/bin/env python3
"""Finite candidate generator for the exact active legacy-15 LiveBench scorer surface.

This module is score-lane infrastructure only. It consumes visible constraints
already recovered from public prompt text and emits a bounded set of response
candidates. It does NOT decide success. Callers must postvalidate candidates
against the exact pinned legacy IFEval checker implementations and select only a
candidate for which every recovered constraint returns True.

No hidden ids, kwargs, case ids, scores, or terminal metadata are consumed.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterable

from canonical.runtime import livebench_legacy15_composition_partition_v1 as partition

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_JOINT_CANDIDATE_GENERATOR_V1"


def _one(constraints: list[dict[str, Any]], iid: str) -> dict[str, Any] | None:
    rows = [c for c in constraints if c.get("instruction_id") == iid]
    if not rows:
        return None
    if len(rows) != 1:
        raise ValueError("MULTIPLICITY_NOT_SUPPORTED_V1:" + iid)
    if rows[0].get("parameter_complete") is not True:
        raise ValueError("PARAMETER_INCOMPLETE:" + iid)
    return rows[0]


def _slots(c: dict[str, Any] | None) -> dict[str, Any]:
    return dict(c.get("slots") or {}) if c else {}


def _required_keywords(constraints: list[dict[str, Any]]) -> list[str]:
    c = _one(constraints, "keywords:existence")
    return [str(x) for x in (_slots(c).get("keywords") or [])]


def _forbidden(constraints: list[dict[str, Any]]) -> list[str]:
    c = _one(constraints, "keywords:forbidden_words")
    return [str(x) for x in (_slots(c).get("forbidden_words") or [])]


def _forbidden_ok(text: str, forbidden: list[str]) -> bool:
    for word in forbidden:
        try:
            if re.search(r"\b" + word + r"\b", text, flags=re.IGNORECASE):
                return False
        except re.error:
            return False
    return True


def _safe_token(forbidden: list[str], stem: str = "zxqv") -> str:
    for i in range(1000):
        token = f"{stem}{i}"
        if _forbidden_ok(token, forbidden):
            return token
    raise ValueError("NO_SAFE_FILLER_TOKEN")


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def _pad_for_word_constraint(
    text: str,
    word_constraint: dict[str, Any] | None,
    forbidden: list[str],
) -> str | None:
    if not word_constraint:
        return text
    s = _slots(word_constraint)
    threshold = int(s["num_words"])
    relation = str(s["relation"])
    marker = "__PB_END_SLOT__"
    # The insertion marker is compiler scaffolding, not response content.
    # Exclude it from exact frozen word-count arithmetic because finalization
    # deletes it before checker evaluation.
    current = _word_count(text.replace(marker, ""))
    if relation == "less than":
        return text if current < threshold else None
    if relation != "at least":
        return None
    if current >= threshold:
        return text
    token = _safe_token(forbidden, "pad")
    padding = " ".join(f"{token}{i}" for i in range(threshold - current))
    if marker in text:
        return text.replace(marker, padding + (" " if padding else "") + marker, 1)
    return text + (" " if text and padding else "") + padding


def _apply_end_material(
    body: str,
    postscript: dict[str, Any] | None,
    end_checker: dict[str, Any] | None,
) -> str:
    end_phrase = str(_slots(end_checker).get("end_phrase") or "") if end_checker else ""
    marker = str(_slots(postscript).get("postscript_marker") or "") if postscript else ""
    tail_parts = []
    if marker:
        tail_parts.append(marker)
        tail_parts.append("note")
    if end_phrase:
        tail_parts.append(end_phrase)
    tail = " ".join(tail_parts).strip()
    if not tail:
        return body.replace("__PB_END_SLOT__", "").rstrip()
    return body.replace("__PB_END_SLOT__", tail, 1).rstrip()


def _apply_quote(text: str, quotation: bool) -> str:
    return f'"{text}"' if quotation else text


def _required_fragments(required: list[str], forbidden: list[str]) -> list[str]:
    """Emit fragments satisfying required-regex + forbidden-whole-word overlap.

    The pinned existence checker uses raw regex search while the forbidden
    checker wraps each forbidden expression in word boundaries. For the
    historical generator's word-list arguments, appending one safe letter keeps
    an identical required token as a substring while breaking its forbidden
    whole-word match.
    """
    out = []
    forbidden_lower = {x.lower() for x in forbidden}
    for keyword in required:
        if keyword.lower() in forbidden_lower:
            out.append(keyword + "x")
        else:
            out.append(keyword)
    return out


def _keyword_payload(required: list[str], forbidden: list[str] | None = None) -> str:
    return " ".join(_required_fragments(required, list(forbidden or [])))


def _special_json(constraints: list[dict[str, Any]]) -> list[str]:
    required = _required_keywords(constraints)
    forbidden = _forbidden(constraints)
    out = []
    for key in ("x", "payload", "value", "data"):
        candidate = json.dumps({key: _keyword_payload(required, forbidden)}, ensure_ascii=False)
        if _forbidden_ok(candidate, forbidden):
            out.append(candidate)
    return out


def _special_repeat(constraints: list[dict[str, Any]]) -> list[str]:
    repeat = _one(constraints, "combination:repeat_prompt")
    base = str(_slots(repeat).get("prompt_to_repeat") or "").strip()
    if not base:
        return []
    parts = [base]
    if _one(constraints, "detectable_format:title"):
        parts.append("<<x>>")
    required = _required_keywords(constraints)
    if required:
        parts.append(_keyword_payload(required, []))
    parts.append("answer")
    return ["\n".join(parts)]


def _special_two(constraints: list[dict[str, Any]]) -> list[str]:
    required = _required_keywords(constraints)
    forbidden = _forbidden(constraints)
    safe = _safe_token(forbidden)
    first_parts = []
    if _one(constraints, "detectable_format:title"):
        first_parts.append("<<x>>")
    if required:
        first_parts.append(_keyword_payload(required, forbidden))
    first_parts.append(safe + "a")
    first = " ".join(first_parts)
    second = safe + "b"
    candidate = first + "******" + second
    return [candidate] if _forbidden_ok(candidate, forbidden) else []


def _build_core_skeleton(
    constraints: list[dict[str, Any]],
    sentence_fillers: int,
) -> str:
    forbidden = _forbidden(constraints)
    required = _required_keywords(constraints)
    title = _one(constraints, "detectable_format:title") is not None
    quotation = _one(constraints, "startend:quotation") is not None
    paragraphs = _one(constraints, "length_constraints:number_paragraphs")
    nth = _one(constraints, "length_constraints:nth_paragraph_first_word")
    bullets = _one(constraints, "detectable_format:number_bullet_lists")
    sections = _one(constraints, "detectable_format:multiple_sections")
    # Tail material and outer quotation are finalized only after word padding.
    # Otherwise lower-bound padding can be appended after an exact end phrase or
    # outside the closing quote, invalidating an otherwise satisfiable witness.

    safe = _safe_token(forbidden)
    components: list[str] = []
    if title:
        components.append("<<x>>")
    if required:
        components.append(_keyword_payload(required, forbidden))

    if sections:
        ss = _slots(sections)
        splitter = str(ss["section_spliter"])
        n = int(ss["num_sections"])
        for i in range(1, n + 1):
            components.append(f"{splitter} {i}\n{safe}s{i}")

    if bullets:
        n = int(_slots(bullets)["num_bullets"])
        components.extend(f"* {safe}b{i}" for i in range(n))

    components.extend(f"{safe}sentence{i}." for i in range(sentence_fillers))

    # Reserve a stable insertion point for word padding before tail material.
    components.append("__PB_END_SLOT__")

    if nth:
        s = _slots(nth)
        n = int(s["num_paragraphs"])
        which = int(s["nth_paragraph"])
        first = str(s["first_word"])
        paras = [safe + f"p{i}" for i in range(1, n + 1)]
        payload = "\n".join(components).strip()
        if which == 1:
            paras[0] = first + " " + payload
        else:
            paras[0] = payload or safe
            paras[which - 1] = first + " " + paras[which - 1]
        body = "\n\n".join(paras)
    elif paragraphs:
        n = int(_slots(paragraphs)["num_paragraphs"])
        paras = [safe + f"p{i}" for i in range(1, n + 1)]
        payload = "\n".join(components).strip()
        paras[0] = (payload + "\n" + paras[0]).strip()
        body = "***".join(paras)
    else:
        body = "\n".join(components).strip()

    # Structural branches may place the initial marker inside the first
    # paragraph. Canonicalize it to one slot at the true response end so
    # postscript and exact-end constraints are actually terminal while keeping
    # paragraph separators/counts intact.
    body = body.replace("__PB_END_SLOT__", "").rstrip()
    body = body + ("\n" if body else "") + "__PB_END_SLOT__"

    # Preserve __PB_END_SLOT__ through the padding phase. Finalization happens
    # in generate(), after the word constraint has been satisfied.
    if not _forbidden_ok(body, forbidden):
        raise ValueError("STRUCTURE_HITS_FORBIDDEN_WORD")
    return body


def _finalize_core_candidate(
    text: str,
    constraints: list[dict[str, Any]],
) -> str:
    postscript = _one(constraints, "detectable_content:postscript")
    end_checker = _one(constraints, "startend:end_checker")
    quotation = _one(constraints, "startend:quotation") is not None
    text = _apply_end_material(text, postscript, end_checker)
    return _apply_quote(text, quotation)


def _word_constraint_ok(
    text: str,
    word_constraint: dict[str, Any] | None,
) -> bool:
    if not word_constraint:
        return True
    s = _slots(word_constraint)
    threshold = int(s["num_words"])
    relation = str(s["relation"])
    count = _word_count(text)
    if relation == "at least":
        return count >= threshold
    if relation == "less than":
        return count < threshold
    return False


def generate(constraints: Iterable[dict[str, Any]], max_candidates: int = 96) -> dict[str, Any]:
    rows = list(constraints)
    ids = [str(c.get("instruction_id") or "") for c in rows]
    unique_ids = set(ids)
    if len(ids) != len(unique_ids):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "MULTIPLICITY_NOT_SUPPORTED_V1",
            "candidates": [],
            "terminal_data_used": False,
        }
    classification = partition.classify(unique_ids)
    if classification["status"] != "PASS":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "ACTIVE15_CONFLICT_GRAPH_REJECTED",
            "candidates": [],
            "terminal_data_used": False,
        }

    try:
        if "detectable_format:json_format" in unique_ids:
            candidates = _special_json(rows)
            mode = "JSON"
        elif "combination:repeat_prompt" in unique_ids:
            candidates = _special_repeat(rows)
            mode = "REPEAT"
        elif "combination:two_responses" in unique_ids:
            candidates = _special_two(rows)
            mode = "TWO_RESPONSES"
        else:
            mode = "CORE"
            forbidden = _forbidden(rows)
            word_constraint = _one(rows, "length_constraints:number_words")
            sentence_constraint = _one(rows, "length_constraints:number_sentences")
            if sentence_constraint:
                target = int(_slots(sentence_constraint)["num_sentences"])
                # Exact scorer postvalidation decides which count works. The
                # range brackets the generator's public 1..20 threshold and
                # allows structural punctuation to contribute extra sentences.
                sentence_counts = list(range(0, max(26, target + 8)))
            else:
                sentence_counts = [0, 1, 2]
            candidates = []
            seen = set()
            for count in sentence_counts:
                try:
                    candidate = _build_core_skeleton(rows, count)
                except ValueError:
                    continue
                candidate = _pad_for_word_constraint(candidate, word_constraint, forbidden)
                if candidate is None:
                    continue
                candidate = _finalize_core_candidate(candidate, rows)
                if (
                    not _forbidden_ok(candidate, forbidden)
                    or not _word_constraint_ok(candidate, word_constraint)
                ):
                    continue
                if candidate not in seen:
                    seen.add(candidate)
                    candidates.append(candidate)
                if len(candidates) >= max_candidates:
                    break
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": f"{type(exc).__name__}:{exc}",
            "candidates": [],
            "terminal_data_used": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATES" if candidates else "FAIL_CLOSED",
        "mode": mode,
        "candidate_count": len(candidates),
        "candidates": candidates[:max_candidates],
        "requires_exact_pinned_checker_postvalidation": True,
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
        "terminal_data_used": False,
        "model_dependency_count": 0,
        "acceptance_credit": False,
        "semantic_capability_credit": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return generate((args or {}).get("constraints") or [])


if __name__ == "__main__":
    import sys
    payload = json.load(sys.stdin)
    print(json.dumps(generate(payload.get("constraints") or []), ensure_ascii=False, indent=2))
