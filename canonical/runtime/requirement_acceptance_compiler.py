"""Compile normalized requirements into independent acceptance obligations.

This module performs no natural-language interpretation. It consumes already-normalized
requirements with explicit transform_kinds and dependency provenance, then expands them
through the Brain-owned independent_acceptance_model.

Unknown transform kinds fail closed. The output is a pre-verification plan, not a
terminal correctness verdict.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping, Sequence

from canonical.runtime import independent_acceptance_model as iam

SCHEMA = "BRAIN_NORMALIZED_REQUIREMENT_ACCEPTANCE_COMPILER_V1"


def _norm_requirement(row: Mapping[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    rid = row.get("id")
    if not isinstance(rid, str) or not rid.strip():
        return None, ["REQUIREMENT_ID_MISSING"]

    kinds = row.get("transform_kinds")
    if not isinstance(kinds, list) or not kinds or any(not isinstance(x, str) or not x for x in kinds):
        errors.append(f"TRANSFORM_KINDS_MISSING_OR_INVALID:{rid}")
        kinds = []

    unknown = sorted(set(kinds) - set(iam.OBLIGATIONS))
    if unknown:
        errors.append(f"UNKNOWN_TRANSFORM_KINDS:{rid}:" + ",".join(unknown))

    builder_dependencies = row.get("builder_dependencies", [])
    if not isinstance(builder_dependencies, list) or any(not isinstance(x, str) for x in builder_dependencies):
        errors.append(f"BUILDER_DEPENDENCIES_INVALID:{rid}")
        builder_dependencies = []

    explicit_modes = row.get("must_detect_failure_modes", [])
    if not isinstance(explicit_modes, list) or any(not isinstance(x, str) for x in explicit_modes):
        errors.append(f"EXPLICIT_FAILURE_MODES_INVALID:{rid}")
        explicit_modes = []

    if errors:
        return None, errors

    return {
        "id": rid,
        "critical": bool(row.get("critical", True)),
        "transform_kinds": kinds,
        "builder_dependencies": builder_dependencies,
        "must_detect_failure_modes": explicit_modes,
    }, []


def compile_requirements(requirements: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(requirements, Sequence) or isinstance(requirements, (str, bytes)):
        raise ValueError("requirements must be a sequence")

    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    plans: list[dict[str, Any]] = []

    for row in requirements:
        if not isinstance(row, Mapping):
            errors.append("REQUIREMENT_NOT_OBJECT")
            continue
        req, req_errors = _norm_requirement(row)
        errors.extend(req_errors)
        if req is None:
            continue
        if req["id"] in seen:
            errors.append(f"REQUIREMENT_ID_DUPLICATE:{req['id']}")
            continue
        seen.add(req["id"])
        normalized.append(req)

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "plans": [],
        }

    for req in normalized:
        obligations = sorted(iam.generated_obligations(req))
        if req["critical"] and not obligations:
            errors.append(f"CRITICAL_REQUIREMENT_WITHOUT_ACCEPTANCE_OBLIGATIONS:{req['id']}")
            continue
        templates = []
        for mode in obligations:
            template = iam.COUNTEREXAMPLE_TEMPLATES.get(mode)
            if not isinstance(template, str) or not template.strip():
                errors.append(f"COUNTEREXAMPLE_TEMPLATE_MISSING:{req['id']}:{mode}")
                continue
            templates.append({"failure_mode": mode, "template": template})
        plans.append({
            "requirement_id": req["id"],
            "critical": req["critical"],
            "transform_kinds": list(req["transform_kinds"]),
            "required_failure_modes": obligations,
            "counterexample_templates": templates,
            "builder_dependencies": list(req["builder_dependencies"]),
            "independence_rule": (
                "CHECK_MUST_NOT_SHARE_NONRAW_BUILDER_DEPENDENCIES_OR_BUILDER_DERIVED_OUTPUT"
            ),
        })

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "plans": plans,
        }

    return {
        "schema": SCHEMA,
        "status": "COMPILED",
        "requirement_count": len(plans),
        "plans": plans,
        "terminal_authority": False,
        "rule": "NORMALIZED_REQUIREMENT_TO_ACCEPTANCE_CONSEQUENCES_ONLY__NO_SEMANTIC_EXTRACTION_OR_TERMINAL_CORRECTNESS_CREDIT",
    }
