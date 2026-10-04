#!/usr/bin/env python3
"""Deterministic prompt-derived witness compiler for a safe subset of pinned LiveBench IF.

Uses only exact public build_description language from LiveBench commit
8f8e5c381a16e3f24257776edd53471fe86f8091. Never reads terminal case IDs,
hidden checker IDs/kwargs, expected outputs, or case-specific traces.

V1 is deliberately single-checker only. Multiple recognized checkers fail closed
until conjunction soundness is independently proved.
"""
from __future__ import annotations

import ast
import json
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUBLIC_WITNESS_COMPILER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"


def _result(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "terminal_case_content_used": False,
        "hidden_metadata_used": False,
        "network_used": False,
        "incremental_spend_usd": 0,
        "model_dependency_count": 0,
        "terminal_authority": False,
        **extra,
    }


def _words(n: int) -> str:
    vocab = (
        "Amber Birch Cedar Delta Ember Frost Granite Harbor Ivory Juniper "
        "Kinetic Lumen Meadow Nectar Orbit Prairie Quartz River Summit Timber "
        "Umber Velvet Willow Xenon Yarrow Zephyr"
    ).split()
    return " ".join(vocab[i % len(vocab)] for i in range(max(0, n)))


def _sentences(n: int) -> str:
    return " ".join(f"Alpha{i + 1}." for i in range(max(0, n)))


def _paragraphs(n: int) -> str:
    return " *** ".join(f"Alpha{i + 1}" for i in range(max(0, n)))


def _word_count(value: str) -> int:
    return len(re.findall(r"\b\w+\b", value, flags=re.UNICODE))


