#!/usr/bin/env python3
"""Exact frozen-checker synthetic audit for the active legacy-15 LiveBench lane.

This audit is deliberately nonterminal:
- it never reads frozen terminal prompts, kwargs, responses, ids, or scores;
- it uses only the already-opened active-15 identity commitment;
- it generates synthetic visible prompts from the exact pinned public checker
  build_description() methods;
- it compiles those visible prompts with Brain's public visible compiler;
- it asks the bounded joint candidate generator for candidates; and
- it accepts a synthetic case only when the exact pinned checker classes all
  return True for the same candidate.

The finite composition claim is exhaustive over the nine already-derived
maximal independent modes. Parameter values are synthetic representatives, not
a claim of exhaustive parameter-space coverage or terminal score.
"""
from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import sys
from typing import Any

from canonical.runtime import livebench_frozen_active_legacy15_v1 as active
from canonical.runtime import livebench_legacy15_composition_partition_v1 as partition
from canonical.runtime import livebench_legacy15_joint_candidate_generator_v1 as generator
from canonical.runtime import livebench_legacy_visible_constraint_compiler_v2 as compiler

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_EXACT_SYNTHETIC_AUDIT_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

SYNTHETIC_KWARGS: dict[str, dict[str, Any]] = {
    "keywords:existence": {"keywords": ["alpha", "cobalt"]},
    "keywords:forbidden_words": {"forbidden_words": ["omega", "dog"]},
    "length_constraints:number_paragraphs": {"num_paragraphs": 3},
    "length_constraints:number_words": {"num_words": 40, "relation": "at least"},
    "length_constraints:number_sentences": {"num_sentences": 3, "relation": "at least"},
    "length_constraints:nth_paragraph_first_word": {
        "num_paragraphs": 3,
        "nth_paragraph": 2,
        "first_word": "anchor",
    },
    "detectable_content:postscript": {"postscript_marker": "P.S."},
    "detectable_format:number_bullet_lists": {"num_bullets": 3},
    "detectable_format:title": {},
    "detectable_format:multiple_sections": {
        "num_sections": 2,
        "section_spliter": "SECTION",
    },
    "detectable_format:json_format": {},
    "combination:repeat_prompt": {},
    "combination:two_responses": {},
    "startend:end_checker": {"end_phrase": "Any other questions?"},
    "startend:quotation": {},
}

BASE_REQUEST = "Write a brief response about a lighthouse."


class AuditFailure(RuntimeError):
    pass


def _load_frozen_registry(livebench_root: pathlib.Path):
    pkg_parent = livebench_root / "livebench" / "if_runner"
    pkg = pkg_parent / "instruction_following_eval"
    if not (pkg / "instructions_registry.py").is_file():
        raise AuditFailure("FROZEN_REGISTRY_NOT_FOUND:" + str(pkg))
    sys.path.insert(0, str(pkg_parent))
    try:
        return importlib.import_module("instruction_following_eval.instructions_registry")
    except Exception as exc:
        raise AuditFailure(
            "FROZEN_REGISTRY_IMPORT_FAILED:"
            + type(exc).__name__
            + ":"
            + str(exc)
        ) from exc


def _description(registry, iid: str, kwargs: dict[str, Any]) -> str:
    cls = registry.INSTRUCTION_DICT[iid]
    inst = cls(iid)
    return str(inst.build_description(**kwargs))


def _render_synthetic_prompt(registry, mode: frozenset[str]) -> tuple[str, dict[str, dict[str, Any]]]:
    if not mode <= set(SYNTHETIC_KWARGS):
        raise AuditFailure("SYNTHETIC_KWARGS_MISSING:" + ",".join(sorted(mode - set(SYNTHETIC_KWARGS))))

    # Keep repeat_prompt last. Its exact historical argument is the entire
    # visible prefix before its own marker, which the V2 compiler recovers.
    ordered = sorted(x for x in mode if x != "combination:repeat_prompt")
    pieces = [BASE_REQUEST]
    source_kwargs: dict[str, dict[str, Any]] = {}

    for iid in ordered:
        kwargs = dict(SYNTHETIC_KWARGS[iid])
        pieces.append(_description(registry, iid, kwargs))
        source_kwargs[iid] = kwargs

    if "combination:repeat_prompt" in mode:
        prompt_to_repeat = " ".join(pieces).strip()
        kwargs = {"prompt_to_repeat": prompt_to_repeat}
        pieces.append(_description(registry, "combination:repeat_prompt", kwargs))
        source_kwargs["combination:repeat_prompt"] = kwargs

    return " ".join(pieces).strip(), source_kwargs


