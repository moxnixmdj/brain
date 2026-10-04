#!/usr/bin/env python3
"""Exact zero-terminal-case falsification sweep for active legacy15 composition.

For every one of the 928 conflict-compatible active-ID sets, synthesize multiple
parameter-boundary prompts using the frozen checkers' own build_description(),
route the visible prompt through the canonical historical-envelope compiler and
joint witness, then score the candidate with the same frozen checker instances.

This is a falsifier, not an acceptance proof: PASS establishes only the finite
synthetic matrix named in the receipt. It reads zero frozen terminal rows.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_joint_witness_v1 as witness

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_END2END_EXACT_SYNTHETIC_AUDIT_V2"

SCENARIOS = (
    "LOW_AT_LEAST",
    "HIGH_AT_LEAST",
    "LOW_LESS_THAN",
    "HIGH_LESS_THAN",
    "KEYWORD_OVERLAP",
)

BASE = (
    "The following are the beginning sentences of a news article from the Guardian.\n"
    "-------\n"
    "Synthetic source text contains neutral material only.\n"
    "-------\n"
    "Rewrite the source faithfully."
)

ENDINGS = (
    "Any other questions?",
    "Is there anything else I can help with?",
)


def _kwargs(iid: str, scenario: str) -> dict[str, Any]:
    high = scenario in {"HIGH_AT_LEAST", "HIGH_LESS_THAN"}
    less = scenario in {"LOW_LESS_THAN", "HIGH_LESS_THAN"}
    overlap = scenario == "KEYWORD_OVERLAP"
    relation = "less than" if less else "at least"

    if iid == "keywords:existence":
        return {"keywords": ["alpha", "bravo", "cedar", "delta", "ember"]}
    if iid == "keywords:forbidden_words":
        words = ["omega", "hazard", "taboo", "neverword", "prohibit"]
        if overlap:
            words[0] = "alpha"
        return {"forbidden_words": words}
    if iid == "length_constraints:number_paragraphs":
        return {"num_paragraphs": 5 if high else 1}
    if iid == "length_constraints:number_words":
        return {"num_words": 500 if high else 100, "relation": relation}
    if iid == "length_constraints:number_sentences":
        return {"num_sentences": 20 if high else 1, "relation": relation}
    if iid == "length_constraints:nth_paragraph_first_word":
        n = 5 if high else 1
        return {"num_paragraphs": n, "nth_paragraph": n, "first_word": "Anchor"}
    if iid == "detectable_content:postscript":
        return {"postscript_marker": "P.P.S" if high else "P.S."}
    if iid == "detectable_format:number_bullet_lists":
        return {"num_bullets": 5 if high else 1}
    if iid == "detectable_format:multiple_sections":
        return {"section_spliter": "SECTION" if high else "Section", "num_sections": 5 if high else 1}
    if iid == "startend:end_checker":
        return {"end_phrase": ENDINGS[1 if high else 0]}
    if iid in {
        "detectable_format:title",
        "detectable_format:json_format",
        "combination:repeat_prompt",
        "combination:two_responses",
        "startend:quotation",
    }:
        return {}
    raise KeyError(iid)


def _load_registry(livebench_root: Path):
    runner = livebench_root / "livebench" / "if_runner"
    sys.path.insert(0, str(runner))
    from instruction_following_eval import instructions_registry  # type: ignore
    return instructions_registry


def _build_case(registry, ids: tuple[str, ...], scenario: str):
    checkers = []
    descriptions = []
    kwargs_rows = []
    for iid in ids:
        checker = registry.INSTRUCTION_DICT[iid](iid)
        kwargs = _kwargs(iid, scenario)
        desc = checker.build_description(**kwargs)
        checkers.append(checker)
        descriptions.append(desc)
        kwargs_rows.append(dict(checker.get_instruction_args() or {}))

    prompt = BASE + " " + " ".join(descriptions)

    if "combination:repeat_prompt" in ids:
        marker = "First repeat the request word for word without change,"
        prefix = prompt.split(marker, 1)[0]
        i = ids.index("combination:repeat_prompt")
        checkers[i].build_description(prompt_to_repeat=prefix)
        kwargs_rows[i] = dict(checkers[i].get_instruction_args() or {})

    return prompt, checkers, kwargs_rows


def _evaluate(checkers, response: str) -> tuple[bool, list[bool]]:
    verdicts = [bool(c.check_following(response)) for c in checkers]
    return all(verdicts), verdicts


def audit(livebench_root: Path) -> dict[str, Any]:
    registry = _load_registry(livebench_root)
    shape_summary = arch.verify()
    sets = arch.enumerate_compatible_sets()
    failures: list[dict[str, Any]] = []
    route_counts: dict[str, int] = {}
    total = 0
    passed = 0

    for ids in sets:
        for scenario in SCENARIOS:
            total += 1
            prompt, checkers, kwargs_rows = _build_case(registry, ids, scenario)
            solved = witness.solve(prompt)
            route = str(solved.get("route") or solved.get("error") or "UNKNOWN")
            route_counts[route] = route_counts.get(route, 0) + 1
            response = solved.get("response")
            if solved.get("status") != "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS" or not isinstance(response, str):
                if len(failures) < 200:
                    failures.append({
                        "ids": list(ids),
                        "scenario": scenario,
                        "phase": "CONSTRUCTION",
                        "status": solved.get("status"),
                        "error": solved.get("error"),
                    })
                continue

            ok, verdicts = _evaluate(checkers, response)
            if ok:
                passed += 1
                continue

            if len(failures) < 200:
                failures.append({
                    "ids": list(ids),
                    "scenario": scenario,
                    "phase": "EXACT_CHECKER",
                    "failed_ids": [iid for iid, v in zip(ids, verdicts) if not v],
                    "kwargs": kwargs_rows,
                    "response_length": len(response),
                })

    status = "PASS" if passed == total else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "frozen_livebench_commit": "8f8e5c381a16e3f24257776edd53471fe86f8091",
        "active_id_count": len(arch.ACTIVE_IDS),
        "compatible_identity_shape_count": len(sets),
        "scenario_count": len(SCENARIOS),
        "scenario_names": list(SCENARIOS),
        "synthetic_case_count": total,
        "synthetic_case_pass_count": passed,
        "synthetic_case_fail_count": total - passed,
        "route_counts": dict(sorted(route_counts.items())),
        "first_failures_capped_200": failures,
        "archetype_verification": shape_summary,
        "terminal_case_content_read": 0,
        "terminal_case_metadata_read": 0,
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit": False,
        "capability_credit": False,
        "hard_nonclaim": (
            "PASS WOULD PROVE ONLY THIS FINITE PUBLIC-SOURCE SYNTHETIC MATRIX; "
            "FAIL IS A VALID CONSTRUCTIVE COUNTEREXAMPLE TO THE CURRENT TOTALITY HYPOTHESIS."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ns = ap.parse_args()
    result = audit(ns.livebench_root)
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "synthetic_case_count": result["synthetic_case_count"],
        "synthetic_case_pass_count": result["synthetic_case_pass_count"],
        "synthetic_case_fail_count": result["synthetic_case_fail_count"],
        "first_failures": result["first_failures_capped_200"][:10],
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
