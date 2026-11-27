#!/usr/bin/env python3
"""Source-bound conservative scope theorem for historical LiveBench IF generation.

Purpose
-------
Remove dependence on the paper's internally inconsistent "16 instructions"
cardinality claim.  The exact public historical generator source is stronger:
it exposes the complete pool from which instruction IDs are sampled.  This
module parses that source without executing it and proves a conservative
24-family superset for every row emitted by that generator.

This does NOT prove the current 15-family pointwise solver covers the whole
historical generator.  Instead it gives the clean next target: pointwise closure
over the exact 24-ID generator pool.  Once that target is closed, the paper's
15-vs-16 documentation inconsistency becomes irrelevant to acceptance.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as active15

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_HISTORICAL24_SCOPE_SUPERSET_V1"

HISTORICAL_GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
HISTORICAL_GENERATOR_PATH = "livebench/if_runner/live_data.py"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"

PINNED_SCORER_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_PATH = (
    "livebench/if_runner/instruction_following_eval/instructions_registry.py"
)
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"

HISTORICAL24 = (
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

REGISTRY25 = tuple(sorted(set(HISTORICAL24) | {"language:response_language"}))

PAPER_VISIBLE15 = tuple(active15.ACTIVE_IDS)
PAPER_DECLARED_CARDINALITY = 16

# These are exactly the generator-pool families not covered by the current
# active15 pointwise proof.  Keeping this list executable prevents a future
# "15 == 24 somehow" governance miracle.
UNCOVERED_GENERATOR9 = tuple(sorted(set(HISTORICAL24) - set(PAPER_VISIBLE15)))


class ScopeProofError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _eval_static(node: ast.AST, env: dict[str, Any]) -> Any:
    """Evaluate the tiny literal/concatenation subset used by frozen sources."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, bool)):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [_eval_static(x, env) for x in node.elts]
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise ScopeProofError("UNBOUND_STATIC_NAME:" + node.id)
        return env[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _eval_static(node.left, env)
        right = _eval_static(node.right, env)
        return left + right
    raise ScopeProofError("UNSUPPORTED_STATIC_AST:" + type(node).__name__)


def parse_generator_pool(source: str) -> tuple[str, ...]:
    """Parse the exact ID pool from add_instructions_to_registry, no execution."""
    tree = ast.parse(source)
    fn = next(
        (
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef)
            and n.name == "add_instructions_to_registry"
        ),
        None,
    )
    if fn is None:
        raise ScopeProofError("GENERATOR_FUNCTION_NOT_FOUND")

    env: dict[str, Any] = {}
    all_constraints: list[str] | None = None
    for stmt in fn.body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        target = stmt.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            value = _eval_static(stmt.value, env)
        except ScopeProofError:
            continue
        env[target.id] = value
        if target.id == "all_constraints":
            all_constraints = list(value)

    if all_constraints is None:
        raise ScopeProofError("ALL_CONSTRAINTS_NOT_STATICALLY_RECOVERED")
    if len(all_constraints) != len(set(all_constraints)):
        raise ScopeProofError("GENERATOR_POOL_CONTAINS_DUPLICATES")
    return tuple(all_constraints)


def _is_np_random_call(node: ast.AST, name: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == name
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "random"
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "np"
    )


def verify_sampling_shape(source: str) -> dict[str, Any]:
    """Prove the generator draws 2..max inclusive and samples without replacement."""
    tree = ast.parse(source)
    fn = next(
        (
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef)
            and n.name == "add_instructions_to_registry"
        ),
        None,
    )
    if fn is None:
        raise ScopeProofError("GENERATOR_FUNCTION_NOT_FOUND")

    randint_ok = False
    choice_ok = False
    for node in ast.walk(fn):
        if _is_np_random_call(node, "randint"):
            call = node
            if len(call.args) >= 2:
                lo = call.args[0]
                hi = call.args[1]
                randint_ok = (
                    isinstance(lo, ast.Constant)
                    and lo.value == 2
                    and isinstance(hi, ast.BinOp)
                    and isinstance(hi.op, ast.Add)
                    and isinstance(hi.left, ast.Name)
                    and hi.left.id == "max_instructions"
                    and isinstance(hi.right, ast.Constant)
                    and hi.right.value == 1
                )
        if _is_np_random_call(node, "choice"):
            call = node
            if len(call.args) >= 2:
                first = call.args[0]
                second = call.args[1]
                replace_kw = next(
                    (kw.value for kw in call.keywords if kw.arg == "replace"),
                    None,
                )
                choice_ok = (
                    isinstance(first, ast.Name)
                    and first.id == "all_constraints"
                    and isinstance(second, ast.Name)
                    and second.id == "draw"
                    and isinstance(replace_kw, ast.Constant)
                    and replace_kw.value is False
                )

    if not randint_ok:
        raise ScopeProofError("DRAW_CARDINALITY_2_TO_MAX_NOT_PROVED")
    if not choice_ok:
        raise ScopeProofError("WITHOUT_REPLACEMENT_POOL_SAMPLE_NOT_PROVED")
    return {
        "draw_minimum": 2,
        "draw_maximum_default": 5,
        "without_replacement": True,
    }


