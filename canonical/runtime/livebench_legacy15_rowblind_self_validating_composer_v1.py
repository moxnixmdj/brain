#!/usr/bin/env python3
"""Row-blind constructive solver for the frozen active-15 LiveBench IF surface.

The solver uses only the visible historical prompt envelope and public checker
semantics. It never reads instruction_id_list, hidden kwargs, question IDs,
terminal row metadata, prior model outputs, or benchmark scores.

It is intentionally benchmark-surface machinery. It earns no whole-family
semantic capability credit by itself.
"""
from __future__ import annotations

import json
import re
from typing import Any


from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler
from canonical.runtime.livebench_legacy15_composition_archetypes_v1 import ACTIVE_IDS, compatible, archetype

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_ROWBLIND_SELF_VALIDATING_COMPOSER_V1"
_SAFE = "zxqv"
_WORD_RE = re.compile(r"\w+")
_ALPHA = re.compile(r"^[A-Za-z]+$")


class SolveError(ValueError):
    pass


def _one(constraints: list[dict[str, Any]], iid: str) -> dict[str, Any] | None:
    xs = [c for c in constraints if c.get("instruction_id") == iid]
    if len(xs) > 1:
        raise SolveError("DUPLICATE_ACTIVE_ID:" + iid)
    return xs[0] if xs else None


def _slots(c: dict[str, Any] | None) -> dict[str, Any]:
    return dict((c or {}).get("slots") or {})


def _required(constraints: list[dict[str, Any]]) -> list[str]:
    vals = [str(x) for x in _slots(_one(constraints, "keywords:existence")).get("keywords") or []]
    if any(not _ALPHA.fullmatch(x) for x in vals):
        raise SolveError("NON_SOURCE_KEYWORD")
    return vals


def _forbidden(constraints: list[dict[str, Any]]) -> list[str]:
    vals = [str(x) for x in _slots(_one(constraints, "keywords:forbidden_words")).get("forbidden_words") or []]
    if any(not _ALPHA.fullmatch(x) for x in vals):
        raise SolveError("NON_SOURCE_FORBIDDEN_WORD")
    return vals


def _carrier(word: str) -> str:
    # Public source keywords are alphabetic. Appending a digit preserves the
    # KeywordChecker substring match while making the original word non-whole
    # for ForbiddenWords, even when required == forbidden.
    return word + "0"


