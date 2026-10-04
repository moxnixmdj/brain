#!/usr/bin/env python3
"""Truth-preserving scope lattice for the public LiveBench IF surface.

This module removes a load-bearing ambiguity from the current active15 proof
route. Three public artifacts expose three different apparent scopes:

* the row-level Table 4 surface: 25 named IFEval families, with 15 visible
  LiveBench checkmarks;
* the prose/caption count: "subset of 16";
* the pinned historical generator: 24 sampled families.

Rather than guess which inconsistent public representation should be treated as
authoritative, this module defines the smallest public union that strictly
subsumes all three named-family possibilities: the 25 Table-4 families.

No terminal benchmark row, hidden instruction_id_list, hidden kwargs, response,
frequency, comparator output, or target score is read.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as active15

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUBLIC_SCOPE_UNION_V1"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"

HISTORICAL_GENERATOR_24 = (
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
)

# Exact row labels represented by Table 4 at the checker-ID level. The active15
# rows plus these ten excluded rows are the full 25-family public table surface.
TABLE4_25 = tuple(
    dict.fromkeys(
        (
            *active15.ACTIVE_IDS,
            "keywords:frequency",
            "keywords:letter_frequency",
            "language:response_language",
            "detectable_content:number_placeholders",
            "detectable_format:constrained_response",
            "detectable_format:number_highlighted_sections",
            "change_case:english_capital",
            "change_case:english_lowercase",
            "change_case:capital_word_frequency",
            "punctuation:no_comma",
        )
    )
)

SUBSUMPTION_THEOREM = (
    "POINTWISE_OPTIMALITY_OVER_PUBLIC_UNION25_IMPLIES_POINTWISE_OPTIMALITY_"
    "OVER_ACTIVE15_AND_OVER_EVERY_SUBSET_OF_TABLE4_25_AND_OVER_EVERY_"
    "HISTORICAL_GENERATOR24_OUTPUT"
)


class PublicScopeError(ValueError):
    pass


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _literal_strings(node: ast.AST) -> tuple[str, ...] | None:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    out: list[str] = []
    for item in node.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            return None
        out.append(item.value)
    return tuple(out)


def _eval_static_concat(
    node: ast.AST,
    env: dict[str, tuple[str, ...]],
) -> tuple[str, ...] | None:
    literal = _literal_strings(node)
    if literal is not None:
        return literal
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _eval_static_concat(node.left, env)
        right = _eval_static_concat(node.right, env)
        if left is None or right is None:
            return None
        return left + right
    return None


def extract_constraint_universe(source: str) -> tuple[str, ...]:
    """Extract all_constraints from the pinned public generator without exec."""
    tree = ast.parse(source)
    fn = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "add_instructions_to_registry"
        ),
        None,
    )
    if fn is None:
        raise PublicScopeError("GENERATOR_FUNCTION_NOT_FOUND")

    env: dict[str, tuple[str, ...]] = {}
    for stmt in fn.body:
        if (
            not isinstance(stmt, ast.Assign)
            or len(stmt.targets) != 1
            or not isinstance(stmt.targets[0], ast.Name)
        ):
            continue
        name = stmt.targets[0].id
        value = _eval_static_concat(stmt.value, env)
        if value is not None:
            env[name] = value
        if name == "all_constraints":
            if value is None:
                raise PublicScopeError("ALL_CONSTRAINTS_NOT_STATIC")
            if not value:
                raise PublicScopeError("ALL_CONSTRAINTS_EMPTY")
            if len(set(value)) != len(value):
                raise PublicScopeError("ALL_CONSTRAINTS_DUPLICATE")
            return value

    raise PublicScopeError("ALL_CONSTRAINTS_NOT_FOUND")


def analyze_source(source: str) -> dict[str, Any]:
    generator = extract_constraint_universe(source)
    expected_generator = set(HISTORICAL_GENERATOR_24)
    generator_set = set(generator)
    active_set = set(active15.ACTIVE_IDS)
    table_set = set(TABLE4_25)

    if generator_set != expected_generator or len(generator) != 24:
        raise PublicScopeError("HISTORICAL_GENERATOR_24_DRIFT")
    if len(active_set) != 15:
        raise PublicScopeError("ACTIVE15_COUNT_DRIFT")
    if len(table_set) != 25:
        raise PublicScopeError("TABLE4_25_COUNT_DRIFT")
    if not active_set < generator_set:
        raise PublicScopeError("ACTIVE15_NOT_STRICT_SUBSET_OF_GENERATOR24")
    if not generator_set < table_set:
        raise PublicScopeError("GENERATOR24_NOT_STRICT_SUBSET_OF_TABLE4_25")
    if table_set - generator_set != {"language:response_language"}:
        raise PublicScopeError("TABLE4_GENERATOR_DELTA_DRIFT")

    generator_minus_active = sorted(generator_set - active_set)
    if len(generator_minus_active) != 9:
        raise PublicScopeError("GENERATOR_ACTIVE_DELTA_COUNT_DRIFT")

    return {
        "schema": SCHEMA,
        "status": "PASS__PUBLIC_SCOPE_LATTICE_15_LT_24_LT_25",
        "active15_count": len(active_set),
        "historical_generator_count": len(generator_set),
        "public_union_count": len(table_set),
        "active15_strict_subset_of_generator24": True,
        "generator24_strict_subset_of_public_union25": True,
        "generator24_minus_active15": generator_minus_active,
        "public_union25_minus_generator24": sorted(table_set - generator_set),
        "ambiguity_free_proof_target": "PUBLIC_TABLE4_UNION_25",
        "subsumption_theorem": SUBSUMPTION_THEOREM,
        "proof_consequence": (
            "A complete pointwise-optimality proof over PUBLIC_TABLE4_UNION_25 "
            "makes the public 15-vs-16-vs-24 scope disagreement non-load-bearing."
        ),
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "terminal_frequency_used": False,
        "target_score_used": False,
        "acceptance_credit": False,
    }


def verify(livebench_root: str | Path) -> dict[str, Any]:
    root = Path(livebench_root).resolve()
    path = root / "livebench" / "if_runner" / "live_data.py"
    if not path.is_file():
        raise PublicScopeError("PINNED_HISTORICAL_GENERATOR_SOURCE_MISSING")

    raw = path.read_bytes()
    actual_blob = _git_blob_sha(raw)
    if actual_blob != HISTORICAL_GENERATOR_BLOB:
        raise PublicScopeError(
            "HISTORICAL_GENERATOR_BLOB_DRIFT:" + actual_blob
        )

    out = analyze_source(raw.decode("utf-8"))
    out["historical_generator_git_blob_sha"] = actual_blob
    out["historical_generator_source_path"] = str(path)
    return out


def run(args=None, root=None):
    args = args or {}
    livebench_root = args.get("livebench_root")
    if not livebench_root:
        raise PublicScopeError("LIVEBENCH_ROOT_REQUIRED")
    return verify(livebench_root)


if __name__ == "__main__":
    import json
    import sys

    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), indent=2, sort_keys=True))
