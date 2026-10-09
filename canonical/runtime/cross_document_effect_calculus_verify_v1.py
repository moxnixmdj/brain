"""Producer-independent verifier for generic cross-document effect composition V1."""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

DOC_SCHEMA = "PROJECT_BRAIN_TYPED_DOCUMENT_EFFECTS_V1"
CASE_SCHEMA = "PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_RESULT_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_VERIFY_V1"
CLASSES = {"DEFINE", "REPLACE", "EXCEPTION", "OVERRIDE"}


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(x: Any) -> str:
    return sha256(_canon(x).encode("utf-8")).hexdigest()


def _date(x: Any) -> date:
    if not isinstance(x, str):
        raise ValueError("DATE_INVALID")
    out = date.fromisoformat(x)
    if out.isoformat() != x:
        raise ValueError("DATE_INVALID")
    return out


def _active(e: Mapping[str, Any], when: date, context: Mapping[str, Any]) -> bool:
    start = e["valid_from"]
    end = e["valid_until"]
    if start is not None and when < _date(start):
        return False
    if end is not None and when >= _date(end):
        return False
    for k, v in e["conditions"].items():
        if k not in context or _canon(context[k]) != _canon(v):
            return False
    return True


def _reachable(graph: Mapping[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    stack = list(graph.get(start, set()))
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, set()))
    return seen


