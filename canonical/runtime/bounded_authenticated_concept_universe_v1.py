"""Bounded authenticated concept-universe bridge V1.

This module closes one narrow semantic-control gap: turning an exact finite concept
registry into a complete semantic hypothesis set *relative to that registry* and,
only when an independently bound verifier authenticates registry scope and concept
semantics, handing the resulting worlds to the existing semantic ambiguity
controller.

It does not infer synonyms, word senses, ontology mappings, source authority, or
open-world completeness. Candidate generators may suggest search order elsewhere;
they cannot delete registry concepts or certify identity here.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.semantic_ambiguity_control_v1 import decide as decide_ambiguity

SCHEMA = "PROJECT_BRAIN_BOUNDED_AUTHENTICATED_CONCEPT_UNIVERSE_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_BOUNDED_CONCEPT_REGISTRY_V1"
AUTHORITY_SCHEMA = "PROJECT_BRAIN_BOUNDED_CONCEPT_REGISTRY_AUTHORITY_RECEIPT_V1"

_HEX = set("0123456789abcdef")


class ConceptUniverseError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _norm(value: Any) -> str:
    return " ".join(str(value if value is not None else "").strip().split()).casefold()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(ch in _HEX for ch in text)


def _base(status: str, *, passed: bool, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "candidate_set_complete_relative_to_registry": False,
        "authenticated_scope_completeness": False,
        "hypothesis_set_complete": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _validate_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise ConceptUniverseError("REGISTRY_SCHEMA_INVALID")
    registry_id = str(registry.get("registry_id") or "").strip()
    scope_id = str(registry.get("scope_id") or "").strip()
    if not registry_id:
        raise ConceptUniverseError("REGISTRY_ID_REQUIRED")
    if not scope_id:
        raise ConceptUniverseError("SCOPE_ID_REQUIRED")
    if registry.get("bounded_finite_registry") is not True:
        raise ConceptUniverseError("BOUNDED_FINITE_REGISTRY_ASSERTION_REQUIRED")

    raw_concepts = registry.get("concepts")
    if (
        not isinstance(raw_concepts, Sequence)
        or isinstance(raw_concepts, (str, bytes))
        or not raw_concepts
    ):
        raise ConceptUniverseError("CONCEPTS_REQUIRED")

    concepts: list[dict[str, Any]] = []
    ids: set[str] = set()
    for i, raw in enumerate(raw_concepts):
        if not isinstance(raw, Mapping):
            raise ConceptUniverseError(f"CONCEPT_NOT_OBJECT:{i}")
        cid = str(raw.get("concept_id") or "").strip()
        if not cid:
            raise ConceptUniverseError(f"CONCEPT_ID_REQUIRED:{i}")
        if cid in ids:
            raise ConceptUniverseError("CONCEPT_ID_DUPLICATE:" + cid)
        ids.add(cid)

        surfaces = raw.get("surfaces")
        if (
            not isinstance(surfaces, Sequence)
            or isinstance(surfaces, (str, bytes))
            or not surfaces
        ):
            raise ConceptUniverseError("CONCEPT_SURFACES_REQUIRED:" + cid)
        normalized_surfaces = sorted({_norm(x) for x in surfaces if _norm(x)})
        if not normalized_surfaces:
            raise ConceptUniverseError("CONCEPT_SURFACES_EMPTY:" + cid)

        attrs = raw.get("attributes", {})
        if not isinstance(attrs, Mapping):
            raise ConceptUniverseError("CONCEPT_ATTRIBUTES_INVALID:" + cid)

        signature = raw.get("terminal_signature")
        if raw.get("terminal_signature_complete") is not True:
            raise ConceptUniverseError(
                "TERMINAL_SIGNATURE_COMPLETENESS_UNPROVED:" + cid
            )
        if not isinstance(signature, Mapping):
            raise ConceptUniverseError("TERMINAL_SIGNATURE_INVALID:" + cid)

        concepts.append({
            "concept_id": cid,
            "surfaces": normalized_surfaces,
            "attributes": deepcopy(dict(attrs)),
            "terminal_signature": deepcopy(dict(signature)),
        })

    raw_obs = registry.get("observations", [])
    if not isinstance(raw_obs, Sequence) or isinstance(raw_obs, (str, bytes)):
        raise ConceptUniverseError("OBSERVATIONS_INVALID")
    observations: list[dict[str, Any]] = []
    obs_ids: set[str] = set()
    for i, raw in enumerate(raw_obs):
        if not isinstance(raw, Mapping):
            raise ConceptUniverseError(f"OBSERVATION_NOT_OBJECT:{i}")
        oid = str(raw.get("observation_id") or "").strip()
        if not oid:
            raise ConceptUniverseError(f"OBSERVATION_ID_REQUIRED:{i}")
        if oid in obs_ids:
            raise ConceptUniverseError("OBSERVATION_ID_DUPLICATE:" + oid)
        obs_ids.add(oid)
        outcomes = raw.get("outcomes")
        if (
            raw.get("outcome_map_complete") is not True
            or not isinstance(outcomes, Mapping)
            or set(str(x) for x in outcomes) != ids
        ):
            raise ConceptUniverseError("OBSERVATION_OUTCOME_MAP_INCOMPLETE:" + oid)
        cost = raw.get("cost_units")
        if (
            isinstance(cost, bool)
            or not isinstance(cost, (int, float))
            or float(cost) < 0
        ):
            raise ConceptUniverseError("OBSERVATION_COST_INVALID:" + oid)
        observations.append({
            "observation_id": oid,
            "outcome_map_complete": True,
            "outcomes": {str(k): deepcopy(v) for k, v in outcomes.items()},
            "cost_units": float(cost),
        })

    normalized = {
        "schema": REGISTRY_SCHEMA,
        "registry_id": registry_id,
        "scope_id": scope_id,
        "bounded_finite_registry": True,
        "concepts": concepts,
        "observations": observations,
    }
    return {
        "registry": normalized,
        "registry_sha256": _sha(normalized),
        "concept_ids": sorted(ids),
    }


def _filter_candidates(
    concepts: Sequence[Mapping[str, Any]],
    query: Mapping[str, Any],
) -> list[dict[str, Any]]:
    required = query.get("required_attributes", {})
    if not isinstance(required, Mapping):
        raise ConceptUniverseError("REQUIRED_ATTRIBUTES_INVALID")
    surface = _norm(query.get("surface"))
    exact_surface_only = query.get("exact_surface_only") is True

    rows = []
    for raw in concepts:
        row = deepcopy(dict(raw))
        attrs = row["attributes"]
        if any(attrs.get(k) != v for k, v in required.items()):
            continue
        if exact_surface_only and surface and surface not in row["surfaces"]:
            continue
        rows.append(row)
    return sorted(rows, key=lambda x: x["concept_id"])


def _authenticate(
    *,
    registry_sha256: str,
    registry_id: str,
    scope_id: str,
    authority_receipt: Mapping[str, Any] | None,
    authority_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> dict[str, Any]:
    if authority_receipt is None or authority_verifier is None:
        return {
            "pass": False,
            "status": "AUTHORITY_NOT_BOUND",
            "reason": "AUTHORITY_RECEIPT_AND_VERIFIER_REQUIRED",
        }
    if not isinstance(authority_receipt, Mapping):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "AUTHORITY_RECEIPT_INVALID",
        }
    result = authority_verifier(deepcopy(dict(authority_receipt)))
    if not isinstance(result, Mapping):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "AUTHORITY_VERIFIER_RETURNED_NO_RECEIPT",
        }
    out = deepcopy(dict(result))
    required = {
        "pass": True,
        "schema": AUTHORITY_SCHEMA,
        "registry_sha256": registry_sha256,
        "registry_id": registry_id,
        "scope_id": scope_id,
        "scope_completeness_authenticated": True,
        "concept_semantics_authenticated": True,
        "verification_authority_mutated": False,
    }
    mismatches = [k for k, v in required.items() if out.get(k) != v]
    if not _valid_sha256(out.get("receipt_sha256")):
        mismatches.append("receipt_sha256")
    if mismatches:
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "AUTHORITY_RECEIPT_BINDING_INVALID",
            "mismatch_fields": sorted(set(mismatches)),
            "authority_result": out,
        }
    return out


def resolve(
    registry: Mapping[str, Any],
    query: Mapping[str, Any],
    *,
    ambiguity_owner: str = "SYSTEM_MODEL",
    authority_receipt: Mapping[str, Any] | None = None,
    authority_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Compile a bounded registry to a complete semantic ambiguity problem.

    Exact surface matching is optional. By default an unknown/messy phrase never
    deletes concepts: all registry concepts consistent with explicit typed
    attributes remain candidates. This prevents candidate-generation heuristics
    from silently destroying completeness.
    """
    try:
        if not isinstance(registry, Mapping):
            raise ConceptUniverseError("REGISTRY_REQUIRED")
        if not isinstance(query, Mapping):
            raise ConceptUniverseError("QUERY_REQUIRED")
        checked = _validate_registry(registry)
        normalized = checked["registry"]
        candidates = _filter_candidates(normalized["concepts"], query)
        if not candidates:
            return _base(
                "MODEL_FALSIFIED__NO_CONCEPT_SURVIVES_DECLARED_REGISTRY_CONSTRAINTS",
                passed=False,
                candidate_set_complete_relative_to_registry=True,
                registry_sha256=checked["registry_sha256"],
                registry_id=normalized["registry_id"],
                scope_id=normalized["scope_id"],
                candidate_concept_ids=[],
            )

        auth = _authenticate(
            registry_sha256=checked["registry_sha256"],
            registry_id=normalized["registry_id"],
            scope_id=normalized["scope_id"],
            authority_receipt=authority_receipt,
            authority_verifier=authority_verifier,
        )
        candidate_ids = [x["concept_id"] for x in candidates]
        if auth.get("pass") is not True:
            return _base(
                "OPEN__AUTHENTICATED_REGISTRY_SCOPE_COMPLETENESS_REQUIRED",
                passed=False,
                candidate_set_complete_relative_to_registry=True,
                registry_sha256=checked["registry_sha256"],
                registry_id=normalized["registry_id"],
                scope_id=normalized["scope_id"],
                candidate_concept_ids=candidate_ids,
                authority_result=auth,
                action=(
                    "ACQUIRE_OR_VERIFY_ONLY_THE_REGISTRY_SCOPE_AND_CONCEPT_"
                    "SEMANTICS_AUTHORITY_BINDING"
                ),
            )

        candidate_set = set(candidate_ids)
        worlds = [{
            "world_id": row["concept_id"],
            "terminal_signature_complete": True,
            "terminal_signature": deepcopy(row["terminal_signature"]),
        } for row in candidates]

        observations = []
        for raw in normalized["observations"]:
            outcomes = {
                cid: deepcopy(raw["outcomes"][cid])
                for cid in candidate_ids
            }
            observations.append({
                "observation_id": raw["observation_id"],
                "outcome_map_complete": set(outcomes) == candidate_set,
                "outcomes": outcomes,
                "cost_units": raw["cost_units"],
            })

        ambiguity_problem = {
            "ambiguity_owner": ambiguity_owner,
            "hypothesis_set_complete": True,
            "worlds": worlds,
            "observations": observations,
        }
        decision = decide_ambiguity(ambiguity_problem)
        return _base(
            (
                "PASS__AUTHENTICATED_BOUNDED_CONCEPT_UNIVERSE_COMPILED"
                if decision.get("pass") is True
                else "OPEN__AUTHENTICATED_BOUNDED_CONCEPT_UNIVERSE_NEEDS_DISCRIMINATOR"
            ),
            passed=decision.get("pass") is True,
            candidate_set_complete_relative_to_registry=True,
            authenticated_scope_completeness=True,
            hypothesis_set_complete=True,
            registry_sha256=checked["registry_sha256"],
            registry_id=normalized["registry_id"],
            scope_id=normalized["scope_id"],
            candidate_concept_ids=candidate_ids,
            authority_result=auth,
            ambiguity_problem=ambiguity_problem,
            ambiguity_decision=decision,
            semantic_truth_authority=False,
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            passed=False,
            reason=type(exc).__name__ + ":" + str(exc),
        )
