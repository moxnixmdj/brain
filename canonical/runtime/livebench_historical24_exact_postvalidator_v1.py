#!/usr/bin/env python3
"""Exact pinned-checker adapter for the conservative historical24 LiveBench scope.

This widens exact postvalidation from Active15 to every family present in the
exact historical generator pool. It does not solve the new families; it makes
their verification semantics executable and fail-closed so the next composer
cannot award itself credit by interpretation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_historical24_composition_space_v1 as space
from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as legacy
from canonical.runtime import livebench_legacy15_hermetic_nltk_binding_v1 as hermetic_nltk

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_HISTORICAL24_EXACT_POSTVALIDATOR_V1"

SLOT_KEYS: dict[str, tuple[str, ...]] = dict(legacy.SLOT_KEYS)
SLOT_KEYS.update({
    "keywords:frequency": ("keyword", "frequency", "relation"),
    "keywords:letter_frequency": ("letter", "let_frequency", "let_relation"),
    "detectable_content:number_placeholders": ("num_placeholders",),
    "detectable_format:constrained_response": (),
    "detectable_format:number_highlighted_sections": ("num_highlights",),
    "change_case:capital_word_frequency": (
        "capital_frequency",
        "capital_relation",
    ),
    "change_case:english_capital": (),
    "change_case:english_lowercase": (),
    "punctuation:no_comma": (),
})

NLTK_DEPENDENT_IDS = frozenset({
    "length_constraints:number_words",
    "length_constraints:number_sentences",
    "change_case:capital_word_frequency",
})


class Historical24PostvalidationError(ValueError):
    pass


def _normalize_contracts(
    contracts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = [dict(c) for c in contracts]
    if not rows:
        raise Historical24PostvalidationError("CONTRACTS_REQUIRED")
    if len(rows) > space.MAX_GENERATED_INSTRUCTIONS:
        raise Historical24PostvalidationError(
            "CHECKER_COUNT_EXCEEDS_HISTORICAL_GENERATOR_BOUND"
        )

    ids = [str(c.get("instruction_id") or "") for c in rows]
    if any(not iid for iid in ids):
        raise Historical24PostvalidationError("INSTRUCTION_ID_REQUIRED")
    if len(ids) != len(set(ids)):
        raise Historical24PostvalidationError("DUPLICATE_INSTRUCTION_ID")
    if not set(ids) <= set(space.IDS):
        raise Historical24PostvalidationError("NON_HISTORICAL24_INSTRUCTION_ID")
    if not space.compatible(ids):
        raise Historical24PostvalidationError(
            "HISTORICAL24_CONFLICT_GRAPH_REJECTED"
        )

    for row in rows:
        iid = str(row["instruction_id"])
        if row.get("parameter_complete") is not True:
            raise Historical24PostvalidationError(
                "PARAMETER_INCOMPLETE:" + iid
            )
        if not isinstance(row.get("slots"), Mapping):
            raise Historical24PostvalidationError(
                "SLOTS_MAPPING_REQUIRED:" + iid
            )
        slots = dict(row["slots"])
        expected = set(SLOT_KEYS[iid])
        actual = set(slots)
        if actual != expected:
            raise Historical24PostvalidationError(
                "VISIBLE_SLOT_SHAPE_MISMATCH:"
                + iid
                + ":missing="
                + ",".join(sorted(expected - actual))
                + ":extra="
                + ",".join(sorted(actual - expected))
            )
        if any(value is None for value in slots.values()):
            raise Historical24PostvalidationError(
                "VISIBLE_SLOT_VALUE_NONE:" + iid
            )
    return rows


def contracts_require_nltk(contracts: Sequence[Mapping[str, Any]]) -> bool:
    return any(
        str(c.get("instruction_id") or "") in NLTK_DEPENDENT_IDS
        for c in contracts
    )


def load_pinned_registry(livebench_root: str | Path):
    registry, source_binding = legacy.load_pinned_registry(livebench_root)
    missing = sorted(set(space.IDS) - set(registry))
    if missing:
        raise Historical24PostvalidationError(
            "HISTORICAL24_MISSING_FROM_PINNED_REGISTRY:" + ",".join(missing)
        )
    return registry, source_binding


def load_proofgrade_registry(
    livebench_root: str | Path,
    contracts: Sequence[Mapping[str, Any]],
    *,
    nltk_wheel_path: str | Path | None = None,
    nltk_data_root: str | Path | None = None,
):
    if contracts_require_nltk(contracts):
        if not nltk_wheel_path or not nltk_data_root:
            raise Historical24PostvalidationError(
                "PROOFGRADE_NLTK_BINDING_REQUIRED"
            )
        try:
            runtime = hermetic_nltk.verify_and_bind(
                nltk_wheel_path,
                nltk_data_root,
            )
        except hermetic_nltk.HermeticNLTKError as exc:
            raise Historical24PostvalidationError(
                "HERMETIC_NLTK_BINDING_FAILED:" + str(exc)
            ) from exc
    else:
        runtime = {
            "schema": hermetic_nltk.SCHEMA,
            "status": "NOT_REQUIRED__NO_NLTK_DEPENDENT_HISTORICAL24_CHECKER",
            "network_used": False,
            "terminal_data_used": False,
        }

    registry, source = load_pinned_registry(livebench_root)
    return registry, {
        "source": source,
        "runtime": runtime,
        "proofgrade_runtime_dependencies_bound": True,
    }


def evaluate_with_registry(
    response: str,
    contracts: Sequence[Mapping[str, Any]],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    rows = _normalize_contracts(contracts)
    strict_eligible = bool(str(response).strip())
    flags: list[bool] = []

    for row in rows:
        iid = str(row["instruction_id"])
        cls = registry.get(iid)
        if cls is None:
            raise Historical24PostvalidationError(
                "INSTRUCTION_NOT_IN_REGISTRY:" + iid
            )
        checker = cls(iid)
        try:
            checker.build_description(**dict(row["slots"]))
            flags.append(
                strict_eligible
                and bool(checker.check_following(str(response)))
            )
        except Exception as exc:
            raise Historical24PostvalidationError(
                "CHECKER_EXECUTION_FAILED:"
                + iid
                + ":"
                + type(exc).__name__
                + ":"
                + str(exc)
            ) from exc

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_PINNED_HISTORICAL24_CHECKER_VECTOR",
        "instruction_ids": [str(x["instruction_id"]) for x in rows],
        "checker_results": flags,
        "true_checker_count": sum(flags),
        "checker_count": len(flags),
        "strict_nonempty_response_gate_applied": True,
        "strict_response_eligible": strict_eligible,
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_id_used": False,
        "acceptance_credit": False,
    }


def postvalidate_proofgrade(
    response: str,
    contracts: Sequence[Mapping[str, Any]],
    livebench_root: str | Path,
    *,
    nltk_wheel_path: str | Path | None = None,
    nltk_data_root: str | Path | None = None,
) -> dict[str, Any]:
    registry, binding = load_proofgrade_registry(
        livebench_root,
        contracts,
        nltk_wheel_path=nltk_wheel_path,
        nltk_data_root=nltk_data_root,
    )
    out = evaluate_with_registry(response, contracts, registry)
    out["binding"] = binding
    return out


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    livebench_root = args.get("livebench_root")
    if not livebench_root:
        raise Historical24PostvalidationError("LIVEBENCH_ROOT_REQUIRED")
    return postvalidate_proofgrade(
        str(args.get("response") or ""),
        args.get("contracts") or [],
        livebench_root,
        nltk_wheel_path=args.get("nltk_wheel_path"),
        nltk_data_root=args.get("nltk_data_root"),
    )


if __name__ == "__main__":
    import json
    import sys

    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), indent=2, sort_keys=True))
