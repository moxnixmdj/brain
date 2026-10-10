"""Source-traceable semantic intermediate representation for bounded Brain pipelines.

This module does not infer semantics from raw input. It merges already-extracted typed
entities, facts, relations, templates, and ambiguities into one deterministic IR while
preserving provenance and surfacing contradictions instead of guessing.

It is intentionally a narrow S0 integration primitive between source-grounded extractors
and the already-owned typed-hypothesis / decision suffixes.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable, Mapping, Sequence
import json

SCHEMA = "BRAIN_SOURCE_TRACEABLE_SEMANTIC_IR_V1"


def _norm_text(v: Any) -> str:
    return " ".join(str(v if v is not None else "").split())


def _canon_value(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _require_source(row: Mapping[str, Any], kind: str, idx: int) -> dict[str, Any]:
    src = row.get("source")
    if not isinstance(src, Mapping):
        raise ValueError(f"{kind}[{idx}] missing source object")
    out = dict(src)
    if not any(k in out for k in ("span", "observation_id", "path", "artifact", "uri")):
        raise ValueError(f"{kind}[{idx}] source lacks traceable locator")
    return out


def _stable_rows(rows: Sequence[Mapping[str, Any]], *, kind: str) -> list[dict[str, Any]]:
    out = []
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"{kind}[{i}] must be object")
        d = dict(row)
        d["source"] = _require_source(row, kind, i)
        out.append(d)
    return sorted(out, key=lambda x: _canon_value(x))


def compile_semantic_ir(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Compile source-grounded semantic fragments into a deterministic IR.

    Expected optional arrays: entities, facts, relations, templates, ambiguities.
    Facts use {subject, predicate, object, source}. Contradictory facts with the same
    (subject,predicate) key are preserved and emitted as explicit conflicts.
    """
    if not isinstance(contract, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["CONTRACT_NOT_OBJECT"]}

    try:
        entities = _stable_rows(contract.get("entities", []), kind="entities")
        facts = _stable_rows(contract.get("facts", []), kind="facts")
        relations = _stable_rows(contract.get("relations", []), kind="relations")
        templates = _stable_rows(contract.get("templates", []), kind="templates")
        ambiguities = _stable_rows(contract.get("ambiguities", []), kind="ambiguities")

        entity_ids: set[str] = set()
        for i, e in enumerate(entities):
            eid = _norm_text(e.get("id"))
            etype = _norm_text(e.get("type"))
            if not eid or not etype:
                raise ValueError(f"entities[{i}] requires nonempty id and type")
            if eid in entity_ids:
                raise ValueError(f"duplicate entity id: {eid}")
            entity_ids.add(eid)
            e["id"] = eid
            e["type"] = etype

        fact_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for i, f in enumerate(facts):
            s = _norm_text(f.get("subject"))
            p = _norm_text(f.get("predicate"))
            if not s or not p or "object" not in f:
                raise ValueError(f"facts[{i}] requires subject, predicate, object")
            if entity_ids and s not in entity_ids:
                raise ValueError(f"facts[{i}] unknown subject entity: {s}")
            f["subject"] = s
            f["predicate"] = p
            fact_groups.setdefault((s, p), []).append(f)

        conflicts = []
        resolved_facts = []
        for (s, p), group in sorted(fact_groups.items()):
            by_value: dict[str, list[dict[str, Any]]] = {}
            for f in group:
                by_value.setdefault(_canon_value(f["object"]), []).append(f)
            if len(by_value) == 1:
                # Preserve all support sources while collapsing duplicate semantic value.
                exemplar = dict(group[0])
                exemplar["sources"] = sorted(
                    [g["source"] for g in group], key=_canon_value
                )
                exemplar.pop("source", None)
                resolved_facts.append(exemplar)
            else:
                conflicts.append({
                    "subject": s,
                    "predicate": p,
                    "alternatives": [
                        {
                            "object": rows[0]["object"],
                            "sources": sorted([r["source"] for r in rows], key=_canon_value),
                        }
                        for _, rows in sorted(by_value.items())
                    ],
                    "status": "UNKNOWN_CONFLICT",
                })

        status = "COMPILED_WITH_UNKNOWNS" if conflicts or ambiguities else "COMPILED"
        return {
            "schema": SCHEMA,
            "status": status,
            "entities": entities,
            "facts": sorted(resolved_facts, key=_canon_value),
            "relations": relations,
            "templates": templates,
            "ambiguities": ambiguities,
            "conflicts": conflicts,
            "terminal_authority": False,
            "scope": "DETERMINISTIC_MERGE_OF_ALREADY_EXTRACTED_SOURCE_TRACEABLE_TYPED_SEMANTIC_FRAGMENTS",
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [f"{type(exc).__name__}:{exc}"],
            "terminal_authority": False,
        }
