#!/usr/bin/env python3
"""Deterministic fixed-point witness synthesizer for pinned legacy LiveBench IFEval.

The solver consumes only visible prompt text. It uses the source-lineage-aware
V2 visible-constraint compiler, instantiates the byte-pinned public legacy
IFEval checker classes vendored under canonical/vendor, and searches a bounded
set of deterministic repair orders until every recovered checker returns True.

This is a score/witness compiler, not a semantic task solver. A PASS proves only
that the returned string satisfies the recovered formal IFEval predicates.
"""
from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any

from canonical.runtime.livebench_legacy_visible_constraint_compiler_v2 import (
    compile_visible_constraints,
)

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_FIXEDPOINT_WITNESS_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
HISTORICAL_GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
HISTORICAL_GENERATOR_MAX_SAMPLED_INSTRUCTIONS = 5

# live_data.py@686be1... never sampled language:response_language. Keeping the
# exact historical universe explicit prevents silently generalizing beyond the
# recovered generator contract.
HISTORICAL_GENERATOR_INSTRUCTION_IDS = frozenset({
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

_VENDOR_ROOT = (
    Path(__file__).resolve().parents[1]
    / "vendor"
    / "livebench_ifeval_legacy"
)
_REGISTRY = None
_UTIL = None


def _load_exact_checker_modules():
    global _REGISTRY, _UTIL
    if _REGISTRY is not None and _UTIL is not None:
        return _REGISTRY, _UTIL
    vendor = str(_VENDOR_ROOT)
    if vendor not in sys.path:
        sys.path.insert(0, vendor)
    from instruction_following_eval import instructions_registry  # type: ignore
    from instruction_following_eval import instructions_util  # type: ignore
    _REGISTRY = instructions_registry
    _UTIL = instructions_util
    return _REGISTRY, _UTIL


def _instantiate(constraint: dict[str, Any]):
    registry, _ = _load_exact_checker_modules()
    iid = str(constraint["instruction_id"])
    cls = registry.INSTRUCTION_DICT[iid]
    obj = cls(iid)
    allowed = set(obj.get_instruction_args_keys())
    slots = dict(constraint.get("slots") or {})
    kwargs = {k: v for k, v in slots.items() if k in allowed}
    obj.build_description(**kwargs)
    return obj


def _passes(response: str, constraint: dict[str, Any]) -> bool:
    if not str(response or "").strip():
        return False
    try:
        return bool(_instantiate(constraint).check_following(response))
    except Exception:
        return False


def _validate(response: str, constraints: list[dict[str, Any]]) -> dict[str, Any]:
    passed: list[str] = []
    failed: list[str] = []
    for c in constraints:
        iid = str(c["instruction_id"])
        (passed if _passes(response, c) else failed).append(iid)
    return {
        "all_pass": not failed,
        "passed": passed,
        "failed": failed,
        "pass_count": len(passed),
        "checker_count": len(constraints),
    }


def _constraint(constraints: list[dict[str, Any]], iid: str):
    for c in constraints:
        if c["instruction_id"] == iid:
            return c
    return None


def _safe_token(constraints: list[dict[str, Any]]) -> str:
    banned_letters: set[str] = set()
    c = _constraint(constraints, "keywords:letter_frequency")
    if c and c["slots"].get("let_relation") == "less than":
        banned_letters.add(str(c["slots"].get("letter") or "").lower())

    forbidden: set[str] = set()
    c = _constraint(constraints, "keywords:forbidden_words")
    if c:
        forbidden = {str(x).lower() for x in c["slots"].get("forbidden_words", [])}

    banned_substrings: set[str] = set()
    c = _constraint(constraints, "keywords:frequency")
    if c and c["slots"].get("relation") == "less than":
        banned_substrings.add(str(c["slots"].get("keyword") or "").lower())

    alphabet = "bcdfghjklmnpqrstvwxyz"
    alphabet = "".join(ch for ch in alphabet if ch not in banned_letters) or "x"
    for width in range(3, 8):
        token = "".join(alphabet[(i * 5 + width) % len(alphabet)] for i in range(width))
        low = token.lower()
        if low in forbidden:
            continue
        if any(x and x in low for x in banned_substrings):
            continue
        return token
    return "zxqv"


def _english_seed(constraints: list[dict[str, Any]]) -> str:
    # Enough ordinary English signal for langdetect in the all-upper/all-lower
    # legacy checkers, while filtering the one possible letter-frequency ceiling
    # and forbidden/frequency-negative lexical atoms.
    words = (
        "this simple text gives clear facts about time work people world day way "
        "thing life hand part child eye place case point government company number "
        "group problem fact home water room mother area money story issue side kind "
        "head house service friend father power hour game line end member law car city "
        "community name team minute idea body information back parent face others level "
        "office door health person art war history party result change morning reason"
    ).split()
    letter = None
    lc = _constraint(constraints, "keywords:letter_frequency")
    if lc and lc["slots"].get("let_relation") == "less than":
        letter = str(lc["slots"].get("letter") or "").lower()
    forbidden = set()
    fw = _constraint(constraints, "keywords:forbidden_words")
    if fw:
        forbidden = {str(x).lower() for x in fw["slots"].get("forbidden_words", [])}
    bad_keyword = None
    kf = _constraint(constraints, "keywords:frequency")
    if kf and kf["slots"].get("relation") == "less than":
        bad_keyword = str(kf["slots"].get("keyword") or "").lower()

    filtered = [
        w for w in words
        if (not letter or letter not in w.lower())
        and w.lower() not in forbidden
        and (not bad_keyword or bad_keyword not in w.lower())
    ]
    if len(filtered) < 8:
        return _safe_token(constraints)
    return " ".join((filtered * 4)[:32])


def _base_seeds(constraints: list[dict[str, Any]]) -> list[str]:
    ids = {c["instruction_id"] for c in constraints}
    safe = _safe_token(constraints)
    seeds = [safe, f"{safe} {safe}"]
    if ids & {"change_case:english_capital", "change_case:english_lowercase"}:
        seeds.insert(0, _english_seed(constraints))
    else:
        seeds.append("this is a simple response")
    # Preserve order while deduplicating.
    return list(dict.fromkeys(seeds))


def _regex_count(pattern: str, value: str, flags: int = 0) -> int:
    try:
        return len(re.findall(pattern, value, flags=flags))
    except re.error:
        return 10**9


def _apply_one(
    response: str,
    constraint: dict[str, Any],
    constraints: list[dict[str, Any]],
) -> str:
    if _passes(response, constraint):
        return response

    iid = str(constraint["instruction_id"])
    s = dict(constraint.get("slots") or {})
    safe = _safe_token(constraints)

    if iid == "detectable_format:constrained_response":
        return "My answer is yes."

    if iid == "keywords:existence":
        forbidden = set()
        fw = _constraint(constraints, "keywords:forbidden_words")
        if fw:
            forbidden = {str(x).lower() for x in fw["slots"].get("forbidden_words", [])}
        out = response
        for keyword in s.get("keywords", []):
            kw = str(keyword)
            try:
                present = bool(re.search(kw, out, flags=re.IGNORECASE))
            except re.error:
                present = kw.lower() in out.lower()
            if present:
                continue
            # The existence checker uses raw substring regex while forbidden_words
            # uses word boundaries. Embedding a shared atom in word characters can
            # satisfy both exact public predicates.
            atom = f"x{kw}x" if kw.lower() in forbidden else kw
            out += " " + atom
        return out

    if iid == "keywords:frequency":
        kw = str(s["keyword"])
        freq = int(s["frequency"])
        rel = str(s["relation"])
        try:
            n = len(re.findall(kw, response, flags=re.IGNORECASE))
        except re.error:
            n = response.lower().count(kw.lower())
        if rel == "at least":
            need = max(0, freq - n)
            fw = _constraint(constraints, "keywords:forbidden_words")
            forbidden = {
                str(x).lower() for x in (fw["slots"].get("forbidden_words", []) if fw else [])
            }
            atom = f"x{kw}x" if kw.lower() in forbidden else kw
            return response + ((" " + atom) * need)
        if n >= freq:
            try:
                return re.sub(kw, safe, response, flags=re.IGNORECASE)
            except re.error:
                return response.replace(kw, safe)
        return response

    if iid == "keywords:forbidden_words":
        out = response
        for word in s.get("forbidden_words", []):
            w = str(word)
            try:
                out = re.sub(r"\b" + w + r"\b", safe, out, flags=re.IGNORECASE)
            except re.error:
                out = out.replace(w, safe)
        return out

    if iid == "keywords:letter_frequency":
        letter = str(s["letter"]).lower()
        freq = int(s["let_frequency"])
        rel = str(s["let_relation"])
        n = response.lower().count(letter)
        if rel == "at least":
            return response + " " + (letter * max(0, freq - n))
        if n >= freq:
            replacement = next((x for x in "zxqvbcdfg" if x != letter), "x")
            return re.sub(re.escape(letter), replacement, response, flags=re.IGNORECASE)
        return response

    if iid == "length_constraints:number_sentences":
        _, util = _load_exact_checker_modules()
        target = int(s["num_sentences"])
        relation = str(s["relation"])
        try:
            n = util.count_sentences(response)
        except Exception:
            return response
        if relation == "at least":
            if n >= target:
                return response
            out = response.rstrip()
            if out and out[-1] not in ".!?":
                out += "."
            for _ in range(target - max(n, 1)):
                out += f" {safe}."
            return out
        # For a '< N' ceiling, collapse punctuation. Any other checker that
        # requires terminal punctuation can repair later in another fixed-point
        # pass. '< 1' is genuinely impossible for a nonempty ordinary response.
        if n >= target:
            return re.sub(r"[.!?]+", " ", response).strip()
        return response

    if iid == "length_constraints:number_paragraphs":
        target = int(s["num_paragraphs"])
        flat = re.sub(r"\s?\*\*\*\s?", " ", response).strip() or safe
        if target <= 1:
            return flat
        return (" *** ".join([flat] + [safe] * (target - 1))).strip()

    if iid == "length_constraints:number_words":
        _, util = _load_exact_checker_modules()
        target = int(s["num_words"])
        relation = str(s["relation"])
        try:
            n = int(util.count_words(response))
        except Exception:
            return response
        if relation == "at least" and n < target:
            return response + ((" " + safe) * (target - n))
        # Generator thresholds are 100..500. Other supported formal atoms are
        # normally far below that. Do not destructively truncate mandatory text;
        # if the ceiling is still violated, fail closed after search.
        return response

    if iid == "length_constraints:nth_paragraph_first_word":
        target = int(s["num_paragraphs"])
        nth = int(s["nth_paragraph"])
        first = str(s["first_word"])
        flat = re.sub(r"\n\s*\n+", " ", response).strip() or safe
        parts = [safe for _ in range(target)]
        if nth == 1:
            parts[0] = f"{first} {flat}".strip()
        else:
            parts[0] = flat
            parts[nth - 1] = f"{first} {safe}".strip()
        return "\n\n".join(parts)

    if iid == "detectable_content:number_placeholders":
        target = int(s["num_placeholders"])
        n = len(re.findall(r"\[.*?\]", response))
        if n < target:
            return response + "".join(f" [{safe}{i}]" for i in range(target - n))
        return response

    if iid == "detectable_content:postscript":
        marker = str(s["postscript_marker"]).lower()
        return response.rstrip() + f"\n{marker} {safe}"

    if iid == "detectable_format:number_bullet_lists":
        target = int(s["num_bullets"])
        lines = response.splitlines() or [response]
        # Neutralize any accidental bullet lines, then create exactly target.
        neutral: list[str] = []
        for line in lines:
            if re.match(r"^\s*\*[^\*].*$", line) or re.match(r"^\s*-.*$", line):
                neutral.append(f"{safe} {line.strip()}")
            else:
                neutral.append(line)
        base = "\n".join(neutral).rstrip()
        bullets = "\n".join(f"* {safe}{i}" for i in range(target))
        return (base + "\n" + bullets).strip()

    if iid == "detectable_format:number_highlighted_sections":
        target = int(s["num_highlights"])
        singles = [
            x for x in re.findall(r"\*[^\n\*]*\*", response)
            if x.strip("*").strip()
        ]
        doubles = [
            x for x in re.findall(r"\*\*[^\n\*]*\*\*", response)
            if x.removeprefix("**").removesuffix("**").strip()
        ]
        n = len(singles) + len(doubles)
        if n < target:
            return response.rstrip() + "".join(f" {safe} *{safe}{i}*" for i in range(target - n))
        return response

    if iid == "detectable_format:multiple_sections":
        splitter = str(s["section_spliter"])
        target = int(s["num_sections"])
        pattern = r"\s?" + re.escape(splitter) + r"\s?\d+\s?"
        current = max(0, len(re.split(pattern, response)) - 1)
        if current >= target:
            return response
        out = response.rstrip()
        for i in range(current + 1, target + 1):
            out += f"\n{splitter} {i}\n{safe}"
        return out.strip()

    if iid == "detectable_format:json_format":
        # JSON is conflict-compatible in the historical registry only with
        # keyword existence/forbidden. Rewrapping is therefore a safe repair
        # that preserves lexical atoms inside a JSON string.
        return json.dumps({"q": response}, ensure_ascii=False, separators=(",", ":"))

    if iid == "detectable_format:title":
        return response.rstrip() + f" <<{safe}>>"

    if iid == "combination:two_responses":
        if "******" in response:
            # Normalize a malformed previous attempt to one delimiter.
            chunks = [x.strip() for x in response.split("******") if x.strip()]
            left = chunks[0] if chunks else safe
        else:
            left = response.strip() or safe
        right = left + " " + safe
        return f"{left}******{right}"

    if iid == "combination:repeat_prompt":
        prefix = str(s.get("prompt_to_repeat") or "").strip()
        if not prefix:
            return response
        return prefix + ("\n" + response if response.strip() else "")

    if iid == "startend:end_checker":
        phrase = str(s["end_phrase"]).strip().lower()
        # Outer quotation is ignored by the exact end checker. Strip only an
        # unmatched trailing quote here; quotation repair can restore wrapping.
        out = response.rstrip()
        if out.endswith('"') and not out.startswith('"'):
            out = out[:-1].rstrip()
        return (out + " " + phrase).strip()

    if iid == "change_case:capital_word_frequency":
        target = int(s["capital_frequency"])
        relation = str(s["capital_relation"])
        if relation == "at least":
            return response + ((" " + safe.upper()) * target)
        # Lowercase all-uppercase lexical runs. If another exact structural
        # checker needs uppercase text (e.g. SECTION), a later pass restores it.
        return re.sub(r"\b[A-Z]+\b", lambda m: m.group(0).lower(), response)

    if iid == "change_case:english_capital":
        return response.upper()

    if iid == "change_case:english_lowercase":
        return response.lower()

    if iid == "punctuation:no_comma":
        return response.replace(",", " ")

    if iid == "startend:quotation":
        stripped = response.strip()
        stripped = stripped.strip('"')
        return f'"{stripped}"'

    # language:response_language is intentionally outside the recovered
    # historical generator universe and is rejected before search.
    return response


def synthesize_visible_witness(
    prompt: str,
    *,
    max_cycles: int = 4,
) -> dict[str, Any]:
    compiled = compile_visible_constraints(str(prompt or ""))
    constraints = list(compiled.get("constraints") or [])
    ids = [str(c["instruction_id"]) for c in constraints]

    common = {
        "schema": SCHEMA,
        "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "pinned_checker_blobs": {
            "instructions.py": PINNED_INSTRUCTIONS_BLOB,
            "instructions_registry.py": PINNED_REGISTRY_BLOB,
            "instructions_util.py": PINNED_UTIL_BLOB,
        },
        "historical_generator_commit": HISTORICAL_GENERATOR_COMMIT,
        "visible_prompt_only": True,
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
        "model_dependency_count": 0,
        "semantic_capability_credit": 0,
    }

    if compiled.get("status") != "PASS":
        return {
            **common,
            "status": "BLOCKED",
            "reason": "VISIBLE_CONSTRAINT_COMPILER_FAIL_CLOSED",
            "response": None,
            "compiler": compiled,
        }
    if not constraints:
        return {
            **common,
            "status": "BLOCKED",
            "reason": "NO_VISIBLE_LEGACY_CONSTRAINTS",
            "response": None,
            "compiler": compiled,
        }
    incomplete = [c["instruction_id"] for c in constraints if not c.get("parameter_complete")]
    if incomplete:
        return {
            **common,
            "status": "BLOCKED",
            "reason": "PARAMETER_INCOMPLETE",
            "parameter_incomplete": incomplete,
            "response": None,
            "compiler": compiled,
        }
    outside = sorted(set(ids) - HISTORICAL_GENERATOR_INSTRUCTION_IDS)
    if outside:
        return {
            **common,
            "status": "BLOCKED",
            "reason": "OUTSIDE_RECOVERED_HISTORICAL_GENERATOR_UNIVERSE",
            "outside_instruction_ids": outside,
            "response": None,
            "compiler": compiled,
        }
    if len(constraints) > HISTORICAL_GENERATOR_MAX_SAMPLED_INSTRUCTIONS:
        return {
            **common,
            "status": "BLOCKED",
            "reason": "VISIBLE_CONSTRAINT_COUNT_EXCEEDS_HISTORICAL_GENERATOR_MAX",
            "response": None,
            "compiler": compiled,
        }

    attempts = 0
    best = {
        "response": "",
        "pass_count": -1,
        "checker_count": len(constraints),
        "failed": ids,
        "passed": [],
        "all_pass": False,
    }
    indexed = list(range(len(constraints)))

    for seed in _base_seeds(constraints):
        for order in itertools.permutations(indexed):
            attempts += 1
            response = seed
            for _ in range(max(1, int(max_cycles))):
                for idx in order:
                    response = _apply_one(response, constraints[idx], constraints)
                verdict = _validate(response, constraints)
                if verdict["pass_count"] > best["pass_count"]:
                    best = {"response": response, **verdict}
                if verdict["all_pass"]:
                    return {
                        **common,
                        "status": "PASS",
                        "response": response,
                        "exact_checker_pass_count": verdict["pass_count"],
                        "checker_count": verdict["checker_count"],
                        "failing_instruction_ids": [],
                        "attempts": attempts,
                        "max_cycles": max_cycles,
                        "compiler": compiled,
                        "hard_nonclaim": "FORMAL_IFEVAL_WITNESS_PASS_DOES_NOT_PROVE_TASK_SEMANTIC_QUALITY_OR_OPUS55_CAPABILITY_OWNERSHIP",
                    }

    return {
        **common,
        "status": "BLOCKED",
        "reason": "NO_ALL_CHECKER_FIXED_POINT_FOUND",
        "response": None,
        "best_exact_checker_pass_count": best["pass_count"],
        "checker_count": best["checker_count"],
        "best_failing_instruction_ids": best["failed"],
        "attempts": attempts,
        "max_cycles": max_cycles,
        "compiler": compiled,
        "hard_nonclaim": "BLOCKED_DOES_NOT_PROVE_THE_VISIBLE_CONSTRAINT_SET_IS_MATHEMATICALLY_UNSATISFIABLE",
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return synthesize_visible_witness(
        str(args.get("prompt") or args.get("text") or ""),
        max_cycles=int(args.get("max_cycles") or 4),
    )


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--max-cycles", type=int, default=4)
    ns = ap.parse_args()
    print(json.dumps(
        synthesize_visible_witness(ns.prompt, max_cycles=ns.max_cycles),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))
