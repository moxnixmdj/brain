"""Objective currentness verifier for pure field-projection capsules.

This verifier answers one narrow question:
  Does current authority project to the exact same semantic capsule that an
  already verified zero-reality result consumed?

It does not verify the result itself and never grants execution, promotion,
acceptance, capability, ownership, fresh-reality, or terminal authority.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.pure_field_projection_capsule_v1 import (
    SCHEMA as CAPSULE_SCHEMA,
    compile_capsule,
)

SCHEMA = "PROJECT_BRAIN_PURE_FIELD_PROJECTION_CURRENTNESS_V1"
CAPSULE_STATUS = "PASS__PURE_FIELD_PROJECTION_SEMANTIC_CAPSULE"


class PureFieldProjectionCurrentnessError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validate_frozen_capsule(capsule: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(capsule, Mapping):
        raise PureFieldProjectionCurrentnessError("FROZEN_CAPSULE_REQUIRED")
    if capsule.get("schema") != CAPSULE_SCHEMA:
        raise PureFieldProjectionCurrentnessError("FROZEN_CAPSULE_SCHEMA_INVALID")
    if capsule.get("pass") is not True or capsule.get("status") != CAPSULE_STATUS:
        raise PureFieldProjectionCurrentnessError("FROZEN_CAPSULE_NOT_PASS")

    sources = capsule.get("selected_sources")
    if not isinstance(sources, list) or not sources:
        raise PureFieldProjectionCurrentnessError("FROZEN_SELECTED_SOURCES_REQUIRED")
    normalized_scope: dict[str, list[str]] = {}
    normalized_sources = []
    for row in sources:
        if not isinstance(row, Mapping):
            raise PureFieldProjectionCurrentnessError("FROZEN_SOURCE_ROW_INVALID")
        path = row.get("source_path")
        deps = row.get("dependencies")
        manifest_sha = row.get("manifest_sha256")
        projection_sha = row.get("projection_sha256")
        if not isinstance(path, str) or not path or path in normalized_scope:
            raise PureFieldProjectionCurrentnessError("FROZEN_SOURCE_PATH_INVALID")
        if not isinstance(deps, list) or not deps:
            raise PureFieldProjectionCurrentnessError(
                "FROZEN_SOURCE_DEPENDENCIES_INVALID:" + path
            )
        pointers = []
        norm_deps = []
        for dep in deps:
            if not isinstance(dep, Mapping):
                raise PureFieldProjectionCurrentnessError(
                    "FROZEN_DEPENDENCY_ROW_INVALID:" + path
                )
            pointer = dep.get("pointer")
            value_sha = dep.get("value_sha256")
            if (
                not isinstance(pointer, str)
                or not isinstance(value_sha, str)
                or len(value_sha) != 64
            ):
                raise PureFieldProjectionCurrentnessError(
                    "FROZEN_DEPENDENCY_BINDING_INVALID:" + path
                )
            pointers.append(pointer)
            norm_deps.append(
                {"pointer": pointer, "value_sha256": value_sha}
            )
        if len(pointers) != len(set(pointers)):
            raise PureFieldProjectionCurrentnessError(
                "FROZEN_DEPENDENCY_POINTER_DUPLICATE:" + path
            )
        if (
            not isinstance(manifest_sha, str)
            or len(manifest_sha) != 64
            or not isinstance(projection_sha, str)
            or len(projection_sha) != 64
        ):
            raise PureFieldProjectionCurrentnessError(
                "FROZEN_SOURCE_HASH_INVALID:" + path
            )
        normalized_scope[path] = sorted(pointers)
        normalized_sources.append(
            {
                "source_path": path,
                "manifest_sha256": manifest_sha,
                "projection_sha256": projection_sha,
                "dependencies": norm_deps,
            }
        )

    consumer_source_sha = capsule.get("consumer_source_sha256")
    consumer_result_sha = capsule.get("consumer_result_sha256")
    projection_bundle_sha = capsule.get("projection_bundle_sha256")
    result = capsule.get("consumer_result")
    for label, digest in (
        ("CONSUMER_SOURCE", consumer_source_sha),
        ("CONSUMER_RESULT", consumer_result_sha),
        ("PROJECTION_BUNDLE", projection_bundle_sha),
    ):
        if not isinstance(digest, str) or len(digest) != 64:
            raise PureFieldProjectionCurrentnessError(
                "FROZEN_" + label + "_SHA256_INVALID"
            )
    if not isinstance(result, Mapping):
        raise PureFieldProjectionCurrentnessError(
            "FROZEN_CONSUMER_RESULT_NOT_MAPPING"
        )
    if _sha256(_canon(dict(result))) != consumer_result_sha:
        raise PureFieldProjectionCurrentnessError(
            "FROZEN_CONSUMER_RESULT_SHA256_MISMATCH"
        )

    semantic_core = {
        "schema": CAPSULE_SCHEMA,
        "projection_bundle_sha256": projection_bundle_sha,
        "consumer_source_sha256": consumer_source_sha,
        "consumer_result_sha256": consumer_result_sha,
        "selected_sources": normalized_sources,
        "consumer_result": dict(result),
    }
    identity = capsule.get("semantic_identity_sha256")
    if (
        not isinstance(identity, str)
        or len(identity) != 64
        or identity != _sha256(_canon(semantic_core))
    ):
        raise PureFieldProjectionCurrentnessError(
            "FROZEN_SEMANTIC_IDENTITY_INVALID"
        )
    return {
        "semantic_identity_sha256": identity,
        "consumer_source_sha256": consumer_source_sha,
        "scope": dict(sorted(normalized_scope.items())),
    }


def _normalize_scope(
    field_dependencies: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    if not isinstance(field_dependencies, Mapping) or not field_dependencies:
        raise PureFieldProjectionCurrentnessError("FIELD_DEPENDENCIES_REQUIRED")
    out: dict[str, list[str]] = {}
    for raw_path, raw_pointers in field_dependencies.items():
        path = str(raw_path)
        if (
            not path
            or not isinstance(raw_pointers, Sequence)
            or isinstance(raw_pointers, (str, bytes))
        ):
            raise PureFieldProjectionCurrentnessError(
                "FIELD_DEPENDENCY_SCOPE_INVALID:" + path
            )
        pointers = [str(x) for x in raw_pointers]
        if not pointers or len(pointers) != len(set(pointers)):
            raise PureFieldProjectionCurrentnessError(
                "FIELD_DEPENDENCY_POINTER_SET_INVALID:" + path
            )
        out[path] = sorted(pointers)
    return dict(sorted(out.items()))


def verify_currentness(
    *,
    frozen_capsule: Mapping[str, Any],
    current_source_documents: Mapping[str, Mapping[str, Any]],
    field_dependencies: Mapping[str, Sequence[str]],
    consumer_source: str,
) -> dict[str, Any]:
    try:
        frozen = _validate_frozen_capsule(frozen_capsule)
        current_scope = _normalize_scope(field_dependencies)
        if current_scope != frozen["scope"]:
            raise PureFieldProjectionCurrentnessError(
                "FIELD_DEPENDENCY_SCOPE_CHANGED"
            )

        current = compile_capsule(
            source_documents=current_source_documents,
            field_dependencies=field_dependencies,
            consumer_source=consumer_source,
        )
        if current.get("pass") is not True:
            raise PureFieldProjectionCurrentnessError(
                "CURRENT_CAPSULE_RECOMPUTE_FAILED:"
                + str(current.get("error") or "")
            )
        if current.get("consumer_source_sha256") != frozen["consumer_source_sha256"]:
            raise PureFieldProjectionCurrentnessError(
                "PURE_CONSUMER_SOURCE_CHANGED"
            )

        current_identity = current["semantic_identity_sha256"]
        same = current_identity == frozen["semantic_identity_sha256"]
        return {
            "schema": SCHEMA,
            "pass": same,
            "status": (
                "PASS__PURE_FIELD_PROJECTION_SEMANTIC_IDENTITY_CURRENT"
                if same
                else "FAIL_CLOSED__PURE_FIELD_PROJECTION_SEMANTIC_DRIFT"
            ),
            "frozen_semantic_identity_sha256": frozen["semantic_identity_sha256"],
            "current_semantic_identity_sha256": current_identity,
            "field_dependency_scope": current_scope,
            "pure_consumer_source_unchanged": True,
            "semantic_identity_current": same,
            "prior_independent_verification_binding_required": True,
            "verification_reuse_authority_granted_by_this_module": False,
            "scheduler_replan_required_on_global_epoch_drift": True,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
            "rule": (
                "UNCHANGED_PURE_FIELD_CAPSULE_IDENTITY_PROVES_ONLY_CURRENT_"
                "SEMANTIC_INPUT_EQUIVALENCE__PRIOR_INDEPENDENT_VERIFICATION_"
                "AND_LIVE_SCHEDULER_AUTHORITY_REMAIN_SEPARATE_REQUIREMENTS"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "error": type(exc).__name__ + ":" + str(exc),
            "verification_reuse_authority_granted_by_this_module": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
