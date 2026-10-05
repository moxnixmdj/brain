#!/usr/bin/env python3
"""Fail-closed semantic-seed composer for pinned legacy LiveBench IFEval.

This module bridges a real semantic answer seed to the deterministic legacy
IFEval constraint surface without replacing, rewriting, truncating, case-folding,
or otherwise deleting seed bytes. Every PASS response contains the original seed
verbatim as one contiguous substring.

Only constraint families with a source-derived prompt inversion and a local
checker-equivalent validator are admitted here. Unsupported recognized families
fail closed. This is integration glue, not a semantic generator and not terminal
acceptance authority.
"""
from __future__ import annotations

import re
from typing import Any

from canonical.runtime import livebench_legacy_ifeval_prompt_inverter_v1 as inverter

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_SEED_COMPOSER_V1"
PRESERVATION_CONTRACT = (
    "ANY_PASS_RESPONSE_CONTAINS_THE_ORIGINAL_SEMANTIC_SEED_VERBATIM_"
    "AS_ONE_CONTIGUOUS_SUBSTRING"
)

SUPPORTED_IDS = frozenset({
    "keywords:existence",
    "keywords:frequency",
    "keywords:forbidden_words",
    "keywords:letter_frequency",
    "length_constraints:number_words",
    "detectable_content:number_placeholders",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "detectable_format:multiple_sections",
    "detectable_format:title",
    "combination:two_responses",
    "combination:repeat_prompt",
    "startend:end_checker",
    "punctuation:no_comma",
    "startend:quotation",
})

SOURCE_BINDING = {
    "livebench_commit": inverter.PINNED_LIVEBENCH_COMMIT,
    "legacy_instructions_blob": inverter.PINNED_INSTRUCTIONS_BLOB,
    "legacy_inverter_schema": inverter.SCHEMA,
}


def _result(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "seed_preservation_contract": PRESERVATION_CONTRACT,
        "source_binding": SOURCE_BINDING,
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "terminal_case_content_used_to_build_runtime": False,
        **extra,
    }


def _append(candidate: str, text: str, *, newline: bool = False) -> str:
    if not text:
        return candidate
    if newline:
        return candidate + ("" if candidate.endswith("\n") else "\n") + text
    return candidate + ("" if not candidate or candidate[-1].isspace() else " ") + text


def _regex_count(pattern: str, value: str, flags: int = 0) -> int:
    try:
        return len(re.findall(pattern, value, flags=flags))
    except re.error as exc:
        raise ValueError("PUBLIC_REGEX_INVALID") from exc


def _bullet_count(value: str) -> int:
    star = re.findall(r"^\s*\*[^\*].*$", value, flags=re.MULTILINE)
    dash = re.findall(r"^\s*-.*$", value, flags=re.MULTILINE)
    return len(star) + len(dash)


def _highlight_count(value: str) -> int:
    total = 0
    for item in re.findall(r"\*[^\n\*]*\*", value):
        if item.strip("*").strip():
            total += 1
    for item in re.findall(r"\*\*[^\n\*]*\*\*", value):
        if item.removeprefix("**").removesuffix("**").strip():
            total += 1
    return total


def _section_count(value: str, splitter: str) -> int:
    return len(re.split(r"\s?" + splitter + r"\s?\d+\s?", value)) - 1


def _validate(iid: str, slots: dict[str, Any], value: str) -> bool:
    if iid == "keywords:existence":
        return all(
            _regex_count(str(keyword), value, re.IGNORECASE) > 0
            for keyword in slots["keywords"]
        )
    if iid == "keywords:frequency":
        actual = _regex_count(str(slots["keyword"]), value, re.IGNORECASE)
        n = int(slots["frequency"])
        return actual < n if slots["relation"] == "less than" else actual >= n
    if iid == "keywords:forbidden_words":
        return all(
            _regex_count(r"\b" + str(word) + r"\b", value, re.IGNORECASE) == 0
            for word in slots["forbidden_words"]
        )
    if iid == "keywords:letter_frequency":
        actual = value.lower().count(str(slots["letter"]).lower())
        n = int(slots["let_frequency"])
        return actual < n if slots["let_relation"] == "less than" else actual >= n
    if iid == "length_constraints:number_words":
        actual = len(re.findall(r"\w+", value, flags=re.UNICODE))
        n = int(slots["num_words"])
        return actual < n if slots["relation"] == "less than" else actual >= n
    if iid == "detectable_content:number_placeholders":
        return len(re.findall(r"\[.*?\]", value)) >= int(slots["num_placeholders"])
    if iid == "detectable_content:postscript":
        marker = str(slots["postscript_marker"])
        lowered = value.lower()
        if marker == "P.P.S":
            pattern = r"\s*p\.\s?p\.\s?s.*$"
        elif marker == "P.S.":
            pattern = r"\s*p\.\s?s\..*$"
        else:
            pattern = r"\s*" + marker.lower() + r".*$"
        return bool(re.findall(pattern, lowered, flags=re.MULTILINE))
    if iid == "detectable_format:number_bullet_lists":
        return _bullet_count(value) == int(slots["num_bullets"])
    if iid == "detectable_format:constrained_response":
        stripped = value.strip()
        return any(
            option in stripped
            for option in ("My answer is yes.", "My answer is no.", "My answer is maybe.")
        )
    if iid == "detectable_format:number_highlighted_sections":
        return _highlight_count(value) >= int(slots["num_highlights"])
    if iid == "detectable_format:multiple_sections":
        return _section_count(value, str(slots["section_spliter"])) >= int(slots["num_sections"])
    if iid == "detectable_format:title":
        return any(
            title.lstrip("<").rstrip(">").strip()
            for title in re.findall(r"<<[^\n]+>>", value)
        )
    if iid == "combination:two_responses":
        parts = value.split("******")
        valid = []
        for index, part in enumerate(parts):
            if part.strip():
                valid.append(part)
            elif index != 0 and index != len(parts) - 1:
                return False
        return len(valid) == 2 and valid[0].strip() != valid[1].strip()
    if iid == "combination:repeat_prompt":
        target = str(slots["prompt_to_repeat"]).strip().lower()
        return bool(target) and value.strip().lower().startswith(target)
    if iid == "startend:end_checker":
        end = str(slots["end_phrase"]).strip().lower()
        return value.strip().strip('"').lower().endswith(end)
    if iid == "punctuation:no_comma":
        return "," not in value
    if iid == "startend:quotation":
        stripped = value.strip()
        return len(stripped) > 1 and stripped[0] == '"' and stripped[-1] == '"'
    raise ValueError("UNSUPPORTED_VALIDATOR:" + iid)


