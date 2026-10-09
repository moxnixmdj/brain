"""Decision-relative cross-document effect hypothesis world set V1.

This layer consumes a DECLARED COMPLETE finite set of typed effect hypotheses.
It grants no raw-language semantic authority. Its job is to remove the need for a
unique document interpretation when the requested effective value is invariant
across every surviving effect interpretation.

Each effect slot represents one unresolved local document-effect interpretation.
Exactly one hypothesis is selected per slot in each world. Every world is compiled
into ordinary typed effect documents and evaluated by cross_document_effect_calculus_v1.

If all worlds imply the same effective value, ambiguity is terminally irrelevant.
If outcomes differ, the module returns a minimum set of hypothesis slots whose
resolution separates all terminally distinct world pairs.

Completeness is relative to the supplied finite hypothesis universe only.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import combinations, product
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import cross_document_effect_calculus_v1 as calculus

SCHEMA = "PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_HYPOTHESIS_WORLDSET_V1"
MAX_DOCUMENTS = 32
MAX_SLOTS = 16
MAX_HYPOTHESES_PER_SLOT = 16
MAX_WORLDS = 4096

_NO_VALUE = "__NO_APPLICABLE_EFFECT__"


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


def _effect_row(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("EFFECT_HYPOTHESIS_NOT_OBJECT")
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
    if set(value) != allowed:
        raise ValueError("EFFECT_HYPOTHESIS_FIELD_SET_NOT_EXACT")
    # Reuse the authoritative local validation logic. This function does not
    # infer source semantics; it only rejects malformed typed effects.
    return calculus._validate_effect(value)


def _parse_problem(problem: Mapping[str, Any]) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    if not isinstance(problem, Mapping) or problem.get("schema") != SCHEMA:
        raise ValueError("PROBLEM_SCHEMA_INVALID")
    if set(problem) != {
        "schema",
        "case_id",
        "hypothesis_set_complete",
        "documents",
        "query",
    }:
        raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
    if problem.get("hypothesis_set_complete") is not True:
        raise ValueError("HYPOTHESIS_SET_NOT_DECLARED_COMPLETE")

    case_id = _token(problem.get("case_id"), "CASE_ID")
    documents = problem.get("documents")
    if (
        not isinstance(documents, Sequence)
        or isinstance(documents, (str, bytes))
        or not documents
        or len(documents) > MAX_DOCUMENTS
    ):
        raise ValueError("DOCUMENTS_INVALID_OR_TOO_LARGE")

    clean_docs: list[dict[str, Any]] = []
    doc_ids: set[str] = set()
    slot_ids: set[str] = set()
    slot_count = 0
    world_count = 1

    for doc in documents:
        if not isinstance(doc, Mapping) or set(doc) != {"document_id", "effect_slots"}:
            raise ValueError("DOCUMENT_HYPOTHESIS_OBJECT_INVALID")
        document_id = _token(doc.get("document_id"), "DOCUMENT_ID")
        if document_id in doc_ids:
            raise ValueError("DOCUMENT_ID_DUPLICATE:" + document_id)
        doc_ids.add(document_id)

        slots = doc.get("effect_slots")
        if (
            not isinstance(slots, Sequence)
            or isinstance(slots, (str, bytes))
            or not slots
        ):
            raise ValueError("EFFECT_SLOTS_INVALID")

        clean_slots = []
        for slot in slots:
            slot_count += 1
            if slot_count > MAX_SLOTS:
                raise ValueError("EFFECT_SLOT_BOUND_EXCEEDED")
            if not isinstance(slot, Mapping) or set(slot) != {
                "slot_id",
                "hypothesis_set_complete",
                "hypotheses",
            }:
                raise ValueError("EFFECT_SLOT_INVALID")
            slot_id = _token(slot.get("slot_id"), "SLOT_ID")
            if slot_id in slot_ids:
                raise ValueError("SLOT_ID_DUPLICATE:" + slot_id)
            slot_ids.add(slot_id)
            if slot.get("hypothesis_set_complete") is not True:
                raise ValueError("SLOT_HYPOTHESIS_SET_NOT_COMPLETE:" + slot_id)

            hypotheses = slot.get("hypotheses")
            if (
                not isinstance(hypotheses, Sequence)
                or isinstance(hypotheses, (str, bytes))
                or not hypotheses
                or len(hypotheses) > MAX_HYPOTHESES_PER_SLOT
            ):
                raise ValueError("HYPOTHESES_INVALID_OR_TOO_LARGE:" + slot_id)

            seen_hypotheses: set[str] = set()
            clean_hypotheses = []
            canonical_effects: set[str] = set()
            for hyp in hypotheses:
                if not isinstance(hyp, Mapping) or set(hyp) != {"hypothesis_id", "effect"}:
                    raise ValueError("HYPOTHESIS_INVALID:" + slot_id)
                hid = _token(hyp.get("hypothesis_id"), "HYPOTHESIS_ID")
                if hid in seen_hypotheses:
                    raise ValueError("HYPOTHESIS_ID_DUPLICATE:" + slot_id + ":" + hid)
                seen_hypotheses.add(hid)
                effect = _effect_row(hyp.get("effect"))
                ce = _canon(effect)
                if ce in canonical_effects:
                    raise ValueError("SEMANTICALLY_DUPLICATE_HYPOTHESIS:" + slot_id)
                canonical_effects.add(ce)
                clean_hypotheses.append({
                    "hypothesis_id": hid,
                    "effect": effect,
                })

            clean_hypotheses.sort(key=lambda x: x["hypothesis_id"])
            world_count *= len(clean_hypotheses)
            if world_count > MAX_WORLDS:
                raise ValueError("WORLD_BOUND_EXCEEDED")

            clean_slots.append({
                "slot_id": slot_id,
                "hypotheses": clean_hypotheses,
            })

        clean_slots.sort(key=lambda x: x["slot_id"])
        clean_docs.append({
            "document_id": document_id,
            "effect_slots": clean_slots,
        })

    query = problem.get("query")
    if not isinstance(query, Mapping) or set(query) != {"target_id", "as_of", "context"}:
        raise ValueError("QUERY_INVALID")
    _token(query.get("target_id"), "QUERY_TARGET_ID")
    _token(query.get("as_of"), "QUERY_AS_OF")
    if not isinstance(query.get("context"), Mapping):
        raise ValueError("QUERY_CONTEXT_NOT_OBJECT")
    _canon(query)

    clean_docs.sort(key=lambda x: x["document_id"])
    return case_id, clean_docs, dict(query)


def _outcomes(result: Mapping[str, Any]) -> list[str]:
    if result.get("pass") is True:
        return [_canon(result.get("effective_value"))]
    if result.get("status") == "OPEN__INCOMPARABLE_EFFECTS_REQUIRE_DISCRIMINATOR":
        rows = result.get("surviving_effects") or []
        values = sorted({_canon(row.get("value")) for row in rows if isinstance(row, Mapping)})
        if values:
            return values
    if result.get("status") == "OPEN__NO_APPLICABLE_EFFECT":
        return [_canon(_NO_VALUE)]
    return [_canon({"status": result.get("status")})]


def _minimum_discriminator_slots(worlds: Sequence[Mapping[str, Any]]) -> list[str]:
    differing_pairs: list[tuple[int, int]] = []
    for i in range(len(worlds)):
        for j in range(i + 1, len(worlds)):
            if worlds[i]["outcome_signature"] != worlds[j]["outcome_signature"]:
                differing_pairs.append((i, j))
    if not differing_pairs:
        return []

    slots = sorted({
        slot
        for world in worlds
        for slot in world["selection"]
    })
    covers: dict[str, set[tuple[int, int]]] = {}
    for slot in slots:
        covered = set()
        for pair in differing_pairs:
            i, j = pair
            if worlds[i]["selection"].get(slot) != worlds[j]["selection"].get(slot):
                covered.add(pair)
        covers[slot] = covered

    universe = set(differing_pairs)
    for width in range(1, len(slots) + 1):
        for subset in combinations(slots, width):
            union: set[tuple[int, int]] = set()
            for slot in subset:
                union.update(covers[slot])
            if union == universe:
                return list(subset)
    return []


def evaluate(problem: Mapping[str, Any]) -> dict[str, Any]:
    try:
        case_id, documents, query = _parse_problem(problem)

        slot_rows: list[tuple[str, str, list[dict[str, Any]]]] = []
        for doc in documents:
            for slot in doc["effect_slots"]:
                slot_rows.append((
                    doc["document_id"],
                    slot["slot_id"],
                    slot["hypotheses"],
                ))

        domains = [row[2] for row in slot_rows]
        worlds = []
        union_outcomes: dict[str, Any] = {}

        for selected in product(*domains):
            selection = {
                slot_id: hyp["hypothesis_id"]
                for (_, slot_id, _), hyp in zip(slot_rows, selected)
            }
            effects_by_doc: dict[str, list[dict[str, Any]]] = {
                doc["document_id"]: [] for doc in documents
            }
            for (document_id, _slot_id, _), hyp in zip(slot_rows, selected):
                effects_by_doc[document_id].append(dict(hyp["effect"]))

            compiled_docs: dict[str, dict[str, Any]] = {}
            specs = []
            for document_id in sorted(effects_by_doc):
                path = "compiled/" + document_id + ".json"
                typed_doc = {
                    "schema": calculus.DOC_SCHEMA,
                    "document_id": document_id,
                    "effects": sorted(
                        effects_by_doc[document_id],
                        key=lambda x: x["effect_id"],
                    ),
                }
                compiled_docs[path] = typed_doc
                specs.append({"path": path, "sha256": _sha(typed_doc)})

            case = {
                "schema": calculus.CASE_SCHEMA,
                "case_id": case_id,
                "documents": specs,
                "query": query,
            }
            try:
                result = calculus.compute(case, compiled_docs)
            except Exception as exc:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED__INVALID_DECLARED_HYPOTHESIS_WORLD",
                    "pass": False,
                    "case_id": case_id,
                    "invalid_world_selection": dict(sorted(selection.items())),
                    "reason": type(exc).__name__ + ":" + str(exc),
                    "semantic_truth_authority": False,
                    "terminal_authority": False,
                }

            outcome_keys = _outcomes(result)
            for key in outcome_keys:
                if key == _canon(_NO_VALUE):
                    union_outcomes[key] = _NO_VALUE
                else:
                    try:
                        union_outcomes[key] = json.loads(key)
                    except Exception:
                        union_outcomes[key] = key

            world_payload = {
                "selection": dict(sorted(selection.items())),
                "outcome_signature": outcome_keys,
                "calculus_status": result.get("status"),
                "effective_value": result.get("effective_value"),
                "surviving_effect_ids": list(result.get("surviving_effect_ids") or []),
            }
            worlds.append({
                "world_id": "WORLD::" + _sha(world_payload)[:24],
                **world_payload,
            })

        worlds.sort(key=lambda x: x["world_id"])
        outcome_keys = sorted(union_outcomes)

        if len(outcome_keys) == 1 and outcome_keys[0] != _canon(_NO_VALUE):
            effective_value = union_outcomes[outcome_keys[0]]
            return {
                "schema": SCHEMA,
                "status": "PASS__EFFECT_AMBIGUITY_TERMINALLY_IRRELEVANT",
                "pass": True,
                "case_id": case_id,
                "world_count": len(worlds),
                "effective_value": effective_value,
                "worlds": worlds,
                "minimum_discriminator_slots": [],
                "hypothesis_set_complete_relative_to_declared_universe": True,
                "does_not_require_unique_effect_interpretation": True,
                "semantic_truth_authority": False,
                "terminal_authority": False,
                "boundary": (
                    "OUTCOME_INVARIANCE_OVER_DECLARED_COMPLETE_FINITE_TYPED_EFFECT_"
                    "HYPOTHESIS_UNIVERSE__NO_RAW_LANGUAGE_HYPOTHESIS_COMPLETENESS_AUTHORITY"
                ),
            }

        minimum_slots = _minimum_discriminator_slots(worlds)
        return {
            "schema": SCHEMA,
            "status": "OPEN__TERMINALLY_RELEVANT_EFFECT_AMBIGUITY",
            "pass": False,
            "case_id": case_id,
            "world_count": len(worlds),
            "possible_outcomes": [union_outcomes[k] for k in outcome_keys],
            "worlds": worlds,
            "minimum_discriminator_slots": minimum_slots,
            "hypothesis_set_complete_relative_to_declared_universe": True,
            "additional_semantic_information_required": True,
            "semantic_truth_authority": False,
            "terminal_authority": False,
            "boundary": (
                "MINIMUM_DISCRIMINATOR_IS_RELATIVE_TO_DECLARED_COMPLETE_FINITE_"
                "TYPED_EFFECT_HYPOTHESIS_UNIVERSE"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
