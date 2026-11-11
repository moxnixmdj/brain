#!/usr/bin/env python3
"""Exact NTH x dual-loss interaction closure for frozen LiveBench active15.

This is a zero-terminal-data falsifier for the sharpest remaining composition seam:
NTH-paragraph structure crossed with sentence construction and the shared
FORBIDDEN collision coordinate.

It composes:
- all 15 public (num_paragraphs, nth_paragraph) positions,
- the four precommitted sentence quotient representatives,
- all 192 exact reachable lexical signatures,
- eight one-slot pressure modes,
for 92,160 exact generator-admitted cases.

Every case is solved by the current canonical pointwise planner and then checked
with the exact frozen public LiveBench checker classes.  The expected minimum
sacrifice set is fixed before execution:
- number_sentences only for strict "less than 1";
- forbidden_words iff NTH or mandatory END collides with a forbidden word.

No terminal row, terminal kwargs, terminal instruction list, response, score,
frequency, or comparator output is read.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_contract_composer_v2 as composer
from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as lexical
from canonical.runtime import livebench_legacy15_numeric_quotient_v1 as numeric
from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as pointwise
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_NTH_DUAL_LOSS_CLOSURE_V1"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PRECOMMIT = (
    "canonical/governance/"
    "LIVEBENCH_NTH_DUAL_LOSS_CLOSURE_PRECOMMIT_20261005_V1.json"
)

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

SENTENCE_REPRESENTATIVES = (
    ("less than", 1, "LESS_THAN_1"),
    ("less than", 2, "LESS_THAN_2_TO_20_TIGHT_BOUNDARY"),
    ("at least", 1, "AT_LEAST_1_LOW_BOUNDARY"),
    ("at least", 20, "AT_LEAST_1_TO_20_HIGH_BOUNDARY"),
)

PRESSURE_MODES = (
    "NONE",
    "POSTSCRIPT_P_S",
    "POSTSCRIPT_P_P_S",
    "WORDS_LT_100",
    "WORDS_GE_500",
    "TITLE",
    "QUOTATION",
    "EXISTENCE_FULL_FORBIDDEN_OVERLAP",
)

EXPECTED_NTH_POSITIONS = 15
EXPECTED_LEXICAL_SIGNATURES = 192
EXPECTED_CASES = (
    EXPECTED_NTH_POSITIONS
    * len(SENTENCE_REPRESENTATIVES)
    * EXPECTED_LEXICAL_SIGNATURES
    * len(PRESSURE_MODES)
)
MAX_RETAINED_FAILURES = 100


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _contract(iid: str, **slots: Any) -> dict[str, Any]:
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def _nth_positions():
    for count in range(1, 6):
        for nth in range(1, count + 1):
            yield count, nth


def _expected_sacrifices(
    sig: lexical.LexicalSignature,
    relation: str,
    threshold: int,
) -> tuple[str, ...]:
    dropped: list[str] = []
    if relation == "less than" and threshold == 1:
        dropped.append(composer.SENTENCES)
    if lexical.predicted_hard_collisions(sig):
        dropped.append(composer.FORBIDDEN)
    return tuple(sorted(dropped))


def _contracts(
    *,
    paragraph_count: int,
    nth_position: int,
    relation: str,
    threshold: int,
    sig: lexical.LexicalSignature,
    pressure: str,
) -> list[dict[str, Any]]:
    slots = lexical.representative_slots(sig)
    forbidden = list(slots[composer.FORBIDDEN]["forbidden_words"])

    out = [
        _contract(
            composer.NTH,
            num_paragraphs=paragraph_count,
            nth_paragraph=nth_position,
            first_word=slots[composer.NTH]["first_word"],
        ),
        _contract(
            composer.SENTENCES,
            num_sentences=threshold,
            relation=relation,
        ),
        _contract(
            composer.FORBIDDEN,
            forbidden_words=forbidden,
        ),
        _contract(
            composer.END,
            end_phrase=slots[composer.END]["end_phrase"],
        ),
    ]

    if pressure == "NONE":
        pass
    elif pressure == "POSTSCRIPT_P_S":
        out.append(_contract(composer.POSTSCRIPT, postscript_marker="P.S."))
    elif pressure == "POSTSCRIPT_P_P_S":
        out.append(_contract(composer.POSTSCRIPT, postscript_marker="P.P.S"))
    elif pressure == "WORDS_LT_100":
        out.append(_contract(composer.WORDS, num_words=100, relation="less than"))
    elif pressure == "WORDS_GE_500":
        out.append(_contract(composer.WORDS, num_words=500, relation="at least"))
    elif pressure == "TITLE":
        out.append(_contract(composer.TITLE))
    elif pressure == "QUOTATION":
        out.append(_contract(composer.QUOTE))
    elif pressure == "EXISTENCE_FULL_FORBIDDEN_OVERLAP":
        # Strong boundary-shield stress case.  Every required keyword is also
        # forbidden, which remains satisfiable because existence is substring
        # matching while forbidden_words uses whole-word boundaries.
        out.append(_contract(composer.EXIST, keywords=forbidden))
    else:
        raise AssertionError("UNKNOWN_PRESSURE_MODE:" + pressure)

    ids = tuple(str(c["instruction_id"]) for c in out)
    if len(ids) > archetypes.MAX_GENERATED_INSTRUCTIONS:
        raise AssertionError("PUBLIC_MAX_INSTRUCTION_COUNT_EXCEEDED")
    if not archetypes.compatible(ids):
        raise AssertionError("NON_GENERATOR_ADMITTED_ID_SET:" + repr(ids))
    return out


def _strict_checker(
    registry: Any,
    contract: Mapping[str, Any],
    response: str,
) -> tuple[bool, str | None]:
    # Exact outer strict gate in frozen evaluation_main semantics.
    if not response.strip():
        return False, None
    iid = str(contract["instruction_id"])
    checker = registry.INSTRUCTION_DICT[iid](iid)
    try:
        checker.build_description(**dict(contract.get("slots") or {}))
        return bool(checker.check_following(response)), None
    except Exception as exc:
        return False, type(exc).__name__ + ":" + str(exc)


def _exact_vector(
    registry: Any,
    contracts: Sequence[Mapping[str, Any]],
    response: str,
) -> tuple[list[bool], list[str | None]]:
    flags: list[bool] = []
    errors: list[str | None] = []
    for contract in contracts:
        ok, error = _strict_checker(registry, contract, response)
        flags.append(ok)
        errors.append(error)
    return flags, errors


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


def _subject_blobs() -> dict[str, str]:
    root = _repo_root()
    paths = {
        "precommit": root / PRECOMMIT,
        "archetypes": Path(archetypes.__file__).resolve(),
        "composer": Path(composer.__file__).resolve(),
        "lexical_quotient": Path(lexical.__file__).resolve(),
        "numeric_quotient": Path(numeric.__file__).resolve(),
        "pointwise_planner": Path(pointwise.__file__).resolve(),
        "feasibility": Path(feasibility.__file__).resolve(),
    }
    return {name: _git_blob_sha(path) for name, path in paths.items()}


def _record_failure(
    failures: list[dict[str, Any]],
    counters: Counter,
    payload: dict[str, Any],
) -> None:
    counters["failures"] += 1
    if len(failures) < MAX_RETAINED_FAILURES:
        failures.append(payload)


def audit(livebench_root: str | Path) -> dict[str, Any]:
    root = Path(livebench_root).resolve()
    registry = _bind_public_runtime(root)

    lexical_receipt = lexical.verify()
    numeric_receipt = numeric.verify()
    if lexical_receipt["exact_reachable_signature_count"] != EXPECTED_LEXICAL_SIGNATURES:
        raise RuntimeError("LEXICAL_QUOTIENT_DRIFT")
    if numeric_receipt["status"] != "PASS__PARAMETRIC_NUMERIC_REDUCTION":
        raise RuntimeError("NUMERIC_QUOTIENT_NOT_PASS")
    if numeric_receipt["word_upper_bound"]["minimum_safety_margin"] != 52:
        raise RuntimeError("WORD_UPPER_BOUND_MARGIN_DRIFT")

    positions = tuple(_nth_positions())
    signatures = lexical.enumerate_signatures()
    if len(positions) != EXPECTED_NTH_POSITIONS:
        raise RuntimeError("NTH_POSITION_COUNT_DRIFT")
    if len(signatures) != EXPECTED_LEXICAL_SIGNATURES:
        raise RuntimeError("LEXICAL_SIGNATURE_COUNT_DRIFT")

    counters: Counter = Counter()
    pressure_counts: dict[str, Counter] = {
        pressure: Counter() for pressure in PRESSURE_MODES
    }
    sentence_counts: dict[str, Counter] = {
        name: Counter() for _, _, name in SENTENCE_REPRESENTATIVES
    }
    loss_histogram: Counter = Counter()
    failures: list[dict[str, Any]] = []

    for paragraph_count, nth_position in positions:
        for relation, threshold, sentence_class in SENTENCE_REPRESENTATIVES:
            for sig in signatures:
                expected_sacrifices = _expected_sacrifices(
                    sig,
                    relation,
                    threshold,
                )
                for pressure in PRESSURE_MODES:
                    counters["cases"] += 1
                    pressure_counts[pressure]["cases"] += 1
                    sentence_counts[sentence_class]["cases"] += 1
                    loss_histogram[len(expected_sacrifices)] += 1

                    contracts = _contracts(
                        paragraph_count=paragraph_count,
                        nth_position=nth_position,
                        relation=relation,
                        threshold=threshold,
                        sig=sig,
                        pressure=pressure,
                    )
                    ids = [str(c["instruction_id"]) for c in contracts]
                    expected_unsat = bool(expected_sacrifices)

                    direct = composer.compose_contracts(contracts)
                    wanted_direct = (
                        "PROVED_UNSAT" if expected_unsat else "CANDIDATE_WITNESS"
                    )
                    if direct.get("status") != wanted_direct:
                        _record_failure(
                            failures,
                            counters,
                            {
                                "kind": "DIRECT_COMPOSER_STATUS_MISMATCH",
                                "paragraph_count": paragraph_count,
                                "nth_position": nth_position,
                                "sentence_class": sentence_class,
                                "pressure": pressure,
                                "lexical_signature": vars(sig),
                                "instruction_ids": ids,
                                "expected_status": wanted_direct,
                                "observed": direct,
                            },
                        )
                        continue

                    if expected_unsat:
                        reasons = tuple(direct.get("hard_unsat_reasons") or ())
                        actual_from_reasons = tuple(
                            sorted(pointwise._sacrifice_ids(reasons))
                        )
                        if actual_from_reasons != expected_sacrifices:
                            _record_failure(
                                failures,
                                counters,
                                {
                                    "kind": "UNSAT_REASON_MINIMUM_CUT_MISMATCH",
                                    "paragraph_count": paragraph_count,
                                    "nth_position": nth_position,
                                    "sentence_class": sentence_class,
                                    "pressure": pressure,
                                    "lexical_signature": vars(sig),
                                    "instruction_ids": ids,
                                    "reasons": list(reasons),
                                    "expected_sacrifices": list(expected_sacrifices),
                                    "actual_sacrifices": list(actual_from_reasons),
                                },
                            )
                            continue
                    else:
                        response = str(direct.get("response") or "")
                        flags, errors = _exact_vector(registry, contracts, response)
                        if not all(flags):
                            _record_failure(
                                failures,
                                counters,
                                {
                                    "kind": "DIRECT_COMPOSER_EXACT_FAILURE",
                                    "paragraph_count": paragraph_count,
                                    "nth_position": nth_position,
                                    "sentence_class": sentence_class,
                                    "pressure": pressure,
                                    "lexical_signature": vars(sig),
                                    "instruction_ids": ids,
                                    "checker_results": flags,
                                    "checker_errors": errors,
                                    "response": response,
                                },
                            )
                            continue
                        counters["direct_exact_full_pass"] += 1
                        pressure_counts[pressure]["direct_exact_full_pass"] += 1
                        sentence_counts[sentence_class]["direct_exact_full_pass"] += 1

                    planned = pointwise.solve_contracts(contracts)
                    if planned.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
                        _record_failure(
                            failures,
                            counters,
                            {
                                "kind": "POINTWISE_FAIL_CLOSED",
                                "paragraph_count": paragraph_count,
                                "nth_position": nth_position,
                                "sentence_class": sentence_class,
                                "pressure": pressure,
                                "lexical_signature": vars(sig),
                                "instruction_ids": ids,
                                "expected_sacrifices": list(expected_sacrifices),
                                "observed": planned,
                            },
                        )
                        continue

                    actual_sacrifices = tuple(
                        sorted(planned.get("sacrificed_instruction_ids") or ())
                    )
                    if actual_sacrifices != expected_sacrifices:
                        _record_failure(
                            failures,
                            counters,
                            {
                                "kind": "PLANNER_SACRIFICE_SET_MISMATCH",
                                "paragraph_count": paragraph_count,
                                "nth_position": nth_position,
                                "sentence_class": sentence_class,
                                "pressure": pressure,
                                "lexical_signature": vars(sig),
                                "instruction_ids": ids,
                                "expected_sacrifices": list(expected_sacrifices),
                                "actual_sacrifices": list(actual_sacrifices),
                                "observed": planned,
                            },
                        )
                        continue

                    response = str(planned.get("response") or "")
                    flags, errors = _exact_vector(registry, contracts, response)
                    exact_pass = sum(bool(x) for x in flags)
                    theoretical = int(
                        planned.get("theoretical_max_pass_count", -1)
                    )
                    expected_max = len(contracts) - len(expected_sacrifices)

                    if (
                        theoretical != expected_max
                        or exact_pass != expected_max
                        or exact_pass != theoretical
                    ):
                        _record_failure(
                            failures,
                            counters,
                            {
                                "kind": "EXACT_POINTWISE_MAX_MISMATCH",
                                "paragraph_count": paragraph_count,
                                "nth_position": nth_position,
                                "sentence_class": sentence_class,
                                "pressure": pressure,
                                "lexical_signature": vars(sig),
                                "instruction_ids": ids,
                                "expected_sacrifices": list(expected_sacrifices),
                                "checker_results": flags,
                                "checker_errors": errors,
                                "exact_pass_count": exact_pass,
                                "theoretical_max_pass_count": theoretical,
                                "expected_max_pass_count": expected_max,
                                "response": response,
                            },
                        )
                        continue

                    exact_score = pointwise.strict_score_from_pass_count(
                        len(contracts),
                        exact_pass,
                    )
                    planned_score = float(
                        planned["theoretical_pointwise_optimum_strict_score"]
                    )
                    if abs(exact_score - planned_score) > 1e-15:
                        _record_failure(
                            failures,
                            counters,
                            {
                                "kind": "STRICT_SCORE_MISMATCH",
                                "paragraph_count": paragraph_count,
                                "nth_position": nth_position,
                                "sentence_class": sentence_class,
                                "pressure": pressure,
                                "lexical_signature": vars(sig),
                                "instruction_ids": ids,
                                "exact_score": exact_score,
                                "planned_score": planned_score,
                            },
                        )
                        continue

                    counters["pointwise_exact_max_match"] += 1
                    pressure_counts[pressure]["pointwise_exact_max_match"] += 1
                    sentence_counts[sentence_class]["pointwise_exact_max_match"] += 1

    if counters["cases"] != EXPECTED_CASES:
        raise RuntimeError(
            f"CASE_COUNT_DRIFT:{counters['cases']}!=EXPECTED:{EXPECTED_CASES}"
        )

    failure_count = int(counters["failures"])
    status = (
        "PASS__92160_NTH_DUAL_LOSS_QUOTIENT_CASES_EXACT_POINTWISE_CLOSED"
        if failure_count == 0
        and counters["pointwise_exact_max_match"] == EXPECTED_CASES
        else "FAIL_CLOSED__NTH_DUAL_LOSS_COUNTEREXAMPLE_FOUND"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "subject_blobs": _subject_blobs(),
        "pinned_public_semantics": {
            "livebench_commit": LIVEBENCH_COMMIT,
            "source_blobs": dict(PINNED),
            "python": ".".join(map(str, sys.version_info[:3])),
            "nltk": "3.10.3",
        },
        "quotient_basis": {
            "nth_positions": len(positions),
            "sentence_representatives": [
                {
                    "relation": relation,
                    "threshold": threshold,
                    "class": name,
                }
                for relation, threshold, name in SENTENCE_REPRESENTATIVES
            ],
            "reachable_lexical_signatures": len(signatures),
            "pressure_modes": list(PRESSURE_MODES),
            "expected_cases": EXPECTED_CASES,
            "numeric_quotient_status": numeric_receipt["status"],
            "word_upper_bound_safety_margin": numeric_receipt[
                "word_upper_bound"
            ]["minimum_safety_margin"],
        },
        "coverage": {
            "cases": int(counters["cases"]),
            "direct_exact_full_pass": int(counters["direct_exact_full_pass"]),
            "pointwise_exact_max_match": int(
                counters["pointwise_exact_max_match"]
            ),
            "loss_histogram": {
                str(k): int(v) for k, v in sorted(loss_histogram.items())
            },
            "by_pressure": {
                k: {kk: int(vv) for kk, vv in v.items()}
                for k, v in pressure_counts.items()
            },
            "by_sentence_class": {
                k: {kk: int(vv) for kk, vv in v.items()}
                for k, v in sentence_counts.items()
            },
        },
        "failure_count": failure_count,
        "failures_retained": failures,
        "theorem_if_pass": (
            "ON_THE_PRECOMMITTED_EXACT_NTH_DUAL_LOSS_QUOTIENT_BASIS__"
            "THE_CANONICAL_POINTWISE_PLANNER_ATTAINS_THE_EXACT_STRICT_CHECKER_"
            "MAXIMUM_FOR_EVERY_CASE__INCLUDING_SIMULTANEOUS_SENTENCE_ZERO_AND_"
            "FORBIDDEN_COLLISION_LOSSES__UNDER_ALL_EIGHT_PRESSURE_MODES"
        ),
        "remaining_nonclaim": (
            "THIS_CLOSES_THE_NTH_DUAL_LOSS_INTERACTION_SEAM_ONLY__A_SEPARATE_"
            "CONTENT_BOUND_VERIFICATION_AND_WIDER_FACTOR_COMPLETENESS_REDUCTION_"
            "ARE_REQUIRED_BEFORE_LIVEBENCH_ACCEPTANCE"
        ),
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "terminal_responses_read": 0,
        "target_scores_read": 0,
        "target_frequencies_read": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--livebench-root", required=True)
    parser.add_argument("--output", required=True)
    ns = parser.parse_args()

    result = audit(ns.livebench_root)
    Path(ns.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "status": result["status"],
            "cases": result["coverage"]["cases"],
            "pointwise_exact_max_match":
                result["coverage"]["pointwise_exact_max_match"],
            "failure_count": result["failure_count"],
        },
        sort_keys=True,
    ))
    return 0 if result["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())
