#!/usr/bin/env python3
"""Exact frozen-checker synthetic audit for the active legacy15 joint witness.

The audit never reads the frozen terminal dataset. It exhaustively enumerates all
928 conflict-compatible active-ID sets reachable at historical generator
cardinality <=5, renders public checker descriptions with deterministic public
kwargs, gives only the resulting visible prompt to the joint witness solver, and
then postvalidates the response with the exact pinned legacy checker classes.

Two parameter profiles exercise both relational branches plus alternate
paragraph/section/bullet/postscript/end values. A third overlap profile is added
when keyword existence and forbidden-words coexist, exercising the scorer's
substring-vs-whole-word semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from collections import Counter
from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as shapes
from canonical.runtime import livebench_legacy15_joint_witness_v1 as witness

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_JOINT_WITNESS_EXACT_SYNTHETIC_AUDIT_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
REPEAT_MARKER = "First repeat the request word for word without change,"


def _profile(name: str) -> dict[str, dict[str, Any]]:
    if name == "A":
        return {
            "keywords:existence": {"keywords": ["alpha", "beta"]},
            "keywords:forbidden_words": {"forbidden_words": ["omega", "delta"]},
            "length_constraints:number_paragraphs": {"num_paragraphs": 2},
            "length_constraints:number_words": {"num_words": 80, "relation": "at least"},
            "length_constraints:number_sentences": {"num_sentences": 3, "relation": "at least"},
            "length_constraints:nth_paragraph_first_word": {
                "num_paragraphs": 2,
                "nth_paragraph": 2,
                "first_word": "anchor",
            },
            "detectable_content:postscript": {"postscript_marker": "P.S."},
            "detectable_format:number_bullet_lists": {"num_bullets": 2},
            "detectable_format:multiple_sections": {
                "section_spliter": "Section",
                "num_sections": 2,
            },
            "startend:end_checker": {"end_phrase": "Any other questions?"},
        }
    if name == "B":
        return {
            "keywords:existence": {"keywords": ["cedar", "river"]},
            "keywords:forbidden_words": {"forbidden_words": ["violet", "quartz"]},
            "length_constraints:number_paragraphs": {"num_paragraphs": 3},
            "length_constraints:number_words": {"num_words": 300, "relation": "less than"},
            "length_constraints:number_sentences": {"num_sentences": 10, "relation": "less than"},
            "length_constraints:nth_paragraph_first_word": {
                "num_paragraphs": 3,
                "nth_paragraph": 1,
                "first_word": "anchor",
            },
            "detectable_content:postscript": {"postscript_marker": "P.P.S"},
            "detectable_format:number_bullet_lists": {"num_bullets": 3},
            "detectable_format:multiple_sections": {
                "section_spliter": "SECTION",
                "num_sections": 3,
            },
            "startend:end_checker": {
                "end_phrase": "Is there anything else I can help with?"
            },
        }
    if name == "OVERLAP":
        p = _profile("A")
        p["keywords:existence"] = {"keywords": ["cat"]}
        p["keywords:forbidden_words"] = {"forbidden_words": ["cat"]}
        return p
    raise ValueError("UNKNOWN_PROFILE:" + name)


STATIC_IDS = {
    "detectable_format:title",
    "detectable_format:json_format",
    "combination:two_responses",
    "combination:repeat_prompt",
    "startend:quotation",
}


def _profiles_for(ids: tuple[str, ...]) -> tuple[str, ...]:
    out = ["A", "B"]
    s = set(ids)
    if {"keywords:existence", "keywords:forbidden_words"} <= s:
        out.append("OVERLAP")
    return tuple(out)


def _install_frozen_import(livebench_root: Path):
    scorer_parent = livebench_root / "livebench" / "if_runner"
    if not scorer_parent.is_dir():
        raise RuntimeError("LIVEBENCH_IF_RUNNER_NOT_FOUND:" + str(scorer_parent))
    sys.path.insert(0, str(scorer_parent))
    from instruction_following_eval import instructions_registry  # type: ignore
    return instructions_registry


def _render_case(registry, ids: tuple[str, ...], profile_name: str):
    profile = _profile(profile_name)
    checkers: list[tuple[str, Any]] = []
    descriptions: list[str] = []

    for iid in ids:
        cls = registry.INSTRUCTION_DICT[iid]
        checker = cls(iid)
        kwargs = dict(profile.get(iid) or {})
        if iid in STATIC_IDS:
            description = checker.build_description()
        else:
            description = checker.build_description(**kwargs)
        descriptions.append(description)
        checkers.append((iid, checker))

    prompt = "Synthetic public audit task. " + " ".join(descriptions)

    if "combination:repeat_prompt" in ids:
        prefix = prompt.split(REPEAT_MARKER, 1)[0]
        replacement = registry.INSTRUCTION_DICT["combination:repeat_prompt"](
            "combination:repeat_prompt"
        )
        replacement.build_description(prompt_to_repeat=prefix)
        checkers = [
            (iid, replacement if iid == "combination:repeat_prompt" else checker)
            for iid, checker in checkers
        ]

    return prompt, checkers


def _case_id(ids: tuple[str, ...], profile_name: str, prompt: str) -> str:
    raw = json.dumps(
        {"ids": list(ids), "profile": profile_name, "prompt": prompt},
        ensure_ascii=False,
        sort_keys=True,
    ).encode()
    return hashlib.sha256(raw).hexdigest()[:20]


def run_audit(livebench_root: Path) -> dict[str, Any]:
    registry = _install_frozen_import(livebench_root)
    id_sets = shapes.enumerate_compatible_sets()
    if len(id_sets) != 928:
        raise RuntimeError("IDENTITY_SET_COUNT_DRIFT")

    attempted = 0
    passed = 0
    unique_prompts: set[str] = set()
    failures: list[dict[str, Any]] = []
    failure_kinds: Counter[str] = Counter()
    archetype_attempts: Counter[str] = Counter()
    archetype_passes: Counter[str] = Counter()

    for ids in id_sets:
        arch = shapes.archetype(ids)
        seen_prompts_for_set: set[str] = set()
        for profile_name in _profiles_for(ids):
            try:
                prompt, checkers = _render_case(registry, ids, profile_name)
            except Exception as exc:
                failure_kinds["RENDER_EXCEPTION"] += 1
                failures.append({
                    "ids": list(ids),
                    "profile": profile_name,
                    "kind": "RENDER_EXCEPTION",
                    "error": f"{type(exc).__name__}:{exc}",
                })
                continue

            # Static-only sets can render identically under A/B. Do not count
            # duplicate prompts as independent audit evidence.
            ph = hashlib.sha256(prompt.encode()).hexdigest()
            if ph in seen_prompts_for_set:
                continue
            seen_prompts_for_set.add(ph)
            unique_prompts.add(ph)

            attempted += 1
            archetype_attempts[arch] += 1
            cid = _case_id(ids, profile_name, prompt)

            try:
                solved = witness.solve(prompt)
            except Exception as exc:
                failure_kinds["SOLVER_EXCEPTION"] += 1
                failures.append({
                    "case_id": cid,
                    "ids": list(ids),
                    "profile": profile_name,
                    "kind": "SOLVER_EXCEPTION",
                    "error": f"{type(exc).__name__}:{exc}",
                })
                continue

            if solved.get("status") != "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS":
                failure_kinds["SOLVER_FAIL_CLOSED"] += 1
                failures.append({
                    "case_id": cid,
                    "ids": list(ids),
                    "profile": profile_name,
                    "kind": "SOLVER_FAIL_CLOSED",
                    "error": solved.get("error"),
                })
                continue

            response = str(solved.get("response") or "")
            checker_results: dict[str, bool] = {}
            checker_error = None
            for iid, checker in checkers:
                try:
                    checker_results[iid] = bool(checker.check_following(response))
                except Exception as exc:
                    checker_results[iid] = False
                    checker_error = f"{iid}:{type(exc).__name__}:{exc}"

            if checker_results and all(checker_results.values()):
                passed += 1
                archetype_passes[arch] += 1
            else:
                failure_kinds["EXACT_CHECKER_REJECT"] += 1
                failures.append({
                    "case_id": cid,
                    "ids": list(ids),
                    "profile": profile_name,
                    "kind": "EXACT_CHECKER_REJECT",
                    "failed_checkers": sorted(
                        iid for iid, ok in checker_results.items() if not ok
                    ),
                    "checker_error": checker_error,
                    "response_sha256": hashlib.sha256(response.encode()).hexdigest(),
                })

    status = (
        "PASS__ALL_PUBLIC_SYNTHETIC_COMPOSITIONS_EXACT_CHECKER_VALIDATED"
        if attempted > 0 and passed == attempted and not failures
        else "FAIL_CLOSED__JOINT_WITNESS_RESIDUALS_FOUND"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "identity_set_count": len(id_sets),
        "audit_case_count": attempted,
        "audit_case_pass_count": passed,
        "audit_case_fail_count": attempted - passed,
        "unique_visible_prompt_count": len(unique_prompts),
        "archetype_attempts": dict(sorted(archetype_attempts.items())),
        "archetype_passes": dict(sorted(archetype_passes.items())),
        "failure_kinds": dict(sorted(failure_kinds.items())),
        "failure_examples": failures[:100],
        "failure_examples_truncated": len(failures) > 100,
        "terminal_dataset_read": False,
        "terminal_prompt_read": False,
        "terminal_kwargs_read": False,
        "terminal_case_metadata_read": False,
        "terminal_case_count_exposed": 0,
        "model_dependency_count": 0,
        "acceptance_credit": 0,
        "capability_credit": 0,
        "hard_nonclaim": (
            "PUBLIC_SYNTHETIC_CHECKER_VALIDATION_IS_NOT_A_TERMINAL_SCORE;"
            "IT_VALIDATES_CONSTRUCTIVE_GRAMMAR_ONLY"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()

    out = run_audit(Path(ns.livebench_root))
    dst = Path(ns.output)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())