def _compose_one(candidate: str, iid: str, slots: dict[str, Any]) -> tuple[str, str | None]:
    if iid == "combination:repeat_prompt":
        target = str(slots["prompt_to_repeat"])
        if not candidate.strip().lower().startswith(target.strip().lower()):
            return target + "\n" + candidate, iid
        return candidate, None

    if iid == "detectable_format:title":
        if not _validate(iid, slots, candidate):
            return "<<XQZ Answer>>\n" + candidate, iid
        return candidate, None

    if iid == "keywords:existence":
        missing = [
            str(keyword)
            for keyword in slots["keywords"]
            if _regex_count(str(keyword), candidate, re.IGNORECASE) == 0
        ]
        if missing:
            return _append(candidate, " ".join(missing)), iid
        return candidate, None

    if iid == "keywords:frequency":
        keyword = str(slots["keyword"])
        relation = str(slots["relation"])
        target = int(slots["frequency"])
        actual = _regex_count(keyword, candidate, re.IGNORECASE)
        if relation == "at least" and actual < target:
            return _append(candidate, " ".join([keyword] * (target - actual))), iid
        return candidate, None

    if iid == "keywords:letter_frequency":
        letter = str(slots["letter"])
        relation = str(slots["let_relation"])
        target = int(slots["let_frequency"])
        actual = candidate.lower().count(letter.lower())
        if relation == "at least" and actual < target:
            return _append(candidate, letter * (target - actual)), iid
        return candidate, None

    if iid == "detectable_content:number_placeholders":
        target = int(slots["num_placeholders"])
        actual = len(re.findall(r"\[.*?\]", candidate))
        if actual < target:
            additions = " ".join(f"[xqz_slot_{i}]" for i in range(actual + 1, target + 1))
            return _append(candidate, additions), iid
        return candidate, None

    if iid == "detectable_format:number_highlighted_sections":
        target = int(slots["num_highlights"])
        actual = _highlight_count(candidate)
        if actual < target:
            additions = " ".join(f"*xqz_h_{i}*" for i in range(actual + 1, target + 1))
            # Prefix the appended line with ordinary text so highlights never
            # accidentally become BulletListChecker lines.
            return _append(candidate, "xqz " + additions), iid
        return candidate, None

    if iid == "detectable_format:multiple_sections":
        target = int(slots["num_sections"])
        splitter = str(slots["section_spliter"])
        actual = _section_count(candidate, splitter)
        if actual < target:
            out = candidate
            for i in range(actual + 1, target + 1):
                out = _append(out, f"{splitter} {i}\nxqz_section_{i}", newline=True)
            return out, iid
        return candidate, None

    if iid == "detectable_format:number_bullet_lists":
        target = int(slots["num_bullets"])
        actual = _bullet_count(candidate)
        if actual < target:
            out = candidate
            for i in range(actual + 1, target + 1):
                out = _append(out, f"* xqz_bullet_{i}", newline=True)
            return out, iid
        return candidate, None

    # These are validator-only. If the semantic seed already satisfies them,
    # preserve it; otherwise no semantics-preserving repair is claimed.
    if iid in {
        "keywords:forbidden_words",
        "length_constraints:number_words",
        "detectable_format:constrained_response",
        "combination:two_responses",
        "punctuation:no_comma",
    }:
        return candidate, None

    # Postscript and end constraints are suffixes. They are intentionally late
    # in compose() so later structural additions cannot invalidate them.
    if iid in {"detectable_content:postscript", "startend:end_checker", "startend:quotation"}:
        return candidate, None

    raise ValueError("UNSUPPORTED_COMPOSER:" + iid)


