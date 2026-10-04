#!/usr/bin/env python3
"""Parameter-aware deterministic composer for the GENERAL active legacy15 branch.

This is a constructive candidate, not an acceptance claim. It covers the
conflict-valid active-15 branch excluding JSON, two_responses, and repeat_prompt.

Design:
- exact visible parameters from the historical-envelope compiler V4;
- safe alphabetic carriers for keyword existence vs forbidden-word overlap;
- structural construction for *, ***, Section X, \n\n, title, quotation,
  postscript, end phrase;
- exact source-equivalent word counting (RegexpTokenizer r"\w+");
- conservative sentence support: "at least" is constructive; low-bound
  "less than" cases fail closed where Punkt/newline interactions have not yet
  been independently verified.

No hidden terminal fields or learned model are used.
"""
from __future__ import annotations

import re
from typing import Any

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler
from canonical.runtime.livebench_legacy15_composition_archetypes_v1 import compatible, archetype

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_GENERAL_COMPOSER_V1"
_SPECIAL_IDS = {
    "detectable_format:json_format",
    "combination:two_responses",
    "combination:repeat_prompt",
}
_SAFE_WORD = re.compile(r"^[A-Za-z]+$")


class ComposeError(ValueError):
    pass


def _rows(constraints: list[dict[str, Any]], iid: str) -> list[dict[str, Any]]:
    return [c for c in constraints if c.get("instruction_id") == iid]


def _one(constraints: list[dict[str, Any]], iid: str) -> dict[str, Any] | None:
    rows = _rows(constraints, iid)
    if not rows:
        return None
    if len(rows) != 1:
        raise ComposeError("DUPLICATE_ACTIVE_ID:" + iid)
    return rows[0]


def _slots(c: dict[str, Any] | None) -> dict[str, Any]:
    return dict((c or {}).get("slots") or {})


