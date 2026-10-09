"""Generic proof-carrying cross-document effect calculus V1.

This module solves interaction among already-typed, content-addressed document
effects. It does NOT infer arbitrary prose semantics. Each document contributes
value-producing effects over semantic targets plus explicit supersession edges.
Conditions and valid-time determine applicability; supersession determines
precedence. Incomparable surviving effects are preserved rather than guessed.

The central reduction is:
    documents -> source-traceable typed effects -> one precedence DAG ->
    effective value for the requested target/context/time

This removes pairwise/triple-specific cross-document combinatorics while
preserving a fail-closed authority boundary around upstream semantic extraction.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

DOC_SCHEMA = "PROJECT_BRAIN_TYPED_DOCUMENT_EFFECTS_V1"
CASE_SCHEMA = "PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_RESULT_V1"

EFFECT_CLASSES = frozenset({"DEFINE", "REPLACE", "EXCEPTION", "OVERRIDE"})


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _token(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + "_INVALID")
    return value.strip()


def _day(value: Any, name: str, *, allow_none: bool = False) -> date | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str):
        raise ValueError(name + "_INVALID")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(name + "_INVALID") from exc
    if parsed.isoformat() != value:
        raise ValueError(name + "_INVALID")
    return parsed


def _validate_effect(row: Any) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise ValueError("EFFECT_NOT_OBJECT")
    allowed = {
        "effect_id",
        "target_id",
        "effect_class",
        "value",
        "conditions",
        "valid_from",
        "valid_until",
        "supersedes",
        "source_locator",
    }
    if set(row) != allowed:
        raise ValueError("EFFECT_FIELD_SET_NOT_EXACT")

    effect_id = _token(row.get("effect_id"), "EFFECT_ID")
    target_id = _token(row.get("target_id"), "TARGET_ID")
    effect_class = _token(row.get("effect_class"), "EFFECT_CLASS").upper()
    if effect_class not in EFFECT_CLASSES:
        raise ValueError("EFFECT_CLASS_UNSUPPORTED:" + effect_class)

    conditions = row.get("conditions")
    if not isinstance(conditions, Mapping):
        raise ValueError("CONDITIONS_NOT_OBJECT")
    clean_conditions: dict[str, Any] = {}
    for key, value in conditions.items():
        clean_key = _token(key, "CONDITION_KEY")
        _canon(value)
        clean_conditions[clean_key] = value

    supersedes = row.get("supersedes")
    if (
        not isinstance(supersedes, Sequence)
        or isinstance(supersedes, (str, bytes))
        or any(not isinstance(x, str) or not x.strip() for x in supersedes)
    ):
        raise ValueError("SUPERSEDES_INVALID")
    supersedes_clean = [x.strip() for x in supersedes]
    if len(supersedes_clean) != len(set(supersedes_clean)):
        raise ValueError("SUPERSEDES_DUPLICATE")

    valid_from = _day(row.get("valid_from"), "VALID_FROM", allow_none=True)
    valid_until = _day(row.get("valid_until"), "VALID_UNTIL", allow_none=True)
    if valid_from is not None and valid_until is not None and valid_from >= valid_until:
        raise ValueError("VALID_INTERVAL_EMPTY_OR_REVERSED")

    source_locator = _token(row.get("source_locator"), "SOURCE_LOCATOR")
    _canon(row.get("value"))

    if effect_class != "DEFINE" and not supersedes_clean:
        raise ValueError("NON_DEFINE_EFFECT_REQUIRES_SUPERSESSION_TARGET")

    return {
        "effect_id": effect_id,
        "target_id": target_id,
        "effect_class": effect_class,
        "value": row.get("value"),
        "conditions": dict(sorted(clean_conditions.items())),
        "valid_from": valid_from.isoformat() if valid_from is not None else None,
        "valid_until": valid_until.isoformat() if valid_until is not None else None,
        "supersedes": supersedes_clean,
        "source_locator": source_locator,
    }


def _validate_document(doc: Any) -> dict[str, Any]:
    if not isinstance(doc, Mapping) or doc.get("schema") != DOC_SCHEMA:
        raise ValueError("DOCUMENT_SCHEMA_INVALID")
    if set(doc) != {"schema", "document_id", "effects"}:
        raise ValueError("DOCUMENT_FIELD_SET_NOT_EXACT")
    document_id = _token(doc.get("document_id"), "DOCUMENT_ID")
    effects = doc.get("effects")
    if (
        not isinstance(effects, Sequence)
        or isinstance(effects, (str, bytes))
        or not effects
    ):
        raise ValueError("DOCUMENT_EFFECTS_INVALID")
    return {
        "schema": DOC_SCHEMA,
        "document_id": document_id,
        "effects": [_validate_effect(row) for row in effects],
    }


def _check_acyclic(graph: Mapping[str, Sequence[str]]) -> None:
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(node: str) -> None:
        if node in done:
            return
        if node in visiting:
            raise ValueError("SUPERSESSION_CYCLE:" + node)
        visiting.add(node)
        for child in graph.get(node, ()):
            visit(child)
        visiting.remove(node)
        done.add(node)

    for node in sorted(graph):
        visit(node)


def _dominates(
    stronger: str,
    weaker: str,
    graph: Mapping[str, Sequence[str]],
    memo: dict[tuple[str, str], bool],
) -> bool:
    key = (stronger, weaker)
    if key in memo:
        return memo[key]
    stack = list(graph.get(stronger, ()))
    seen: set[str] = set()
    while stack:
        node = stack.pop()
        if node == weaker:
            memo[key] = True
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, ()))
    memo[key] = False
    return False


def _applies(effect: Mapping[str, Any], as_of: date, context: Mapping[str, Any]) -> bool:
    start = effect.get("valid_from")
    end = effect.get("valid_until")
    if start is not None and as_of < date.fromisoformat(str(start)):
        return False
    if end is not None and as_of >= date.fromisoformat(str(end)):
        return False
    for key, expected in dict(effect.get("conditions") or {}).items():
        if key not in context or _canon(context[key]) != _canon(expected):
            return False
    return True


def compute(
    case: Mapping[str, Any],
    documents_by_path: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(case, Mapping) or case.get("schema") != CASE_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    if set(case) != {"schema", "case_id", "documents", "query"}:
        raise ValueError("CASE_FIELD_SET_NOT_EXACT")

    case_id = _token(case.get("case_id"), "CASE_ID")
    document_specs = case.get("documents")
    if (
        not isinstance(document_specs, Sequence)
        or isinstance(document_specs, (str, bytes))
        or not document_specs
    ):
        raise ValueError("CASE_DOCUMENTS_INVALID")

    query = case.get("query")
    if not isinstance(query, Mapping) or set(query) != {"target_id", "as_of", "context"}:
        raise ValueError("QUERY_INVALID")
    target_id = _token(query.get("target_id"), "QUERY_TARGET_ID")
    as_of = _day(query.get("as_of"), "QUERY_AS_OF")
    context = query.get("context")
    if not isinstance(context, Mapping):
        raise ValueError("QUERY_CONTEXT_NOT_OBJECT")
    for key, value in context.items():
        _token(key, "QUERY_CONTEXT_KEY")
        _canon(value)

    effects: dict[str, dict[str, Any]] = {}
    document_receipts: list[dict[str, Any]] = []
    document_ids: set[str] = set()

    for spec in document_specs:
        if not isinstance(spec, Mapping) or set(spec) != {"path", "sha256"}:
            raise ValueError("DOCUMENT_SPEC_INVALID")
        path = _token(spec.get("path"), "DOCUMENT_PATH")
        expected_sha = _token(spec.get("sha256"), "DOCUMENT_SHA256")
        if path not in documents_by_path:
            raise ValueError("DOCUMENT_MISSING:" + path)
        raw_doc = documents_by_path[path]
        actual_sha = _sha(raw_doc)
        if actual_sha != expected_sha:
            raise ValueError("DOCUMENT_CONTENT_ADDRESS_MISMATCH:" + path)
        doc = _validate_document(raw_doc)
        if doc["document_id"] in document_ids:
            raise ValueError("DOCUMENT_ID_DUPLICATE:" + doc["document_id"])
        document_ids.add(doc["document_id"])

        for effect in doc["effects"]:
            effect_id = effect["effect_id"]
            if effect_id in effects:
                raise ValueError("EFFECT_ID_DUPLICATE:" + effect_id)
            bound = dict(effect)
            bound["source_document_id"] = doc["document_id"]
            bound["source_document_path"] = path
            bound["source_document_sha256"] = actual_sha
            effects[effect_id] = bound

        document_receipts.append(
            {
                "path": path,
                "document_id": doc["document_id"],
                "sha256": actual_sha,
                "effect_count": len(doc["effects"]),
            }
        )

    graph: dict[str, list[str]] = {eid: list(row["supersedes"]) for eid, row in effects.items()}
    for effect_id, weaker_ids in graph.items():
        for weaker in weaker_ids:
            if weaker not in effects:
                raise ValueError("SUPERSESSION_TARGET_UNKNOWN:" + effect_id + "->" + weaker)
            if effects[weaker]["target_id"] != effects[effect_id]["target_id"]:
                raise ValueError("CROSS_TARGET_SUPERSESSION_FORBIDDEN:" + effect_id + "->" + weaker)
            if weaker == effect_id:
                raise ValueError("SELF_SUPERSESSION_FORBIDDEN:" + effect_id)
    _check_acyclic(graph)

    relevant = [row for row in effects.values() if row["target_id"] == target_id]
    applicable = [row for row in relevant if _applies(row, as_of, context)]

    base = {
        "schema": RESULT_SCHEMA,
        "case_id": case_id,
        "target_id": target_id,
        "as_of": as_of.isoformat(),
        "context": dict(sorted(context.items())),
        "document_receipts": sorted(document_receipts, key=lambda x: x["path"]),
        "relevant_effect_ids": sorted(row["effect_id"] for row in relevant),
        "applicable_effect_ids": sorted(row["effect_id"] for row in applicable),
        "model_dependency_count": 0,
        "external_world_truth_claimed": False,
        "semantic_extraction_claimed": False,
        "terminal_authority": False,
    }

    if not applicable:
        return {
            **base,
            "status": "OPEN__NO_APPLICABLE_EFFECT",
            "pass": False,
            "effective_value": None,
            "surviving_effect_ids": [],
            "decision_ambiguity_irrelevant": False,
            "composition_sha256": _sha(
                {
                    "target_id": target_id,
                    "as_of": as_of.isoformat(),
                    "context": dict(sorted(context.items())),
                    "applicable_effect_ids": [],
                }
            ),
        }

    memo: dict[tuple[str, str], bool] = {}
    maxima: list[dict[str, Any]] = []
    for candidate in applicable:
        cid = candidate["effect_id"]
        if not any(
            other["effect_id"] != cid
            and _dominates(other["effect_id"], cid, graph, memo)
            for other in applicable
        ):
            maxima.append(candidate)

    maxima.sort(key=lambda row: row["effect_id"])
    values = {_canon(row["value"]): row["value"] for row in maxima}
    composition_payload = {
        "target_id": target_id,
        "as_of": as_of.isoformat(),
        "context": dict(sorted(context.items())),
        "applicable_effect_ids": sorted(row["effect_id"] for row in applicable),
        "surviving_effect_ids": [row["effect_id"] for row in maxima],
        "surviving_values": sorted(values),
    }

    if len(values) != 1:
        return {
            **base,
            "status": "OPEN__INCOMPARABLE_EFFECTS_REQUIRE_DISCRIMINATOR",
            "pass": False,
            "effective_value": None,
            "surviving_effect_ids": [row["effect_id"] for row in maxima],
            "surviving_effects": [
                {
                    "effect_id": row["effect_id"],
                    "effect_class": row["effect_class"],
                    "value": row["value"],
                    "source_document_id": row["source_document_id"],
                    "source_locator": row["source_locator"],
                }
                for row in maxima
            ],
            "decision_ambiguity_irrelevant": False,
            "composition_sha256": _sha(composition_payload),
        }

    selected_value = next(iter(values.values()))
    return {
        **base,
        "status": "PASS__COMMON_EFFECTIVE_VALUE_COMPOSED",
        "pass": True,
        "effective_value": selected_value,
        "surviving_effect_ids": [row["effect_id"] for row in maxima],
        "surviving_effects": [
            {
                "effect_id": row["effect_id"],
                "effect_class": row["effect_class"],
                "value": row["value"],
                "source_document_id": row["source_document_id"],
                "source_locator": row["source_locator"],
            }
            for row in maxima
        ],
        "decision_ambiguity_irrelevant": len(maxima) > 1,
        "composition_sha256": _sha(composition_payload),
        "authority_boundary": (
            "GENERAL_COMPOSITION_OVER_TYPED_CONTENT_ADDRESSED_VALUE_EFFECTS_WITH_"
            "EXPLICIT_CONDITIONS_VALID_TIME_AND_SUPERSESSION_DAG__NO_ARBITRARY_"
            "RAW_LANGUAGE_SEMANTIC_EXTRACTION_EXTERNAL_WORLD_TRUTH_OR_IMPLICIT_PRECEDENCE"
        ),
    }