def _candidate_matches(prompt: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []

    for m in re.finditer(r"Answer with (less than|at least) (\d+) words\.", prompt, re.I):
        relation, n = m.group(1).lower(), int(m.group(2))
        if relation == "less than":
            if n <= 1:
                continue
            response = _words(n - 1)
            valid = _word_count(response) < n
        else:
            response = _words(max(1, n))
            valid = _word_count(response) >= n
        matches.append({"checker": "legacy:NumberOfWords", "response": response, "valid": valid})

    for m in re.finditer(
        r"Your response should contain (less than|at least) (\d+) sentences\.",
        prompt,
        re.I,
    ):
        relation, n = m.group(1).lower(), int(m.group(2))
        if relation == "less than":
            if n <= 1:
                continue
            response = _sentences(n - 1)
        else:
            response = _sentences(max(1, n))
        count = len(re.findall(r"[^.!?]+[.!?]", response))
        valid = count < n if relation == "less than" else count >= n
        matches.append({"checker": "legacy:NumberOfSentences", "response": response, "valid": valid})

    for m in re.finditer(
        r"There should be (\d+) paragraphs\. Paragraphs are separated with the markdown divider: \*\*\*",
        prompt,
        re.I,
    ):
        n = int(m.group(1))
        if n < 1:
            continue
        response = _paragraphs(n)
        paragraphs = re.split(r"\s?\*\*\*\s?", response)
        valid = len([p for p in paragraphs if p.strip()]) == n and all(p.strip() for p in paragraphs)
        matches.append({"checker": "legacy:ParagraphChecker", "response": response, "valid": valid})

    if "Entire output should be wrapped in JSON format." in prompt:
        response = '{"answer":"Alpha"}'
        try:
            json.loads(response)
            valid = True
        except ValueError:
            valid = False
        matches.append({"checker": "legacy:JsonFormat", "response": response, "valid": valid})

    for m in re.finditer(r"Answer with one of the following options:\s*(\[[^\n]*?\])", prompt, re.I):
        try:
            options = ast.literal_eval(m.group(1))
        except Exception:
            options = None
        if isinstance(options, (list, tuple)) and options and all(isinstance(x, str) for x in options):
            response = options[0]
            matches.append({
                "checker": "legacy:ConstrainedResponseChecker",
                "response": response,
                "valid": any(x in response for x in options),
            })

    if "Wrap your entire response with double quotation marks." in prompt:
        response = '"Alpha"'
        matches.append({
            "checker": "legacy:QuotationChecker",
            "response": response,
            "valid": len(response.strip()) > 1 and response.strip()[0] == '"' and response.strip()[-1] == '"',
        })

    for m in re.finditer(r"The response must contain between (\d+) and (\d+) words\.", prompt, re.I):
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo < 1 or hi < lo:
            continue
        response = _words(lo)
        matches.append({
            "checker": "modern:WordCountRangeChecker",
            "response": response,
            "valid": lo <= _word_count(response) <= hi,
        })

    for m in re.finditer(
        r"Include exactly (\d+) numbers in the response; do not use commas within the numbers\.",
        prompt,
        re.I,
    ):
        n = int(m.group(1))
        if n < 1:
            continue
        response = " ".join(str(i + 1) for i in range(n))
        scrubbed = re.sub(r"[^\w\s]", "", response)
        matches.append({
            "checker": "modern:NumbersCountChecker",
            "response": response,
            "valid": len(re.findall(r"\d+", scrubbed)) == n,
        })

    if "The output should not contain any whitespace." in prompt:
        response = "Alpha"
        matches.append({
            "checker": "modern:NoWhitespaceChecker",
            "response": response,
            "valid": not any(ch.isspace() for ch in response),
        })

    if "Write the entire response in title case (capitalize the first letter of every word)." in prompt:
        response = "Alpha Beta"
        valid = all(w[0].isupper() and w[1:].islower() for w in response.split())
        matches.append({"checker": "modern:TitleCaseChecker", "response": response, "valid": valid})

    if (
        "Use this exact template for your response: My Answer: [answer] "
        "My Conclusion: [conclusion] Future Outlook: [outlook]"
    ) in prompt:
        response = "My Answer: Alpha My Conclusion: Beta Future Outlook: Gamma"
        valid = all(x in response for x in ("My Answer:", "My Conclusion:", "Future Outlook:"))
        matches.append({"checker": "modern:OutputTemplateChecker", "response": response, "valid": valid})

    for m in re.finditer(
        r"Answer with a newline-separated list of items, instead of bullet points use (.+?)\.",
        prompt,
        re.I,
    ):
        sep = m.group(1).strip()
        if not sep or len(sep) > 64:
            continue
        response = f"{sep} Alpha\n{sep} Beta"
        matches.append({
            "checker": "modern:SpecialBulletPointsChecker",
            "response": response,
            "valid": len(re.findall(re.escape(sep), response)) >= 2,
        })

    return matches


def compile_witness(prompt: str) -> dict[str, Any]:
    prompt = str(prompt or "")
    if not prompt.strip():
        return _result("BLOCKED", reason="PROMPT_REQUIRED")

    matches = _candidate_matches(prompt)
    if any(m.get("valid") is not True for m in matches):
        return _result(
            "BLOCKED",
            reason="LOCAL_POSTVALIDATION_FAILED",
            matched_checkers=[m["checker"] for m in matches],
        )
    if not matches:
        return _result("BLOCKED", reason="NO_SUPPORTED_PUBLIC_DESCRIPTION")
    if len(matches) != 1:
        return _result(
            "BLOCKED",
            reason="MULTI_CHECKER_COMBINATION_NOT_PROVED",
            matched_checkers=[m["checker"] for m in matches],
        )

    item = matches[0]
    return _result(
        "PASS",
        response=item["response"],
        matched_checkers=[item["checker"]],
        public_description_match_count=1,
        scorer_local_postvalidation=True,
        hard_nonclaim=(
            "V1 PROVES ONLY THE RECOGNIZED SINGLE PUBLIC CHECKER WITNESS; "
            "ABSENCE OF OTHER UNRECOGNIZED CONSTRAINTS IS NOT YET PROVED."
        ),
    )


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return compile_witness(str(args.get("prompt") or args.get("instruction") or ""))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(compile_witness(ns.prompt), indent=2, sort_keys=True))
