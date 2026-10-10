"""Fail-closed dependency closure for professional-quality same-subject binding.

Classifies every content-addressed dependency exposed by the scoped evidence
registry as either a declared-system component or an external evidence input.
It also tracks the dynamic, claim-instance inputs required by each root.

This module grants no root, quality, acceptance, promotion, or terminal credit.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_SUBJECT_DEPENDENCY_CLOSURE_VERIFY_V1"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = "canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"
SUBJECT_PATH = "canonical/governance/PROFESSIONAL_QUALITY_P1_V4_DECLARED_SYSTEM_SUBJECT_20261010_V3.json"
WORKLIST_PATH = "canonical/governance/PROFESSIONAL_QUALITY_P1_V4_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V3.json"

ROOTS = (
    "R1_TARGET_SPECIFICATION",
    "R2_CANDIDATE_SEARCH",
    "R3_REALIZATION_OBSERVATION",
    "R4_MEASUREMENT_CONSTRUCT",
    "R5_EVALUATOR_REFERENCE",
    "R6_EVIDENCE_GROUNDING_DEPENDENCE",
    "R7_CAUSAL_PRESCRIPTIVE",
    "R8_POPULATION_CONTEXT_OPERATOR",
    "R9_TEMPORAL_DEPLOYMENT",
    "R10_ANALYSIS_DECISION",
    "R11_ADAPTIVE_INTEGRITY_SECURITY",
    "R12_META_COMPOSITION_CLOSURE",
)

SUBJECT_REF_FIELDS = frozenset({
    "reusable_compiler",
    "measurement_runtime",
    "minimax_runtime",
    "registry_extension_runtime",
    "dynamic_extension_runtime",
    "contract_registry",
    "contract_schema",
})
EXTERNAL_REF_FIELDS = frozenset({
    "source_receipt",
    "compiler_verification",
    "scope_governance",
})

# Dynamic dependencies are the non-static objects named by the root worklist.
# They are claim-instance evidence/configuration, not reusable system bytes.
DYNAMIC_EXTERNAL_INPUTS = {
    "R1_TARGET_SPECIFICATION": (
        "EXACT_TARGET_INSTANCE_AND_AUTHENTICATED_GOAL_TO_DECISION_BINDING",
    ),
    "R2_CANDIDATE_SEARCH": (
        "EXACT_CANDIDATE_UNIVERSE_OR_GENERATOR_OUTPUT_AND_SCOPE_COMPLETENESS_EVIDENCE",
    ),
    "R3_REALIZATION_OBSERVATION": (
        "EXACT_ARTIFACT_BYTES_DELIVERY_ENVIRONMENT_AND_AUDIENCE_VIEW_OBSERVATION",
    ),
    "R4_MEASUREMENT_CONSTRUCT": (
        "EXACT_CRITERION_ONTOLOGY_SCALE_ACCEPTANCE_FLOORS_AND_MEASUREMENT_INPUTS",
    ),
    "R5_EVALUATOR_REFERENCE": (
        "EXACT_JUDGE_OR_REFERENCE_SET_AND_LOCAL_QUALIFICATION_DISAGREEMENT_EVIDENCE",
    ),
    "R6_EVIDENCE_GROUNDING_DEPENDENCE": (
        "ALL_LOAD_BEARING_TYPED_EVIDENCE_WITH_PROVENANCE_GROUNDING_INDEPENDENCE_FRESHNESS_AND_UNCERTAINTY",
    ),
    "R7_CAUSAL_PRESCRIPTIVE": (
        "EXACT_INTERVENTION_INSTANCE_PRE_POST_ARTIFACTS_AND_POST_EDIT_OUTCOME_EVIDENCE",
    ),
    "R8_POPULATION_CONTEXT_OPERATOR": (
        "TARGET_CONSTITUENCY_OPERATOR_CONTEXT_DEPLOYMENT_ENVELOPE_AND_TRANSPORT_EVIDENCE",
    ),
    "R9_TEMPORAL_DEPLOYMENT": (
        "TIME_HORIZON_DRIFT_CENSORING_DELAYED_OUTCOME_RARE_EVENT_AND_TRANSPORT_EVIDENCE",
    ),
    "R10_ANALYSIS_DECISION": (
        "EXACT_AGGREGATION_THRESHOLD_COMPENSATION_RISK_POLICY_AND_DECISION_RELEVANT_FACTS",
    ),
    "R11_ADAPTIVE_INTEGRITY_SECURITY": (
        "CLEAN_DEV_SELECTION_CERTIFICATION_LANE_HOLDOUT_STATE_EXPOSURE_LEDGER_AND_EVALUATOR_CONTROL_EVIDENCE",
    ),
    "R12_META_COMPOSITION_CLOSURE": (
        "ALL_ROOT_BINDINGS_ASSUMPTION_GUARANTEE_GRAPH_DEFEATER_SET_AND_CHALLENGE_COVERAGE_EVIDENCE",
    ),
}


class DependencyClosureError(ValueError):
    pass


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _resolve(root: Path, raw: Any) -> Path:
    if not isinstance(raw, str) or not raw.startswith("canonical/"):
        raise DependencyClosureError("PATH_INVALID")
    p = (root / raw).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError as exc:
        raise DependencyClosureError("PATH_ESCAPES_REPO") from exc
    return p


def _read_json(root: Path, raw: str) -> dict[str, Any]:
    p = _resolve(root, raw)
    if not p.is_file() or p.is_symlink():
        raise DependencyClosureError("FILE_INVALID:" + raw)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DependencyClosureError("JSON_INVALID:" + raw) from exc
    if not isinstance(doc, dict):
        raise DependencyClosureError("DOCUMENT_INVALID:" + raw)
    return doc


def _content_ref(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, Mapping):
        return None
    if "path" not in value and "git_blob_sha" not in value:
        return None
    path = value.get("path")
    sha = value.get("git_blob_sha")
    if not isinstance(path, str) or not isinstance(sha, str) or len(sha) != 40:
        raise DependencyClosureError("CONTENT_REFERENCE_INVALID")
    return path, sha


def classify_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise DependencyClosureError("REGISTRY_ENTRIES_INVALID")

    by_root = {
        root: {
            "root_id": root,
            "subject_components": [],
            "external_evidence_references": [],
            "dynamic_external_inputs": list(DYNAMIC_EXTERNAL_INPUTS[root]),
        }
        for root in ROOTS
    }
    observed_roots: set[str] = set()
    subject_refs: dict[str, str] = {}
    external_refs: dict[str, str] = {}

    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise DependencyClosureError(f"ENTRY_INVALID:{index}")
        root_id = entry.get("root_id")
        if root_id not in by_root:
            raise DependencyClosureError(f"ROOT_INVALID:{root_id}")
        observed_roots.add(str(root_id))
        scope_id = entry.get("scope_id")
        if not isinstance(scope_id, str) or not scope_id:
            raise DependencyClosureError(f"SCOPE_ID_INVALID:{index}")

        for key, value in entry.items():
            ref = _content_ref(value)
            if ref is None:
                continue
            path, sha = ref
            record = {
                "scope_id": scope_id,
                "field": key,
                "path": path,
                "git_blob_sha": sha,
            }
            if key in SUBJECT_REF_FIELDS:
                prior = subject_refs.setdefault(path, sha)
                if prior != sha:
                    raise DependencyClosureError("SUBJECT_COMPONENT_HASH_CONFLICT:" + path)
                by_root[root_id]["subject_components"].append(record)
            elif key in EXTERNAL_REF_FIELDS:
                prior = external_refs.setdefault(path, sha)
                if prior != sha:
                    raise DependencyClosureError("EXTERNAL_REFERENCE_HASH_CONFLICT:" + path)
                by_root[root_id]["external_evidence_references"].append(record)
            else:
                raise DependencyClosureError(f"UNCLASSIFIED_CONTENT_REFERENCE_FIELD:{key}")

    if observed_roots != set(ROOTS):
        missing = sorted(set(ROOTS) - observed_roots)
        raise DependencyClosureError("ROOT_COVERAGE_INCOMPLETE:" + ",".join(missing))

    overlap = sorted(set(subject_refs) & set(external_refs))
    if overlap:
        raise DependencyClosureError("SUBJECT_EXTERNAL_ROLE_COLLISION:" + ",".join(overlap))

    for root_id, row in by_root.items():
        if not row["subject_components"]:
            raise DependencyClosureError("ROOT_SUBJECT_COMPONENT_SET_EMPTY:" + root_id)
        if not row["external_evidence_references"]:
            raise DependencyClosureError("ROOT_EXTERNAL_REFERENCE_SET_EMPTY:" + root_id)
        row["subject_components"].sort(key=lambda x: (x["path"], x["field"], x["scope_id"]))
        row["external_evidence_references"].sort(key=lambda x: (x["path"], x["field"], x["scope_id"]))

    return {
        "root_count": len(ROOTS),
        "classified_root_count": len(by_root),
        "roots": [by_root[root] for root in ROOTS],
        "required_subject_components": [
            {"path": path, "git_blob_sha": subject_refs[path]}
            for path in sorted(subject_refs)
        ],
        "external_evidence_references": [
            {"path": path, "git_blob_sha": external_refs[path]}
            for path in sorted(external_refs)
        ],
        "dynamic_external_inputs_by_root": {
            root: list(DYNAMIC_EXTERNAL_INPUTS[root]) for root in ROOTS
        },
    }


def verify_current(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    try:
        registry = _read_json(root, REGISTRY_PATH)
        subject = _read_json(root, SUBJECT_PATH)
        worklist = _read_json(root, WORKLIST_PATH)
        classified = classify_registry(registry)

        # Verify every referenced static dependency is current on disk.
        for bucket in ("required_subject_components", "external_evidence_references"):
            for ref in classified[bucket]:
                p = _resolve(root, ref["path"])
                if not p.is_file() or p.is_symlink():
                    raise DependencyClosureError("DEPENDENCY_FILE_INVALID:" + ref["path"])
                actual = _blob(p)
                if actual != ref["git_blob_sha"]:
                    raise DependencyClosureError("DEPENDENCY_BLOB_STALE:" + ref["path"])

        material = (subject.get("system_material") or {}).get("components")
        if not isinstance(material, list):
            raise DependencyClosureError("SUBJECT_COMPONENTS_INVALID")
        current = {
            x.get("path"): x.get("git_blob_sha")
            for x in material
            if isinstance(x, Mapping) and isinstance(x.get("path"), str)
        }
        required = {
            x["path"]: x["git_blob_sha"]
            for x in classified["required_subject_components"]
        }
        missing = [
            {"path": path, "git_blob_sha": sha}
            for path, sha in sorted(required.items())
            if current.get(path) != sha
        ]

        roots = worklist.get("roots")
        if not isinstance(roots, list) or {
            x.get("root_id") for x in roots if isinstance(x, Mapping)
        } != set(ROOTS):
            raise DependencyClosureError("WORKLIST_ROOT_SET_DRIFT")

        return {
            "schema": SCHEMA,
            "status": "PASS__SUBJECT_DEPENDENCY_CLASSIFICATION_COMPLETE",
            "pass": True,
            "dependency_classification_complete": True,
            "classified_root_count": classified["classified_root_count"],
            "required_subject_component_count": len(classified["required_subject_components"]),
            "external_evidence_reference_count": len(classified["external_evidence_references"]),
            "dynamic_external_input_root_count": len(classified["dynamic_external_inputs_by_root"]),
            "current_subject_component_count": len(current),
            "missing_required_subject_components": missing,
            "subject_refresh_required": bool(missing),
            "classification": deepcopy(classified),
            "root_subject_binding_authority": False,
            "quality_authority": False,
            "acceptance_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }
    except DependencyClosureError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SUBJECT_DEPENDENCY_CLASSIFICATION_INVALID",
            "pass": False,
            "reason": str(exc),
            "dependency_classification_complete": False,
            "root_subject_binding_authority": False,
            "quality_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }


if __name__ == "__main__":
    print(json.dumps(verify_current(), indent=2, sort_keys=True))
