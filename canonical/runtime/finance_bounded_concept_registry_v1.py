"""Bounded Finance concept registry from explicit source definitions only.

Scope is deliberately narrow:
- source text is exact bytes supplied by the caller;
- every explicit definition in the source must resolve, by exact named-reference
  chaining only, to one canonical role from the already-verified V32 normalized
  Finance source universe;
- no implicit synonymy, ontology inference, pronoun resolution, or world knowledge.

A registry is complete only for the explicit-definition statements in that exact
source. It is not a complete Finance ontology.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.explicit_definition_reference_graph import compile_reference_graph

SCHEMA = "PROJECT_BRAIN_FINANCE_BOUNDED_CONCEPT_REGISTRY_V1"
CLAIM_SCHEMA = "PROJECT_BRAIN_FINANCE_BOUNDED_CONCEPT_IDENTITY_CLAIM_V1"
ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_PATH = "canonical/runtime/r2_finance_normalized_source_universe_direct_adequacy_v1.py"
EXPECTED_AUTHORITY_GIT_BLOB_SHA = "7530b3717eda4429a7903bf5d317384d727b8de7"

ROLES = (
    "RULE",
    "EXCEPTION",
    "ESCALATION",
    "DISCLOSURE",
    "FACT",
    "CROSS_REFERENCE",
    "CONTRADICTION",
    "RECONCILIATION",
)


class ConceptRegistryError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = _canon(value).encode("utf-8")
    return sha256(raw).hexdigest()


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _authority(root: Path) -> dict[str, str]:
    path = (root / AUTHORITY_PATH).resolve(strict=True)
    path.relative_to(root)
    got = _git_blob(path)
    if got != EXPECTED_AUTHORITY_GIT_BLOB_SHA:
        raise ConceptRegistryError("FINANCE_ROLE_AUTHORITY_BLOB_DRIFT:" + got)
    return {"path": AUTHORITY_PATH, "git_blob_sha": got}


def build_registry(
    *,
    source_id: str,
    source_text: str,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    source_id = _norm(source_id)
    if not source_id:
        raise ConceptRegistryError("SOURCE_ID_REQUIRED")
    if not isinstance(source_text, str) or not source_text.strip():
        raise ConceptRegistryError("SOURCE_TEXT_REQUIRED")

    authority = _authority(root)
    graph = compile_reference_graph(source_text)
    if graph.get("status") != "COMPILED":
        raise ConceptRegistryError(
            "EXPLICIT_DEFINITION_GRAPH_NOT_COMPILED:"
            + ",".join(graph.get("errors") or [])
        )
    definitions = graph.get("definitions")
    if not isinstance(definitions, list) or not definitions:
        raise ConceptRegistryError("AT_LEAST_ONE_EXPLICIT_DEFINITION_REQUIRED")

    by_term: dict[str, dict[str, Any]] = {}
    for row in definitions:
        if not isinstance(row, Mapping):
            raise ConceptRegistryError("DEFINITION_ROW_INVALID")
        term = _norm(row.get("term"))
        definition = _norm(row.get("definition"))
        if not term or not definition:
            raise ConceptRegistryError("DEFINITION_TERM_OR_VALUE_EMPTY")
        by_term[term.casefold()] = {
            "term": term,
            "definition": definition,
            "sentence_index": int(row.get("sentence_index", -1)),
        }

    roles = {x.casefold(): x for x in ROLES}
    resolving: set[str] = set()
    resolved: dict[str, str] = {}

    def resolve(term_key: str) -> str:
        if term_key in resolved:
            return resolved[term_key]
        if term_key in resolving:
            raise ConceptRegistryError("DEFINITION_CYCLE:" + term_key)
        resolving.add(term_key)
        row = by_term[term_key]
        target = row["definition"].casefold()
        if target in roles:
            role = roles[target]
        elif target in by_term:
            role = resolve(target)
        else:
            raise ConceptRegistryError(
                "DEFINITION_OUTSIDE_VERIFIED_FINANCE_ROLE_UNIVERSE:"
                + row["term"]
                + "=>"
                + row["definition"]
            )
        resolving.remove(term_key)
        resolved[term_key] = role
        return role

    bindings = []
    for key in sorted(by_term):
        row = by_term[key]
        role = resolve(key)
        binding = {
            "term": row["term"],
            "term_casefold": key,
            "definition": row["definition"],
            "definition_sha256": _sha(row["definition"]),
            "sentence_index": row["sentence_index"],
            "concept_id": "FINANCE_ROLE::" + role,
            "concept_semantics": role,
        }
        binding["binding_sha256"] = _sha(binding)
        bindings.append(binding)

    registry_core = {
        "schema": SCHEMA,
        "scope_id": "finance:explicit-definitions:" + _sha(
            {"source_id": source_id, "source_text_sha256": _sha(source_text)}
        )[:24],
        "source_id": source_id,
        "source_text_sha256": _sha(source_text),
        "authority": authority,
        "canonical_role_universe": list(ROLES),
        "explicit_definition_count": len(bindings),
        "bindings": bindings,
        "scope_completeness": {
            "complete_for": "ALL_EXPLICIT_DEFINITION_STATEMENTS_IN_EXACT_SOURCE",
            "all_explicit_definitions_resolve_to_verified_role_universe": True,
            "open_world_finance_ontology_complete": False,
        },
        "semantic_boundary": (
            "EXACT_EXPLICIT_DEFINITION_CHAIN_TO_VERIFIED_V32_FINANCE_ROLE_ONLY"
        ),
        "model_dependency_count": 0,
        "terminal_authority": False,
    }
    registry = dict(registry_core)
    registry["registry_sha256"] = _sha(registry_core)
    return registry


def make_identity_claim(
    registry: Mapping[str, Any],
    *,
    left_id: str,
    right_id: str,
) -> dict[str, Any]:
    if not isinstance(registry, Mapping) or registry.get("schema") != SCHEMA:
        raise ConceptRegistryError("REGISTRY_SCHEMA_INVALID")
    left = _norm(left_id)
    right = _norm(right_id)
    if not left or not right:
        raise ConceptRegistryError("LEFT_AND_RIGHT_ID_REQUIRED")
    by_term = {
        str(row.get("term_casefold") or ""): row
        for row in registry.get("bindings") or []
        if isinstance(row, Mapping)
    }
    lrow = by_term.get(left.casefold())
    rrow = by_term.get(right.casefold())
    if not isinstance(lrow, Mapping) or not isinstance(rrow, Mapping):
        raise ConceptRegistryError("TERM_NOT_BOUND_IN_REGISTRY")
    if lrow.get("concept_id") != rrow.get("concept_id"):
        raise ConceptRegistryError("TERMS_DO_NOT_SHARE_CONCEPT")
    claim_core = {
        "schema": CLAIM_SCHEMA,
        "scope_id": registry.get("scope_id"),
        "left_id": left,
        "right_id": right,
        "shared_concept_id": lrow.get("concept_id"),
        "source_id": registry.get("source_id"),
        "source_text_sha256": registry.get("source_text_sha256"),
        "registry_sha256": registry.get("registry_sha256"),
        "left_binding_sha256": lrow.get("binding_sha256"),
        "right_binding_sha256": rrow.get("binding_sha256"),
        "authority_git_blob_sha": (
            registry.get("authority") or {}
        ).get("git_blob_sha"),
    }
    claim = dict(claim_core)
    claim["claim_sha256"] = _sha(claim_core)
    return claim