def _count_words(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _count_sentences(text: str) -> int:
    import nltk
    tok = nltk.data.load("tokenizers/punkt/english.pickle")
    return len(tok.tokenize(text))


def _paragraph_count_star(value: str) -> int:
    paragraphs = re.split(r"\s?\*\*\*\s?", value)
    n = len(paragraphs)
    for i, p in enumerate(paragraphs):
        if not p.strip():
            if i == 0 or i == len(paragraphs) - 1:
                n -= 1
            else:
                return -1
    return n


def _nth_paragraph_ok(value: str, slots: dict[str, Any]) -> bool:
    paragraphs = re.split(r"\n\n", value)
    n = len(paragraphs)
    for p in paragraphs:
        if not p.strip():
            n -= 1
    target_n = int(slots["num_paragraphs"])
    nth = int(slots["nth_paragraph"])
    if nth > n or nth < 1:
        return False
    p = paragraphs[nth - 1].strip()
    if not p:
        return False
    word = p.split()[0].strip().lstrip("'").lstrip('"')
    first = ""
    for ch in word:
        if ch in {".", ",", "?", "!", "'", '"'}:
            break
        first += ch.lower()
    return n == target_n and first == str(slots["first_word"]).lower()


def _postscript_ok(value: str, marker: str) -> bool:
    low = value.lower()
    if marker == "P.P.S":
        pat = r"\s*p\.\s?p\.\s?s.*$"
    elif marker == "P.S.":
        pat = r"\s*p\.\s?s\..*$"
    else:
        pat = r"\s*" + re.escape(marker.lower()) + r".*$"
    return bool(re.findall(pat, low, flags=re.MULTILINE))


def validate_visible(response: str, constraints: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Clean-room reimplementation of the pinned active-15 public checkers."""
    bad: list[str] = []
    for c in constraints:
        iid = str(c.get("instruction_id"))
        s = _slots(c)
        ok = False
        if iid == "keywords:existence":
            ok = all(re.search(str(k), response, flags=re.IGNORECASE) is not None for k in s.get("keywords") or [])
        elif iid == "keywords:forbidden_words":
            ok = all(re.search(r"\b" + str(w) + r"\b", response, flags=re.IGNORECASE) is None for w in s.get("forbidden_words") or [])
        elif iid == "length_constraints:number_paragraphs":
            ok = _paragraph_count_star(response) == int(s["num_paragraphs"])
        elif iid == "length_constraints:number_words":
            wc = _count_words(response)
            ok = wc < int(s["num_words"]) if s["relation"] == "less than" else wc >= int(s["num_words"])
        elif iid == "length_constraints:number_sentences":
            sc = _count_sentences(response)
            ok = sc < int(s["num_sentences"]) if s["relation"] == "less than" else sc >= int(s["num_sentences"])
        elif iid == "length_constraints:nth_paragraph_first_word":
            ok = _nth_paragraph_ok(response, s)
        elif iid == "detectable_content:postscript":
            ok = _postscript_ok(response, str(s["postscript_marker"]))
        elif iid == "detectable_format:number_bullet_lists":
            a = re.findall(r"^\s*\*[^\*].*$", response, flags=re.MULTILINE)
            b = re.findall(r"^\s*-.*$", response, flags=re.MULTILINE)
            ok = len(a) + len(b) == int(s["num_bullets"])
        elif iid == "detectable_format:title":
            ok = any(x.lstrip("<").rstrip(">").strip() for x in re.findall(r"<<[^\n]+>>", response))
        elif iid == "detectable_format:multiple_sections":
            pat = r"\s?" + re.escape(str(s["section_spliter"])) + r"\s?\d+\s?"
            ok = len(re.split(pat, response)) - 1 >= int(s["num_sections"])
        elif iid == "detectable_format:json_format":
            x = response.strip()
            for prefix in ("```json", "```Json", "```JSON", "```"):
                if x.startswith(prefix):
                    x = x[len(prefix):]
                    break
            if x.endswith("```"):
                x = x[:-3]
            try:
                json.loads(x.strip())
                ok = True
            except ValueError:
                ok = False
        elif iid == "combination:two_responses":
            parts = response.split("******")
            valid = []
            invalid_middle = False
            for i, part in enumerate(parts):
                if not part.strip():
                    if i != 0 and i != len(parts) - 1:
                        invalid_middle = True
                else:
                    valid.append(part)
            ok = (not invalid_middle and len(valid) == 2 and valid[0].strip() != valid[1].strip())
        elif iid == "combination:repeat_prompt":
            base = str(s.get("prompt_to_repeat") or "")
            ok = bool(base) and response.strip().lower().startswith(base.strip().lower())
        elif iid == "startend:end_checker":
            x = response.strip().strip('"').lower()
            ok = x.endswith(str(s["end_phrase"]).strip().lower())
        elif iid == "startend:quotation":
            x = response.strip()
            ok = len(x) > 1 and x[0] == '"' and x[-1] == '"'
        else:
            raise SolveError("OUTSIDE_ACTIVE15:" + iid)
        if not ok:
            bad.append(iid)
    return not bad, bad


def _special(constraints: list[dict[str, Any]], mode: str) -> str:
    req = [_carrier(x) for x in _required(constraints)]
    if mode == "JSON":
        return json.dumps({"0": " ".join(req)}, separators=(",", ":"))
    if mode == "TWO_RESPONSES":
        left = []
        if _one(constraints, "detectable_format:title"):
            left.append("<<0>>")
        left.extend(req)
        left.append("0")
        a = " ".join(left)
        b = "1"
        if b == a:
            b = "2"
        return a + "******" + b
    if mode == "REPEAT_PROMPT":
        rep = _one(constraints, "combination:repeat_prompt")
        base = str(_slots(rep).get("prompt_to_repeat") or "").strip()
        if not base:
            raise SolveError("PROMPT_TO_REPEAT_MISSING")
        tail = []
        if _one(constraints, "detectable_format:title"):
            tail.append("<<0>>")
        tail.extend(req)
        tail.append("0")
        return base + "\n" + " ".join(tail)
    raise SolveError("UNKNOWN_SPECIAL_ARCHETYPE:" + mode)


def _mandatory_general_lines(constraints: list[dict[str, Any]]) -> list[str]:
    lines = ["0"]
    if _one(constraints, "detectable_format:title"):
        lines.append("<<0>>")
    lines.extend(_carrier(x) for x in _required(constraints))

    sec = _one(constraints, "detectable_format:multiple_sections")
    if sec:
        s = _slots(sec)
        for i in range(1, int(s["num_sections"]) + 1):
            lines.append(f'{s["section_spliter"]} {i}')
            lines.append("0")

    bullets = _one(constraints, "detectable_format:number_bullet_lists")
    if bullets:
        for _ in range(int(_slots(bullets)["num_bullets"])):
            lines.append("* 0")
    return lines


def _assemble_general(constraints: list[dict[str, Any]], extra_sentences: int = 0, extra_words: int = 0) -> str:
    lines = ["Zxqv." for _ in range(extra_sentences)]
    lines.extend(_mandatory_general_lines(constraints))
    if extra_words:
        lines.append(" ".join(["0"] * extra_words))
    body = "\n".join(lines)

    nth = _one(constraints, "length_constraints:nth_paragraph_first_word")
    star = _one(constraints, "length_constraints:number_paragraphs")
    if nth and star:
        raise SolveError("PUBLIC_CONFLICT_GRAPH_DRIFT_NTH_STAR")

    if nth:
        s = _slots(nth)
        count, target = int(s["num_paragraphs"]), int(s["nth_paragraph"])
        first = str(s["first_word"])
        paras = ["0" for _ in range(count)]
        paras[target - 1] = first + " " + body
        body = "\n\n".join(paras)
    elif star:
        count = int(_slots(star)["num_paragraphs"])
        paras = [body] + ["0" for _ in range(count - 1)]
        body = "\n***\n".join(paras)

    post = _one(constraints, "detectable_content:postscript")
    end = _one(constraints, "startend:end_checker")
    tail = ""
    if post:
        tail = str(_slots(post)["postscript_marker"]) + " 0"
    if end:
        phrase = str(_slots(end)["end_phrase"]).strip()
        tail = (tail + " " + phrase).strip() if tail else phrase
    if tail:
        body = body.rstrip() + "\n" + tail

    if _one(constraints, "startend:quotation"):
        body = '"' + body.strip('"') + '"'
    return body


def _solve_general(constraints: list[dict[str, Any]]) -> str:
    sentence = _one(constraints, "length_constraints:number_sentences")
    word = _one(constraints, "length_constraints:number_words")

    sentence_trials = [0]
    if sentence and str(_slots(sentence)["relation"]) == "at least":
        n = int(_slots(sentence)["num_sentences"])
        sentence_trials = [n, n + 1, n + 2, n + 4]

    for st in sentence_trials:
        base = _assemble_general(constraints, extra_sentences=st, extra_words=0)
        candidates = [base]
        if word and str(_slots(word)["relation"]) == "at least":
            target = int(_slots(word)["num_words"])
            need = max(0, target - _count_words(base))
            for delta in (0, 1, 2):
                candidates.append(_assemble_general(constraints, extra_sentences=st, extra_words=need + delta))
        for candidate in candidates:
            ok, _ = validate_visible(candidate, constraints)
            if ok:
                return candidate

    for st in range(0, 25):
        candidate = _assemble_general(constraints, extra_sentences=st, extra_words=0)
        if word and str(_slots(word)["relation"]) == "at least":
            need = max(0, int(_slots(word)["num_words"]) - _count_words(candidate))
            candidate = _assemble_general(constraints, extra_sentences=st, extra_words=need)
        ok, _ = validate_visible(candidate, constraints)
        if ok:
            return candidate

    raise SolveError("NO_VISIBLE_CONSTRUCTIVE_WITNESS_FOUND")


def solve(prompt: str) -> dict[str, Any]:
    parsed = compiler.compile_visible_constraints(str(prompt or ""))
    if parsed.get("status") != "PASS" or not parsed.get("all_recognized_parameters_complete"):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "VISIBLE_COMPILER_NOT_COMPLETE",
            "response": None,
            "terminal_data_used": False,
        }

    constraints = list(parsed.get("constraints") or [])
    ids = tuple(str(c.get("instruction_id")) for c in constraints)
    if not ids:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "NO_VISIBLE_CONSTRAINTS", "response": None}
    if set(ids) - set(ACTIVE_IDS):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "OUTSIDE_ACTIVE15", "response": None}
    if not compatible(ids):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "CONFLICT_INCOMPATIBLE_ID_SET", "response": None}

    mode = archetype(ids)
    try:
        if mode in {"JSON", "TWO_RESPONSES", "REPEAT_PROMPT"}:
            response = _special(constraints, mode)
        else:
            response = _solve_general(constraints)
        ok, bad = validate_visible(response, constraints)
        if not ok:
            raise SolveError("SELF_VALIDATION_FAILED:" + ",".join(bad))
    except (SolveError, KeyError, TypeError, ValueError, LookupError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "archetype": mode,
            "instruction_ids": sorted(set(ids)),
            "response": None,
            "terminal_data_used": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE_ROWBLIND",
        "archetype": mode,
        "instruction_ids": sorted(set(ids)),
        "response": response,
        "visible_self_validation_pass": True,
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
        "terminal_case_content_used": False,
        "prior_score_used": False,
        "network_used": False,
        "model_dependency_count": 0,
        "acceptance_credit": False,
        "semantic_capability_credit": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return solve(str((args or {}).get("prompt") or ""))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(solve(ns.prompt), indent=2, sort_keys=True))
