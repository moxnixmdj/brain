#!/usr/bin/env python3
"""Exact pinned-checker synthetic audit for the active legacy15 constructor.

This audit enumerates every conflict-compatible active15 identity shape of
historical cardinality <=5, synthesizes source-legal visible descriptions from
the pinned public checker classes, compiles only the visible historical suffix,
generates bounded candidates, and postvalidates every candidate with the exact
pinned checker implementations.

It uses zero active terminal rows, prompts, kwargs, responses, ids, or scores.
Synthetic hidden kwargs are verifier labels only and are never given to the
constructor.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as shapes
from canonical.runtime import livebench_legacy15_joint_candidate_generator_v1 as generator
from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_JOINT_WITNESS_EXACT_SYNTHETIC_AUDIT_V1"
PINNED = "8f8e5c381a16e3f24257776edd53471fe86f8091"


def _load_registry(root: Path):
    sys.path.insert(0, str(root / "livebench" / "if_runner"))
    from instruction_following_eval import instructions_registry  # type: ignore
    return instructions_registry


def _profile_kwargs(iid: str, profile: str) -> dict[str, Any]:
    upper = profile == "UPPER"
    table: dict[str, dict[str, Any]] = {
        "keywords:existence": {"keywords": ["rock", "alpha"]},
        "keywords:forbidden_words": {"forbidden_words": ["rock", "omega"]},
        "length_constraints:number_paragraphs": {"num_paragraphs": 3 if not upper else 1},
        "length_constraints:number_words": {
            "num_words": 48 if not upper else 80,
            "relation": "at least" if not upper else "less than",
        },
        "length_constraints:number_sentences": {
            "num_sentences": 4 if not upper else 5,
            "relation": "at least" if not upper else "less than",
        },
        "length_constraints:nth_paragraph_first_word": {
            "num_paragraphs": 3 if not upper else 1,
            "nth_paragraph": 2 if not upper else 1,
            "first_word": "anchor",
        },
        "detectable_content:postscript": {"postscript_marker": "P.S." if not upper else "P.P.S"},
        "detectable_format:number_bullet_lists": {"num_bullets": 3 if not upper else 1},
        "detectable_format:title": {},
        "detectable_format:multiple_sections": {
            "section_spliter": "Section" if not upper else "SECTION",
            "num_sections": 2 if not upper else 1,
        },
        "detectable_format:json_format": {},
        "combination:repeat_prompt": {},
        "combination:two_responses": {},
        "startend:end_checker": {"end_phrase": "Any other questions?"},
        "startend:quotation": {},
    }
    return dict(table[iid])


def _build_case(ids: tuple[str, ...], profile: str, registry):
    descriptions: list[tuple[str, str, Any, dict[str, Any]]] = []
    for iid in ids:
        cls = registry.INSTRUCTION_DICT[iid]
        checker = cls(iid)
        kwargs = _profile_kwargs(iid, profile)
        desc = checker.build_description(**kwargs)
        descriptions.append((iid, desc, checker, kwargs))

    prefix = (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\n"
        "Synthetic public nonterminal article text only.\n"
        "-------\n"
    )
    prompt = prefix + " ".join(x[1] for x in descriptions)

    # Historical generator fills prompt_to_repeat from the exact visible prefix
    # before the rendered repeat marker after the prompt is assembled.
    marker = (
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)"
    )
    scorers: list[tuple[str, Any]] = []
    for iid, _desc, checker, kwargs in descriptions:
        if iid == "combination:repeat_prompt":
            repeat_kwargs = {"prompt_to_repeat": prompt.split(marker)[0]}
            checker = registry.INSTRUCTION_DICT[iid](iid)
            checker.build_description(**repeat_kwargs)
        scorers.append((iid, checker))
    return prompt, scorers


def _all_true(response: str, scorers: list[tuple[str, Any]]) -> tuple[bool, int]:
    truths = [bool(checker.check_following(response)) for _iid, checker in scorers]
    return bool(truths and all(truths)), sum(truths)


def audit(root: Path) -> dict[str, Any]:
    registry = _load_registry(root)
    compatible = shapes.enumerate_compatible_sets()
    profiles = ("LOWER", "UPPER")
    total = 0
    compiled = 0
    candidate_nonempty = 0
    full_pass = 0
    failure = Counter()
    failure_by_archetype = Counter()
    candidate_hist = Counter()

    for ids in compatible:
        for profile in profiles:
            total += 1
            prompt, scorers = _build_case(ids, profile, registry)
            parsed = compiler.compile_visible_constraints(prompt)
            got = {str(c.get("instruction_id")) for c in parsed.get("constraints") or []}
            if parsed.get("status") != "PASS" or got != set(ids):
                failure["COMPILER"] += 1
                failure_by_archetype[shapes.archetype(ids)] += 1
                continue
            compiled += 1
            gen = generator.generate(parsed["constraints"])
            candidates = list(gen.get("candidates") or [])
            candidate_hist[len(candidates)] += 1
            if not candidates:
                failure["NO_CANDIDATE"] += 1
                failure_by_archetype[shapes.archetype(ids)] += 1
                continue
            candidate_nonempty += 1

            best_true = -1
            passed = False
            for response in candidates:
                ok, true_n = _all_true(response, scorers)
                best_true = max(best_true, true_n)
                if ok:
                    passed = True
                    break
            if passed:
                full_pass += 1
            else:
                failure["EXACT_CHECKER_REJECT"] += 1
                failure_by_archetype[shapes.archetype(ids)] += 1

    result = {
        "schema": SCHEMA,
        "status": "PASS_AUDIT_COMPLETE" if total == 1856 else "FAIL_CLOSED_AUDIT_DOMAIN_DRIFT",
        "bindings": {
            "pinned_livebench_commit": PINNED,
            "active15_shape_source": shapes.SCHEMA,
            "candidate_generator": generator.SCHEMA,
            "visible_compiler": compiler.SCHEMA,
        },
        "domain": {
            "identity_shapes": len(compatible),
            "profiles_per_shape": len(profiles),
            "synthetic_cases": total,
            "active_terminal_cases_used": 0,
        },
        "results": {
            "compiler_exact_id_set_cases": compiled,
            "candidate_nonempty_cases": candidate_nonempty,
            "full_exact_checker_pass_cases": full_pass,
            "full_exact_checker_pass_fraction": full_pass / total if total else 0.0,
        },
        "failure_counts": dict(sorted(failure.items())),
        "failure_by_archetype": dict(sorted(failure_by_archetype.items())),
        "candidate_count_histogram": {str(k): v for k, v in sorted(candidate_hist.items())},
        "contamination_firewall": {
            "active_terminal_rows_read": 0,
            "active_terminal_prompt_text_read": False,
            "active_terminal_kwargs_read": False,
            "active_terminal_response_read": False,
            "synthetic_hidden_kwargs_used_only_by_verifier": True,
            "constructor_hidden_ids_used": False,
            "constructor_hidden_kwargs_used": False,
        },
        "hard_nonclaims": [
            "SYNTHETIC_PARAMETER_PROFILES_ARE_NOT_ACTIVE_TERMINAL_FREQUENCIES",
            "PASS_FRACTION_IS_A_CONSTRUCTOR_STRESS_METRIC_NOT_A_TERMINAL_SCORE",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()
    out = audit(Path(ns.livebench_root).resolve())
    Path(ns.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": out["status"],
        "synthetic_cases": out["domain"]["synthetic_cases"],
        "compiled": out["results"]["compiler_exact_id_set_cases"],
        "candidate_nonempty": out["results"]["candidate_nonempty_cases"],
        "full_exact_checker_pass": out["results"]["full_exact_checker_pass_cases"],
        "full_fraction": out["results"]["full_exact_checker_pass_fraction"],
        "failures": out["failure_counts"],
    }, sort_keys=True))
    return 0 if out["status"] == "PASS_AUDIT_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