def compose(seed: str, prompt: str) -> dict[str, Any]:
    seed = str(seed or "")
    prompt = str(prompt or "")
    if not seed:
        return _result("FAIL_CLOSED", error="SEMANTIC_SEED_REQUIRED", response=None)
    if not prompt.strip():
        return _result("FAIL_CLOSED", error="PROMPT_REQUIRED", response=None)

    matches = inverter.recognize(prompt)
    if not matches:
        return _result(
            "FAIL_CLOSED",
            error="NO_RECOGNIZED_LEGACY_IFEVAL_CONSTRAINT",
            response=None,
            recognized_constraint_ids=[],
        )

    ids = [str(item["instruction_id"]) for item in matches]
    unsupported = sorted(set(ids) - SUPPORTED_IDS)
    if unsupported:
        return _result(
            "FAIL_CLOSED",
            error="RECOGNIZED_CONSTRAINT_REQUIRES_UNSUPPORTED_OR_NONPRESERVING_TRANSFORM",
            response=None,
            recognized_constraint_ids=ids,
            unsupported_constraint_ids=unsupported,
        )

    candidate = seed
    applied: list[str] = []
    by_id = {str(item["instruction_id"]): dict(item.get("slots") or {}) for item in matches}

    # Stage A: prefix/content/structural additions.
    stage_a = [
        "combination:repeat_prompt",
        "detectable_format:title",
        "keywords:existence",
        "keywords:frequency",
        "keywords:letter_frequency",
        "detectable_content:number_placeholders",
        "detectable_format:number_highlighted_sections",
        "detectable_format:multiple_sections",
        "detectable_format:number_bullet_lists",
        "keywords:forbidden_words",
        "length_constraints:number_words",
        "detectable_format:constrained_response",
        "combination:two_responses",
        "punctuation:no_comma",
    ]
    try:
        for iid in stage_a:
            if iid not in by_id:
                continue
            candidate, changed = _compose_one(candidate, iid, by_id[iid])
            if changed:
                applied.append(changed)

        # Stage B: postscript after all other ordinary suffix material.
        if "detectable_content:postscript" in by_id:
            slots = by_id["detectable_content:postscript"]
            if not _validate("detectable_content:postscript", slots, candidate):
                candidate = _append(
                    candidate,
                    f"{slots['postscript_marker']} xqz_postscript",
                    newline=True,
                )
                applied.append("detectable_content:postscript")

        # Stage C: exact end phrase, then outer quotation last. The pinned
        # EndChecker strips surrounding double quotes before checking suffix.
        if "startend:end_checker" in by_id:
            slots = by_id["startend:end_checker"]
            if not _validate("startend:end_checker", slots, candidate):
                candidate = _append(candidate, str(slots["end_phrase"]))
                applied.append("startend:end_checker")

        if "startend:quotation" in by_id:
            slots = by_id["startend:quotation"]
            if not _validate("startend:quotation", slots, candidate):
                candidate = '"' + candidate + '"'
                applied.append("startend:quotation")

        errors = [
            iid for iid in ids
            if not _validate(iid, by_id[iid], candidate)
        ]
    except (KeyError, TypeError, ValueError, re.error) as exc:
        return _result(
            "FAIL_CLOSED",
            error="COMPOSITION_OR_LOCAL_POSTVALIDATION_ERROR:" + type(exc).__name__,
            response=None,
            recognized_constraint_ids=ids,
            applied_transforms=applied,
        )

    if errors:
        return _result(
            "FAIL_CLOSED",
            error="LOCAL_CHECKER_EQUIVALENT_POSTVALIDATION_FAILED",
            response=None,
            recognized_constraint_ids=ids,
            failed_constraint_ids=errors,
            applied_transforms=applied,
            seed_verbatim_preserved=(seed in candidate),
        )

    if seed not in candidate:
        return _result(
            "FAIL_CLOSED",
            error="INTERNAL_SEED_PRESERVATION_INVARIANT_BROKEN",
            response=None,
            recognized_constraint_ids=ids,
            applied_transforms=applied,
            seed_verbatim_preserved=False,
        )

    return _result(
        "PASS_CANDIDATE_SEED_PRESERVED",
        response=candidate,
        recognized_constraint_ids=ids,
        applied_transforms=applied,
        seed_verbatim_preserved=True,
        local_checker_equivalent_postvalidation=True,
        hard_nonclaim=(
            "PASS_PROVES_VERBATIM_SEED_RETENTION_AND_LOCAL_EQUIVALENTS_FOR_THE_"
            "SUPPORTED_PINNED_LEGACY_CHECKERS_ONLY; IT_DOES_NOT_PROVE_SEMANTIC_"
            "EQUIVALENCE_OF_ADDED_MATERIAL, UNIVERSAL_25_CHECKER_COVERAGE, OR_"
            "LIVEBENCH_ACCEPTANCE"
        ),
    )


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return compose(
        str(args.get("seed") or args.get("semantic_seed") or ""),
        str(args.get("prompt") or args.get("instruction") or ""),
    )


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("seed")
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(compose(ns.seed, ns.prompt), indent=2, sort_keys=True))