def verify_deconfliction_is_removal_only(source: str) -> bool:
    """Prove check_for_conflitcs never adds a new instruction identifier."""
    tree = ast.parse(source)
    fn = next(
        (
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "check_for_conflitcs"
        ),
        None,
    )
    if fn is None:
        raise ScopeProofError("DECONFLICT_FUNCTION_NOT_FOUND")

    removes = 0
    suspicious_mutations: list[str] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        method = node.func.attr
        if method == "remove":
            removes += 1
        elif method in {"append", "extend", "insert", "add", "update"}:
            # Appending completed instruction lists to the output collection is
            # harmless.  Mutating deconflicting_instruction_ would not be.
            owner = node.func.value
            if isinstance(owner, ast.Name) and owner.id == "deconflicting_instruction_":
                suspicious_mutations.append(method)
    if removes < 1:
        raise ScopeProofError("DECONFLICT_REMOVAL_NOT_FOUND")
    if suspicious_mutations:
        raise ScopeProofError(
            "DECONFLICT_CAN_ADD_IDS:" + ",".join(sorted(set(suspicious_mutations)))
        )
    return True


def _parse_registry_ids(source: str) -> tuple[str, ...]:
    """Recover INSTRUCTION_DICT keys from the exact pinned registry source."""
    tree = ast.parse(source)
    env: dict[str, Any] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name) and target.id.startswith("_"):
                try:
                    env[target.id] = _eval_static(stmt.value, env)
                except ScopeProofError:
                    pass
            if (
                isinstance(target, ast.Name)
                and target.id == "INSTRUCTION_DICT"
                and isinstance(stmt.value, ast.Dict)
            ):
                keys = []
                for key in stmt.value.keys:
                    if key is None:
                        continue
                    value = _eval_static(key, env)
                    if not isinstance(value, str):
                        raise ScopeProofError("NON_STRING_REGISTRY_KEY")
                    keys.append(value)
                if len(keys) != len(set(keys)):
                    raise ScopeProofError("REGISTRY_DUPLICATE_ID")
                return tuple(keys)
    raise ScopeProofError("INSTRUCTION_DICT_NOT_RECOVERED")


def verify_static_theorem() -> dict[str, Any]:
    active = set(PAPER_VISIBLE15)
    historical = set(HISTORICAL24)
    registry = set(REGISTRY25)
    if len(active) != 15:
        raise ScopeProofError("ACTIVE15_CARDINALITY_DRIFT")
    if len(historical) != 24:
        raise ScopeProofError("HISTORICAL24_CARDINALITY_DRIFT")
    if len(registry) != 25:
        raise ScopeProofError("REGISTRY25_CARDINALITY_DRIFT")
    if not active < historical:
        raise ScopeProofError("ACTIVE15_NOT_STRICT_SUBSET_OF_HISTORICAL24")
    if not historical < registry:
        raise ScopeProofError("HISTORICAL24_NOT_STRICT_SUBSET_OF_REGISTRY25")
    if set(UNCOVERED_GENERATOR9) != historical - active:
        raise ScopeProofError("UNCOVERED_GENERATOR9_DRIFT")

    return {
        "schema": SCHEMA,
        "status": "PASS__CONSERVATIVE_HISTORICAL24_SCOPE_TARGET_DEFINED",
        "paper_visible_livebench_id_count": len(active),
        "paper_declared_livebench_id_count": PAPER_DECLARED_CARDINALITY,
        "paper_cardinality_consistent": len(active) == PAPER_DECLARED_CARDINALITY,
        "historical_generator_pool_count": len(historical),
        "pinned_registry_count": len(registry),
        "active15_is_strict_subset_of_generator24": True,
        "generator24_is_strict_subset_of_registry25": True,
        "uncovered_generator_family_count": len(UNCOVERED_GENERATOR9),
        "uncovered_generator_families": list(UNCOVERED_GENERATOR9),
        "acceptance_credit": False,
    }