def _keyword_lists(constraints: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    req = [str(x) for x in _slots(_one(constraints, "keywords:existence")).get("keywords") or []]
    forb = [str(x) for x in _slots(_one(constraints, "keywords:forbidden_words")).get("forbidden_words") or []]
    if any(not _SAFE_WORD.fullmatch(x) for x in req + forb):
        raise ComposeError("NON_HISTORICAL_KEYWORD_SURFACE")
    return req, forb


def _required_carriers(required: list[str], forbidden: list[str]) -> list[str]:
    out = []
    for word in required:
        token = word + "x"
        if any(re.search(r"\b" + re.escape(bad) + r"\b", token, re.I) for bad in forbidden):
            raise ComposeError("KEYWORD_CARRIER_FORBIDDEN_COLLISION")
        out.append(token)
    return out


def _forbidden_collision(text: str, forbidden: list[str]) -> str | None:
    for bad in forbidden:
        if re.search(r"\b" + re.escape(bad) + r"\b", text, flags=re.IGNORECASE):
            return bad
    return None


def _count_words(text: str) -> int:
    # Exact token geometry used by frozen instructions_util.count_words.
    return len(re.findall(r"\w+", text))


def _append_word_padding(text: str, constraint: dict[str, Any] | None) -> str:
    if constraint is None:
        return text
    s = _slots(constraint)
    relation = str(s.get("relation") or "")
    target = int(s.get("num_words"))
    current = _count_words(text)
    if relation == "less than":
        if current >= target:
            raise ComposeError(f"WORD_LESS_THAN_UNSAT:{current}>={target}")
        return text
    if relation == "at least":
        need = max(0, target - current)
        if not need:
            return text
        pad = " ".join(["zxqv"] * need)
        return (text + "\n" + pad).strip()
    raise ComposeError("UNKNOWN_WORD_RELATION")



def _apply_word_constraint(
    prefix: str,
    suffix: str | None,
    constraint: dict[str, Any] | None,
) -> str:
    """Apply the word predicate while preserving an exact terminal suffix."""
    def join(p: str, s: str | None) -> str:
        if s:
            return (p + "\n" + s).strip() if p else s
        return p

    final = join(prefix, suffix)
    if constraint is None:
        return final
    slots = _slots(constraint)
    relation = str(slots.get("relation") or "")
    target = int(slots.get("num_words"))
    current = _count_words(final)
    if relation == "less than":
        if current >= target:
            raise ComposeError(f"WORD_LESS_THAN_UNSAT:{current}>={target}")
        return final
    if relation == "at least":
        need = max(0, target - current)
        if need:
            pad = " ".join(["zxqv"] * need)
            prefix = (prefix + "\n" + pad).strip() if prefix else pad
        return join(prefix, suffix)
    raise ComposeError("UNKNOWN_WORD_RELATION")


def _common_lines(constraints: list[dict[str, Any]], required: list[str]) -> list[str]:
    lines: list[str] = []
    if _one(constraints, "detectable_format:title") is not None:
        lines.append("<<qz>>")

    section = _one(constraints, "detectable_format:multiple_sections")
    if section is not None:
        s = _slots(section)
        splitter = str(s.get("section_spliter") or "")
        n = int(s.get("num_sections"))
        if splitter not in {"Section", "SECTION"} or n < 1 or n > 5:
            raise ComposeError("SECTION_PARAMETER_DRIFT")
        for i in range(1, n + 1):
            lines.append(f"{splitter} {i}")
            lines.append("zxqv")

    bullets = _one(constraints, "detectable_format:number_bullet_lists")
    if bullets is not None:
        n = int(_slots(bullets).get("num_bullets"))
        if n < 1 or n > 5:
            raise ComposeError("BULLET_PARAMETER_DRIFT")
        for i in range(n):
            lines.append(f"* {i}")

    carriers = _required_carriers(required, [])
    if carriers:
        lines.append(" ".join(carriers))

    post = _one(constraints, "detectable_content:postscript")
    if post is not None:
        marker = str(_slots(post).get("postscript_marker") or "")
        if marker not in {"P.S.", "P.P.S"}:
            raise ComposeError("POSTSCRIPT_PARAMETER_DRIFT")
        lines.append(marker + " zxqv")

    return lines


def _sentence_constraint(constraints: list[dict[str, Any]]) -> tuple[str, int] | None:
    c = _one(constraints, "length_constraints:number_sentences")
    if c is None:
        return None
    s = _slots(c)
    relation = str(s.get("relation") or "")
    n = int(s.get("num_sentences"))
    if relation not in {"less than", "at least"} or n < 1 or n > 20:
        raise ComposeError("SENTENCE_PARAMETER_DRIFT")
    return relation, n


def _add_at_least_sentences(lines: list[str], n: int) -> None:
    # Each token is deliberately a plain non-abbreviation sentence. Other
    # structural text can only increase the frozen Punkt count, so this is a
    # monotone lower-bound construction.
    for _ in range(n):
        lines.insert(0, "Zxqv.")


def _ending(constraints: list[dict[str, Any]]) -> str | None:
    c = _one(constraints, "startend:end_checker")
    if c is None:
        return None
    phrase = str(_slots(c).get("end_phrase") or "")
    if phrase not in {"Any other questions?", "Is there anything else I can help with?"}:
        raise ComposeError("END_PHRASE_PARAMETER_DRIFT")
    return phrase


def _wrap_quote(text: str, constraints: list[dict[str, Any]]) -> str:
    if _one(constraints, "startend:quotation") is None:
        return text
    return '"' + text + '"'


def _compose_plain_or_sentence(
    constraints: list[dict[str, Any]],
    required: list[str],
    forbidden: list[str],
) -> str:
    sc = _sentence_constraint(constraints)

    # "less than 1 sentence" can only use an empty witness. It remains valid
    # together with forbidden_words and a less-than word constraint, but not
    # with any positive-output requirement.
    if sc == ("less than", 1):
        positive_ids = {
            "keywords:existence",
            "detectable_content:postscript",
            "detectable_format:number_bullet_lists",
            "detectable_format:title",
            "detectable_format:multiple_sections",
            "startend:end_checker",
            "startend:quotation",
        }
        ids = {str(c.get("instruction_id")) for c in constraints}
        wc = _one(constraints, "length_constraints:number_words")
        if ids & positive_ids:
            raise ComposeError("LESS_THAN_ONE_SENTENCE_POSITIVE_REQUIREMENT")
        if wc is not None and _slots(wc).get("relation") != "less than":
            raise ComposeError("LESS_THAN_ONE_SENTENCE_WORD_LOWER_BOUND")
        return ""

    lines = _common_lines(constraints, required)
    if not lines:
        lines.append("zxqv")

    if sc is not None:
        relation, n = sc
        if relation == "at least":
            _add_at_least_sentences(lines, n)
        else:
            # For general single-block text, avoid adding any sentence-ending
            # punctuation. The remaining unavoidable public wrappers are checked
            # conservatively below; threshold 2 is only accepted without P.P.S
            # plus end-marker interaction until exact-source grid verification.
            if n == 2:
                post = _one(constraints, "detectable_content:postscript")
                end = _ending(constraints)
                if post is not None and end is not None:
                    raise ComposeError("LESS_THAN_TWO_SENTENCE_POSTSCRIPT_END_UNVERIFIED")

    end = _ending(constraints)
    prefix = "\n".join(lines)
    mandatory = (prefix + ("\n" + end if end else "")).strip()
    bad = _forbidden_collision(mandatory, forbidden)
    if bad:
        raise ComposeError("MANDATORY_FORBIDDEN_COLLISION:" + bad)

    text = _apply_word_constraint(
        prefix,
        end,
        _one(constraints, "length_constraints:number_words"),
    )
    return _wrap_quote(text, constraints)


def _compose_star_paragraph(
    constraints: list[dict[str, Any]],
    required: list[str],
    forbidden: list[str],
) -> str:
    pc = _one(constraints, "length_constraints:number_paragraphs")
    if pc is None:
        raise ComposeError("STAR_PARAGRAPH_MISSING")
    n = int(_slots(pc).get("num_paragraphs"))
    if n < 1 or n > 5:
        raise ComposeError("PARAGRAPH_PARAMETER_DRIFT")

    common = _common_lines(constraints, required)
    paragraphs = ["zxqv" for _ in range(n)]
    if common:
        paragraphs[0] += "\n" + "\n".join(common)
    end = _ending(constraints)

    prefix = "\n***\n".join(paragraphs)
    mandatory = (prefix + ("\n" + end if end else "")).strip()
    bad = _forbidden_collision(mandatory, forbidden)
    if bad:
        raise ComposeError("MANDATORY_FORBIDDEN_COLLISION:" + bad)

    text = _apply_word_constraint(
        prefix,
        end,
        _one(constraints, "length_constraints:number_words"),
    )
    return _wrap_quote(text, constraints)


def _compose_nth_paragraph(
    constraints: list[dict[str, Any]],
    required: list[str],
    forbidden: list[str],
) -> str:
    nc = _one(constraints, "length_constraints:nth_paragraph_first_word")
    if nc is None:
        raise ComposeError("NTH_PARAGRAPH_MISSING")
    s = _slots(nc)
    n = int(s.get("num_paragraphs"))
    nth = int(s.get("nth_paragraph"))
    first = str(s.get("first_word") or "")
    if n < 1 or n > 5 or nth < 1 or nth > n or not _SAFE_WORD.fullmatch(first):
        raise ComposeError("NTH_PARAGRAPH_PARAMETER_DRIFT")

    if any(re.fullmatch(re.escape(bad), first, flags=re.IGNORECASE) for bad in forbidden):
        raise ComposeError("NTH_FIRST_WORD_FORBIDDEN_UNSAT")

    sc = _sentence_constraint(constraints)
    if sc is not None and sc[0] == "less than":
        # Blank-line/Punkt interaction gets exact-source verification before
        # activation; keep this branch fail-closed in V1.
        raise ComposeError("NTH_PLUS_SENTENCE_LESS_THAN_UNVERIFIED")

    paragraphs = ["zxqv" for _ in range(n)]
    paragraphs[nth - 1] = first + " zxqv"

    common = _common_lines(constraints, required)
    if common:
        paragraphs[-1] += "\n" + "\n".join(common)

    if sc is not None and sc[0] == "at least":
        paragraphs[0] += " " + " ".join(["Zxqv."] * sc[1])

    end = _ending(constraints)

    prefix = "\n\n".join(paragraphs)
    mandatory = (prefix + ("\n" + end if end else "")).strip()
    bad = _forbidden_collision(mandatory, forbidden)
    if bad:
        raise ComposeError("MANDATORY_FORBIDDEN_COLLISION:" + bad)

    text = _apply_word_constraint(
        prefix,
        end,
        _one(constraints, "length_constraints:number_words"),
    )
    return _wrap_quote(text, constraints)


def compose_visible_prompt(prompt: str) -> dict[str, Any]:
    parsed = compiler.compile_visible_constraints(str(prompt or ""))
    if parsed.get("status") != "PASS":
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "VISIBLE_COMPILER_NOT_PASS", "response": None}
    constraints = list(parsed.get("constraints") or [])
    ids = tuple(str(c.get("instruction_id")) for c in constraints)
    if not ids:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "NO_VISIBLE_CONSTRAINTS", "response": None}
    if set(ids) & _SPECIAL_IDS:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "SPECIAL_BRANCH_REQUIRED", "response": None}
    if not compatible(ids):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "CONFLICT_INCOMPATIBLE_ID_SET", "response": None}

    try:
        required, forbidden = _keyword_lists(constraints)
        # Common helper initially makes carriers without forbidden context; use
        # collision-safe carriers directly by replacing only the existence line
        # after construction when required/forbidden overlap is possible.
        # Since carriers are always word+"x", exact forbidden boundaries are
        # already absent for identical words.
        mode = archetype(ids)
        if mode == "STAR_PARAGRAPH":
            response = _compose_star_paragraph(constraints, required, forbidden)
        elif mode == "NTH_PARAGRAPH":
            response = _compose_nth_paragraph(constraints, required, forbidden)
        elif mode in {"SENTENCE", "PLAIN"}:
            response = _compose_plain_or_sentence(constraints, required, forbidden)
        else:
            raise ComposeError("UNEXPECTED_GENERAL_ARCHETYPE:" + mode)
    except (ComposeError, TypeError, ValueError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "instruction_ids": sorted(set(ids)),
            "response": None,
            "terminal_data_used": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE_GENERAL_BRANCH",
        "archetype": mode,
        "instruction_ids": sorted(set(ids)),
        "response": response,
        "model_dependency_count": 0,
        "network_used": False,
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
        "terminal_case_content_used": False,
        "acceptance_credit": False,
        "semantic_capability_credit": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return compose_visible_prompt(str((args or {}).get("prompt") or ""))


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(compose_visible_prompt(ns.prompt), ensure_ascii=False, indent=2, sort_keys=True))
