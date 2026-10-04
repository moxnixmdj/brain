#!/usr/bin/env python3
"""Exhaust the LiveBench active15 sentence/wrapper interaction seam.

The existing pointwise-envelope receipt exhausts every public sentence threshold,
but its sentence sweep does not jointly cross those thresholds with every fixed
END phrase, postscript marker, quote wrapper, maximum word-pressure carrier, and
maximum bullet/section carrier.

This verifier closes that seam without reading terminal rows. It executes the
canonical composer and pointwise planner against the exact frozen public
LiveBench checker classes for every generator-admitted combination below.

Scope:
- sentence relation: at least / less than
- sentence threshold: 1..20
- END: absent / both frozen phrases
- postscript: absent / P.S. / P.P.S
- quote: absent / present
- word pressure: absent / >=500 / <100
- structural pressure: bullets=5 + sections=5, both splitter spellings

The families are separated so the historical maximum of five instructions per
case is never exceeded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_contract_composer_v2 as composer
from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as pointwise

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_SENTENCE_WRAPPER_CLOSURE_V1"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED = {
    "livebench/if_runner/instruction_following_eval/instructions.py":
        "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "livebench/if_runner/instruction_following_eval/instructions_registry.py":
        "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "livebench/if_runner/instruction_following_eval/instructions_util.py":
        "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "livebench/if_runner/instruction_following_eval/evaluation_main.py":
        "4a341984936c4d609644a3b77f8c030ac5aa7269",
}
END_PHRASES = (
    None,
    "Any other questions?",
    "Is there anything else I can help with?",
)
POSTSCRIPTS = (None, "P.S.", "P.P.S")
SPLITTERS = ("Section", "SECTION")
EXPECTED_CASES = 2880


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _contract(iid: str, **slots: Any) -> dict[str, Any]:
    return {"instruction_id": iid, "slots": slots, "parameter_complete": True}


def _base_sentence(relation: str, threshold: int) -> list[dict[str, Any]]:
    return [_contract(
        composer.SENTENCES,
        num_sentences=threshold,
        relation=relation,
    )]


def _add_wrappers(
    contracts: list[dict[str, Any]],
    *,
    end_phrase: str | None,
    postscript: str | None,
    quote: bool,
) -> None:
    if end_phrase is not None:
        contracts.append(_contract(composer.END, end_phrase=end_phrase))
    if postscript is not None:
        contracts.append(_contract(composer.POSTSCRIPT, postscript_marker=postscript))
    if quote:
        contracts.append(_contract(composer.QUOTE))


def _strict_checker(
    registry: Any,
    contract: Mapping[str, Any],
    response: str,
) -> bool:
    # Frozen evaluation_main strict mode rejects empty/whitespace responses
    # before per-instruction credit. This is the exact gate relevant here.
    if not response.strip():
        return False
    iid = str(contract["instruction_id"])
    checker = registry.INSTRUCTION_DICT[iid](iid)
    checker.build_description(**dict(contract.get("slots") or {}))
    return bool(checker.check_following(response))


def _exact_flags(
    registry: Any,
    contracts: Sequence[Mapping[str, Any]],
    response: str,
) -> list[bool]:
    return [_strict_checker(registry, c, response) for c in contracts]


def _subject_blobs() -> dict[str, str]:
    paths = {
        "archetypes": Path(archetypes.__file__).resolve(),
        "composer": Path(composer.__file__).resolve(),
        "pointwise_planner": Path(pointwise.__file__).resolve(),
    }
    return {name: _git_blob_sha(path) for name, path in paths.items()}


def _bind_public_runtime(livebench_root: Path):
    head = subprocess.run(
        ["git", "-C", str(livebench_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != LIVEBENCH_COMMIT:
        raise RuntimeError("LIVEBENCH_COMMIT_DRIFT:" + head)

    for rel, expected in PINNED.items():
        path = livebench_root / rel
        if not path.is_file():
            raise RuntimeError("PINNED_SOURCE_MISSING:" + rel)
        got = _git_blob_sha(path)
        if got != expected:
            raise RuntimeError(f"PINNED_BLOB_DRIFT:{rel}:{got}")

    import nltk
    if nltk.__version__ != "3.10.3":
        raise RuntimeError("NLTK_VERSION_DRIFT:" + nltk.__version__)

    sys.path.insert(0, str(livebench_root / "livebench/if_runner"))
    from instruction_following_eval import instructions_registry
    return instructions_registry


def _check_case(
    *,
    name: str,
    contracts: list[dict[str, Any]],
    registry: Any,
    counters: dict[str, int],
    failures: list[dict[str, Any]],
) -> None:
    ids = tuple(str(c["instruction_id"]) for c in contracts)
    if len(ids) > archetypes.MAX_GENERATED_INSTRUCTIONS:
        raise RuntimeError("CASE_EXCEEDS_PUBLIC_MAX:" + name)
    if not archetypes.compatible(ids):
        raise RuntimeError("CASE_NOT_CONFLICT_COMPATIBLE:" + name)

    counters["cases"] += 1
    sentence = next(c for c in contracts if c["instruction_id"] == composer.SENTENCES)
    slots = dict(sentence["slots"])
    sentence_zero = (
        str(slots["relation"]) == "less than"
        and int(slots["num_sentences"]) == 1
    )

    built = composer.compose_contracts(contracts)
    expected_status = "PROVED_UNSAT" if sentence_zero else "CANDIDATE_WITNESS"
    if built.get("status") != expected_status:
        failures.append({
            "name": name,
            "kind": "COMPOSER_STATUS",
            "expected": expected_status,
            "observed": built,
        })
        return

    if sentence_zero:
        reasons = set(built.get("hard_unsat_reasons") or ())
        if "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE" not in reasons:
            failures.append({
                "name": name,
                "kind": "MISSING_SENTENCE_ZERO_CERTIFICATE",
                "observed": built,
            })
            return
        counters["proved_sentence_zero_unsat"] += 1
    else:
        response = str(built.get("response") or "")
        flags = _exact_flags(registry, contracts, response)
        if not all(flags):
            failures.append({
                "name": name,
                "kind": "COMPOSER_EXACT_CHECKER_FAILURE",
                "instruction_ids": list(ids),
                "checker_results": flags,
                "response": response,
            })
            return
        counters["composer_full_exact_pass"] += 1

    planned = pointwise.solve_contracts(contracts)
    if planned.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
        failures.append({
            "name": name,
            "kind": "POINTWISE_FAIL_CLOSED",
            "observed": planned,
        })
        return

    response = str(planned.get("response") or "")
    flags = _exact_flags(registry, contracts, response)
    exact_pass = sum(flags)
    theoretical = int(planned.get("theoretical_max_pass_count", -1))
    expected = len(contracts) - (1 if sentence_zero else 0)

    if theoretical != expected or exact_pass != theoretical:
        failures.append({
            "name": name,
            "kind": "POINTWISE_MAX_MISMATCH",
            "instruction_ids": list(ids),
            "checker_results": flags,
            "exact_pass_count": exact_pass,
            "theoretical_max_pass_count": theoretical,
            "expected_max_pass_count": expected,
            "sacrificed_instruction_ids": planned.get("sacrificed_instruction_ids"),
            "response": response,
        })
        return

    counters["pointwise_exact_max_match"] += 1


def audit(livebench_root: str | Path) -> dict[str, Any]:
    root = Path(livebench_root).resolve()
    registry = _bind_public_runtime(root)
    counters = {
        "cases": 0,
        "composer_full_exact_pass": 0,
        "proved_sentence_zero_unsat": 0,
        "pointwise_exact_max_match": 0,
        "wrapper_cases": 0,
        "word_pressure_cases": 0,
        "structure_pressure_cases": 0,
    }
    failures: list[dict[str, Any]] = []

    sentence_states = [
        (relation, n)
        for relation in ("at least", "less than")
        for n in range(1, 21)
    ]

    # Family 1: exact punctuation/wrapper cross-product.
    for relation, n in sentence_states:
        for end_phrase in END_PHRASES:
            for postscript in POSTSCRIPTS:
                for quote in (False, True):
                    contracts = _base_sentence(relation, n)
                    _add_wrappers(
                        contracts,
                        end_phrase=end_phrase,
                        postscript=postscript,
                        quote=quote,
                    )
                    _check_case(
                        name=f"wrapper:{relation}:{n}:{end_phrase}:{postscript}:{quote}",
                        contracts=contracts,
                        registry=registry,
                        counters=counters,
                        failures=failures,
                    )
                    counters["wrapper_cases"] += 1

    # Family 2: same wrapper seam under both extreme public word-pressure modes.
    for relation, n in sentence_states:
        for end_phrase in END_PHRASES:
            for postscript in POSTSCRIPTS:
                for quote in (False, True):
                    for word_relation, word_threshold in (
                        ("at least", 500),
                        ("less than", 100),
                    ):
                        contracts = _base_sentence(relation, n)
                        _add_wrappers(
                            contracts,
                            end_phrase=end_phrase,
                            postscript=postscript,
                            quote=quote,
                        )
                        contracts.append(_contract(
                            composer.WORDS,
                            num_words=word_threshold,
                            relation=word_relation,
                        ))
                        _check_case(
                            name=(
                                f"word:{relation}:{n}:{end_phrase}:{postscript}:{quote}:"
                                f"{word_relation}:{word_threshold}"
                            ),
                            contracts=contracts,
                            registry=registry,
                            counters=counters,
                            failures=failures,
                        )
                        counters["word_pressure_cases"] += 1

    # Family 3: punctuation seam under maximum bullet+section structural pressure.
    # Keep cardinality <=5 by omitting quote/word here.
    for relation, n in sentence_states:
        for end_phrase in END_PHRASES:
            for postscript in POSTSCRIPTS:
                for splitter in SPLITTERS:
                    contracts = _base_sentence(relation, n)
                    _add_wrappers(
                        contracts,
                        end_phrase=end_phrase,
                        postscript=postscript,
                        quote=False,
                    )
                    contracts.extend([
                        _contract(composer.BULLETS, num_bullets=5),
                        _contract(
                            composer.SECTIONS,
                            section_spliter=splitter,
                            num_sections=5,
                        ),
                    ])
                    _check_case(
                        name=f"struct:{relation}:{n}:{end_phrase}:{postscript}:{splitter}",
                        contracts=contracts,
                        registry=registry,
                        counters=counters,
                        failures=failures,
                    )
                    counters["structure_pressure_cases"] += 1

    if counters["cases"] != EXPECTED_CASES:
        raise RuntimeError(
            f"CASE_COUNT_DRIFT:{counters['cases']}!=EXPECTED:{EXPECTED_CASES}"
        )

    status = (
        "PASS__2880_SENTENCE_WRAPPER_CASES_EXACT_POINTWISE_CLOSED"
        if not failures and counters["pointwise_exact_max_match"] == EXPECTED_CASES
        else "FAIL_CLOSED__SENTENCE_WRAPPER_COUNTEREXAMPLE_FOUND"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "subject_blobs": _subject_blobs(),
        "pinned_public_semantics": {
            "livebench_commit": LIVEBENCH_COMMIT,
            "source_blobs": dict(PINNED),
            "nltk_version": "3.10.3",
        },
        "coverage": counters,
        "failure_count": len(failures),
        "failures": failures[:100],
        "theorem_if_pass": (
            "WITHIN_THE_FROZEN_PUBLIC_ACTIVE15_DOMAIN_THE_CANONICAL_COMPOSER_AND_"
            "POINTWISE_PLANNER_REMAIN_EXACT_ACROSS_EVERY_PUBLIC_SENTENCE_THRESHOLD_"
            "WHEN_CROSSED_WITH_ALL_FIXED_END_POSTSCRIPT_QUOTE_WRAPPERS_AND_THE_"
            "SELECTED_MAXIMAL_WORD_OR_BULLET_SECTION_PRESSURE_CARRIERS"
        ),
        "remaining_nonclaim": (
            "THIS_CLOSES_THE_PREVIOUS_SENTENCE_WRAPPER_CROSS_SEAM_BUT_DOES_NOT_BY_"
            "ITSELF_PROVE_THE_FULL_GENERATOR_CARTESIAN_QUOTIENT"
        ),
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()

    result = audit(ns.livebench_root)
    Path(ns.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "coverage": result["coverage"],
        "failure_count": result["failure_count"],
    }, sort_keys=True))
    return 0 if result["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())