def _recompute(case: Mapping[str, Any], docs: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if case.get("schema") != CASE_SCHEMA or set(case) != {"schema", "case_id", "documents", "query"}:
        raise ValueError("CASE_INVALID")
    if not isinstance(case.get("case_id"), str) or not case["case_id"].strip():
        raise ValueError("CASE_ID_INVALID")

    q = case["query"]
    if not isinstance(q, Mapping) or set(q) != {"target_id", "as_of", "context"}:
        raise ValueError("QUERY_INVALID")
    target = q["target_id"]
    if not isinstance(target, str) or not target.strip():
        raise ValueError("TARGET_INVALID")
    when = _date(q["as_of"])
    context = q["context"]
    if not isinstance(context, Mapping):
        raise ValueError("CONTEXT_INVALID")

    specs = case["documents"]
    if not isinstance(specs, Sequence) or isinstance(specs, (str, bytes)) or not specs:
        raise ValueError("DOCUMENT_SPECS_INVALID")

    effects: dict[str, dict[str, Any]] = {}
    receipts = []
    doc_ids: set[str] = set()
    exact_effect_fields = {
        "effect_id", "target_id", "effect_class", "value", "conditions",
        "valid_from", "valid_until", "supersedes", "source_locator",
    }

    for spec in specs:
        if not isinstance(spec, Mapping) or set(spec) != {"path", "sha256"}:
            raise ValueError("DOCUMENT_SPEC_INVALID")
        path = spec["path"]
        if not isinstance(path, str) or not path or path not in docs:
            raise ValueError("DOCUMENT_PATH_INVALID")
        doc = docs[path]
        if _sha(doc) != spec["sha256"]:
            raise ValueError("DOCUMENT_HASH_MISMATCH")
        if (
            not isinstance(doc, Mapping)
            or doc.get("schema") != DOC_SCHEMA
            or set(doc) != {"schema", "document_id", "effects"}
        ):
            raise ValueError("DOCUMENT_INVALID")
        did = doc["document_id"]
        if not isinstance(did, str) or not did or did in doc_ids:
            raise ValueError("DOCUMENT_ID_INVALID_OR_DUPLICATE")
        doc_ids.add(did)
        rows = doc["effects"]
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
            raise ValueError("EFFECTS_INVALID")

        for raw in rows:
            if not isinstance(raw, Mapping) or set(raw) != exact_effect_fields:
                raise ValueError("EFFECT_INVALID")
            eid = raw["effect_id"]
            tid = raw["target_id"]
            cls = raw["effect_class"]
            if (
                not isinstance(eid, str) or not eid
                or not isinstance(tid, str) or not tid
                or cls not in CLASSES
                or eid in effects
            ):
                raise ValueError("EFFECT_ID_TARGET_OR_CLASS_INVALID")
            cond = raw["conditions"]
            supersedes = raw["supersedes"]
            if not isinstance(cond, Mapping):
                raise ValueError("CONDITIONS_INVALID")
            if (
                not isinstance(supersedes, Sequence)
                or isinstance(supersedes, (str, bytes))
                or any(not isinstance(x, str) or not x for x in supersedes)
                or len(list(supersedes)) != len(set(supersedes))
            ):
                raise ValueError("SUPERSEDES_INVALID")
            if cls != "DEFINE" and not supersedes:
                raise ValueError("NON_DEFINE_WITHOUT_PREDECESSOR")
            vf = raw["valid_from"]
            vu = raw["valid_until"]
            if vf is not None:
                _date(vf)
            if vu is not None:
                _date(vu)
            if vf is not None and vu is not None and _date(vf) >= _date(vu):
                raise ValueError("VALID_INTERVAL_INVALID")
            if not isinstance(raw["source_locator"], str) or not raw["source_locator"]:
                raise ValueError("SOURCE_LOCATOR_INVALID")
            _canon(raw["value"])
            for ck, cv in cond.items():
                if not isinstance(ck, str) or not ck:
                    raise ValueError("CONDITION_KEY_INVALID")
                _canon(cv)

            row = dict(raw)
            row["source_document_id"] = did
            row["source_document_path"] = path
            effects[eid] = row

        receipts.append({
            "path": path,
            "document_id": did,
            "sha256": _sha(doc),
            "effect_count": len(rows),
        })

    graph: dict[str, set[str]] = {eid: set(e["supersedes"]) for eid, e in effects.items()}
    for eid, children in graph.items():
        for child in children:
            if child not in effects:
                raise ValueError("UNKNOWN_SUPERSESSION_TARGET")
            if child == eid:
                raise ValueError("SELF_SUPERSESSION")
            if effects[child]["target_id"] != effects[eid]["target_id"]:
                raise ValueError("CROSS_TARGET_SUPERSESSION")

    for eid in graph:
        if eid in _reachable(graph, eid):
            raise ValueError("SUPERSESSION_CYCLE")

    relevant = [e for e in effects.values() if e["target_id"] == target]
    active = [e for e in relevant if _active(e, when, context)]

    maxima = []
    for e in active:
        eid = e["effect_id"]
        dominated = False
        for other in active:
            oid = other["effect_id"]
            if oid != eid and eid in _reachable(graph, oid):
                dominated = True
                break
        if not dominated:
            maxima.append(e)
    maxima.sort(key=lambda e: e["effect_id"])

    values = {_canon(e["value"]): e["value"] for e in maxima}
    payload = {
        "target_id": target,
        "as_of": when.isoformat(),
        "context": dict(sorted(context.items())),
        "applicable_effect_ids": sorted(e["effect_id"] for e in active),
        "surviving_effect_ids": [e["effect_id"] for e in maxima],
        "surviving_values": sorted(values),
    }

    if not active:
        status = "OPEN__NO_APPLICABLE_EFFECT"
        passed = False
        value = None
        irrelevant = False
    elif len(values) != 1:
        status = "OPEN__INCOMPARABLE_EFFECTS_REQUIRE_DISCRIMINATOR"
        passed = False
        value = None
        irrelevant = False
    else:
        status = "PASS__COMMON_EFFECTIVE_VALUE_COMPOSED"
        passed = True
        value = next(iter(values.values()))
        irrelevant = len(maxima) > 1

    return {
        "schema": RESULT_SCHEMA,
        "case_id": case["case_id"].strip(),
        "target_id": target.strip(),
        "as_of": when.isoformat(),
        "context": dict(sorted(context.items())),
        "document_receipts": sorted(receipts, key=lambda x: x["path"]),
        "relevant_effect_ids": sorted(e["effect_id"] for e in relevant),
        "applicable_effect_ids": sorted(e["effect_id"] for e in active),
        "status": status,
        "pass": passed,
        "effective_value": value,
        "surviving_effect_ids": [e["effect_id"] for e in maxima],
        "decision_ambiguity_irrelevant": irrelevant,
        "composition_sha256": _sha(payload),
    }


def verify(
    case: Mapping[str, Any],
    documents_by_path: Mapping[str, Mapping[str, Any]],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        if not isinstance(result, Mapping) or result.get("schema") != RESULT_SCHEMA:
            raise ValueError("RESULT_SCHEMA_INVALID")
        expected = _recompute(case, documents_by_path)
        for key, value in expected.items():
            if result.get(key) != value:
                errors.append("MISMATCH:" + key)

        allowed_extra = {
            "model_dependency_count",
            "external_world_truth_claimed",
            "semantic_extraction_claimed",
            "terminal_authority",
            "surviving_effects",
            "authority_boundary",
        }
        if result.get("model_dependency_count") != 0:
            errors.append("MODEL_DEPENDENCY_COUNT_NOT_ZERO")
        if result.get("external_world_truth_claimed") is not False:
            errors.append("EXTERNAL_WORLD_TRUTH_CLAIMED")
        if result.get("semantic_extraction_claimed") is not False:
            errors.append("SEMANTIC_EXTRACTION_CLAIMED")
        if result.get("terminal_authority") is not False:
            errors.append("TERMINAL_AUTHORITY_CLAIMED")
        unexpected = set(result) - set(expected) - allowed_extra
        if unexpected:
            errors.append("UNEXPECTED_RESULT_FIELDS:" + ",".join(sorted(unexpected)))
    except Exception as exc:
        errors.append(type(exc).__name__ + ":" + str(exc))

    return {
        "schema": VERIFY_SCHEMA,
        "verified": not errors,
        "status": (
            "PASS__INDEPENDENT_CROSS_DOCUMENT_EFFECT_RECOMPUTATION"
            if not errors
            else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "producer_independent": True,
        "model_dependency_count": 0,
        "terminal_authority": False,
        "boundary": (
            "INDEPENDENT_RECOMPUTATION_OF_TYPED_CONTENT_ADDRESSED_EFFECT_"
            "APPLICABILITY_SUPERSESSION_AND_COMMON_VALUE_ONLY"
        ),
    }