def _exact_checker_truth(registry, iid: str, slots: dict[str, Any], prompt: str, response: str) -> bool:
    cls = registry.INSTRUCTION_DICT[iid]
    inst = cls(iid)
    kwargs = dict(slots or {})
    # language compiler carries a display-only language_name, though language is
    # not in active15. Keep this adapter generic and fail closed if it ever
    # appears.
    kwargs.pop("language_name", None)
    inst.build_description(**kwargs)
    args = inst.get_instruction_args()
    # Mirror the pinned evaluator's prompt rebinding rule exactly.
    if args and "prompt" in args:
        inst.build_description(prompt=prompt)
    return bool(response.strip() and inst.check_following(response))


def _audit_mode(registry, mode_index: int, mode: frozenset[str]) -> dict[str, Any]:
    if not partition.is_valid(mode):
        raise AuditFailure(f"MODE_{mode_index}_INVALID")
    prompt, source_kwargs = _render_synthetic_prompt(registry, mode)
    parsed = compiler.compile_visible_constraints(prompt)
    parsed_ids = [x["instruction_id"] for x in parsed.get("constraints") or []]
    if parsed.get("status") != "PASS":
        raise AuditFailure(f"MODE_{mode_index}_VISIBLE_COMPILER_FAIL:{parsed}")
    if set(parsed_ids) != set(mode) or len(parsed_ids) != len(mode):
        raise AuditFailure(
            f"MODE_{mode_index}_PARSE_ID_MISMATCH:"
            + json.dumps({"expected": sorted(mode), "got": parsed_ids}, sort_keys=True)
        )
    if not parsed.get("all_recognized_parameters_complete"):
        raise AuditFailure(f"MODE_{mode_index}_PARAMETER_INCOMPLETE:{parsed.get('parameter_incomplete')}")

    generated = generator.generate(parsed["constraints"])
    candidates = list(generated.get("candidates") or [])
    if generated.get("status") != "PASS_CANDIDATES" or not candidates:
        raise AuditFailure(
            f"MODE_{mode_index}_GENERATOR_FAIL:"
            + json.dumps({k: generated.get(k) for k in ("status", "error", "mode", "candidate_count")}, sort_keys=True)
        )

    selected = None
    failure_matrix = []
    for candidate_index, candidate in enumerate(candidates):
        truths = {}
        errors = {}
        for constraint in parsed["constraints"]:
            iid = constraint["instruction_id"]
            try:
                truths[iid] = _exact_checker_truth(
                    registry, iid, constraint.get("slots") or {}, prompt, candidate
                )
            except Exception as exc:
                truths[iid] = False
                errors[iid] = type(exc).__name__ + ":" + str(exc)
        failed = sorted(k for k, v in truths.items() if not v)
        if not failed:
            selected = {
                "candidate_index": candidate_index,
                "response": candidate,
                "exact_checker_truths": truths,
            }
            break
        failure_matrix.append(
            {
                "candidate_index": candidate_index,
                "failed_instruction_ids": failed,
                "errors": errors,
            }
        )

    if selected is None:
        return {
            "mode_index": mode_index,
            "status": "FAIL_NO_JOINT_EXACT_WITNESS",
            "instruction_ids": sorted(mode),
            "prompt": prompt,
            "source_kwargs": source_kwargs,
            "compiled_constraint_count": len(parsed_ids),
            "generator_mode": generated.get("mode"),
            "candidate_count": len(candidates),
            "failure_matrix": failure_matrix,
        }

    return {
        "mode_index": mode_index,
        "status": "PASS_EXACT_FROZEN_CHECKERS",
        "instruction_ids": sorted(mode),
        "source_kwargs": source_kwargs,
        "compiled_constraint_count": len(parsed_ids),
        "generator_mode": generated.get("mode"),
        "candidate_count": len(candidates),
        "selected_candidate_index": selected["candidate_index"],
        "selected_response": selected["response"],
        "exact_checker_truths": selected["exact_checker_truths"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()

    root = pathlib.Path(ns.livebench_root).resolve()
    registry = _load_frozen_registry(root)

    opened = active.verify()
    partition_receipt = partition.prove_exhaustive_partition()
    if opened["commitment_sha256"] != partition.ACTIVE_SET_COMMITMENT:
        raise AuditFailure("ACTIVE_COMMITMENT_DRIFT")
    if set(active.ACTIVE_IDS) != set(partition.ACTIVE_IDS):
        raise AuditFailure("ACTIVE_IDENTITY_SET_DRIFT")
    if partition_receipt["maximal_mode_count"] != 9:
        raise AuditFailure("MAXIMAL_MODE_COUNT_DRIFT")

    rows = []
    for i, mode in enumerate(partition.MAXIMAL_MODES):
        row = _audit_mode(registry, i, mode)
        rows.append(row)
        print(
            json.dumps(
                {
                    "mode_index": i,
                    "status": row["status"],
                    "instruction_count": len(row["instruction_ids"]),
                    "generator_mode": row.get("generator_mode"),
                    "candidate_count": row.get("candidate_count"),
                    "selected_candidate_index": row.get("selected_candidate_index"),
                    "failed_instruction_ids": sorted(
                        {
                            iid
                            for f in row.get("failure_matrix", [])
                            for iid in f.get("failed_instruction_ids", [])
                        }
                    ),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    passed = all(x["status"] == "PASS_EXACT_FROZEN_CHECKERS" for x in rows)
    receipt = {
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_9_MAXIMAL_ACTIVE15_MODES_HAVE_SYNTHETIC_JOINT_WITNESS_UNDER_EXACT_FROZEN_CHECKERS"
            if passed
            else "FAIL_CLOSED__AT_LEAST_ONE_MAXIMAL_MODE_HAS_NO_SYNTHETIC_JOINT_WITNESS"
        ),
        "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "pinned_registry_blob": PINNED_REGISTRY_BLOB,
        "pinned_instructions_blob": PINNED_INSTRUCTIONS_BLOB,
        "active_set_commitment_sha256": opened["commitment_sha256"],
        "active_identity_count": len(active.ACTIVE_IDS),
        "all_active_subsets": partition_receipt["all_subsets"],
        "conflict_valid_subsets": partition_receipt["valid_subsets"],
        "maximal_mode_count": partition_receipt["maximal_mode_count"],
        "maximum_simultaneous_family_count": partition_receipt["maximum_simultaneous_family_count"],
        "maximal_modes_passed": sum(x["status"] == "PASS_EXACT_FROZEN_CHECKERS" for x in rows),
        "terminal_prompt_rows_read": 0,
        "terminal_kwargs_rows_read": 0,
        "terminal_responses_read": 0,
        "new_terminal_cases_exposed": 0,
        "model_dependency_count": 0,
        "network_dependency_during_candidate_generation": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "hard_nonclaims": [
            "SYNTHETIC_PARAMETER_VALUES_DO_NOT_PROVE_EXHAUSTIVE_PARAMETER_SPACE",
            "PUBLIC_SYNTHETIC_JOINT_WITNESSES_DO_NOT_PROVE_FROZEN_TERMINAL_SCORE",
            "SCORER_PASS_DOES_NOT_PROVE_SEMANTIC_TEXT_TRANSFORMATION_CAPABILITY",
            "NO_TERMINAL_CASE_CONTENT_OR_HIDDEN_KWARGS_USED",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "rows": rows,
    }
    pathlib.Path(ns.output).write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "maximal_modes_passed": receipt["maximal_modes_passed"],
                "maximal_mode_count": receipt["maximal_mode_count"],
            },
            sort_keys=True,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