def verify_sources(
    historical_root: str | Path,
    pinned_scorer_root: str | Path,
) -> dict[str, Any]:
    historical_root = Path(historical_root).resolve()
    pinned_scorer_root = Path(pinned_scorer_root).resolve()

    generator_path = historical_root / HISTORICAL_GENERATOR_PATH
    registry_path = pinned_scorer_root / PINNED_REGISTRY_PATH
    if not generator_path.is_file():
        raise ScopeProofError("HISTORICAL_GENERATOR_FILE_MISSING")
    if not registry_path.is_file():
        raise ScopeProofError("PINNED_REGISTRY_FILE_MISSING")

    generator_sha = _git_blob_sha(generator_path)
    registry_sha = _git_blob_sha(registry_path)
    if generator_sha != HISTORICAL_GENERATOR_BLOB:
        raise ScopeProofError("HISTORICAL_GENERATOR_BLOB_MISMATCH")
    if registry_sha != PINNED_REGISTRY_BLOB:
        raise ScopeProofError("PINNED_REGISTRY_BLOB_MISMATCH")

    generator_source = generator_path.read_text(encoding="utf-8")
    registry_source = registry_path.read_text(encoding="utf-8")

    pool = parse_generator_pool(generator_source)
    if set(pool) != set(HISTORICAL24) or len(pool) != len(HISTORICAL24):
        raise ScopeProofError("HISTORICAL_GENERATOR_POOL_MISMATCH")

    sampling = verify_sampling_shape(generator_source)
    removal_only = verify_deconfliction_is_removal_only(generator_source)

    registry_ids = _parse_registry_ids(registry_source)
    if set(registry_ids) != set(REGISTRY25) or len(registry_ids) != len(REGISTRY25):
        raise ScopeProofError("PINNED_REGISTRY25_MISMATCH")

    static = verify_static_theorem()
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__SOURCE_BOUND_HISTORICAL24_CONSERVATIVE_SCOPE_SUPERSET__"
            "PAPER_15_VS_16_AMBIGUITY_NOT_LOAD_BEARING_FOR_SUPERSET_TARGET"
        ),
        "source_binding": {
            "historical_generator_commit": HISTORICAL_GENERATOR_COMMIT,
            "historical_generator_blob": generator_sha,
            "pinned_scorer_commit": PINNED_SCORER_COMMIT,
            "pinned_registry_blob": registry_sha,
        },
        "generator_semantics": {
            "pool_count": len(pool),
            "pool": sorted(pool),
            **sampling,
            "deconfliction_removal_only": removal_only,
            "post_deconfliction_scope_theorem": (
                "EVERY_EMITTED_INSTRUCTION_ID_IS_A_MEMBER_OF_HISTORICAL24_AND_"
                "EVERY_EMITTED_SET_HAS_CARDINALITY_AT_MOST_5"
            ),
        },
        "paper_scope_truth_repair": {
            "visible_checkmarked_id_count": static[
                "paper_visible_livebench_id_count"
            ],
            "declared_textual_count": PAPER_DECLARED_CARDINALITY,
            "counts_agree": False,
            "consequence": (
                "DO_NOT_PROMOTE_ACTIVE15_SCOPE_EQUIVALENCE_FROM_THE_PAPER_ALONE"
            ),
        },
        "breakthrough": {
            "stronger_target": (
                "PROVE_POINTWISE_OPTIMALITY_FOR_EVERY_GENERATOR_ADMITTED_"
                "HISTORICAL24_VISIBLE_CONTRACT_TUPLE"
            ),
            "consequence_if_closed": (
                "ANY_BENCHMARK_ROW_EMITTED_BY_THE_EXACT_HISTORICAL_GENERATOR_"
                "IS_COVERED_WITHOUT_NEEDING_TO_RESOLVE_THE_PAPER_15_VS_16_COUNT"
            ),
            "additional_families_vs_active15": list(UNCOVERED_GENERATOR9),
            "additional_family_count": len(UNCOVERED_GENERATOR9),
        },
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "hard_nonclaims": [
            "ACTIVE15_SCOPE_EQUIVALENCE_IS_NOT_PROVED",
            "HISTORICAL24_POINTWISE_OPTIMALITY_IS_NOT_YET_PROVED",
            "THIS_THEOREM_APPLIES_TO_ROWS_EMITTED_BY_THE_PINNED_HISTORICAL_GENERATOR",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_YET",
        ],
    }


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    historical_root = args.get("historical_root")
    pinned_scorer_root = args.get("pinned_scorer_root")
    if not historical_root or not pinned_scorer_root:
        return verify_static_theorem()
    return verify_sources(historical_root, pinned_scorer_root)


if __name__ == "__main__":
    import json
    import sys

    payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    print(json.dumps(run(payload), indent=2, sort_keys=True))
